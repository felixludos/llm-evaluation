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
		return


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



###############################################################################################33



class GenericPlayer(AbstractCalculation):
	def __init__(self, world: Iterable[AbstractGadget] | Mapping[str, AbstractGadget] = (),
				 out: Mapping[str, Iterable[str]] | Mapping[str, Mapping[str, bool]] = None, **kwargs):
		if not isinstance(world, Mapping):
			world = {str(i): gadget for i, gadget in enumerate(world)}
		if out is None:
			out = {}
		super().__init__(**kwargs)
		self.world = world
		products = {name: sorted([key for key, value in contents.items() if value]) if isinstance(contents, Mapping)
					else (sorted(contents) if isinstance(contents, set) else list(contents))
					for name, contents in out.items()}
		self.products = products

	def _process_products(self, products: Iterable[str] | Mapping[str, bool] | Mapping[str, Iterable[str]] | Mapping[str, Mapping[str, bool]]):
		if not isinstance(products, Mapping):
			products = {str(i): keys for i, keys in enumerate(products)}
		return products


	def describe(self) -> DESCRIPTION:
		return {k: v.describe() for k, v in self.world.items()}


	def contents(self) -> Iterator[AbstractGadget]:
		yield from self.world.values()


	def setup(self, src: Context = None):
		if src is None:
			src = Context()
		for gadget in self.contents():
			if isinstance(gadget, AbstractStaged):
				gadget.stage()
		return src.extend(self.contents())


	def play(self, state: Context) -> dict[str, dict[str, Any]]:
		result = {name: {key: state[key] for key in keys} for name, keys in self.products.items()}
		return result


	def finish(self, state: Context) -> JSONABLE:
		content = {name: {key: state[key] for key in keys} for name, keys in self.products.items()}
		for name, data in content.items():
			with self.root.joinpath(f'{name}.json').open('w') as f:
				json.dump(data, f, indent=4)
		return content



@fig.component('simple-player')
class SimplePlayer(GenericPlayer):
	def __init__(self, world: Iterable[AbstractGadget] | Mapping[str, AbstractGadget] = (),
				 out: Iterable[str] | Mapping[str, bool] = None,
				 out_name: str = 'out', **kwargs):
		super().__init__(world=world, out={out_name: out}, **kwargs)



CTX_GENERATOR = Union[int, Iterable[Context]]


class IterativePlayer(GenericPlayer):
	def __init__(self, source: CTX_GENERATOR,
				 viewers: Mapping[str, AbstractGadget] = (), **kwargs):
		super().__init__(**kwargs)
		self.source = source
		self.viewers = viewers
		self.progression = None

	def _as_iterator(self, source: CTX_GENERATOR) -> Iterator[Context]:
		for ctx in source:
			ctx.extend(self.contents())
			yield ctx

	def setup(self, src: Context = None):
		if src is None:
			src = self._as_iterator(self.source)
		for gadget in self.contents():
			if isinstance(gadget, AbstractStaged):
				gadget.stage()
		return src.extend(self.contents())

	def play(self, src: Context) -> dict[str, dict[str, Any]]:
		for ctx in src:
			for viewer in self.viewers:
				viewer.play(ctx)

		return

	def finish(self, state: Context) -> JSONABLE:
		return {name: viewer.finish() for name, viewer in self.viewers.items()}



