from .imports import *

from omnibelt import pathfinder
from omniply import AbstractGig

from omniply import Context
from omniply.core.gadgets import SingleGadgetBase, GadgetFailure
from omniply.apps import Template, DictGadget, StreamMogul




class PromptFile:
	def __init__(self, path: Path | str, *, lazy_loading=False, **kwargs):
		path = Path(path)
		assert path.exists(), f'Path does not exist: {path}'
		if lazy_loading:
			raise NotImplementedError('not currently supported')
		if lazy_loading and path.suffix not in {'.txt', '.jsonl', '.csv'}:
			raise ValueError(f"Lazy loading only supported for {{txt, jsonl, csv}} files, not {path.suffix}")
		super().__init__(**kwargs)
		self.path = path
		self.input_items = list(self._load_input_items())
		self.lazy_loading = lazy_loading

	def __getitem__(self, idx):
		'''doesn't announce the item (it won't be a context)'''
		return self.input_items[idx]


	def __len__(self):
		return len(self.input_items)


	def __iter__(self):
		yield from self.input_items


	_line_number_key = 'linenum'
	def _load_input_items(self) -> Iterable[dict]:
		for i, item in enumerate(self._load_unnumbered_input_items()):
			if self._line_number_key is not None and self._line_number_key not in item:
				item[self._line_number_key] = i
			yield item
	def _load_unnumbered_input_items(self) -> Iterable[dict]:
		assert self.path.exists(), f'Path does not exist: {self.path}'

		if self.path.suffix == '.jsonl':
			with self.path.open('r') as f:
				for line in f:
					obj = json.loads(line.strip())
					yield {'text': obj} if isinstance(obj, str) else obj
		elif self.path.suffix == '.txt':
			with self.path.open('r') as f:
				for line in f:
					yield {'text': line.strip()}
		elif self.path.suffix == '.csv':
			with self.path.open('r') as f:
				reader = csv.DictReader(f)
				yield from reader

		elif self.path.suffix == '.json':
			full = json.load(self.path.open('r'))
			assert isinstance(full, (list, dict)), f'Invalid JSON file: {self.path}'
			if isinstance(full, list):
				for obj in full:
					yield {'text': obj} if isinstance(obj, str) else obj
			else:
				for key, obj in full.items():
					if isinstance(obj, str):
						obj = {'text': obj}
					obj['_key'] = key
					yield obj

		else:
			raise ValueError(f'Unsupported file type: {self.path.suffix}')



class ItemContext(Context):
	def __init__(self, item: dict, **kwargs):
		super().__init__(**kwargs)
		assert 'item' not in kwargs, f'Cannot specify item in ItemContext: {kwargs}'
		self._item = item
		self.include(DictGadget(item, item=item))


	@property
	def item(self):
		return self._item



class PromptStreamer(PromptFile, StreamMogul):
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



