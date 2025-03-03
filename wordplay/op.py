from .imports import *
from .abstract import AbstractBenchmark



@fig.script('run')
def run_benchmark(cfg: fig.Configuration):

	benchmark: AbstractBenchmark = cfg.pull('benchmark')

	system = benchmark.prepare()

	print(benchmark.announce(system))

	out = benchmark.run(system)

	print(out)










