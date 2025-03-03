from .imports import *



@fig.component('randint')
class RandomAgent(Module):
	def __init__(self, options: int, seed: int = None, **kwargs):
		super().__init__(**kwargs)
		self._options = options
		self._seed = seed
		self._rng = random.Random(seed)


	@tool('pick')
	def make_pick(self) -> int:
		return self._rng.randint(0, self._options)




