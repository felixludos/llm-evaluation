from .imports import *

from omnibelt import pathfinder
from omniply import AbstractGig

from omniply import Context
from omniply.core.gadgets import SingleGadgetBase, GadgetFailure
from omniply.apps import Template, DictGadget

from .benchmarks.base import PromptFile


@fig.component('default-prompter')
class DefaultPrompter(fig.Configurable, SingleGadgetBase):
	def __init__(self, **kwargs):
		assert 'gizmo' not in kwargs or kwargs['gizmo'] == 'prompt', \
			f'Cannot specify different gizmo in DefaultPrompter: {kwargs}'
		super().__init__(gizmo='prompt', **kwargs)


	_input_keys = ('input', 'text', 'question')
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
				 shot_template: str | Template = '{question}\n{answer}', question_template: str | Template = None,
				 delimiter: str = '\n\n', **kwargs):
		if isinstance(shots_file, (str, Path)):
			shots_file = PromptFile(shots_file)
		if isinstance(shot_template, str):
			shot_template = TemplatePrompter(shot_template)
		if shot_template is None:
			shot_template = DefaultPrompter()
		if question_template is None:
			question_template = shot_template
		elif isinstance(question_template, str):
			question_template = TemplatePrompter(question_template)
		super().__init__(**kwargs)
		self.support_source = shots_file
		self.master_seed = seed
		self.rng = random.Random(seed)
		self.num_shots = num_shots
		self.shot_template = shot_template
		self.question_template = question_template
		self.delimiter = delimiter


	@tool('prompt')
	def get_prompt(self, _question_shot: str, support_shots: str | list[str] = None, delimiter: str = None):
		delimiter = delimiter or self.delimiter
		terms = []
		if support_shots is not None:
			(terms.append if isinstance(support_shots, str) else terms.extend)(support_shots)
		terms.append(_question_shot)
		return delimiter.join(terms)


	@tool.from_context('_question_shot')
	def get_question_shot(self, ctx: Context):
		return self.render_shot(self.num_shots, self.question_template, ctx, answer='')
	# @get_question_shot.genes # TODO: tool should have a `genes` aux decorator
	# def _question_shot_genes(self, gizmo: str):
	# 	assert gizmo == 'question_shot'
	# 	yield from self.shot_template.genes('prompt')
	def genes(self, gizmo: str):
		if gizmo == '_question_shot':
			yield from self.shot_template.genes('prompt')
		else:
			yield from super().genes(gizmo)


	def render_shot(self, idx: int, template: Template, src: Context, **manual):
		shot = Context(template, DictGadget(shot_idx=idx, **manual), src)
		return shot['prompt']


	@tool('support_shots')
	def format_shots(self, support_IDs: list[int]):
		shots = [self.render_shot(idx, self.shot_template, self.support_source[ID])
				 for idx, ID in enumerate(support_IDs)]
		return shots


	@tool('seed')
	def generate_seed(self):
		return (random if self.master_seed is None else self.rng).randint(0, 2**32)


	@tool('support_IDs')
	def select_shots(self, seed: int = None):
		picks = (random if seed is None else random.Random(seed)).sample(
			range(len(self.support_source)), self.num_shots)
		return picks



@fig.component('chain-of-thought')
class ChainOfThought(FewShotPrompter):
	def __init__(self, question_template: str | Template = '{question}\n',
				 shot_template: str | Template = '{question}\n{rationale}\nFinal answer: {answer}', **kwargs):
		super().__init__(shot_template=shot_template, question_template=question_template, **kwargs)



