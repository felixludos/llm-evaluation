from omniply.apps.staging import AbstractPlan
from .imports import *

from omniply.apps import Table
from .calculations import MutableIteration, AbstractSourced



class Benchmark(Table, AbstractSourced):
	def __init__(self, path: Path | str, **kwargs):
		super().__init__(**kwargs)
		self.path = Path(path)


	def as_source(self) -> Iterable[Context]:
		return MutableIteration(len(self.data))


	def _stage(self, plan: AbstractPlan):
		super()._stage(plan)
		self.load()






















