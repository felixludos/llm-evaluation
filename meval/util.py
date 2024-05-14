from .imports import *

import os
import re


@fig.autocomponent('repo')
def repo_root():
	return Path(__file__).parent.parent



@fig.autocomponent('env-var')
def get_env_variable(var: str):
	return os.environ.get(var, None)



def remove_ansi_escape_sequences(text):
	# This regex matches the escape character \x1b followed by [, then any number of characters that are not 'm',
	# and finally ends with 'm'. This pattern matches ANSI escape codes.
	ansi_escape_regex = re.compile(r'\x1b\[.*?m')
	clean_text = re.sub(ansi_escape_regex, '', text)
	return clean_text



