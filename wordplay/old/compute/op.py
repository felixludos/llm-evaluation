from .imports import *

from ..abstract import AbstractEnvironment
from ..client import Client
from ..tasks import start_task

from .abstract import AbstractCalculation
from .calculations import (Runnable, MultiCalculation, Worldly, Calculation, RecordedCalculation, AppendCalculation,
						   IterativeCalculation, SYSTEM)



@fig.component('computation')
class ComputationClient(Client, fig.Configurable, Runnable, MultiCalculation, Worldly):
	_default_recorder = None

	def __init__(self, rec: Mapping[str, Union[Mapping[str, bool], Iterable[str]]] = None,
				 world: Mapping[str, AbstractGadget] = None,
				 calculations: dict[str, AbstractCalculation] = None, *,
				 head_name: str = None, **kwargs):
		if calculations is None:
			calculations = {}
		super().__init__(calculations=calculations, world=world, **kwargs)
		self._process_recordings(rec)
		self.system = None
		self._env = None
		self.head_name = head_name


	def _process_recordings(self, recordings: Mapping[str, Any]):
		if recordings is not None:
			self.calculations.update({name: self._default_recorder(
				products=set(key for key, value in calc.items() if value) if isinstance(calc, Mapping) else calc,
																   path=name)
					for name, calc in recordings.items()})


	@property
	def workspace(self):
		return self._env.workspace


	def prepare(self, env: AbstractEnvironment) -> None:
		super().prepare(env)
		self._env = env


	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		assert len(self.calculations) > 0, 'No calculations were provided'
		self.system = self.setup()
		desc = self.describe()
		print(f'Job ident: {self._env.ident}')
		if self.head_name is not None:
			path = self.workspace.joinpath(f'{self.head_name}.json')
			with path.open('w') as f:
				json.dump(desc, f)
			print(f'World description saved to: {path}')
		return desc


	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONABLE:
		self.work(self.system)
		out = self.finish(self.system)
		return out



@fig.component('calc')
class Calculator(ComputationClient, Calculation):
	_default_recorder = RecordedCalculation



@fig.component('proc')
class Procedure(ComputationClient, IterativeCalculation):
	_default_recorder = AppendCalculation
	_default_iterator = Guru

	def __init__(self, source: AbstractMogul = None, auto_add_source: bool = True, **kwargs):
		if source is None:
			raise ValueError(f'No iteration source was provided for this procedure: {self}')
		super().__init__(source=source, **kwargs)
		if auto_add_source:
			self.world['source'] = source


	def _create_system(self) -> SYSTEM:
		return self.source.guide() if isinstance(self.source, AbstractMogul) else self._default_iterator(self.source)



@fig.script('compute')
def start_computation(cfg: fig.Configuration):
	cfg.push('client._type', 'calc', silent=True, overwrite=False)
	return start_task(cfg, task_key='client')



@fig.script('do')
def start_do(cfg: fig.Configuration, **kwargs):
	cfg.push('calculations.printer._type', 'printer', silent=True, overwrite=False)
	return start_computation(cfg)




