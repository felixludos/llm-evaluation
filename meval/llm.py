from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations




@fig.component('dummy')
class DummyTask(ExpectedResources, fig.Configurable):
	def __init__(self, num=100, **kwargs):
		super().__init__(**kwargs)
		self.num = num
		self.itr = 0


	def _run(self):
		for _ in range(10):
			time.sleep(1)
			self.itr += 1


	def status(self, fast: bool = False):
		return {'itr': self.itr, **super().status(fast=fast)}



@fig.component('loader')
class LoadTask(ExpectedResources, fig.Configurable):
	def __init__(self, runner, **kwargs):
		super().__init__(**kwargs)
		self.runner = runner


	def _run(self):
		self.runner.load()



class GenerateTask(ExpectedResources, ExpectedIterations, fig.Configurable):
	def __init__(self, runner=None, **kwargs):
		super().__init__(**kwargs)
		self.runner = runner


	def chain(self, loader: LoadTask):
		if loader.runner is None:
			raise ValueError("Loader has no runner")

		self.runner = loader.runner
		return self


	# def _run(self):





















