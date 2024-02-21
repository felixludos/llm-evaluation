from .imports import *
from .util import deep_update



class Runner(fig.Configurable):
	model = None
	@property
	def is_loaded(self):
		return self.model is not None


	def load(self):
		raise NotImplementedError



@fig.component('default-huggingface')
class DefaultRunner(Runner):
	def __init__(self, model_id: str, model_args=None, tokenizer_args=None, generate_args=None, **kwargs):
		super().__init__(**kwargs)
		self.model = None
		self.tokenizer = None

		self.model_id = model_id
		self.model_args = model_args or {}
		self.tokenizer_args = tokenizer_args or {}
		self.generate_args = generate_args or {}


	def load(self):
		if self.is_loaded:
			return

		model_id = self.model_id
		model_args = self.model_args
		tokenizer_args = self.tokenizer_args

		# torch_dtype=torch.bfloat16
		model = AutoModelForCausalLM.from_pretrained(model_id, **model_args)
		tokenizer = AutoTokenizer.from_pretrained(model_id, **tokenizer_args)

		self.tokenizer = tokenizer
		self.model = model


	def generate(self, text: str, **params):
		'''top level function, not really used by tasks'''
		if not self.is_loaded:
			raise ValueError("Model not loaded")
		params = deep_update(self.generate_args, params)
		return self.get_response(text, params)


	def get_response(self, text: str, params: dict):
		input_ids = self.tokenizer.encode(text, return_tensors='pt').to(self.model.device)
		# with torch.no_grad():
		output = self.model.generate(input_ids, **params)
		num_input_tokens, num_output_tokens = input_ids.size(1), output.size(1)
		response = self.tokenizer.decode(output[0], skip_special_tokens=True)
		return {'response': response, 'inp_tok': num_input_tokens, 'out_tok': num_output_tokens}


	# def get_probs(self):























