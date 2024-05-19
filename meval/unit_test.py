from .imports import *


from tempfile import TemporaryDirectory
from contextlib import chdir


from .calculations import *


class _Calc(StickyCalculation, Worldly, CreativeCalculation):
	pass


class _PersistentCalc(PersistentCalculation, _Calc):
	pass


class _AppendCalc(AppendCalculation, _Calc):
	pass



class _Kit(ToolKit):
	@tool('a')
	def get_a(self, b, c):
		return b + c

	@tool('c')
	def get_c(self):
		return 22

class _Source(ToolKit):
	@tool('b')
	def get_b(self):
		return 11




def test_calc():

	world = [_Kit(), _Source()]

	products = ['a']

	calc = _Calc(world=world, products=products)

	ctx = calc.setup()

	calc.work(ctx)

	out = calc.finish(ctx)

	assert out['a'] == 33



def test_persistent_calc():
	world = [_Kit(), _Source()]

	products = ['a']

	with TemporaryDirectory() as tempdir:
		with chdir(tempdir):

			path = Path(tempdir) / 'out.json'

			assert not path.exists()

			calc = _PersistentCalc(path, world=world, products=products)

			ctx = calc.setup()

			calc.work(ctx)

			out = calc.finish(ctx)
			assert out['a'] == 33

			assert path.exists()

			with path.open('r') as f:
				data = json.load(f)

				assert data['a'] == 33



class _Mean(Aggregator):
	def finish(self, system: SYSTEM) -> JSONABLE:
		history = super().finish(system)
		return sum(history) / len(history)



from omniply.apps import DictGadget
from .calculations import MutableIteration



class _Itr(CreativeCalculation, Worldly, IterativeCalculator):
	def _create_system(self) -> SYSTEM:
		return MutableIteration(itr=[1, 2, 3], key='b')



def test_itr():

	world = [_Kit()]

	calc = _Itr(world=world, calculations={'mean': _Mean('a')})

	src = calc.setup()

	calc.work(src)

	out = calc.finish(src)

	assert out['mean'] == 24.0











