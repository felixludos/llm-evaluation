from .imports import *

from omnibelt import pathfinder
from omniply import AbstractGig

from omniply import Context
from omniply.core.gadgets import SingleGadgetBase, GadgetFailure
from omniply.apps import Template, DictGadget




class PromptStreamer(PromptFile):
	_context_type = ItemContext


	def _generate_stream(self):
		if not self.lazy_loading and self.input_items is None:
			self.input_items = list(self._load_input_items())
		elif self.input_items is None:
			yield from self._load_input_items()
			return
		yield from self.input_items



@fig.component('default-prompter')
class DefaultPrompter(fig.Configurable, SingleGadgetBase):
	def __init__(self, **kwargs):
		assert 'gizmo' not in kwargs or kwargs['gizmo'] == 'prompt', \
			f'Cannot specify different gizmo in DefaultPrompter: {kwargs}'
		super().__init__(gizmo='prompt', **kwargs)


	_input_keys = ('input', 'text', 'question', 'prompt')
	def _grab_from(self, ctx: AbstractGig):
		for key in self._input_keys:
			try:
				return ctx[key]
			except GadgetFailure:
				pass
		raise ValueError(f"Item must contain at least one of: {self._input_keys}")



@fig.component('templated')
class TemplatePrompter(Template, fig.Configurable):
	def __init__(self, template: str = None, tmplpath: Path | str = None, **kwargs):
		if tmplpath is not None:
			tmplpath = Path(tmplpath)
		assert template is None or tmplpath is None, 'Cannot specify both template and tmplpath'
		assert tmplpath is None or tmplpath.exists(), f'Template path does not exist: {tmplpath}'
		if tmplpath is not None:
			template = tmplpath.read_text()
		super().__init__(template=template, gizmo='prompt', **kwargs)



@fig.component('few-shot')
class FewShotPrompter(fig.Configurable, ToolKit):
	def __init__(self, shots_file: str | Path | PromptFile, num_shots: int = 10, *, seed: int = None,
				 shot_template: str | Template = '{question}\n{answer}',
				 delimiter: str = '\n\n', **kwargs):
		if isinstance(shots_file, (str, Path)):
			shots_file = PromptFile(shots_file, lazy_loading=False)
		if isinstance(shot_template, str):
			shot_template = TemplatePrompter(shot_template)
		if shot_template is None:
			shot_template = DefaultPrompter()
		super().__init__(**kwargs)
		self.fewshots = shots_file
		self.master_seed = seed
		self.rng = random.Random(seed)
		self.num_shots = num_shots
		self.shot_template = shot_template
		self.delimiter = delimiter


	@tool('prompt')
	def get_prompt(self, item: dict, shots: str, delimiter: str = None):
		delimiter = delimiter or self.delimiter
		question_shot = self.render_shot(self.num_shots, item, answer='')
		return f'{shots}{delimiter}{question_shot}'


	def render_shot(self, idx: int, item: dict, **manual):
		ctx = Context(self.shot_template, DictGadget(item, idx=idx, **manual))
		return ctx['prompt']


	@tool('shots')
	def format_shots(self, shot_items: list[dict], delimiter: str = None):
		delimiter = delimiter or self.delimiter
		lines = []
		for idx, item in enumerate(shot_items):
			lines.append(self.render_shot(idx, item))
		return delimiter.join(lines)


	@tool('seed')
	def generate_seed(self):
		return (random if self.master_seed is None else self.rng).randint(0, 2**32)


	@tool('shot_IDs')
	def select_shots(self, seed: int = None):
		picks = (random if seed is None else random.Random(seed)).sample(range(len(self.fewshots)), self.num_shots)
		return picks


	@tool('shot_items')
	def get_shot_items(self, shot_IDs: list[int]):
		return [self.fewshots[i] for i in shot_IDs]



@fig.component('chain-of-thought')
class ChainOfThought(FewShotPrompter):
	def __init__(self, shot_template: str | Template = '{question}\n{rationale}\nFinal answer: {answer}', **kwargs):
		super().__init__(shot_template=shot_template, **kwargs)



