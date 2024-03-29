import time

from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations



class DemoLoader(ExpectedResources):
	tokenizer = None
	model = None

	def _run(self):
		torch.set_default_device("cuda")
		self.tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2", trust_remote_code=True)

		self.model = AutoModelForCausalLM.from_pretrained("microsoft/phi-2", torch_dtype="auto", trust_remote_code=True)


class IterativeLoader(ExpectedResources, ExpectedIterations):
	result = None

	def __init__(self, total_iterations=50):
		self.expected_num_iterations = total_iterations


	def _generate_stream(self):
		data = []
		for i in range(self.expected_num_iterations):
			data.append(torch.randn(100,100,100, 10))
			data.append(torch.randn(100,100,100, 10, device='cuda'))
			time.sleep(1)
			yield

		self.result = data


def test_heavy_job():
	print()

	job = DemoLoader()
	job.expected_duration = timedelta(seconds=84.394543)
	job.expected_ram_usage = 1.378997802734375
	job.expected_gpu_usage = 5.375
	job.start()

	prs = []

	while not job.is_done and len(prs) < 20:
		progress = job.status()
		prs.append(progress)
		time.sleep(5)

	job.complete()

	progress = job.status()
	print(progress)

	print('done')

	assert job.is_done
	assert job.model is not None
	assert job.tokenizer is not None
	# assert job.model is not None
	# assert job.tokenizer is not None


def test_iterative_job():
	print()

	job = IterativeLoader(20)
	job.start()

	prs = []

	while not job.is_done and len(prs) < 20:
		progress = job.status()
		prs.append(progress)
		time.sleep(2)

	job.complete()

	progress = job.status()
	print(progress)

	print('done')

	assert job.is_done
	assert job.result is not None


from .prompting import *
from .util import repo_root
from .benchmarks import GSM8k


def test_gsm8k():

	src = GSM8k(repo_root() / 'benchmarks' / 'dev.jsonl')

	src.load()

	print(src)



def test_few_shot():

	# shot_source = PromptFile(repo_root() / 'benchmarks' / 'dev.jsonl')
	shot_source = GSM8k(repo_root() / 'benchmarks' / 'dev.jsonl').load()
	eval_source = GSM8k(repo_root() / 'benchmarks' / 'eval.jsonl').load()

	cot = ChainOfThought(shots_file=shot_source, num_shots=5, seed=11)

	ctx = next(eval_source)
	ctx.include(cot)

	print(ctx)

	prompt = ctx['prompt']

	assert ctx['seed'] == 1999951809
	assert ctx['shot_IDs'] == [579, 152, 342, 707, 908]
	assert ctx['index'] == 0

	print(prompt)












