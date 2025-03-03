from .imports import *
from .errors import InteractionFailed
from .endpoints import Endpoint



class Interaction(ToolKit):
	_InteractionFailed = InteractionFailed
	def __init__(self, *, endpoint: Endpoint, **kwargs):
		super().__init__(**kwargs)
		self.endpoint = endpoint.validate()


	def __repr__(self):
		return f'<{self.__class__.__name__} {self.endpoint}>'



class SimpleInteraction(Interaction):
	def __str__(self):
		base = super().__str__()
		if '(' in base:
			name, params = base.split('(', 1)
			return f'{name}[{self.endpoint}]({params})'
		return f'{base}[{self.endpoint}]'


	@tool('resp')
	def send(self, prompt: str) -> JSONOBJ:
		return self.endpoint.send(self.endpoint.wrap_prompt(prompt))


	@tool('response')
	def get_response(self, resp: JSONOBJ) -> str:
		# resp = None
		# for _ in range(self.retries + 1):
		# 	resp = self.endpoint.send(self.endpoint.wrap_prompt(prompt))
		# 	if self.validate(prompt, resp):
		# 		return self.endpoint.extract_response(resp)
		# raise self._InteractionFailed(prompt, resp)
		return self.endpoint.extract_response(resp)



class SessionInteraction(Interaction):
	def __init__(self, *, endpoint: Union[str, Endpoint], role: str='user', response_role: str='assistant', **kwargs):
		super().__init__(endpoint=endpoint, **kwargs)
		self.response_role = response_role
		self.role = role


	@tool('resp')
	def send(self, prompt: str, session: Optional[List[Dict[str,str]]] = None) -> JSONOBJ:
		if session is None: session = []
		session.append({'role': self.role, 'content': prompt})
		return self.endpoint.send(self.endpoint.wrap_chat(session))


	@tool('response')
	def get_response(self, resp: JSONOBJ, session: Optional[List[Dict[str,str]]]) -> str:
		response = self.endpoint.extract_response(resp)
		session.append({'role': self.response_role, 'content': response})
		return response











