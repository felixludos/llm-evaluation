from .imports import *


from tempfile import TemporaryDirectory
from contextlib import chdir


from .calculations import *


class _Calc(StickyCalculation, Calculation):
	pass


class _PersistentCalc(RecordedCalculation, _Calc):
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

			calc = _PersistentCalc(path=path, world=world, products=products)

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



class _Itr(IterativeCalculation, MultiCalculation):
	def _create_system(self) -> SYSTEM:
		return Guru(src=[1, 2, 3], key='b')



def test_itr():

	world = [_Kit()]

	calc = _Itr(world=world, calculations={'mean': _Mean('a')})

	src = calc.setup()

	calc.work(src)

	out = calc.finish(src)

	assert out['mean'] == 24.0



from .benchmarks import Table, CustomBenchmark


def test_procedure():

	dummy_data = [
		{'x': 1, 'y': 2},
		{'x': 2, 'y': 4},
		{'x': 3, 'y': 7}, # bad sample
		{'x': 4, 'y': 8},
		{'x': 5, 'y': 10},
	]
	# dataset = CustomBenchmark(table=dummy_data)
	dataset = Table.from_rows(dummy_data)

	@tool('pred')
	def model(x):
		return x * 2

	@tool('loss')
	def l1_loss(y, pred):
		return abs(y - pred)

	@tool('correct')
	def is_correct(y, pred):
		return y == pred

	world = [dataset, model, l1_loss, is_correct]

	proc = Procedure(source=dataset, # what is the source of the iteration (subclass of AbstractMogul)
					 world=world, # should all be subclasses of AbstractGadget (e.g. Toolkits and tools)
					 calculations={'accuracy': _Mean('correct'),
								   'loss': _Mean('loss')})

	# sys = proc.setup()
	# proc.work(sys)
	# out = proc.finish(sys)
	out = proc.run()

	assert out['accuracy'] == 0.8
	assert out['loss'] == 0.2

















