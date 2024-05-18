
from .imports import *


from .calculations import Calculation, PersistentCalculation, AppendCalculation



class _Kit(ToolKit):
	@tool('a')
	def get_a(self, b, c):
		return b + c


class _Source(ToolKit):
	@tool('b')
	def get_b(self):
		return 11

	@tool('c')
	def get_c(self):
		return 22



def test_calc():

	world = [_Kit(), _Source()]

	products = ['a']

	calc = Calculation(world=world, products=products)

	ctx = calc.setup()

	calc.work(ctx)

	out = calc.finish(ctx)

	assert out['a'] == 33


class _PersistentCalc(PersistentCalculation, Calculation):
	pass


class _AppendCalc(AppendCalculation, Calculation):
	pass


from tempfile import TemporaryDirectory
from contextlib import chdir


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

