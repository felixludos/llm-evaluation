from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations
from .util import App, post, get, config_data_root, data_root
# from .models import Runner



@fig.component('manager-server')
class Manager_Server(App):
	def __init__(self, manager, **kwargs):
		super().__init__(**kwargs)
		self.manager = manager


	@get
	async def ping(self):
		return 'pong'


	@get
	async def snapshot(self):
		return ResourceAware.resource_snapshot()


	@get
	async def create(self, id: str, **params):
		out = self.manager.create_job(id, **params)
		return out


	@get
	async def start(self, id: str | int):
		out = self.manager.start_task(id)
		return out


	@get
	async def tasks(self, limit: int = 5, status: bool = False):
		out = self.manager.report(limit, status=status)
		return out


	@get
	async def status(self, id: str | int):
		out = self.manager.task_status(id)
		return out


	@get
	async def terminate(self, id: str | int):
		out = self.manager.terminate_task(id)
		return out


	@get
	async def complete(self, id: str | int):
		out = self.manager.complete_task(id)
		return out


	@get
	async def chain(self, prev: str | int, link: str | int):
		out = self.manager.chain_tasks(prev, link)
		return out


	# def _load_meta_config(self, ident: str):
	# 	options = list(self.config_root.glob(f'{ident}*'))
	# 	if not options:
	# 		raise HTTPException(status_code=500, detail=f"Meta file not found: {ident}")
	# 	if len(options) > 1:
	# 		raise HTTPException(status_code=500,
	# 							 detail=f"Multiple meta files found: {', '.join(o.name for o in options)}")
	#
	# 	meta = fig.create_config(options[0])
	# 	meta.push('ident', ident, overwrite=True, silent=True)
	# 	meta.push('config-path', str(options[0]), overwrite=False, silent=True)
	# 	return meta


	# @staticmethod
	# def create_outdir(ident: str, root: Path):
	# 	now = datetime.now().strftime(f"%Y%m%d-%H%M%S")
	# 	outdir = root / f"{ident}_{now}"
	# 	outdir.mkdir(exist_ok=True)
	# 	return outdir
	#
	#
	# @get
	# async def track(self, ident: str, force: bool = False):
	# 	if self.outdir is None or force:
	# 		self.outdir = self.create_outdir(ident, self.out_root)
	# 	return {'outdir': str(self.outdir)}
	#
	#
	# @post
	# async def load(self, ident: str, force: bool = False):
	# 	if self.runner is None or force:
	#
	# 		meta = self._load_meta_config(ident)
	#
	# 		meta.push('runner._type', 'default', overwrite=False, silent=True)
	# 		self.runner = meta.pull('runner')
	#
	# 	if not self.runner.is_loaded():
	#
	# 		if self.outdir is not None:
	# 			save_json(self._get_resource_info(), self.outdir / 'preload-resources.json')
	#
	# 		self.runner.load()
	#
	# 		if self.outdir is not None:
	# 			save_json(self._get_resource_info(), self.outdir / 'postload-resources.json')
	#
	#
	#
	# 	pass
	#
	#
	# 	model_id = payload.name or self.model_id
	#
	# 	status = 'loaded' if self.model is None else 'null'
	#
	# 	if self.model is None:
	#
	# 		model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, **self.model_args)
	# 		tokenizer = AutoTokenizer.from_pretrained(model_id, **self.tokenizer_args)
	#
	# 		self.model = model
	# 		self.tokenizer = tokenizer
	#
	# 	elif self.model_id != model_id:
	# 		raise ValueError(f"Model already loaded: {self.model_id}")
	#
	# 	return {'model_id': model_id, 'status': status}
	#
	#
	# @get
	# async def autocomplete(self, text: str, max_length: int = 50, num_return_sequences: int = 1):
	# 	if self.model is None:
	# 		raise ValueError("Model not loaded")
	#
	# 	input_ids = self.tokenizer.encode(text, return_tensors='pt')
	# 	input_ids = input_ids.to(self.model.device)
	#
	# 	output = self.model.generate(input_ids, max_length=max_length, num_return_sequences=num_return_sequences)
	#
	# 	return [self.tokenizer.decode(o, skip_special_tokens=True) for o in output]



@fig.script('start-server')
def start_server(cfg: fig.Configuration):
	cfg.push('server._type', 'manager-server', overwrite=False, silent=True)
	app = cfg.pull('server')
	app.run()














