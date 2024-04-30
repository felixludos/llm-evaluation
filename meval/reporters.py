from .imports import *

from .abstract import AbstractReporter


class ReporterBase(AbstractReporter):
	def report_launch(self, info: dict[str, JSONABLE]) -> Self:
		return self.report('launch', info)


	def report_error(self, info: dict[str, JSONABLE]) -> Self:
		return self.report('error', info)


	def report_exit(self, info: dict[str, JSONABLE]) -> Self:
		return self.report('exit', info)



