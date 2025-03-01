from .imports import *
from .errors import InteractionFailed
from .endpoints import Endpoint



class Interaction(ToolKit):
	_InteractionFailed = InteractionFailed
	def __init__(self, endpoint: Union[str, Endpoint] = None, **kwargs):
		super().__init__(**kwargs)
		self.endpoint = Endpoint.connect(endpoint)



class SimpleInteraction(Interaction):
	def __init__(self, endpoint: Union[str, Endpoint] = None, retries: int = 0, **kwargs):
		super().__init__(endpoint=endpoint, **kwargs)
		self.retries = retries


	def __repr__(self):
		return f'<{self.__class__.__name__} {self.endpoint}>'


	def validate(self, prompt: str, response: str) -> bool:
		return True


	@tool('response')
	def get_response(self, prompt: str) -> str:
		for _ in range(self.retries):
			response = self.endpoint.get_response(prompt)
			if self.validate(prompt, response):
				return response
		raise ValueError(f'Failed to validate response after {self.retries} attempts.')










