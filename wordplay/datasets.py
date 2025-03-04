from .imports import *
from omniply.apps import Table
from omniply.apps.training import Frame
from .abstract import AbstractDataset, AbstractPlanner, AbstractSample, AbstractSystem
from .mixins import Describable, DESCRIPTION
from .errors import NoMoreSamplesError, NoNewSamplesError



class Planner(AbstractPlanner):
	def __init__(self, src: AbstractDataset, *, shuffle: bool = None, seed: int = None,
				 index_key: str = 'index', **kwargs):
		super().__init__(src, **kwargs)
		self._src = src
		self._index_key = index_key
		if shuffle:
			indices = list(range(src.size))
			random.Random(seed).shuffle(indices)
		else:
			indices = None
		self._indices = indices
		self._offset = 0
		self._num_iterations = 0


	_NoMoreSamplesError = NoMoreSamplesError
	def draw(self) -> Dict[str, Any]:
		if self._offset >= self._src.size:
			raise self._NoMoreSamplesError(f'{self._src}')
		data = {self._index_key: self._offset if self._indices is None else self._indices[self._offset]}
		self._offset += 1
		return data


	def step(self) -> Dict[str, Any]:
		self._num_iterations += 1
		return self.draw()


	def generate(self) -> Iterator[Dict[str, Any]]:
		while self._offset < self._src.size:
			yield self.step()


	def expected_iterations(self) -> Optional[int]:
		return self._src.size - self._num_iterations



class SampleInfo(DictGadget):
	pass



class Sample(Describable, Context, AbstractSample):
	_SampleInfo = SampleInfo
	def __init__(self, info: dict[str, Any], *, plan: AbstractPlanner, allow_draw: bool = True, **kwargs):
		if isinstance(info, dict):
			info = self._SampleInfo(info)
		super().__init__(**kwargs)
		self._info = info
		self._plan = plan
		self._allow_draw = allow_draw
		self.include(info)


	def describe(self) -> DESCRIPTION:
		return {'gadgets': list(self.gadgetry()), **self._info.data}


	def gadgetry(self) -> Iterator[AbstractGadget]:
		for gadget in self.vendors():
			if gadget is not self._info:
				yield gadget


	@property
	def plan(self) -> AbstractPlanner:
		return self._plan


	def _new(self, *, plan=None, allow_draw=None, **kwargs) -> 'Sample':
		if plan is None:
			plan = self._plan
		if allow_draw is None:
			allow_draw = self._allow_draw
		new = self.__class__(plan.draw(), plan=plan, allow_draw=allow_draw, **kwargs)
		new.extend(tuple(self.gadgetry()))
		return new


	def new(self, size: int = None) -> 'Sample':
		if self._allow_draw: return self._new()
		raise NoNewSamplesError(f'creating new samples using the current sample is currently not allowed')



class SimpleSystem(Describable, ToolKit, AbstractSystem):
	def __init__(self, dataset: AbstractDataset, *gadgets, **kwargs):
		super().__init__(dataset, *gadgets, **kwargs)
		self._dataset = dataset
		self._gadgets = gadgets


	def gadgetry(self) -> Iterator[AbstractGadget]:
		yield from self._gadgets


	@property
	def dataset(self):
		return self._dataset


	@property
	def size(self) -> Optional[int]:
		return self.dataset.size


	def iterate(self, *gadgets: AbstractGadget, plan: Optional[AbstractPlanner] = None,
				shuffle: Optional[bool] = None, allow_draw: bool = True) -> Iterator[AbstractSample]:
		yield from self.dataset.iterate(*gadgets, *self.gadgetry(), shuffle=shuffle, allow_draw=allow_draw)


	def sample(self, *gadgets: AbstractGadget, shuffle: bool = True, **kwargs) -> AbstractSample:
		return self.dataset.sample(*gadgets, *self.gadgetry(), shuffle=shuffle, **kwargs)


	def describe(self) -> DESCRIPTION:
		return {'dataset': self.dataset, 'gadgets': list(self.gadgetry())}



class System(SimpleSystem):
	def __init__(self, dataset: AbstractDataset, env: Dict[str, AbstractGadget], **kwargs):
		super().__init__(dataset, *env.values(), **kwargs)
		self._env = env


	def gadgetry(self) -> Iterator[AbstractGadget]:
		yield from self._env.values()


	def announce(self) -> str:
		tbl = [('dataset', '\n'.join(map(str, self.dataset.genes())), self.dataset)]
		for name, gadget in self._env.items():
			tbl.append((name, '\n'.join(map(str, gadget.genes())), gadget))
		return tabulate(tbl, tablefmt='fancy_grid')


	def describe(self) -> DESCRIPTION:
		return {'dataset': self.dataset, **self._env}



