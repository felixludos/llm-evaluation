from .imports import *

import os
import subprocess
import socket

from .abstract import AbstractTask, AbstractReporter
from .reporters import ReporterBase



@fig.component('server-reporter')
class ServerReporter(ReporterBase, fig.Configurable):
	def __init__(self, ident: str, master_log: Union[str, Path] = '~/master-log.jsonl',
				 work_root: Union[str, Path] = '~/prod/', include_config: bool = False):
		'''name must be unique to a single job'''
		self.master_log = Path(master_log).expanduser()
		self.work_root = Path(work_root).expanduser()
		self.work_dir = None

		self.include_config = include_config
		self.config = None

		self.ident = ident
		self.hostname = socket.gethostname()


	def prepare(self, config: fig.Configuration) -> Path:
		self.work_root.mkdir(exist_ok=True)
		self.work_dir = self.work_root / f'{self.ident}'
		assert not self.work_dir.exists(), (f'Work directory for {self.ident} on {self.hostname} already exists: '
											f'{self.work_dir}')
		self.work_dir.mkdir()
		if self.include_config:
			self.config = config.to_python()

		return self.work_dir


	def report(self, event: str, info: dict[str, JSONABLE]) -> Self:
		with self.master_log.open('a') as f:
			f.write(json.dumps({'time': datetime.now().isoformat(), 'event': event, 'id': self.ident, **info}) + '\n')
		return self


	def report_launch(self, info: dict[str, JSONABLE]) -> Self:
		assert self.work_dir is not None and self.work_dir.exists(), ('Work directory must be prepared before launch '
																	  '(call `.prepare(config)`)')
		info['path'] = str(self.work_dir)
		if self.config is not None:
			info['config'] = self.config
		return super().report_launch(info)



@fig.component('cluster-reporter')
class ClusterReporter(ServerReporter):
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


	def monitor(self, reporter: AbstractReporter) -> dict[str, JSONABLE]:
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





