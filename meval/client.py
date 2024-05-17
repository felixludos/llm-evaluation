from .imports import *

from .abstract import AbstractTask, AbstractEnvironment

from functools import lru_cache, cached_property
import socket, requests



class ServerSeeker:
	def __init__(self, host: str = None):
		self.host = host or socket.gethostname()


	def _is_remote(self, host: str):
		# return host != self.host
		return False


	def _launch_event(self, events: list[JSONOBJ]):
		return next((item for item in events if item['event'] == 'launch'), None)


	def _static_server_status(self, events: list[JSONOBJ]) -> str:
		if any(item['event'] in ['exit', 'error'] for item in events):
			return 'dead'
		if events[-1]['event'] == 'launch':
			return 'launched'
		if events[-1]['event'] == 'connected':
			launch = self._launch_event(events)
			if self._is_remote(launch['host']):
				return 'remote'
			return 'candidate'


	def _is_live(self, url: str):
		try:
			requests.get(url)
		except requests.exceptions.ConnectionError:
			return False
		return True


	def to_server_url(self, events: list[JSONOBJ]) -> str:
		launch = self._launch_event(events)
		return f'http://{self.host or launch["host"]}:{launch["info"]["port"]}'


	def server_status(self, history: Iterator[JSONOBJ], *, verify_live=False,
					  include_remote: bool = False,
					  include_launched: bool = False, include_dead: bool = False) -> dict[str, list[JSONOBJ]]:

		_statuses = {
			'dead': 'Log confirms server is dead',
			'launched': 'Log only mentions server has launched',
			'remote': 'Log suggests server is live but it can\'t be verified because the host is remote',
			'unreachable': 'Server is confirmed to be unreachable (but it probably should be)',
			'candidate': 'Log suggests server is live (but not confirmed)',
			'live': 'Server is live (confirmed)',
		}
		_status_order = ['live', 'candidate', 'remote', 'launched', 'dead']

		candidates = {}
		for item in history:
			if 'category' in item:
				if item['category'] == 'server':
					ID = item['id']
					if item['event'] == 'launch':
						candidates[ID] = [item]
				elif item['category'] == 'helper' and item['event'] == 'report-death':
					ID = item['info'].get('id', None)
					candidates.pop(ID, None)

			elif item['id'] in candidates:
				candidates[item['id']].append(item)

		servers = [{'id': ID, 'status': self._static_server_status(events), 'events': events}
				   for ID, events in candidates.items()]

		if not include_dead:
			servers = [server for server in servers if server['status'] != 'dead']
		if not include_remote:
			servers = [server for server in servers if server['status'] != 'remote']
		if not include_launched:
			servers = [server for server in servers if server['status'] != 'launched']

		servers.sort(key=lambda item: _status_order.index(item['status']))

		for server in servers:
			# warning: this can't differentiate between a live server and a dead server that used the same port before
			if verify_live and server['status'] == 'candidate':
				server['status'] = 'live' if self._is_live(self.to_server_url(server['events'])) else 'unreachable'
			yield server


	def find_server(self, history: Iterator[JSONOBJ], *, server_reqs: dict[str, Any] = None) -> str:
		for server in self.server_status(history, verify_live=True):
			if server['status'] == 'live':
				info = server['events'][-1]['info']['server']
				if server_reqs is None or all(info.get(key, None) == value for key, value in server_reqs.items()):
					return self.to_server_url(server['events'])
		raise ValueError('No live servers found')



class Endpoint(fig.Configurable):
	def __init__(self, url: str = None, **kwargs):
		super().__init__(**kwargs)
		self.url = url


	def connect(self, env: AbstractEnvironment = None):
		if self.url is None:
			self.url = self._infer_server(env.world_history())


	def _infer_server(self, history: Iterator[JSONOBJ]) -> str:
		url = ServerSeeker().find_server(history)
		print(f'Selected server: {url}')
		return url


	@cached_property
	def info(self):
		return requests.get(f'{self.url}/info', headers={"Content-Type": "application/json"}).json()



