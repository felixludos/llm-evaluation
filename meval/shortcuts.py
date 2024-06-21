from .imports import *

from .descriptions import Describable
from .endpoints import ChatEndpoint
from .basics import Template



@fig.component('quick-response')
class QuickResponse(fig.Configurable, Selection, Describable):
	def __init__(self, prompt: str | AbstractGadget, endpoint: str | ChatEndpoint, *, name: str = 'response',
				 show_prompt: str | bool = False, gate=None, **kwargs):
		if gate is None:
			gate = {}
		gate['response'] = name
		if show_prompt:
			gate['prompt'] = show_prompt if isinstance(show_prompt, str) else 'prompt'
		if isinstance(prompt, str):
			prompt = Template(prompt, name='prompt')
		if isinstance(endpoint, str):
			endpoint = ChatEndpoint(url=endpoint)
		super().__init__(gate=gate, **kwargs)
		self.prompt = prompt
		self.endpoint = endpoint
		self.include(prompt, endpoint)
		endpoint.connect() # TODO: should be in staging


	def describe(self):
		return {
			'prompt': self.prompt.describe(),
			'endpoint': self.endpoint.describe(),
		}



def test_quick():

	q = QuickResponse('Test prompt', 'http://127.0.0.1:4010')

	ctx = Context(q)

	print()
	print(list(ctx.gizmos()))
	print(ctx['response'])
	print(ctx)


def test_double_quick():

	q1 = QuickResponse('Test prompt', 'http://127.0.0.1:4010', name='r1')

	q2 = QuickResponse('Test prompt using {r1}', 'http://127.0.0.1:4010', name='r2', show_prompt='p2')

	ctx = Context(q1, q2)

	print()
	print(list(ctx.gizmos()))
	print(ctx['r2'])
	print(ctx['r1'])
	print(ctx['p2'])




