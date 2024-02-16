from .imports import *

from .iteration import Job, ResourceAware



class DemoLoader(ResourceAware):
	tokenizer = None
	model = None

	def heavy(self):
		torch.set_default_device("cuda")
		self.tokenizer = AutoTokenizer.from_pretrained("microsoft/phi-2", trust_remote_code=True)

		self.model = AutoModelForCausalLM.from_pretrained("microsoft/phi-2", torch_dtype="auto", trust_remote_code=True)


	def _run_job(self):
		self.heavy()


def test_heavy_job():

	job = DemoLoader()
	job.start()

	while not job.is_done:
		progress = job.progress()
		print(progress)
		time.sleep(1)

	progress = job.progress()
	print(progress)

	print('done')

	assert job.is_done
	assert job.model is not None
	assert job.tokenizer is not None
	# assert job.model is not None
	# assert job.tokenizer is not None
















