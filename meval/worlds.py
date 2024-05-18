from .abstract import AbstractEnvironment
from .imports import *

from omniply import AbstractGadget
from omniply.apps.staging import AbstractStaged

from .client import Client
from .tasks import start_task



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























