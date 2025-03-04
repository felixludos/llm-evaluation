from .imports import *
from .abstract import AbstractBenchmark

from pprint import pprint



def _format_result_value(key: str, value: Any) -> str:
	if isinstance(value, dict):
		if 'avg' in value:
			return value['avg']
	return value


@fig.script('run')
def run_benchmark(cfg: fig.Configuration):

	benchmark: AbstractBenchmark = cfg.pull('benchmark')

	print()

	system = benchmark.prepare()

	print(benchmark.announce(system))

	out = benchmark.run(system)

	if len(out) == 0:
		print('No results')

	else:
		print('Results:\n')

		tbl = [(key, _format_result_value(key, value)) for key, value in out.items()]
		print(tabulate(tbl, tablefmt='fancy_grid'))

	return out






