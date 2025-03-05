from .imports import *



@fig.component('gsm8k')
class GSM8k(FileDataset):
	@property
	def name(self):
		return 'GSM8k'


	def _load_data(self) -> dict[str, list[Any]]:

		data = super()._load_data()

		full = data['answer']

		expr = [re.findall(r'<<.*?>>', line) for line in full]
		expr = [[e[2:-2] for e in line] for line in expr]

		full = [re.sub(r'<<.*?>>', '', line) for line in full]

		rationale, answer = zip(*[line.split('\n####') for line in full])
		rationale = [line.strip() for line in rationale]
		answer = [line.strip() for line in answer]

		data['rationale'] = rationale
		data['answer'] = answer
		data['expr'] = expr

		return data



