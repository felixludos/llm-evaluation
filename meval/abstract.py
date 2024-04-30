from .imports import *



class AbstractReporter:
	def prepare(self, cfg: fig.Configuration) -> Path:
		pass


	def report(self, event: str, info: dict[str, JSONABLE]) -> Self:
		raise NotImplementedError



class AbstractTask:
	def launch(self, working_dir: Path) -> JSONABLE:
		'''
		returns PID of the launched server process
		'''
		raise NotImplementedError


	def monitor(self, reporter: AbstractReporter) -> dict[str, JSONABLE]:
		'''
		returns optional information about the server to save to the era file
		'''
		raise NotImplementedError


	def handle(self, exception: Exception) -> Optional[dict[str, JSONABLE]]:
		'''
		returns optional information about the error to save to the era file
		'''
		raise NotImplementedError



