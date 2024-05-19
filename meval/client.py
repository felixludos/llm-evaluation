from .imports import *

from .abstract import AbstractTask, AbstractEnvironment

from functools import lru_cache, cached_property
import socket, requests

from .calculations import AbstractCalculation


class Client(AbstractTask):
	@property
	def category(self):
		return 'client'


	@property
	def quiet(self):
		return True



@fig.component('calculation')
class CalculationClient(Client):
	def __init__(self, calc: AbstractCalculation, head_name: str = None, **kwargs):
		super().__init__(**kwargs)
		self.calc = calc
		self.system = None
		self.workspace = None
		self.head_name = head_name


	def prepare(self, env: AbstractEnvironment) -> None:
		super().prepare(env)
		if self.head_name is not None:
			self.workspace = env.workspace


	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		self.system = self.calc.setup()
		desc = self.calc.describe()
		if self.head_name is not None:
			with self.workspace.joinpath(f'{self.head_name}.json').open('w') as f:
				json.dump(desc, f)
		return desc


	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONABLE:
		self.calc.work(self.system)
		out = self.calc.finish(self.system)
		return out













