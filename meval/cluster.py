from .imports import *

import sys


@fig.script('submit-llm')
def submit_llm(cfg: fig.Configuration):
	command = cfg.pull('command', None, silent=True)
	if command is None:
		prefix = cfg.pull('prefix', 'fig serve cluster')
		skip = cfg.pull('skip', 1)

		raw = sys.argv[skip:] if skip is not None else sys.argv

		command = f'{prefix} {" ".join(raw)}'

		cfg.push('command', command)

	return fig.run_script('mpi_cluster:submit', cfg)












