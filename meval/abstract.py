from .imports import *



class AbstractEnvironment:
	'''
	A context manager for a specific task.
	Mostly the meta data for a task.
	Could be nested, but not recommended.
	Mostly delegates to the manager instance shared by all tasks.
	Should be customized for different run environemnts (local/CLI, cluster, jupyter, etc.)
	'''
	@property
	def ident(self) -> str:
		'''should be unique identifier for a single task'''
		raise NotImplementedError


	@property
	def workspace(self) -> Path:
		'''Working directory unique to this task. Can be created on demand'''
		raise NotImplementedError


	def world_history(self) -> Iterator[JSONOBJ]:
		'''Lazily yields all past events in the task log from oldest to most recent.'''
		raise NotImplementedError


	def prepare(self, manager: 'AbstractManager', task: 'AbstractTask') -> Self:
		return self


	def __enter__(self):
		return self


	def __exit__(self, exc_type, exc_val, exc_tb):
		pass


	def report(self, event: str, info: JSONOBJ = None):
		raise NotImplementedError


	def report_launch(self, info: JSONOBJ):
		raise NotImplementedError


	def report_error(self, info: JSONOBJ):
		raise NotImplementedError


	def report_exit(self, info: JSONOBJ):
		raise NotImplementedError



class AbstractManager:
	'''
	Manages all tasks that have to be run.
	Maintains global state (especially paths and roots).
	'''
	def prepare(self, task: 'AbstractTask') -> AbstractEnvironment:
		pass


	def record_config(self, config: fig.Configuration):
		pass


	def world_history(self) -> Iterator[JSONOBJ]:
		'''Lazily yields all past events in the task log from oldest to most recent.'''
		raise NotImplementedError


	def report(self, env: AbstractEnvironment, event: str, info: JSONOBJ, **details: JSONABLE) -> Self:
		raise NotImplementedError


	def generate_ident(self, env: AbstractEnvironment) -> str:
		raise NotImplementedError


	@classmethod
	def get_current_environment(cls):
		raise NotImplementedError



class AbstractTask:
	@property
	def category(self) -> str:
		raise NotImplementedError


	@property
	def quiet(self) -> bool:
		'''skips the launch, complete, and error reporting (default=False)'''
		return False


	def prepare(self, env: AbstractEnvironment) -> None:
		pass


	def status(self) -> JSONABLE:
		'''non blocking work'''
		pass


	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		'''non blocking'''
		raise NotImplementedError


	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		'''blocking'''
		raise NotImplementedError


	def handle(self, exception: Exception, report: Callable[[str, JSONOBJ], None]) -> Optional[JSONOBJ]:
		'''non blocking handle the exception or provide the error info'''
		return {'type': type(exception).__name__, 'message': str(exception)}