@fig.modifier('toked')
class TokedEndpoint(Endpoint):
	def __init__(self, *, use_local: bool = True, **kwargs):
		super().__init__(**kwargs)
		self.tokenizer = None
		self.use_local = use_local


	def connect(self, env: AbstractEnvironment = None):
		super().connect(env)
		if self.use_local and self.tokenizer is None:
			try:
				from transformers import AutoTokenizer
			except ImportError:
				pass
			else:
				self.tokenizer = AutoTokenizer.from_pretrained(self.info['model_id'])


	def apply_chat_template(self, chat: list[dict[str, str]]) -> str:
		if self.tokenizer is None:
			raise ValueError('Tokenizer not loaded')
		prompt = self.tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
		return prompt


	def count(self, message: str | list[dict[str, str]]) -> int:
		if not isinstance(message, str):
			message = self.apply_chat_template(message)
		if self.tokenizer is None:
			data = requests.post(f'{self.url}/tokenize', json={'inputs': message}).json()
			# [{"id": 578,"text": " and","start": 18,"stop": 22},]
			return len(data)
		return len(self.tokenizer.encode(message)) - int(not isinstance(message, str)) # chat template repeats bos



@fig.component('chat-endpoint')
class ChatEndpoint(TokedEndpoint):
	@fig.silent_config_args('api_key')
	def __init__(self, *,
				 max_tokens: int = None,

				 seed: int = None,
				 stop: list[str] = None,
				 temperature: float = None,

				 top_p: float = None,

				 frequency_penalty: float = None,
				 presence_penalty: float = None,

				 api_key: str = '-', **kwargs):
		super().__init__(**kwargs)
		self.client = None
		self.api_key = api_key
		self._call_model = 'tgi'
		self._max_tokens = max_tokens
		self._call_args = {
			'seed': seed,
			'stop': stop,
			'temperature': temperature,
			'top_p': top_p,
			'frequency_penalty': frequency_penalty,
			'presence_penalty': presence_penalty,
		}
		self._call_args = {key: value for key, value in self._call_args.items() if value is not None}


	def connect(self, env: AbstractEnvironment = None):
		super().connect(env)
		assert self.client is None, f'already connected to {self.url}'
		from openai import OpenAI
		self.client = OpenAI(
			base_url=f"{self.url}/v1",
			api_key=self.api_key,
		)


	def _client_call(self, chat: list[dict[str, str]], **kwargs):
		max_new = self._max_tokens
		if isinstance(self, TokedEndpoint):
			num = self.count(chat)
			max_new = self.info['max_total_tokens'] - num
			max_new = max(1, max_new)

		return self.client.chat.completions.create(
			model=self._call_model,
			messages=chat,
			max_tokens = max_new,
			**self._call_args,
			**kwargs
		)


	def respond(self, chat: list[dict[str, str]]) -> str:
		return self._client_call(chat).choices[0].message.content


	def stream(self, chat: list[dict[str, str]]) -> Iterator[str]:
		for token in self._client_call(chat, stream=True):
			if token.choices[0].delta.content:
				yield token.choices[0].delta.content



class Client(AbstractTask):
	@property
	def category(self):
		return 'client'


	@property
	def quiet(self):
		return True



from omniply import AbstractGadget



class WorldClient(Client):
	def __init__(self, source: Iterable[Context], world: Iterable[AbstractGadget], **kwargs):
		self._progress = None
		self.source = source
		self.world = world


class IterationClient(Client):
	def __init__(self, source: Iterable[Context], world: Iterable[AbstractGadget], **kwargs):
		self._progress = None
		self.source = source
		self.world = world

	def _as_iterator(self, source: Iterable[Context]):
		for ctx in source:
			ctx.extend(self.world.values() if isinstance(self.world, dict) else self.world)
			yield ctx

	def launch(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		# prepare for the iteration

		self._progress = self._as_iterator(self.source)

		try:
			n = len(self.source)
		except TypeError:
			n = None

		return {'n': n}


	def complete(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		for ctx in self._iterator(source, **kwargs):
			self.step(ctx)
		return self.finish(report)


	def finish(self, report: Callable[[str, JSONOBJ], None]) -> JSONOBJ:
		pass


	def step(self, ctx: Context):
		raise NotImplementedError















