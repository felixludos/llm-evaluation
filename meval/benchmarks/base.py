from typing import Any, Iterable, Iterator
from pathlib import Path
import json, csv

from omnibelt import load_json, save_json, load_csv, load_yaml, save_yaml, load_csv_rows, pformat

from omniply import Context, ToolKit
from omniply.core.gadgets import SingleGadgetBase, GadgetFailure
from omniply.apps import Template, DictGadget, Table, GuruBase



class IndexContext(Context):
	_index_gizmo = 'index'
	def __init__(self, index: int = None, **kwargs):
		if index is None and self._index_gizmo in kwargs:
			index = kwargs.pop(self._index_gizmo)
		super().__init__(**kwargs)
		if index is not None:
			self[self._index_gizmo] = index


	@property
	def index(self):
		return self[self._index_gizmo]



class PromptFile(Table, GuruBase):
	def __init__(self, path: Path | str, autoload: bool = True, **kwargs):
		if path is not None:
			path = Path(path)
		super().__init__(**kwargs)
		self.path = path
		self._autoload = autoload


	def __repr__(self):
		rows = self.number_of_rows

		terms = [f'{self.__class__.__name__}']
		if rows:
			terms.append(f'[{rows}]')
		path = self.path.relative_to(Path.cwd()) if self.path.is_absolute() else self.path
		terms.append(f'({path})')
		return ''.join(terms)


	_Gift = IndexContext
	def _guide_sparks(self):
		self.load()
		yield from range(self.number_of_rows)


	def __getitem__(self, index: int):
		return self._Gift(index).include(self)


	@staticmethod
	def _load_raw_items(path: Path, *, default_text_key='text', json_obj_key='_key') -> list[dict[str,Any]]:
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

		if any('prompt' in row for row in rows):
			print(f'Warning: "prompt" key found in {path}, replacing it with {default_text_key}')
			for row in rows:
				if 'prompt' in row:
					row[default_text_key] = row.pop('prompt')
		return rows


	def _load_data(self) -> dict[str, list[Any]]:
		return self._validate_rows(self._load_raw_items(self.path))










