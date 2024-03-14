from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations, Chainable, PersistentTask, Subtask
from . import util


@fig.component('dummy')
class DummyTask(ExpectedResources, fig.Configurable):
	def __init__(self, num=100, **kwargs):
		super().__init__(**kwargs)
		self.num = num
		self.itr = 0


	def _run(self):
		for _ in range(10):
			time.sleep(1)
			self.itr += 1


	def status(self, fast: bool = False):
		return {'itr': self.itr, **super().status(fast=fast)}



@fig.component('loader')
class LoadTask(ExpectedResources, fig.Configurable):
	def __init__(self, runner, expected_duration=None, expected_gpu=None, **kwargs):
		if isinstance(expected_duration, (int, float)):
			expected_duration = timedelta(seconds=expected_duration)
		super().__init__(**kwargs)
		self.expected_duration = expected_duration
		self.runner = runner


	def _run(self):
		self.runner.load()



class AbstractGenerateTask(Subtask, ExpectedResources, fig.Configurable):
	def __init__(self, generate_args=None, template: str = None, tmplpath: Path | str = None, **kwargs):
		if tmplpath is not None:
			tmplpath = Path(tmplpath)
		assert template is None or tmplpath is None, 'Cannot specify both template and tmplpath'
		assert tmplpath is None or tmplpath.exists(), f'Template path does not exist: {tmplpath}'
		if tmplpath is not None:
			with open(tmplpath, 'r') as f:
				template = f.read()
		super().__init__(**kwargs)
		self.generate_args = generate_args or {}
		self.template = template


	_input_keys = ('input', 'text', 'prompt', 'question')
	def _find_main_input(self, inputs: dict):
		for key in self._input_keys:
			if key in inputs:
				return inputs.pop(key)
		raise ValueError("No input text provided")


	def _to_prompt(self, text: str = None, **inputs: str):
		if self.template is None:
			if text is None:
				text = self._find_main_input(inputs)
			return text

		try:
			prompt = self.template.format(**inputs) if text is None else self.template.format(text=text, **inputs)
		except IndexError:
			pass
		else:
			return prompt

		if text is None:
			text = self._find_main_input(inputs)
		return self.template.format(text)


	def chain(self, loader: LoadTask):
		if loader.runner is None:
			raise ValueError("Loader has no runner")
		self.runner = loader.runner
		self.generate_args = util.deep_update(getattr(self.runner, 'generate_args', {}), self.generate_args)
		return self



@fig.component('generate')
class GenerateTask(AbstractGenerateTask):
	class _Stream(TextStreamer):
		def __init__(self, tokenizer: "AutoTokenizer", skip_prompt: bool = False, **decode_kwargs):
			super().__init__(tokenizer=tokenizer, skip_prompt=skip_prompt, **decode_kwargs)
			self.num_tokens = 0
			# self.response = []


		def put(self, value):
			if not self.next_tokens_are_prompt or not self.skip_prompt:
				self.num_tokens += len(value)
			return super().put(value)


		def on_finalized_text(self, text: str, stream_end: bool = False):
			# silence to avoid clogging stdout - response will be outputted when completed anyway
			# TODO: maybe compute metrics based on generated text (rather than tokens)
			# self.response.append(text)
			pass


	def __init__(self, text: str, stream_generation: bool = True, **kwargs):
		super().__init__(**kwargs)
		self.text = text
		self.as_stream = stream_generation
		self.stream = None
		self.response = None


	def _run(self):
		assert self.runner is not None and self.runner.is_loaded, "Runner not set"
		generate_args = util.deep_update(getattr(self.runner, 'generate_args', {}), self.generate_args)
		if self.as_stream:
			self.stream = self._Stream(self.runner.tokenizer, skip_prompt=True)
			generate_args['streamer'] = self.stream
		self.response = self.runner.get_response(self._to_prompt(self.text), generate_args)


	def _get_response(self):
		return self.response


	def status(self, fast: bool = False):
		progress = super().status()
		if self.stream is not None:
			progress['tokens'] = self.stream.num_tokens
			if 'duration' in progress:
				progress['token_rate'] = progress['tokens'] / progress['duration'].total_seconds()
			elif 'started' in progress:
				progress['token_rate'] = progress['tokens'] / progress['started'].total_seconds()
		return progress



