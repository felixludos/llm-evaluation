from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations
from .util import App, post, get, config_data_root, data_root
# from .models import Runner



@fig.component('manager-server')
class Manager_Server(App):
	def __init__(self, manager, **kwargs):
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
	async def create(self, name: str, item: str = 'task'):
		out = self.manager.create_task(name, task_key=item)
		return out


	@post
	async def create_custom(self, config: dict, item: str = 'task'):
		out = self.manager.create_task(config, task_key=item)
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
	async def terminate(self, code: str | int):
		out = self.manager.terminate_task(code)
		return out


	@get
	async def complete(self, code: str | int):
		out = self.manager.complete_task(code)
		return out


	@get
	async def chain(self, prev: str | int, link: str | int):
		out = self.manager.chain_tasks(prev, link)
		return out



@fig.component('llm-server')
class LLM_Server(Manager_Server):



	pass




@fig.script('start-server')
def start_server(cfg: fig.Configuration):
	cfg.push('server._type', 'manager-server', overwrite=False, silent=True)
	app = cfg.pull('server')
	app.record_description()
	app.run()














