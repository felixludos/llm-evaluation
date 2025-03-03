from .imports import *
from omniply.apps import Table
from omniply.apps.training import Frame
from .abstract import AbstractDataset, AbstractPlanner, AbstractSample, AbstractSystem



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


	def draw(self, size: int = 1) -> Dict[str, Any]:
		assert size == 1, f'Collection planner only supports size=1, not {size}'
		data = {self._index_key: self._offset if self._indices is None else self._indices[self._offset]}
		self._offset += 1
		return data


	def step(self, size: int = 1) -> Dict[str, Any]:
		assert size == 1, f'Collection planner only supports size=1, not {size}'
		self._num_iterations += 1
		return self.draw()


	def generate(self, size: int = 1) -> Iterator[Dict[str, Any]]:
		assert size == 1, f'Collection planner only supports size=1, not {size}'
		while self._offset < self._src.size:
			yield self.step()



class Sample(Frame, AbstractSample):
	pass



class System(AbstractSystem):
	def __init__(self, source: AbstractDataset, *gadgets, **kwargs):
		super().__init__(source, *gadgets, **kwargs)
		self._source = source


	def iterate(self, *gadgets: AbstractGadget,
				shuffle: Optional[bool] = None, allow_draw: bool = True) -> Iterator[AbstractSample]:
		yield from self._source.iterate(*gadgets, shuffle=shuffle, allow_draw=allow_draw)


	def sample(self, *gadgets: AbstractGadget, shuffle: bool = True, **kwargs) -> AbstractSample:
		return self._source.sample(*gadgets, shuffle=shuffle, **kwargs)



class Dataset(AbstractDataset):
	_Planner = Planner
	_Sample = Sample
	def iterate(self, *gadgets: AbstractGadget,
				shuffle: Optional[bool] = None, allow_draw: bool = True) -> Iterator[Sample]:
		planner = self._Planner(self, shuffle=shuffle)
		for info in planner.generate():
			sample = self._Sample(info, planner=planner, allow_draw=allow_draw)
			yield sample.include(*gadgets, self)


	def sample(self, *gadgets: AbstractGadget, shuffle: bool = True, **kwargs) -> Sample:
		return next(self.iterate(*gadgets, shuffle=shuffle, **kwargs))



@fig.component('table')
class TableDataset(fig.Configurable, Dataset, Table):
	def __init__(self, data: dict[str, list[Any]] = None, **kwargs):
		super().__init__(data=data, **kwargs)


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
		return self._path


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











