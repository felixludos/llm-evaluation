from .imports import *



@fig.component('randint')
class RandomAgent(Module):
	options = hparam()
	seed = hparam(None)

	def __init__(self, *args, **kwargs):
		super().__init__(**kwargs)
		self._rng = random.Random(self.seed)


	@tool('pick')
	def make_pick(self) -> int:
		return self._rng.randint(0, self.options-1)




