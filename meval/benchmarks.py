from omniply.apps.staging import AbstractPlan
from .imports import *

from .descriptions import Describable

import re
# from omniply.apps import Table as _Table
import csv


@fig.component('raw-table')
class Table(fig.Configurable, TableBase, Staged, AbstractMogul):
	@classmethod
	def from_rows(cls, data_in_rows: list[dict[str,Any]]):
		return cls(data=cls._validate_rows(data_in_rows))


	@classmethod
	def from_columns(cls, data_in_columns: dict[str, list[Any]]):
		return cls(data=cls._validate_columns(data_in_columns))


	def __init__(self, data: dict[str, list[Any]] = None, *, index_key='idx', gap: dict[str, str] = None, **kwargs):
		super().__init__(data_in_columns=data, gap=gap, **kwargs)
		self._index_gizmo = index_key


	def _stage(self, plan: AbstractPlan = None):
		self.load()


	def guide(self) -> AbstractGuru:
		return Guru(self.number_of_rows, key=self.index_key).include(self)


	@property
	def index_key(self) -> str:
		return self._index_gizmo
	@index_key.setter
	def index_key(self, value: str):
		self._index_gizmo = value



@fig.component('table')
class FileTable(Table):
	def __init__(self, path: Path | str, **kwargs):
		if path is not None:
			path = Path(path)
		super().__init__(**kwargs)
		self.path = path


	def describe(self) -> dict[str, Any]:
		return dict(path=str(self.path))


	def _load_data(self) -> dict[str, list[Any]]:
		return self._validate_rows(self._load_rows(self.path))


	def _load_rows(self, path: Path = None, *, default_text_key='text', json_obj_key='_key') -> list[dict[str,Any]]:
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
				rows = list(csv.DictReader(f))

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



class NLP_Table(FileTable):
	def _load_rows(self, path: Path = None, *, default_text_key='text', json_obj_key='_key') -> dict[str, list[Any]]:
		rows = super()._load_rows(path, default_text_key=default_text_key, json_obj_key=json_obj_key)

		if any('prompt' in row for row in rows):
			print(f'Warning: "prompt" key found in {path}, replacing it with {default_text_key}')
			for row in rows:
				if 'prompt' in row:
					row[default_text_key] = row.pop('prompt')

		return rows



class CustomBenchmark(ToolKit, AbstractMogul):
	_Table = Table

	def __init__(self, *, table: Table | list[dict[str, Any]] | dict[str, list[Any]] = None, **kwargs):
		super().__init__(**kwargs)
		self.table = table


	def guide(self) -> AbstractGuru:
		return self.table.guide()


	def _stage(self, plan: AbstractPlan):
		if isinstance(self.table, list):
			self.table = self._Table.from_rows(self.table)
		elif isinstance(self.table, dict):
			self.table = self._Table.from_columns(self.table)
		assert isinstance(self.table, Table), f'Invalid table: {self.table}'
		self.table.stage()
		self.include(self.table)
		super()._stage(plan)



@fig.component('gsm8k')
class GSM8k(FileTable):
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


















