import time

from .imports import *

import sys, os
import subprocess
import socket
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from contextlib import redirect_stdout, redirect_stderr

from .abstract import AbstractTask, AbstractEnvironment
from .tasks import start_task, Environment



@fig.component('cluster-env')
class ClusterEnvironment(Environment):
	def __init__(self, job_id: str = os.environ.get('JOB_ID', None), job_name: str = os.environ.get('JOB_NAME', None),
				 **kwargs):
		if job_id is None:
			super().__init__(ident=job_id, **kwargs)
		else:
			super().__init__(**kwargs)
		self.job_id = job_id
		self.job_name = job_name


	def report_launch(self, info: dict, **details: JSONABLE):
		details['name'] = self.job_name
		return super().report_launch(info, **details)



@fig.component('tgi-server')
class InferenceServer(AbstractTask, fig.Configurable):
	# region init
	def __init__(self,
				 command: str,
				 port: Union[str, int] = 3000,
				 allow_stdout: bool = False,

				 model_id: str = 'bigscience/bloom-560m',

				 sharded: bool = None,
				 num_shards: int = None,

				 quantize: str = None,
				 speculate: int = None,

				 dtype: str = 'float16', # 'bfloat16', 'float16'
				 trust_remote_code: bool = False,

				 max_concurrent_requests: int = None,
				 max_best_of: int = None,
				 max_stop_sequences: int = None,
				 max_top_n_tokens: int = None,
				 max_input_tokens: int = None,
				 max_total_tokens: int = None,

				 waiting_served_ratio: float = None, # 0.3

				 max_batch_total_tokens: int = None,

				 **kwargs):
		super().__init__(**kwargs)
		self._process = None
		self._exit_reason = None
		self._command_base = command
		self.workspace = None
		self._port = port
		self._allow_stdout = allow_stdout
		server_args = {}
		if model_id is not None:
			server_args['model-id'] = model_id
		if sharded is not None:
			server_args['sharded'] = sharded
		if num_shards is not None:
			server_args['num_shards'] = num_shards
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
		if max_input_tokens is not None:
			server_args['max-input-tokens'] = max_input_tokens
		if max_total_tokens is not None:
			server_args['max-total-tokens'] = max_total_tokens
		if waiting_served_ratio is not None:
			server_args['waiting-served-ratio'] = waiting_served_ratio
		if max_batch_total_tokens is not None:
			server_args['max-batch-total-tokens'] = max_batch_total_tokens
		self._server_args = server_args

	@property
	def type(self):
		return 'server'

	# endregion

	def prepare(self, env: AbstractEnvironment) -> None:
		super().prepare(env)
		self.workspace = env.workspace

	# _cmd = ('singularity run --nv --bind ~/workspace/singe/data/:/data ~/workspace/singe/text-generation-inference.sif'
	# 		' --port {port} -e')
	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		'''non blocking, returns the process id of the launched process'''
		assert self._process is None, f'already launched'
		args = ' '.join([f'--{k}' if v is True else f'--{k} {v}' for k, v in self._server_args.items()
					if v is not None and v is not False])
		cmd = f'{self._command_base.format(port=self._port)} {args}'

		assert self.workspace is not None, f'workspace not set (have you called `prepare()`?)'
		self._logfile = self.workspace / 'server.log'
		self._logfile.touch()
		self._msgfile = self.workspace / '.server.message'
		self._msgfile.touch()

		self.observer = Observer()
		self.observer.schedule(self._Monitor(self._msgfile, self._handle_cmd), self._msgfile.parent)
		self.observer.schedule(self._Monitor(self._logfile, self._handle_log), self._logfile.parent)
		self.observer.start()
		self._process = subprocess.Popen(cmd.split(), shell=True, text=True,
										 stdout=self._logfile.open('a'), stderr=self._logfile.open('a'))
		return {'command': cmd, 'pid': self._process.pid, 'msg': str(self._msgfile), 'log': str(self._logfile)}


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
			self._process.terminate()
			self._process.wait()
			self._exit_reason = message.strip()
		else:
			raise NotImplementedError(f'Unknown command: {message!r}')


	def _handle_log(self, message: str):
		if self._allow_stdout:
			sys.stdout.write(message)



		pass


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
		raise NotImplementedError('todo')



@fig.script('serve')
def start_server(cfg: fig.Configuration):
	cfg.push('server._type', 'tgi-server', silent=True, overwrite=False)
	return start_task(cfg, task_key='server')


	# working_dir = reporter.prepare(cfg)
	#
	# launch_info = server.launch(working_dir)
	# reporter.report_launch(launch_info)
	#
	# while True:
	# 	try:
	# 		exit_info = server.monitor(reporter)
	# 	except Exception as error:
	# 		error_info = server.handle(error)
	# 		if error_info is not None:
	# 			reporter.report_error(error_info)
	# 			raise error
	# 	else:
	# 		assert exit_info is not None, f'Monitor must return some exit info: {server}'
	# 		reporter.report_exit(exit_info)
	# 		break
	#
	# code = exit_info.get('code', None)
	# return code
	#
	# # old
	#
	# listen_freq = cfg.pull('listen-freq', 1)
	#
	# manifest_path = cfg.pull('manifest', '~/manifest.jsonl')
	# manifest_path = Path(manifest_path).expanduser()
	#
	# event_root = cfg.pull('events', '~/events/')
	# event_root = Path(event_root).expanduser()
	# event_root.mkdir(exist_ok=True)
	#
	# reporter.prepare(cfg)
	#
	#
	# if cfg.pull('dry-run', False):
	# 	raise NotImplementedError
	#
	# # change directory and make sure environment vars are set
	# working_dir = cfg.pull('working-dir', None)
	# if working_dir is not None:
	# 	os.chdir(working_dir)
	#
	#
	# # fixed info
	# ID = cfg.pull('job-id', os.environ.get('JOB_ID', None))
	# name = cfg.pull('job-name', os.environ.get('JOB_NAME', None))
	# event_path = event_root / f'{ID}.txt'
	# event_path.touch()
	#
	# # launch server using singularity (capture output) as a subprocess
	# pid = manager.launch()
	#
	#
	# launch_info = {
	# 	'event': 'launch',
	# 	'id': ID,
	# 	'host': hostname,
	# 	'pid': pid,
	# 	'name': name,
	# 	'path': str(event_path),
	# }
	# if cfg.pull('include-config', False):
	# 	launch_info['config'] = cfg.to_python()
	# launch_info['info'] = manager.info()
	#
	# with manifest_path.open('a') as f:
	# 	f.write(json.dumps({'time': datetime.now().isoformat(), **launch_info}) + '\n')
	#
	#
	# # listen kill trigger
	#
	# exit_code = manager.monitor(reporter)
	#
	# # report exit
	#
	#
	# pass



class _Logger:
	def __init__(self, filename, mirror=True):
		self.mirror = mirror
		self._stdout = sys.stdout
		self._stderr = sys.stderr
		self.logfile = open(filename, "a+")

	def write(self, message):
		if self.mirror:
			self._stdout.write(message)
		self.logfile.write(message)

	def flush(self):
		if self.mirror:
			self._stdout.flush()
		self.logfile.flush()

	def __enter__(self):
		sys.stdout = self
		sys.stderr = self
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		sys.stdout = self._stdout
		sys.stderr = self._stderr
		self.logfile.close()
		return False




