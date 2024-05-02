from .imports import *

import os
import subprocess
import socket

from .abstract import AbstractTask, AbstractEnvironment



@fig.component('server-reporter')
class ServerEnvironment(AbstractEnvironment, fig.Configurable):
	def __init__(self, category: str, *, include_config: bool = False,
				 task_board: Union[str, Path] = os.environ.get('TASK_BOARD', '~/task-board.jsonl'),
				 task_root: Union[str, Path] = os.environ.get('TASK_ROOT', '~/prod/')):
		'''name must be unique to a single job'''
		self.task_board = Path(task_board).expanduser().absolute()
		self.task_root = Path(task_root).expanduser().absolute()
		self.task_dir = None

		self.include_config = include_config
		self.config = None

		self.category = category
		self.hostname = socket.gethostname()


	def record_config(self, config: JSONABLE):
		if self.include_config:
			self.config = config


	def prepare(self, task: fig.Configuration) -> Path:
		self.task_root.mkdir(exist_ok=True)
		self.task_dir = self.task_root / f'{self.ident}'
		assert not self.task_dir.exists(), (f'Work directory for {self.ident} on {self.hostname} already exists: '
											f'{self.task_dir}')
		self.task_dir.mkdir()
		return self.task_dir


	def report(self, task: AbstractTask, event: str, info: dict[str, JSONABLE]) -> Self:
		with self.task_board.open('a') as f:
			f.write(json.dumps({'time': datetime.now().isoformat(), 'event': event, 'id': self.ident, **info}) + '\n')
		return self


	def report_launch(self, task: AbstractTask, info: dict[str, JSONABLE]) -> Self:
		assert self.task_dir is not None and self.task_dir.exists(), ('Work directory must be prepared before launch '
																	  '(call `.prepare(config)`)')
		if self.task_dir is not None:
			info['path'] = str(self.task_dir)
		if self.include_config:
			info['config'] = self.config
		return super().report_launch(task, info)



@fig.component('cluster-reporter')
class ClusterReporter(ServerEnvironment):
	def __init__(self, job_id: str = None, job_name: str = None, **kwargs):
		if job_id is None:
			super().__init__(ident=job_id, **kwargs)
		else:
			super().__init__(**kwargs)
		self.job_id = job_id
		self.job_name = job_name


	def report_launch(self, info: dict):
		info['name'] = self.job_name
		return super().report_launch(info)



@fig.component('server')
class ServerTask(AbstractTask, fig.Configurable):
	def launch(self, working_dir: Path) -> dict[str, JSONABLE]:
		'''non blocking, returns the process id of the launched process'''
		raise NotImplementedError('todo')


	def monitor(self, reporter: AbstractEnvironment) -> dict[str, JSONABLE]:
		'''blocking, use the reporter to report actionable events, return with exit code if one is received'''
		raise NotImplementedError('todo')


	def handle(self, exception: Exception) -> Optional[dict[str, JSONABLE]]:
		'''blocking'''
		raise NotImplementedError('todo')



@fig.script('serve')
def start_server(cfg: fig.Configuration):

	cfg.push('server._type', 'server', silent=True, overwrite=False)
	server: AbstractTask = cfg.pull('server')

	cfg.push('reporter._type', 'reporter', silent=True, overwrite=False)
	reporter: ReporterBase = cfg.pull('reporter')

	working_dir = reporter.prepare(cfg)

	launch_info = server.launch(working_dir)
	reporter.report_launch(launch_info)

	while True:
		try:
			exit_info = server.monitor(reporter)
		except Exception as error:
			error_info = server.handle(error)
			if error_info is not None:
				reporter.report_error(error_info)
				raise error
		else:
			assert exit_info is not None, f'Monitor must return some exit info: {server}'
			reporter.report_exit(exit_info)
			break

	code = exit_info.get('code', None)
	return code

	# old

	listen_freq = cfg.pull('listen-freq', 1)

	manifest_path = cfg.pull('manifest', '~/manifest.jsonl')
	manifest_path = Path(manifest_path).expanduser()

	event_root = cfg.pull('events', '~/events/')
	event_root = Path(event_root).expanduser()
	event_root.mkdir(exist_ok=True)

	reporter.prepare(cfg)


	if cfg.pull('dry-run', False):
		raise NotImplementedError

	# change directory and make sure environment vars are set
	working_dir = cfg.pull('working-dir', None)
	if working_dir is not None:
		os.chdir(working_dir)


	# fixed info
	ID = cfg.pull('job-id', os.environ.get('JOB_ID', None))
	name = cfg.pull('job-name', os.environ.get('JOB_NAME', None))
	event_path = event_root / f'{ID}.txt'
	event_path.touch()

	# launch server using singularity (capture output) as a subprocess
	pid = manager.launch()


	launch_info = {
		'event': 'launch',
		'id': ID,
		'host': hostname,
		'pid': pid,
		'name': name,
		'path': str(event_path),
	}
	if cfg.pull('include-config', False):
		launch_info['config'] = cfg.to_python()
	launch_info['info'] = manager.info()

	with manifest_path.open('a') as f:
		f.write(json.dumps({'time': datetime.now().isoformat(), **launch_info}) + '\n')


	# listen kill trigger

	exit_code = manager.monitor(reporter)

	# report exit




	pass





