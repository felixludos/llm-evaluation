
import omnifig as fig

from omniply import Context, ToolKit, AbstractGaggle, AbstractGig, AbstractGadget
from omniply.apps import Staged

from .descriptions import Describable, deposit




@fig.script('eval', description='Load a pre-trained model and evaluate it on a simple benchmark')
def run_eval(cfg: fig.Configuration):

	benchmark = cfg.pull('benchmark')
	print(f'Benchmark: {benchmark}')

	kits = cfg.pull('kits', {})

	for name, kit in kits.items():
		print(f'{name}: {kit}')

	deposit_path =

	content = deposit(kits)

	cfg.print(f'Staging {len(kits)} kits.')

	for kit in kits:
		if isinstance(kit, Staged):
			kit.stage()




	cfg.print(f'Staging {len(kits)} kits.')


	outkeys = cfg.pull('outkeys', None)





	# Load the model
	model = fig.run('load-model', cfg)

	# Load the benchmark
	benchmark = fig.run('load-benchmark', cfg)

	# Evaluate the model on the benchmark
	results = model.evaluate(benchmark)

	# Print the results
	print(results)















