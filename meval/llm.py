from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations



@fig.component('loader')
class LoadTask(ExpectedResources, fig.Configurable):
	def __init__(self, runner, **kwargs):
		super().__init__(**kwargs)
		self.runner = runner


	def _run_job(self):
		self.runner.load()

























