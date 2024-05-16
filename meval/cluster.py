from .imports import *
from .util import repo_root

import sys



@fig.script('submit-llm')
def submit_llm(cfg: fig.Configuration):
	try:
		from mpi_cluster.submit_jobs import create_jobs
	except ImportError as error:
		raise ImportError('Please install mpi_cluster to use this command (github: felixludos/mpi-cluster)') from error

	if cfg.pull('repo-working-dir', True):
		cfg.push('working-dir', str(repo_root))

	command = cfg.pull('command', None, silent=True)
	if command is None:
		prefix = cfg.pull('prefix', 'fig serve cluster')
		skip = cfg.pull('skip', 2)

		raw = sys.argv[skip:] if skip is not None and len(sys.argv) >= skip else sys.argv

		command = f'{prefix} {" ".join(raw)}'

		cfg.push('command', command)

	# return fig.run_script('mpi_cluster:submit', cfg)
	return create_jobs(cfg, command=command)












