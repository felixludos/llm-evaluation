from .imports import *

from .jobs import Job, ResourceAware, ExpectedResources, ExpectedIterations



@fig.component('loader')
class LoadJob(ExpectedResources, fig.Configurable):
	def __init__(self, runner, **kwargs):
		super().__init__(**kwargs)
		self.runner = runner


	def _run_job(self):
		self.runner.load()

























