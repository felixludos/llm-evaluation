from .imports import *

from .tasks import start_task
from .client import Client
from .endpoints import ChatEndpoint



@fig.component('chat-interface')
class ChatInterface(Client, fig.Configurable):
	def __init__(self, endpoint: ChatEndpoint, system_message: str = None, *, host: str = None, port: int = 7860,
				 examples: list[str] = None, **kwargs):
		super().__init__(**kwargs)
		self.endpoint = endpoint
		self.system_message = system_message
		self.host = host
		self.port = port
		self._examples = examples


	def prepare(self, env) -> Self:
		super().prepare(env)
		self.endpoint.connect(env)
		return self


	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		import gradio as gr
		self.interface = gr.ChatInterface(
			self.step,
			# chatbot=gr.Chatbot(height=690),
			textbox=gr.Textbox(placeholder="Chat with me!", container=False, scale=7),
			# description=f"Spec: {self.info['model_device_type']} {self.info['model_dtype']}  "
			# 			f"|  version: {self.info['version']}",
			title=f"Chat with {self.endpoint.info['model_id']} ({self.endpoint.info['model_device_type']} "
				  f"{self.endpoint.info['model_dtype'].replace('torch.', '')})",
			examples=self._examples,
			retry_btn="Retry",
			undo_btn="Undo",
			clear_btn="Clear",
		)
		return {'host': self.host, 'port': self.port}


	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		self.interface.queue().launch(server_name=self.host, server_port=self.port)
		return {'reason': 'interface terminated unexpectedly'}


	def step(self, message: str, history: list[tuple[str, str]]):
		chat = []
		if self.system_message is not None:
			chat.append({'role': 'system', 'content': self.system_message})
		for user, assistant in history:
			chat.append({'role': 'user', 'content': user})
			chat.append({'role': 'assistant', 'content': assistant})
		chat.append({'role': 'user', 'content': message})

		response = ''
		for token in self.endpoint.stream(chat):
			response += token
			yield response



@fig.script('chat')
def start_gui(cfg: fig.Configuration):
	cfg.push('client._type', 'chat-interface', silent=True, overwrite=False)
	cfg.push('endpoint._type', 'chat-endpoint', silent=True, overwrite=False)
	return start_task(cfg, task_key='client')


