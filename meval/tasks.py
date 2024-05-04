import socket

from .imports import *

import os
from functools import cached_property

from .abstract import AbstractTask, AbstractManager, AbstractEnvironment



@fig.component('env')
class Environment(AbstractEnvironment, fig.Configurable):
	'''this should be used to run a single task.'''
	def __init__(self, ident: str = None, include_config: bool = False, **kwargs):
		super().__init__(**kwargs)
		self._ident = ident
		self._manager = None
		self._task = None
		self._config = None
		self._include_config = include_config
		self._workspace = None


	def prepare(self, manager: AbstractManager, task: AbstractTask) -> Self:
		assert self._task is None, 'Environment is already prepared'
		self._manager = manager
		self._task = task
		return super().prepare(manager, task)


	@property
	def ident(self) -> str:
		'''unique identifier for the task (environment)'''
		return self._ident


	@property
	def workspace(self) -> Path:
		if self._workspace is None:
			assert self._manager is not None, 'Manager must be set before workspace is accessed'
			self._workspace = self._manager.create_workspace(self._task)
		return self._workspace


	def record_config(self, config: JSONABLE):
		if self._include_config:
			self._config = config


	def world_history(self, *args, **kwargs) -> Iterator[JSONOBJ]:
		yield from self._manager.world_history(*args, **kwargs)


	def _report(self, event: str, info: JSONOBJ, **details: JSONABLE):
		assert self._manager is not None, 'Manager must be set before reporting'
		self._manager.report(self, event, info, **details)


	def report_launch(self, info: JSONOBJ, **details: JSONABLE):
		if self._workspace is not None:
			details['path'] = str(self._workspace)
		if self._include_config:
			details['config'] = self._config
		return self._report('launch', info, category=self._task.category, host=socket.gethostname(), **details)


	def report_error(self, info: JSONOBJ, **details: JSONABLE):
		return self._report('error', info, **details)


	def report_exit(self, info: JSONOBJ, **details: JSONABLE):
		return self._report('exit', info, **details)



@fig.component('default-manager')
class Manager(AbstractManager, fig.Configurable):
	_Environment = Environment

	def __init__(self, env: AbstractEnvironment = None,
				 task_log: Union[str, Path] = os.environ.get('TASK_LOG', '~/task-log.jsonl'),
				 working_root: Union[str, Path] = os.environ.get('TASK_WORK_ROOT', '~/task-work/'), **kwargs):
		if env is None:
			env = self._Environment()
		super().__init__(**kwargs)
		self.env = env
		self._config = None
		self.task_log = Path(task_log).expanduser().absolute()
		self.working_root = Path(working_root).expanduser().absolute()


	def world_history(self) -> Iterator[JSONOBJ]:
		with self.task_log.open('r') as f:
			for line in f:
				yield json.loads(line)


	def prepare(self, task: AbstractTask) -> AbstractEnvironment:
		self.working_root.mkdir(exist_ok=True)
		self.task_log.touch()
		env = self._Environment() if self.env is None else self.env
		env.record_config(self._config)
		return env.prepare(self, task)


	def create_workspace(self, env: AbstractEnvironment) -> Path:
		workspace = self.working_root / env.ident
		if workspace.exists():
			raise ValueError(f'{env.ident} is not a unique task identifier')
		workspace.mkdir()
		return workspace


	def record_config(self, config: fig.Configuration):
		self._config = config.to_python()


	def report(self, env: AbstractEnvironment, event: str, info: JSONOBJ = None, **details: JSONABLE):
		payload = {'time': datetime.now().isoformat(), 'event': event, 'id': env.ident, **details}
		if info is not None:
			payload['info'] = info
		with self.task_log.open('a') as f:
			f.write(json.dumps(payload) + '\n')



@fig.script('start')
def start_task(cfg: fig.Configuration, *, manager: AbstractManager = None, task: AbstractTask = None,
			   manager_key='manager', task_key='task'):

	if manager is None:
		manager: AbstractManager = cfg.pull(manager_key)

	if task is None:
		task: AbstractTask = cfg.pull(task_key)

	manager.record_config(cfg)
	with manager.prepare(task) as env:
		launch_info = task.launch(env.report)
		if not task.quiet:
			env.report_launch(launch_info)

		while True:
			try:
				exit_info = task.complete(env.report)
			except Exception as error:
				try:
					error_info = task.handle(error, env.report)
				except NotImplementedError:
					error_info = {'type': type(error), 'message': str(error)}
				finally:
					if error_info is not None:
						if not task.quiet:
							env.report_error(error_info)
						raise error
			else:
				# assert exit_info is not None, f'Monitor must return some exit info: {task}'
				if not task.quiet:
					env.report_exit(exit_info)
				break

	code = exit_info.get('code', None)
	return code








