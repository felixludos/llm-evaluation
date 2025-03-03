from omniply.apps.staging import AbstractPlan

from .imports import *

from .descriptions import Describable, DESCRIBABLE


@fig.component('hf')
class HuggingFaceModel(Describable, ToolKit):
	def __init__(self, model_id: str, model_args=None, tokenizer_args=None, generate_args=None,
				 tokenizer_id: str = None, device: str = 'cuda', **kwargs):
		super().__init__(**kwargs)
		self.model = None
		self.tokenizer = None

		self.device = device
		self.model_id = model_id
		self.tokenizer_id = tokenizer_id or model_id
		self.model_args = model_args or {}
		self.tokenizer_args = tokenizer_args or {}
		self.generate_args = generate_args or {}


	def describe(self) -> DESCRIBABLE:
		return {
			'model': self.model_id,
			'device': self.device,
		}


	def _stage(self, plan: AbstractPlan = None):
		assert self.model is None, f'{self} is already loaded.'
		import torch
		from transformers import AutoModelForCausalLM, AutoTokenizer
		torch.set_default_device('cpu')
		self.model = AutoModelForCausalLM.from_pretrained(self.model_id, **self.model_args)
		self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_id, **self.tokenizer_args)
		if self.device is not None:
			self.model.to(self.device)


	def update_generate_args(self, params: dict[str, Any]):
		self.generate_args.update(params)
		return self


	def _generate(self, input_ids):
		output = self.model.generate(input_ids, **self.generate_args)
		num_input_tokens = input_ids.size(1)
		generated = output[0][num_input_tokens:]
		return generated


	@tool('response', 'inp_tok', 'out_tok')
	def get_response(self, prompt: str):
		input_ids = self.tokenizer.encode(prompt, return_tensors='pt').to(self.model.device)
		num_input_tokens = input_ids.size(1)
		generated = self._generate(input_ids)
		num_output_tokens = len(generated)
		response = self.tokenizer.decode(generated, skip_special_tokens=True)
		return response, num_input_tokens, num_output_tokens


	@tool('prompt')
	def format_prompt(self, chat: dict[str, Any]):
		return self.tokenizer.apply_chat_template(chat, tokenize=False)


class ChatFormatting(ToolKit):
	@tool('system')
	def default_system_prompt(self):
		return ('You are a knowledgeable and helpful assistant, ready to provide information, solve problems, '
				'and engage in meaningful conversations.')


	@tool('chat_in')
	def past_conversation(self, system: str):
		return [{'role': 'system', 'content': system}]


	@tool('chat')
	def default_chat(self, user: str, chat_in: list[dict[str, Any]]):
		return [*chat_in, {'role': 'user', 'content': user}]


	@tool('chat_out')
	def resulting_chat(self, response: str, chat: list[dict[str, Any]]):
		return [*chat, {'role': 'assistant', 'content': response}]



class MiniApple(HuggingFaceModel):
	def __init__(self, **kwargs):
		super().__init__('apple/OpenELM-270M-Instruct', tokenizer_id='meta-llama/Llama-2-7b-hf', **kwargs)
		self.model_args.update({'trust_remote_code': True, 'torch_dtype': 'auto'})
		self.tokenizer_args.update({'trust_remote_code': True})



class Phi3(HuggingFaceModel):
	def __init__(self, **kwargs):
		super().__init__('microsoft/Phi-3-mini-4k-instruct', **kwargs)
		self.model_args.update({'trust_remote_code': True, 'torch_dtype': 'auto'})
		self.tokenizer_args.update({'trust_remote_code': True})







