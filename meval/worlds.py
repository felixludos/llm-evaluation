from .abstract import AbstractEnvironment
from .imports import *

from omniply import AbstractGadget
from omniply.apps.staging import AbstractStaged

from .client import Client
from .tasks import start_task


DESCRIBABLE = Union[JSONABLE, 'DescribableBase']
DESCRIPTION = dict[str, DESCRIBABLE]

SELECTION = Union[str, Iterable[str], Mapping[str, bool]]


class AbstractDescribable:
	def describe(self) -> DESCRIPTION:
		raise NotImplementedError


	@classmethod
	def display(cls, desc: DESCRIPTION, *, detail: int | None = None) -> str:
		raise NotImplementedError



class AbstractPlayer(AbstractDescribable):
	def setup(self, src: Context = None) -> Context:
		raise NotImplementedError


	def play(self, state: Context) -> Context:
		raise NotImplementedError


	def finish(self, state: Context) -> JSONABLE:
		pass


class PersistentPlayer(AbstractPlayer):
	def __init__(self, root: Path = None):
		self._root = root

	@property
	def persistent(self) -> bool:
		return False
	@property
	def root(self) -> Path:
		return self._root
	@root.setter
	def root(self, value: Path):
		self._root = Path(value)



class GenericPlayer(PersistentPlayer):
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



@fig.component('calculation')
class PlayableClient(Client):
	def __init__(self, player: PersistentPlayer, meta_name: str = None, **kwargs):
		super().__init__(**kwargs)
		self.player = player
		self.state = None
		self.workspace = None
		self.meta_name = meta_name

	def prepare(self, env: AbstractEnvironment) -> None:
		super().prepare(env)
		if self.player.persistent:
			self.player.root = env.workspace
		if self.meta_name is not None:
			self.workspace = env.workspace

	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		self.state = self.player.setup()
		desc = self.player.describe()
		if self.meta_name is not None:
			with self.workspace.joinpath(f'{self.meta_name}.json').open('w') as f:
				json.dump(desc, f)
		return desc

	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONABLE:
		result = self.player.play(self.state)
		out = self.player.finish(result)
		return out



@fig.script('calc')
def calculate_simple(cfg: fig.Configuration):
	cfg.push('client._type', 'calculation', silent=True, overwrite=False)
	cfg.push('player._type', 'simple-player', silent=True, overwrite=False)
	return start_task(cfg, task_key='client')



#############################



class WorldClient(Client):
	def __init__(self, world: Iterable[AbstractGadget] | Mapping[str, AbstractGadget],
				 out: Mapping[str, set[str]] | Mapping[str, Mapping[str, bool]], *,
				 head_name: str = None, base_name: str = None, **kwargs):
		out = {name: sorted([key for key, value in contents.items() if value])
						if isinstance(contents, Mapping)
						else (sorted(contents) if isinstance(contents, set) else list(contents))
			   for name, contents in out.items()}
		super().__init__(**kwargs)
		self.world = world
		self.products = out
		self.head_name = head_name
		self.base_name = base_name


	def prepare(self, env: AbstractEnvironment) -> None:
		super().prepare(env)
		self.workspace = env.workspace


	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:

		world = self.world

		if not isinstance(world, Mapping):
			world = {str(i): gadget for i, gadget in enumerate(world)}

		self.ctx = Context().extend(world.values())

		desc = {k: v.describe() for k, v in world.items()}
		if self.head_name:
			with self.workspace.joinpath(f'{self.head_name}.json').open('w') as f:
				json.dump(desc, f, indent=4)
		return {'world': desc}


	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		content = {name: {key: self.ctx[key] for key in keys} for name, keys in self.products.items()}

		for name, data in content.items():
			if self.base_name:
				name = f'{self.base_name}_{name}'
			with self.workspace.joinpath(f'{name}.json').open('w') as f:
				json.dump(data, f, indent=4)

		return content







class IterationClient(Client):
	def __init__(self, source: Iterable[Context], world: Iterable[AbstractGadget], **kwargs):
		self._progress = None
		self.source = source
		self.world = world

	def _as_iterator(self, source: Iterable[Context]):
		for ctx in source:
			ctx.extend(self.world.values() if isinstance(self.world, dict) else self.world)
			yield ctx

	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		# prepare for the iteration

		self._progress = self._as_iterator(self.source)

		try:
			n = len(self.source)
		except TypeError:
			n = None

		return {'n': n}


	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		for ctx in self._iterator(source, **kwargs):
			self.step(ctx)
		return self.finish(report)


	def finish(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		pass


	def step(self, ctx: Context):
		raise NotImplementedError























