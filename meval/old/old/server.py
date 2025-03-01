from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations
from .util import App, post, get, config_data_root, data_root
from .manager import Manager
# from .models import Runner



@fig.component('manager-server')
class Manager_Server(App):
	def __init__(self, manager: Manager, **kwargs):
		super().__init__(**kwargs)
		self.manager = manager


	def record_description(self):
		self.manager.append_description({'server': {'host': self.host, 'port': self.port}})
		return self


	@get
	async def ping(self):
		return 'pong'


	@get
	async def snapshot(self):
		return ResourceAware.resource_snapshot()


	@get
	async def create(self, name: str, item: str = 'task', parent: str | int = None):
		out = self.manager.create_task(name, task_key=item, base=parent)
		return out


	@post
	async def custom(self, config: dict, item: str = 'task', parent: str | int = None):
		out = self.manager.create_task(config, task_key=item, base=parent)
		return out


	@get
	async def start(self, code: str | int):
		out = self.manager.start_task(code)
		return out


	@get
	async def tasks(self, limit: int = 5, status: bool = False):
		out = self.manager.report(limit, status=status)
		return out


	@get
	async def status(self, code: str | int):
		out = self.manager.task_status(code)
		return out


	@get
	async def meta(self, code: str | int):
		out = self.manager.task_meta(code)
		return out


	@get
	async def report(self, limit: int = None, status: bool = False):
		out = self.manager.report(limit=limit, status=status)
		return out


	@get
	async def terminate(self, code: str | int):
		out = self.manager.terminate_task(code)
		return out


	@get
	async def complete(self, code: str | int):
		out = self.manager.complete_task(code)
		return out


	@get
	async def response(self, code: str | int):
		out = self.manager.task_response(code)
		return out


	@get
	async def chain(self, prev: str | int, link: str | int):
		out = self.manager.chain_tasks(prev, link)
		return out



@fig.component('llm-server')
class LLM_Server(Manager_Server):
	def __init__(self, load_name: str = None, generate_name: str = None, **kwargs):
		super().__init__(**kwargs)
		self.load_name = load_name
		self.generate_name = generate_name
		self._load_id = None
		self._gen_ids = {}


	@get
	def load(self, name: str = None, block: bool = False):
		if name is None:
			name = self.load_name

		if self._load_id is None:
			self._load_id = self.manager.create_task(name)

		status = self.manager.task_status(self._load_id)

		if not status['is_done']:
			if block:
				self.manager.complete_task(self._load_id)
			elif not status['is_running']:
				self.manager.start_task(self._load_id)

		return {'code': self._load_id, 'status': self.manager.task_status(self._load_id)}


	@get
	def loadid(self):
		return self._load_id


	@post
	def generate(self, text: str = None, *, block: bool = False, code: int = None,
				 generate_args: dict = None, name: str = None):
		if code is None:
			if name is None:
				name = self.generate_name
			info = dict(_base=name, generate_args=generate_args)
			if text is None and generate_args is not None and 'text' in generate_args:
				text = generate_args.pop('text')
			if text is not None:
				info['text'] = text
			code = self.manager.create_task(info, base=self._load_id)

		response = None
		status = self.manager.task_status(code)
		if not status['is_done']:
			if block:
				self.manager.complete_task(code)
				response = self.manager.task_response(code)
			elif not status['is_running']:
				self.manager.start_task(code)
		else:
			response = self.manager.task_response(code)

		return {'code': code, 'status': status, 'response': response}


	@get
	def genstatus(self, code: int):
		return self.manager.task_status(code)



@fig.script('start-server')
def start_server(cfg: fig.Configuration):
	cfg.push('server._type', 'manager-server', overwrite=False, silent=True)
	app = cfg.pull('server')
	app.record_description()
	app.run()














