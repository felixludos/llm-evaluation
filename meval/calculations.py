from .imports import *




DESCRIBABLE = Union[JSONABLE, 'DescribableBase']
DESCRIPTION = dict[str, DESCRIBABLE]

SELECTION = Union[str, Iterable[str], Mapping[str, bool]]


class AbstractDescribable:
	def describe(self) -> DESCRIPTION:
		raise NotImplementedError


	@classmethod
	def display(cls, desc: DESCRIPTION, *, detail: int | None = None) -> str:
		raise NotImplementedError


class DescribableGadget(AbstractGadget, AbstractDescribable): # TODO
	pass


SYSTEM = Union[Context, AbstractGuru]
SOURCE = Iterator[Context]



class AbstractCalculation(AbstractDescribable):
	def sub(self, *, recursive: bool = False) -> Iterator['AbstractCalculation']:
		yield self


	def setup(self, system: SYSTEM = None) -> SYSTEM:
		return system


	def work(self, system: SYSTEM) -> Optional[SYSTEM]:
		raise NotImplementedError


	def finish(self, system: SYSTEM) -> JSONABLE:
		pass



class ProcedureBase(AbstractCalculation):
	def work(self, source: SOURCE) -> Optional[SOURCE]:
		for ctx in source:
			self.step(ctx)
		return


	def step(self, system: SYSTEM):
		raise NotImplementedError



Mutable = list[DescribableGadget] # TODO



class Runnable(AbstractCalculation):
	def run(self):
		system = self.setup()
		self.work(system)
		return self.finish(system)



class Worldly(AbstractCalculation):
	def __init__(self, world: Iterable[DescribableGadget] | Mapping[str, DescribableGadget] = (), **kwargs):
		if not isinstance(world, Mapping):
			world = {str(i): gadget for i, gadget in enumerate(world)}
		super().__init__(**kwargs)
		self.world = world

	def describe(self) -> DESCRIPTION:
		return {k: v.describe() for k, v in self.world.items()}

	def setup(self, system: Mutable = None) -> SYSTEM:
		system = super().setup(system)
		for gadget in self.world.values():
			if isinstance(gadget, AbstractStaged):
				gadget.stage()
		return system.extend(self.world.values())



class CreativeCalculation(AbstractCalculation):
	def _create_system(self) -> SYSTEM:
		return Context()

	def setup(self, system: SYSTEM = None) -> SYSTEM:
		if system is None:
			system = self._create_system()
		return super().setup(system)



class SimpleSelector(AbstractCalculation):
	def __init__(self, target: str, **kwargs):
		super().__init__(**kwargs)
		self.target = target

	def work(self, system: SYSTEM) -> SYSTEM:
		return system[self.target]



class MultiSelector(AbstractCalculation):
	def __init__(self, products: Iterable[str], **kwargs):
		if isinstance(products, str):
			products = [products]
		super().__init__(**kwargs)
		self.products = products

	def work(self, system: SYSTEM) -> SYSTEM:
		return {name: system[name] for name in self.products}



class StickyCalculation(AbstractCalculation):
	result = None
	def setup(self, system: SYSTEM = None) -> SYSTEM:
		self.result = None
		return super().setup(system)

	def work(self, system: SYSTEM) -> SYSTEM:
		self.result = super().work(system)
		return self.result

	def finish(self, system: SYSTEM) -> JSONABLE:
		result = self.result
		self.result = None
		return result



class PersistentCalculation(AbstractCalculation):
	def __init__(self, *, path: Path | str, **kwargs):
		super().__init__(**kwargs)
		self._raw_path = path
		self._path = None

	def _process_raw_path(self) -> Path:
		return Path(self._raw_path)

	@property
	def path(self) -> Path:
		if self._path is None:
			self._path = self._process_raw_path()
		return self._path
	@path.setter
	def path(self, value: Path):
		self._path = value



class RecordedCalculation(PersistentCalculation, StickyCalculation, MultiSelector):
	def _process_raw_path(self):
		path = super()._process_raw_path()
		if path.suffix == '':
			path = Path(f'{path}.json')
		assert path.suffix == '.json', f'Invalid path: {path}'
		return path

	def finish(self, system: SYSTEM) -> JSONABLE:
		result = super().finish(system)
		with self.path.open('w') as f:
			json.dump(result, f, indent=4, sort_keys=isinstance(self.products, set))
		return result



class AppendCalculation(PersistentCalculation, MultiSelector):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self._file = None

	def _process_raw_path(self):
		path = super()._process_raw_path()
		if path.suffix == '':
			path = Path(f'{path}.jsonl')
		assert path.suffix == '.jsonl', f'Invalid path: {path}'
		return path

	def setup(self, system: SYSTEM = None) -> SYSTEM:
		system = super().setup(system)
		self._file = self.path.open('a')
		return system

	def work(self, system: SYSTEM) -> SYSTEM:
		result = super().work(system)
		self._file.write(json.dumps(result, indent=4, sort_keys=isinstance(self.products, set)) + '\n')
		return system

	def finish(self, system: SYSTEM) -> JSONABLE:
		self._file.close()
		return super().finish(system)



class Calculation(Worldly, MultiSelector, CreativeCalculation):
	def __init__(self, world: Iterable[DescribableGadget] | Mapping[str, DescribableGadget] = (),
				 products: Mapping[str, bool] | Iterable[str] = None, **kwargs):
		super().__init__(world=world, products=products, **kwargs)



class MultiCalculation(AbstractCalculation):
	def __init__(self, calculations: Mapping[str, AbstractCalculation] | Iterable[AbstractCalculation], **kwargs):
		super().__init__(**kwargs)
		self.calculations = calculations


	def sub(self, *, recursive: bool = False) -> Iterator[AbstractCalculation]:
		yield from self.calculations.values() if isinstance(self.calculations, Mapping) else self.calculations


	def setup(self, system: SYSTEM = None) -> SYSTEM:
		system = super().setup(system)
		for calc in self.sub():
			system = calc.setup(system)
		return system


	def work(self, system: SYSTEM) -> Optional[SYSTEM]:
		for calc in self.sub():
			calc.work(system)
		return system


	def finish(self, system: SYSTEM) -> JSONABLE:
		if isinstance(self.calculations, Mapping):
			return {name: calc.finish(system) for name, calc in self.calculations.items()}
		for calc in self.sub():
			calc.finish(system)



class IterativeCalculation(ProcedureBase, MultiCalculation, Calculation):
	def __init__(self, source: AbstractMogul, **kwargs):
		super().__init__(**kwargs)
		self.source = source


	def setup(self, system: SYSTEM = None) -> SYSTEM:
		if isinstance(self.source, AbstractStaged):
			self.source.stage()
		return super().setup(system)


	def _create_system(self) -> SYSTEM:
		return self.source.guide()


	def step(self, system: SYSTEM):
		out = super(ProcedureBase, self).work(system)
		return out



class Aggregator(SimpleSelector):
	history = None

	def setup(self, system: SYSTEM = None) -> SYSTEM:
		self.history = []
		return super().setup(system)


	def work(self, system: SYSTEM) -> SYSTEM:
		result = super().work(system)
		self.history.append(result)
		return result


	def finish(self, system: SYSTEM) -> JSONABLE:
		return self.history



##############################################################


from .abstract import AbstractEnvironment
from .client import Client
from .tasks import start_task



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
		if self.head_name is not None:
			with self.workspace.joinpath(f'{self.head_name}.json').open('w') as f:
				json.dump(desc, f)
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