@fig.component('chatgen')
class ChatTask(GenerateTask):
	def _to_prompt(self, text: str = None, **inputs: str):
		tokenizer = self.runner.tokenizer
		chat = [
			{"role": "user", "content": super()._to_prompt(text, **inputs)},
		]
		prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
		return prompt



@fig.component('benchmark')
class BenchmarkTask(ExpectedIterations, PersistentTask, AbstractGenerateTask):
	def __init__(self, path: str | Path, outpath=None, lazy_loading=False,
				 input_keys=('linenum',), **kwargs):
		path = Path(path)
		assert path.exists(), f'Path does not exist: {path}'
		outpath = Path(outpath)
		if lazy_loading and path.suffix not in {'.txt', '.jsonl', '.csv'}:
			raise ValueError(f"Lazy loading only supported for {{txt, jsonl, csv}} files, not {path.suffix}")
		super().__init__(**kwargs)
		self.lazy_loading = lazy_loading
		self.runner = None
		self.path = path
		self.outpath = outpath
		self.outwriter = None
		self.input_keys = input_keys
		self.input_items = None
		self.first_item = None
		self.total_prompt_tokens = 0
		self.total_response_tokens = 0


	def reset(self):
		super().reset()
		self.outwriter = None
		self.input_items = None
		self.first_item = None
		self.total_prompt_tokens = 0
		self.total_response_tokens = 0


	def _prepare(self):
		if self.input_items is None and not self.lazy_loading:
			self.input_items = list(self._input_item_stream())
		if self.input_items is not None:
			self.expected_num_iterations = len(self.input_items)
		self.outwriter = self.outpath.open('a')


	_line_number_key = 'linenum'
	def _input_item_stream(self):
		if self.input_items is not None:
			yield from self.input_items
			return
		if self._line_number_key is None:
			yield from self._load_input_items()
		else:
			for i, item in enumerate(self._load_input_items()):
				if self._line_number_key not in item:
					item[self._line_number_key] = i
					yield item


	def _load_input_items(self) -> Iterable[dict]:
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
					if self._line_number_key is not None:
						obj[self._line_number_key] = key
					yield obj

		else:
			raise ValueError(f'Unsupported file type: {self.path.suffix}')


	def status(self, fast: bool = False):
		progress = super().status(fast=fast)
		if progress.get('num_iterations'):
			progress['total_out_tokens'] = self.total_response_tokens
			progress['total_inp_tokens'] = self.total_prompt_tokens
			progress['out_tokens_per_item'] = progress['total_out_tokens'] / progress['num_iterations']
			progress['inp_tokens_per_item'] = progress['total_inp_tokens'] / progress['num_iterations']
			if 'duration' in progress:
				progress['token_rate'] = progress['total_tokens'] / progress['duration'].total_seconds()
			elif 'started' in progress:
				progress['token_rate'] = progress['total_tokens'] / progress['started'].total_seconds()
		return progress


	def _process_response(self, input_item: dict, prompt: str, response: dict):
		if self.first_item is None:
			self.first_item = {'input': input_item, 'prompt': prompt, 'response': response}

		if self.input_keys is not None:
			for key in self.input_keys:
				if key in input_item:
					response[key] = input_item[key]

		self.total_prompt_tokens += response['inp_tok']
		self.total_response_tokens += response['out_tok']

		if self.outwriter is None:
			with self.outpath.open('a') as f:
				json.dump(response, f)
				f.write('\n')
		else:
			json.dump(response, self.outwriter)
			self.outwriter.write('\n')


	def _cleanup(self):
		if self.outwriter is not None:
			self.outwriter.close()


	def _generate_stream(self):
		for item in self._input_item_stream():
			prompt = self._to_prompt(**item)
			response = self.runner.get_response(prompt, self.generate_args)
			self._process_response(item, prompt, response)
			yield



class FewShotTask(BenchmarkTask):
	def __init__(self, num_shot: int = 10, shot_path: Path | str = None, seed: int = 7427466391, **kwargs):
		if shot_path is not None and num_shot > 0:
			shot_path = Path(shot_path)
			assert shot_path.exists(), f'Path does not exist: {shot_path}'
		super().__init__(**kwargs)
		self.num_shot = num_shot
		self.shot_path = shot_path
		self.seed = seed
		self.rng = random.Random(seed)


	def _select_shots(self, items: list):
		return self.rng.sample(items, self.num_shot)





















