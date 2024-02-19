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
	def __init__(self, model_id: str, model_args=None, tokenizer_args=None,
				 max_new_tokens: int = 50, num_return_sequences: int = 1,
				 **kwargs):
		super().__init__(**kwargs)
		self.model = None
		self.tokenizer = None

		self.model_id = model_id
		self.model_args = model_args or {}
		self.tokenizer_args = tokenizer_args or {}

		self.max_new_tokens = max_new_tokens
		self.num_return_sequences = num_return_sequences


	def _load(self):
		model_id = self.model_id
		model_args = self.model_args
		tokenizer_args = self.tokenizer_args

		model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, **model_args)
		tokenizer = AutoTokenizer.from_pretrained(model_id, **tokenizer_args)

		self.tokenizer = tokenizer
		self.model = model


	def generate(self, text: str, max_new_tokens: int = None, num_return_sequences: int = None):
		if max_new_tokens is None:
			max_new_tokens = self.max_new_tokens
		if num_return_sequences is None:
			num_return_sequences = self.num_return_sequences
		if self.model is None:
			raise ValueError("Model not loaded")

		input_ids = self.tokenizer.encode(text, return_tensors='pt')
		input_ids = input_ids.to(self.model.device)

		with torch.no_grad():
			output = self.model.generate(input_ids, max_new_tokens=max_new_tokens,
										 num_return_sequences=num_return_sequences)
		return output


