class Dataset(Describable, AbstractDataset):
	_Planner = Planner
	_Sample = Sample
	def iterate(self, *gadgets: AbstractGadget, plan: Optional[AbstractPlanner] = None,
				shuffle: Optional[bool] = None, allow_draw: bool = True) -> Iterator[Sample]:
		if plan is None:
			plan = self._Planner(self, shuffle=shuffle)
		for info in plan.generate():
			sample = self._Sample(info, plan=plan, allow_draw=allow_draw)
			yield sample.include(*gadgets, self)

	def display(self, level: str = None, **kwargs) -> str:
		base = super().display(level=level, **kwargs)
		assert '(' in base, f'confused: {base!r}'
		size = self.size
		if size is not None:
			name, params = base.split('(', 1)
			return f'{name}[{self.size}]({params}'
		return base


	def sample(self, *gadgets: AbstractGadget, shuffle: bool = True, **kwargs) -> Sample:
		return next(self.iterate(*gadgets, shuffle=shuffle, **kwargs))



@fig.component('table')
class TableDataset(fig.Configurable, Dataset, Table):
	def __init__(self, data: dict[str, list[Any]] = None, **kwargs):
		super().__init__(data_in_columns=data, **kwargs)


	@property
	def size(self):
		return self.number_of_rows



@fig.component('file')
class FileDataset(TableDataset):
	def __init__(self, path: Path, **kwargs):
		super().__init__(data=None, **kwargs)
		self._path = path


	@property
	def path(self) -> Path:
		return Path(self._path)


	def describe(self) -> DESCRIPTION:
		return {'path': self.path}


	def _load_data(self) -> dict[str, list[Any]]:
		return self._validate_rows(self._load_rows(self.path, columns=self.columns))


	def _load_rows(self, path: Path = None, *, columns: Optional[Iterable[str]] = None, default_text_key='text',
				   json_obj_key='_key') -> list[dict[str,Any]]:
		if path is None:
			path = self.path
		assert path.exists(), f'Path does not exist: {path}'

		if path.suffix == '.jsonl':
			with path.open('r') as f:
				rows = [json.loads(line) for line in f]
		elif path.suffix == '.txt':
			with path.open('r') as f:
				rows = [line.strip() for line in f]
		elif path.suffix == '.csv':
			with path.open('r') as f:
				rows = list(csv.DictReader(f, fieldnames=columns))

		elif path.suffix == '.json':
			full = json.load(path.open('r'))
			assert isinstance(full, (list, dict)), f'Invalid JSON file: {path}'
			if isinstance(full, list):
				rows = full
			else:
				rows = []
				for key, obj in full.items():
					if isinstance(obj, str):
						obj = {default_text_key: obj}
					assert isinstance(obj, dict), f'Invalid JSON object: {obj}'
					obj[json_obj_key] = key
					rows.append(obj)

		else:
			raise ValueError(f'Unsupported file type: {path.suffix}')

		if isinstance(rows[0], str):
			rows = [{default_text_key: row} for row in rows]

		return rows



class MultipleChoiceQuestions(Dataset): # TODO: maybe add support for answer space
	pass



@fig.component('mmlu/single')
class SingleMMLU(FileDataset, MultipleChoiceQuestions):
	_columns = ('question', 'A', 'B', 'C', 'D', 'answer') # columns of the raw csv files
	def _load_data(self) -> dict[str, list[Any]]:
		data = super()._load_data()
		choices = list(zip(data['A'], data['B'], data['C'], data['D']))
		del data['A'], data['B'], data['C'], data['D']
		data['choices'] = choices
		self._columns = ('question', 'choices', 'answer')
		order = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
		data['answer'] = [order[a] for a in data['answer']]
		return data

	@property
	def name(self):
		return f'MMLU-{self.path.stem}'



@fig.component('gsm8k')
class GSM8k(FileDataset):
	def _load_data(self) -> dict[str, list[Any]]:

		data = super()._load_data()

		full = data['answer']

		expr = [re.findall(r'<<.*?>>', line) for line in full]
		expr = [[e[2:-2] for e in line] for line in expr]

		full = [re.sub(r'<<.*?>>', '', line) for line in full]

		rationale, answer = zip(*[line.split('\n####') for line in full])
		rationale = [line.strip() for line in rationale]
		answer = [line.strip() for line in answer]

		data['rationale'] = rationale
		data['answer'] = answer
		data['expr'] = expr

		return data











