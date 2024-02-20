from .imports import *



def repo_root():
	return Path(__file__).parent.parent



@fig.autocomponent('default-config-root')
def config_job_root():
	return repo_root() / 'job-config'



def config_model_root():
	return repo_root() / 'config' / 'models'



def config_data_root():
	return repo_root() / 'config' / 'data'



def data_root():
	return repo_root() / 'out-data'



class _hook:
	def __init__(self, fn=None, *args, **kwargs):
		super().__init__()
		self.fn = fn
		self.name = None if fn is None else fn.__name__
		self._got_called = False
		self.args, self.kwargs = args, kwargs

	def __call__(self, fn):
		self._got_called = True
		self.name = self.fn or fn.__name__
		self.fn = fn

	def package(self, app):
		assert self.name is not None
		self.name = f'/{self.name}'
		return self.fn.__get__(app, type(app))


class post(_hook):
	pass


class get(_hook):
	pass


class App(fig.Configurable):
	def __init__(self, *, host='localhost', port=8000):
		app = FastAPI()
		self.app = app
		self.host = host
		self.port = port

		for item in dir(type(self)):
			if item.startswith('_'):
				continue
			attr = getattr(self, item)
			if isinstance(attr, _hook):
				fn = attr.package(self)
				if isinstance(attr, post):
					app.post(attr.name, *attr.args, **attr.kwargs)(fn)
				elif isinstance(attr, get):
					app.get(attr.name, *attr.args, **attr.kwargs)(fn)
				else:
					raise TypeError(f"Unknown hook type: {type(attr)}")

	def run(self):
		# self.cfg.print('Starting server')
		uvicorn.run(self.app, host=self.host, port=self.port)



def deep_update(info1: dict, info2: dict, *other: dict):
	if len(other):
		merged = deep_update(info1, info2)
		return deep_update(merged, *other)

	merged = {}
	for k1, v1 in info1.items():
		if k1 in info2:
			v2 = info2[k1]
			if isinstance(v1, dict) and isinstance(v2, dict):
				merged[k1] = deep_update(v1, v2)
			merged[k1] = v2
		else:
			merged[k1] = v1
	return merged




