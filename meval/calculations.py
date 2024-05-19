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



class SimpleCalculation(AbstractCalculation):
	def __init__(self, products: Mapping[str, bool] | Iterable[str], **kwargs):
		if isinstance(products, Mapping):
			products = {name for name, value in products.items() if value}
		if isinstance(products, str):
			products = [products]
		super().__init__(**kwargs)
		self.products = products


	def work(self, system: SYSTEM) -> SYSTEM:
		return {name: system[name] for name in self.products}



class StickyCalculation(SimpleCalculation):
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



class PersistentCalculation(StickyCalculation):
	def __init__(self, path: Path | str, append_mode: bool = False, **kwargs):
		if isinstance(path, str) and 'json' not in path:
			path = f'{path}.jsonl' if append_mode else f'{path}.json'
		super().__init__(**kwargs)
		self.path = Path(path)
		self.append_mode = append_mode
		self._file = None


	def finish(self, system: SYSTEM) -> JSONABLE:
		result = super().finish(system)
		with self.path.open('w') as f:
			json.dump(result, f, indent=4)
		return result



class AppendCalculation(SimpleCalculation):
	def __init__(self, path: Path | str, append_mode: bool = False, **kwargs):
		if isinstance(path, str) and 'jsonl' not in path:
			path = f'{path}.jsonl'
		super().__init__(**kwargs)
		self.path = Path(path)
		self._file = None

	def setup(self, system: SYSTEM = None) -> SYSTEM:
		self._file = self.path.open('a')
		return super().setup(system)

	def work(self, system: SYSTEM) -> SYSTEM:
		result = super().work(system)
		self._file.write(json.dumps(result, indent=4) + '\n')
		return system

	def finish(self, system: SYSTEM) -> JSONABLE:
		self._file.close()
		return super().finish(system)



class Calculation(Worldly, SimpleCalculation):
	def __init__(self, world: Iterable[DescribableGadget] | Mapping[str, DescribableGadget] = (),
				 products: Mapping[str, bool] | Iterable[str] = None, **kwargs):
		super().__init__(world=world, products=products, **kwargs)



class Calculator(AbstractCalculation):
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



class IterativeCalculator(ProcedureBase, Calculator):
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



from omniply.apps import DictGadget
from omniply.core.abstract import AbstractMutable



IterableSource = Union[Iterable[int], int]



class SimpleIteration:
	def __init__(self, src: IterableSource, key: str = 'ID', **kwargs):
		super().__init__(**kwargs)
		self._past = 0
		self._len = None
		self._itr = iter(src)
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
	def __init__(self, src: IterableSource, key: str = 'ID', **kwargs):
		super().__init__(src=src, key=key, **kwargs)
		self._gadgets = []


	def _create_context(self, value: int):
		return super()._create_context(value).extend(self._gadgets)


	def extend(self, gadgets):
		self._gadgets.extend(gadgets)
		return self



class CountableIteration(SimpleIteration):
	def __init__(self, src: IterableSource, key: str = 'ID', **kwargs):
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


	def __len__(self):
		return self.total()


	def total(self):
		return self._len


	def remaining(self):
		if self._len is not None:
			return self._len - self._past


	def past(self):
		return self._past


	def __next__(self):
		ctx = super().__next__()
		self._past += 1
		return ctx






