from .imports import *
from .abstract import AbstractSystem, AbstractBenchmark, AbstractDataset, AbstractSample
from .datasets import System



class BenchmarkBase(AbstractBenchmark):
	def run(self, dataset: AbstractDataset, **kwargs) -> Self:
		system = self.prepare(dataset, **kwargs)

		sample = None
		for sample in self.loop(system):
			self.step(sample)

		self.end(sample)
		return self


	def loop(self, system: AbstractSystem) -> Iterator[AbstractSample]:
		for sample in system.iterate():
			yield sample


	_System = System
	def prepare(self, dataset: AbstractDataset, **kwargs) -> System:
		return self._System(dataset, *self.gadgetry())


	def step(self, sample: AbstractSample):
		raise NotImplementedError


	def end(self, last_sample: Optional[AbstractSample]):
		raise NotImplementedError






















