from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations




@fig.component('dummy')
class DummyTask(ExpectedResources, fig.Configurable):
	def __init__(self, runner, **kwargs):
		super().__init__(**kwargs)
		self.runner = runner


	def _run(self):
		for _ in range(10):
			time.sleep(1)


@fig.component('loader')
class LoadTask(ExpectedResources, fig.Configurable):
	def __init__(self, runner, **kwargs):
		super().__init__(**kwargs)
		self.runner = runner


	def _run(self):
		self.runner.load()

























