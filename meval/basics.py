from .imports import *

from .descriptions import Describable

from omniply.apps.templating import Template as _Template
from omniply.apps.gaps import Gapped



@fig.component('template')
class Template(fig.Configurable, Describable, Gapped, _Template):
	def __init__(self, template: str, name: str = 'output', gap: dict[str, str] = None):
		super().__init__(gizmo=name, template=template, gap=gap)


	def _grab_from(self, ctx) -> Any:
		reqs = {key: ctx.grab_from(ctx, self.gap(key)) for key in self.keys}
		return self.fill_in(reqs)


	def describe(self):
		'''
		should be overridden to include any necessary data
		(values don't have to be jsonable, as long as attrs are describable)
		'''
		return {'keys': [self.gap(key) for key in self.keys], 'template': self.template}



@fig.component('const')
class Constant(fig.Configurable, Describable, DictGadget):
	def __init__(self, data: dict[str, JSONABLE] = None, gap: dict[str, str] = None):
		if data is None:
			data = {}
		super().__init__(data, gap=gap)


	def describe(self):
		'''
		should be overridden to include any necessary data
		(values don't have to be jsonable, as long as attrs are describable)
		'''
		return self.data







