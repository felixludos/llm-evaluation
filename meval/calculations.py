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


SYSTEM = Context
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
	def __init__(self, products: Mapping[str, bool] | Iterable[str], **kwargs):
		if isinstance(products, Mapping):
			products = {name for name, value in products.items() if value}
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
			json.dump(result, f, indent=4)
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
		self._file.write(json.dumps(result, indent=4) + '\n')
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
	def step(self, system: SYSTEM):
		return super(ProcedureBase, self).work(system)



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



IterableSource = Union[Iterable[int], int]



class SimpleIteration:
	def __init__(self, src: IterableSource, key: str = 'idx', **kwargs):
		super().__init__(**kwargs)
		self._itr = self._process_iterator(src)
		self._key = key


	def _process_iterator(self, src: IterableSource):
		if isinstance(src, int):
			src = range(src)
		return iter(src)


	def _create_context(self, value: int):
		return Context(DictGadget({self._key: value}))


	def __iter__(self):
		return self


	def __next__(self):
		value = next(self._itr)
		return self._create_context(value)



class MutableIteration(SimpleIteration, AbstractMutable):
	def __init__(self, src: IterableSource, key: str = 'idx', **kwargs):
		super().__init__(src=src, key=key, **kwargs)
		self._gadgets = []


	def _create_context(self, value: int):
		return super()._create_context(value).extend(self._gadgets)


	def extend(self, gadgets):
		self._gadgets.extend(gadgets)
		return self



class CountableIteration(SimpleIteration):
	def __init__(self, src: IterableSource, key: str = 'idx', **kwargs):
		super().__init__(src=src, key=key, **kwargs)
		self._past = 0
		self._len = None

	def _process_iterator(self, src: IterableSource):
		if isinstance(src, int):
			self._len = src
		else:
			try:
				self._len = len(src)
			except TypeError:
				pass
		return super()._process_iterator(src)

	def __next__(self):
		ctx = super().__next__()
		self._past += 1
		return ctx

	def __len__(self):
		return self.total

	@property
	def total(self):
		return self._len

	@property
	def remaining(self):
		if self._len is not None:
			return self._len - self._past

	@property
	def past(self):
		return self._past



##############################################################


class AbstractSourced(AbstractGadget):
	def as_source(self) -> Iterable[Context]:
		raise NotImplementedError

	def __iter__(self):
		return self.as_source()



class Live(fig.Configurable, PersistentCalculation, MultiCalculation):
	_default_calc = None

	def __init__(self, out: Mapping[str, Any], world: Mapping[str, AbstractGadget] = None, **kwargs):
		super().__init__(calculations={}, world=world, **kwargs)
		self.calculations.update(self._process_subs(out))


	def _process_subs(self, raw_calcs: Mapping[str, Any]) -> dict[str, AbstractCalculation]:
		return {name: calc if isinstance(calc, AbstractCalculation) else self._default_calc(products=calc, path=name)
				for name, calc in raw_calcs.items()}



@fig.component('calc')
class Calculator(Live, Calculation):
	_default_calc = RecordedCalculation



@fig.component('proc')
class Procedure(Live, IterativeCalculation):
	_default_calc = AppendCalculation


	def __init__(self, source: AbstractStaged, **kwargs):
		super().__init__(**kwargs)
		self.source = source


	class _default_iterator(CountableIteration, MutableIteration):
		pass


	def setup(self, system: SYSTEM = None) -> SYSTEM:
		self.source.stage()
		return super().setup(system)


	def _create_system(self) -> SYSTEM:
		src = self.source.as_source()
		if not isinstance(src, MutableIteration):
			src = self._default_iterator(src=src)
		return src









