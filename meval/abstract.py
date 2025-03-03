from .imports import *

from omniply.apps.training.abstract import AbstractDataset as _AbstractDataset, AbstractPlanner, AbstractBatch


class AbstractEndpoint:
	@property
	def ident(self) -> str:
		raise NotImplementedError

	def describe(self) -> Dict[str, JSONABLE]:
		raise NotImplementedError

	def wrap_prompt(self, prompt: str) -> JSONOBJ:
		raise NotImplementedError

	def wrap_chat(self, chat: List[Dict[str, str]]) -> JSONOBJ:
		raise NotImplementedError

	def send_no_wait(self, data: JSONOBJ) -> JSONOBJ:
		raise NotImplementedError

	def send(self, data: JSONOBJ) -> JSONOBJ:
		raise NotImplementedError

	def get_response(self, prompt: Union[str, List[Dict[str, str]]]) -> str:
		raise NotImplementedError

	def extract_response(self, data: JSONOBJ) -> str:
		raise NotImplementedError

	def count_tokens(self, message: str) -> int:
		raise NotImplementedError


class AbstractSample(AbstractBatch):
	pass



class AbstractDataset(_AbstractDataset, AbstractGadget):
	@property
	def name(self):
		raise NotImplementedError


	def iterate(self, *gadgets: AbstractGadget, planner: AbstractPlanner = None,
				shuffle: Optional[bool] = None, allow_draw: bool = True) -> Iterator[AbstractSample]:
		raise NotImplementedError


	def sample(self, *gadgets: AbstractGadget, shuffle: bool = True, **kwargs) -> 'AbstractSample':
		raise NotImplementedError



class AbstractSystem(AbstractDataset):
	@property
	def source(self):
		raise NotImplementedError


	def announce(self) -> str:
		raise NotImplementedError



class AbstractBenchmark:
	def gadgetry(self) -> Iterator[AbstractGadget]:
		raise NotImplementedError


	def run(self, dataset: AbstractDataset, **kwargs) -> Self:
		raise NotImplementedError


	def loop(self, system: AbstractSystem) -> Iterator[AbstractSample]:
		raise NotImplementedError


	def prepare(self, dataset: AbstractDataset, **kwargs) -> AbstractSystem:
		raise NotImplementedError


	def step(self, sample: AbstractSample) -> None:
		raise NotImplementedError


	def end(self, last_sample: Optional[AbstractSample]) -> None:
		raise NotImplementedError


