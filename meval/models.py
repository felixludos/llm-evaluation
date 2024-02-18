from .imports import *



class Runner(fig.Configurable):
	model = None
	@property
	def is_loaded(self):
		return self.model is not None


	def load(self, *args, **kwargs):
		if self.is_loaded:
			return
		self._load(*args, **kwargs)
		return self


	def _load(self, *args, **kwargs):
		raise NotImplementedError



@fig.component('default-huggingface')
class DefaultRunner(Runner):
	def __init__(self, model_id: str, model_args=None, tokenizer_args=None, **kwargs):
		super().__init__(**kwargs)
		self.model_id = model_id
		self.model_args = model_args or {}
		self.tokenizer_args = tokenizer_args or {}
		self.model = None
		self.tokenizer = None


	def _load(self):
		model_id = self.model_id
		model_args = self.model_args
		tokenizer_args = self.tokenizer_args

		model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, **model_args)
		tokenizer = AutoTokenizer.from_pretrained(model_id, **tokenizer_args)

		self.tokenizer = tokenizer
		self.model = model




























