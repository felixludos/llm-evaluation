import socket

from .imports import *

import os
from functools import cached_property

from .abstract import AbstractTask, AbstractManager, AbstractEnvironment
from .util import get_task_root


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


	def prepare(self, manager: AbstractManager, task: AbstractTask = None) -> Self:
		assert self._task is None, 'Environment is already prepared'
		self._manager = manager
		self._task = task
		self._prepare(manager, task)
		return super().prepare(manager, task)


	def _prepare(self, manager: AbstractManager, task: AbstractTask):
		pass


	def wrap_command(self, cmd: str) -> str:
		return cmd


	@property
	def ident(self) -> str:
		'''unique identifier for the task (environment)'''
		if self._ident is None:
			self._ident = self._manager.generate_ident(self)
		return self._ident


	@property
	def workspace(self) -> Path:
		if self._workspace is None:
			assert self._manager is not None, 'Manager must be set before workspace is accessed'
			self._workspace = self._manager.create_workspace(self)
		return self._workspace


	def record_config(self, config: JSONABLE):
		if self._include_config:
			self._config = config


	def world_history(self, *args, **kwargs) -> Iterator[JSONOBJ]:
		yield from self._manager.world_history(*args, **kwargs)


	def _report(self, event: str, info: JSONOBJ, **details: JSONABLE):
		assert self._manager is not None, 'Manager must be set before reporting'
		self._manager.report(self, event, info, **details)


	def report(self, event: str, info: JSONOBJ = None):
		return self._report(event, info)


	def report_launch(self, info: JSONOBJ, **details: JSONABLE):
		if self._workspace is not None and 'TASK_LOG' not in os.environ:
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
	_current_env = None

	def __init__(self, env: AbstractEnvironment = None,
				 task_root: Union[str, Path] = os.environ.get('TASK_ROOT', get_task_root()),
				 # task_log: Union[str, Path] = os.environ.get('TASK_LOG', '~/log.jsonl'),
				 # working_root: Union[str, Path] = os.environ.get('TASK_WORK_ROOT', '~/tasks/'),
				 **kwargs):
		if env is None:
			env = self._Environment()
		super().__init__(**kwargs)
		self.env = env
		self._config = None
		self.task_root = Path(task_root).expanduser().resolve()


	@property
	def task_log(self) -> Path:
		return self.task_root / 'log.jsonl'


	@classmethod
	def set_current_environment(cls, env: AbstractEnvironment):
		cls._current_env = env


	@classmethod
	def get_current_environment(cls) -> AbstractEnvironment:
		return cls._current_env


	def world_history(self) -> Iterator[JSONOBJ]:
		with self.task_log.open('r') as f:
			for line in f:
				yield json.loads(line)


	def prepare(self, task: AbstractTask) -> AbstractEnvironment:
		self.task_root.mkdir(exist_ok=True)
		self.task_log.touch()
		env = self._Environment() if self.env is None else self.env
		self.set_current_environment(env)
		env.record_config(self._config)
		return env.prepare(self, task)


	def create_workspace(self, env: AbstractEnvironment) -> Path:
		workspace = self.task_root / env.ident
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


	def generate_ident(self, env: AbstractEnvironment) -> str:
		existing = list(self.task_root.glob('*'))
		n = len(existing)

		while True:
			candidate = f'{str(n).zfill(3)}'
			if (self.task_root / candidate).exists():
				n += 1
			else:
				return candidate



def default_environment(*, manager=None):
	env = Environment()
	if manager is None:
		manager = Manager()
	return env.prepare(manager)



def get_environment(force=True) -> AbstractEnvironment:
	env = Manager.get_current_environment()
	if env is None and force:
		env = default_environment()
	return env



@fig.script('start')
def start_task(cfg: fig.Configuration, *, manager: AbstractManager = None, task: AbstractTask = None,
			   manager_key='manager', task_key='task'):

	if manager is None:
		cfg.push(f'{manager_key}._type', 'default-manager', overwrite=False, silent=True)
		manager: AbstractManager = cfg.pull(manager_key)

	if task is None:
		task: AbstractTask = cfg.pull(task_key)

	manager.record_config(cfg)
	with manager.prepare(task) as env:
		task.prepare(env)

		launch_info = task.launch(env.report)
		if not task.quiet:
			env.report_launch(launch_info)

		while True:
			try:
				exit_info = task.complete(env.report)
			except (KeyboardInterrupt, Exception) as error:
				error_info = task.handle(error, env.report)
				if error_info is not None:
					if not task.quiet:
						env.report_error(error_info)
					raise
			else:
				# assert exit_info is not None, f'Monitor must return some exit info: {task}'
				if not task.quiet:
					env.report_exit(exit_info)
				break

	code = exit_info.get('code', exit_info)
	return code



# @fig.script('sandbox')
# def _sandbox(cfg: fig.Configuration):
# 	import subprocess, sys, os
# 	from omnibelt import colorize
#
# 	# cmd = 'source ~/.bashrc && conda activate llm && conda info'
# 	cmd = '''
# 	source $CONDA_PREFIX/etc/profile.d/conda.sh
# 	conda activate llm
# 	conda info
# 	'''
# 	# cmd = 'conda run -n llm text-generation-launcher'
# 	# cmd = ('echo $CONDA_PREFIX;'
# 	# 	   'conda activate llm;'
# 	# 	   'echo $CONDA_PREFIX;')
# 	cmd = 'source $CONDA_PREFIX/etc/profile.d/conda.sh; conda activate llm; text-generation-launcher'
#
# 	proc = subprocess.Popen(cmd, shell=True, text=True, executable="/bin/bash", env=os.environ.copy())
#
# 	print(colorize('started', 'green'))
# 	print()
#
# 	out = proc.wait()
#
# 	print(colorize(f'finished: {out}', 'green'))





