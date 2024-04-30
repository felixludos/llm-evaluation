import omnifig as fig
# import asyncio
import requests
from functools import lru_cache, cached_property
import gradio as gr
# from huggingface_hub import InferenceClient
from openai import OpenAI


# @fig.component('chat-inference')
class ChatInference:
	# @fig.silent_config_args('api_key')
	def __init__(self, url: str, api_key: str = '-', system_message: str = None):
		self.client = OpenAI(
			base_url=f"{url}/v1",
			api_key=api_key,
		)
		self.url = url
		self.system_message = system_message


	@cached_property
	def info(self):
		# {'model_id': 'google/gemma-2b-it', 'model_sha': None, 'model_dtype': 'torch.float16',
		#  'model_device_type': 'cuda', 'model_pipeline_tag': None, 'max_concurrent_requests': 128, 'max_best_of': 2,
		#  'max_stop_sequences': 4, 'max_input_length': 1000, 'max_total_tokens': 1001, 'waiting_served_ratio': 0.3,
		#  'max_batch_total_tokens': 1001, 'max_waiting_tokens': 20, 'max_batch_size': None, 'validation_workers': 2,
		#  'max_client_batch_size': 4, 'version': '2.0.1', 'sha': '007d5e54aa76be74925501011fa8029bc5034f89',
		#  'docker_label': None}
		return requests.get(f'{self.url}/info', headers={"Content-Type": "application/json"}).json()


	def step(self, message: str, history: list[tuple[str, str]]):
		chat = []
		if self.system_message is not None:
			chat.append({'role': 'system', 'content': self.system_message})
		for user, assistant in history:
			chat.append({'role': 'user', 'content': user})
			chat.append({'role': 'assistant', 'content': assistant})
		chat.append({'role': 'user', 'content': message})

		chat_completion = self.client.chat.completions.create(
			model="tgi",
			messages=chat,
			max_tokens=500,
			temperature=0.6,
			# n=2,
			stream=True
		)

		response = ''
		for token in chat_completion:
			if token.choices[0].delta.content:
				response += token.choices[0].delta.content
				yield response


	def launch(self):
		gr.ChatInterface(
			self.step,
			chatbot=gr.Chatbot(height=690),
			textbox=gr.Textbox(placeholder="Chat with me!", container=False, scale=7),
			# description=f"Spec: {self.info['model_device_type']} {self.info['model_dtype']}  "
			# 			f"|  version: {self.info['version']}",
			title=f"Chat with {self.info['model_id']} ({self.info['model_device_type']} {self.info['model_dtype'].replace('torch.', '')})",
			examples=["Are tomatoes vegetables?"],
			retry_btn="Retry",
			undo_btn="Undo",
			clear_btn="Clear",
		).queue().launch()

# CUDA_AVAILABLE_DEVICES=0 text-generation-launcher --model-id google/gemma-2b-it --hostname localhost --port 8080 --max-batch-total-tokens 1001 --max-batch-prefill-tokens 1000 --max-input-tokens 1000 --max-total-tokens 1001

@fig.script('gui')
def start_gui(cfg: fig.Configuration):

	url = cfg.pull('url', 'http://127.0.0.1:8080')
	api_key = cfg.pull('api-key', '-', silent=True)

	system_message = cfg.pull('system', None)

	manager = ChatInference(url, api_key, system_message)

	manager.launch()


