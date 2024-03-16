import re

from ..prompting import PromptFile



class GSM8k(PromptFile):
	def _load_input_items(self):
		for item in super()._load_input_items():
			full = item['answer']

			# extract all substrings between "<<" and ">>"
			expr = re.findall(r'<<.*?>>', full)
			expr = [e[2:-2] for e in expr]

			# filter out all substrings between "<<" and ">>"
			full = re.sub(r'<<.*?>>', '', full)

			rationale, answer = full.split('\n####')
			rationale = rationale.strip()
			answer = answer.strip()

			yield {**item, 'rationale': rationale, 'answer': answer, 'expr': expr}
















