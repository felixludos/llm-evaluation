from .imports import *

from .abstract import AbstractTask, AbstractEnvironment
from .reporters import ReporterBase



class Client(AbstractTask):
	@property
	def needs_space(self):
		return False

	@property
	def type(self):
		return 'client'

	@property
	def quiet(self):
		return True


	def _item_to_url(self, item: JSONOBJ) -> str:
		info = item.get('info', {})
		assert 'info' in item and 'host' in info and 'port' in info, f'Invalid server item: {item}'
		return f'http://{info["host"]}:{info["port"]}'


	def infer_server(self, log_path: Path) -> str:
		candidates = {}
		for line in log_path.open('r'):
			item = json.loads(line)
			assert 'type' in item and 'event' in item, f'Invalid item: {item}'
			if item['type'] == 'server':
				url = self._item_to_url(item)
				if item['event'] == 'launch':
					candidates[url] = [item]
				elif item['event'] == 'exit':
					candidates.pop(url, None)
				else:
					candidates[url].append(item)

		if not candidates:
			raise ValueError('No active servers found')

		url = self._select_server(candidates)
		return url


	def _select_server(self, candidates: dict[str, list[JSONOBJ]]) -> str:
		if len(candidates) == 1:
			return next(iter(candidates))

		most_recent = max(candidates.values(), key=lambda items: items[0]['time'])
		return self._item_to_url(most_recent[0])


	server = None
	def prepare(self, reporter: AbstractEnvironment) -> Self:
		if self.server is None:
			self.server = self.infer_server(reporter.board_path)
		return self


















