from .imports import *



class AbstractEnvironment:
	@property
	def board_path(self) -> Path:
		raise NotImplementedError


	def prepare(self, task: 'AbstractTask') -> Optional[Path]:
		pass


	def record_config(self, config: JSONABLE):
		pass


	def report(self, task: 'AbstractTask', event: str, info: JSONOBJ) -> Self:
		raise NotImplementedError


	def report_launch(self, task: 'AbstractTask', info: JSONOBJ) -> Self:
		return self.report(task, 'launch', info)


	def report_error(self, task: 'AbstractTask', info: JSONOBJ) -> Self:
		return self.report(task, 'error', info)


	def report_exit(self, task: 'AbstractTask', info: JSONOBJ) -> Self:
		return self.report(task, 'exit', info)



class AbstractTask:
	@property
	def needs_space(self):
		raise NotImplementedError


	@property
	def ident(self):
		raise NotImplementedError


	@property
	def quiet(self):
		return False


	def prepare(self, reporter: AbstractEnvironment) -> Self:
		pass


	def launch(self, working_dir: Optional[Path] = None) -> JSONOBJ:
		'''
		returns specific launch info
		'''
		raise NotImplementedError


	def status(self) -> JSONABLE:
		'''
		returns nonblocking status of task
		'''
		pass


	def monitor(self, reporter: AbstractEnvironment) -> JSONOBJ:
		'''
		returns optional information about the server to save to the era file
		'''
		raise NotImplementedError


	def handle(self, exception: Exception) -> Optional[JSONOBJ]:
		'''
		returns optional information about the error to save to the era file
		'''
		raise NotImplementedError



