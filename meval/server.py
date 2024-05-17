import time

from .imports import *

import sys, os, signal, psutil
import subprocess
import requests, json
import socket
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from contextlib import redirect_stdout, redirect_stderr

from .abstract import AbstractTask, AbstractEnvironment
from .tasks import start_task, Environment
from .resources import resource_snapshot, gpu_snapshot
from .util import remove_ansi_escape_sequences


@fig.component('cluster-env')
class ClusterEnvironment(Environment):
	def __init__(self, job_id: str = os.environ.get('JOB_ID', None), job_name: str = os.environ.get('JOB_NAME', None),
				 **kwargs):
		if job_id is not None:
			terms = job_id.split('#')
			if len(terms) > 1:
				job_id = terms[1]
			else:
				job_id = None
		if job_id is not None:
			super().__init__(ident=job_id, **kwargs)
		else:
			super().__init__(**kwargs)
		self.job_id = job_id
		self.job_name = job_name


	def report_launch(self, info: dict, **details: JSONABLE):
		details['name'] = self.job_name
		return super().report_launch(info, **details)



@fig.component('local-env')
class LocalEnvironment(Environment):
	def wrap_command(self, cmd: str) -> str:
		return (f'PATH=/home/fleeb/.cargo/bin:$PATH; source $CONDA_PREFIX/etc/profile.d/conda.sh; conda activate llm; '
				f'{cmd}')



