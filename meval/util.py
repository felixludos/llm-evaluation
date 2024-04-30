from .imports import *

import os


@fig.autocomponent('repo')
def repo_root():
	return Path(__file__).parent.parent



@fig.autocomponent('env-var')
def get_env_variable(var: str):
	return os.environ.get(var, None)




