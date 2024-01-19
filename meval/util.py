from .imports import *


class _hook:
	def __init__(self, fn=None, *args, **kwargs):
		super().__init__()
		self.fn = fn
		self._got_called = False
		self.args, self.kwargs = args, kwargs

	def __call__(self, fn):
		self._got_called = True
		self.fn = fn

	def package(self, app):
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
					app.post(fn, *attr.args, **attr.kwargs)
				elif isinstance(attr, get):
					app.get(fn, *attr.args, **attr.kwargs)
				else:
					raise TypeError(f"Unknown hook type: {type(attr)}")

	def run(self):
		# self.cfg.print('Starting server')
		uvicorn.run(self.app, host=self.host, port=self.port)