@fig.component('tgi-server')
class InferenceServer(AbstractTask, fig.Configurable):
	# region init
	def __init__(self,
				 task_command: str,
				 port: Union[str, int] = 3000,
				 allow_stdout: bool = True,

				 model_id: str = None, # 'bigscience/bloom-560m'

				 sharded: bool = None,
				 num_shard: int = None,

				 quantize: str = None,
				 speculate: int = None,

				 dtype: str = None, # 'bfloat16', 'float16'
				 trust_remote_code: bool = False,

				 max_concurrent_requests: int = None,
				 max_best_of: int = None,
				 max_stop_sequences: int = None,
				 max_top_n_tokens: int = None,
				 max_input_length: int = None,
				 max_total_tokens: int = None,

				 waiting_served_ratio: float = None, # 0.3

				 max_batch_total_tokens: int = None,

				 **kwargs):
		if max_total_tokens is not None and max_input_length is None:
			max_input_length = max_total_tokens - 1
		super().__init__(**kwargs)
		self._process = None
		self._exit_reason = None
		self._command_base = task_command
		if '{port}' not in task_command:
			raise ValueError('WARNING: command does not contain {port} placeholder')
		self.workspace = None
		self._port = port
		self._allow_stdout = allow_stdout
		self._core_command = None
		server_args = {}
		if model_id is not None:
			server_args['model-id'] = model_id
		if sharded is not None:
			server_args['sharded'] = sharded
		if num_shard is not None:
			server_args['num-shard'] = num_shard
		if quantize is not None:
			server_args['quantize'] = quantize
		if speculate is not None:
			server_args['speculate'] = speculate
		if dtype is not None:
			server_args['dtype'] = dtype
		if trust_remote_code is not None:
			server_args['trust-remote-code'] = trust_remote_code
		if max_concurrent_requests is not None:
			server_args['max-concurrent-requests'] = max_concurrent_requests
		if max_best_of is not None:
			server_args['max-best-of'] = max_best_of
		if max_stop_sequences is not None:
			server_args['max-stop-sequences'] = max_stop_sequences
		if max_top_n_tokens is not None:
			server_args['max-top-n-tokens'] = max_top_n_tokens
		if max_input_length is not None:
			server_args['max-input-length'] = max_input_length
		if max_total_tokens is not None:
			server_args['max-total-tokens'] = max_total_tokens
		if waiting_served_ratio is not None:
			server_args['waiting-served-ratio'] = waiting_served_ratio
		if max_batch_total_tokens is not None:
			server_args['max-batch-total-tokens'] = max_batch_total_tokens
		self._server_args = server_args

	@property
	def category(self):
		return 'server'

	# endregion

	def prepare(self, env: Environment) -> None:
		super().prepare(env)
		self.env = env
		self.workspace = env.workspace
		if isinstance(env, ClusterEnvironment) and 'max-input-tokens' in self._server_args:
			self._server_args['max-input-length'] = self._server_args.pop('max-input-tokens')

	def _build_command(self):
		args = ' '.join([f'--{k}' if v is True else f'--{k} {v}' for k, v in self._server_args.items()
					if v is not None and v is not False])
		cmd = f'{self._command_base.format(port=self._port)} {args}'
		return self.env.wrap_command(cmd)

	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		'''non blocking, returns the process id of the launched process'''
		assert self._process is None, f'already launched'
		cmd = self._build_command()

		assert self.workspace is not None, f'workspace not set (have you called `prepare()`?)'
		self._logfile = self.workspace / 'server.log'
		self._logfile.touch()
		self._msgfile = self.workspace / '.server.message'
		self._msgfile.touch()

		self._report = report
		self._shard_load_info = {}
		self.observer = Observer()
		self.observer.schedule(self._Monitor(str(self._msgfile), self._handle_cmd), self._msgfile.parent, recursive=False)
		self.observer.schedule(self._Monitor(str(self._logfile), self._handle_log), self._logfile.parent, recursive=False)
		self.observer.start()

		self._process = subprocess.Popen(cmd, shell=True, text=True, executable="/bin/bash", env=os.environ.copy(),
										 stdout=self._logfile.open('a'), stderr=self._logfile.open('a'))
		server_info = {
			'model_id': self._server_args.get('model-id', 'bigscience/bloom-560m'),
			'model_dtype': self._server_args.get('model-dtype', 'torch.float16'),
		}
		return {'pid': self._process.pid,
				# 'msg': str(self._msgfile), 'log': str(self._logfile),
				'port': self._port,
				'server': server_info, 'snapshot': self._get_resource_snapshot()}


	class _Monitor(FileSystemEventHandler):
		def __init__(self, path: str, callback: Callable[[str], None], pos: int = None):
			if pos is None:
				pos = open(path, 'r').tell()
			self.path = path
			self.callback = callback
			self.pos = pos

		def on_modified(self, event):
			if event.src_path == self.path:
				with open(self.path, 'r') as f:
					f.seek(self.pos)
					message = f.read()
					self.pos = f.tell()
				self.callback(message)


	def _handle_cmd(self, message: str):
		if message.strip().startswith('exit'):
			self._exit_reason = message.strip()
			self._terminate()
			print(f'Received message to exit: {self._exit_reason!r}')
		else:
			raise NotImplementedError(f'Unknown command: {message!r}')


	def _handle_log(self, message: str):
		if self._allow_stdout:
			sys.stdout.write(message)

		for line in message.splitlines():

			if 'Shard ready in ' in line:

				*tm, r = line.split('Shard ready in ')[1].split()
				rank = remove_ansi_escape_sequences(r.split('=')[1])

				dt = ' '.join(tm)
				if ' ' not in dt:
					dt = float(dt[:-1])
				self._shard_load_info[rank] = dt

			elif line.endswith('Connected'):
				info = self._get_server_info()
				self._report('connected', {'shards': self._shard_load_info,
										   'snapshot': self._get_resource_snapshot(),
										   'server': info,
										   'url': self._get_server_url(),
										   })


	def _get_server_url(self):
		return f'http://{socket.gethostname()}:{self._port}'


	def _get_server_info(self):
		time.sleep(1) # to avoid timing issues
		return requests.get(f'{self._get_server_url()}/info').json()


	def _get_resource_snapshot(self):
		return gpu_snapshot()


	def _terminate(self):
		if self._process is not None:
			pid = self._process.pid
			try:
				parent = psutil.Process(pid)
			except psutil.NoSuchProcess:
				return
			else:
				for child in parent.children(recursive=True):
					child.kill()
				self._process.kill()
				self._process.wait()


	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		'''blocking, use the reporter to report actionable events, return with exit code if one is received'''
		self._process.wait()
		self.observer.stop()
		self.observer.join()
		exit_info = {'code': self._process.returncode}
		if self._exit_reason is not None:
			exit_info['reason'] = 'message'
			exit_info['message'] = self._exit_reason
		return exit_info


	def handle(self, exception: Exception, report: Callable[[str, JSONOBJ], None]) -> Optional[JSONOBJ]:
		'''blocking'''
		self._terminate()
		self.observer.stop()
		self.observer.join()
		return super().handle(exception, report)



@fig.script('serve')
def start_server(cfg: fig.Configuration):
	cfg.push('server._type', 'tgi-server', silent=True, overwrite=False)
	return start_task(cfg, task_key='server')




