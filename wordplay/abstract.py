from .imports import *
from omniply import AbstractGame



class AbstractJsonable:
	def json(self) -> JSONOBJ:
		raise NotImplementedError



class AbstractDescribable(AbstractJsonable):
	def describe(self) -> DESCRIPTION:
		raise NotImplementedError


	def display(self, level: str = 'single', **kwargs) -> str:
		"""
		multi-full | single-full | multi | single | min | None
		"""
		raise NotImplementedError



class AbstractSample(AbstractGame):
	def gadgetry(self) -> Iterator[AbstractGadget]:
		'''all vendors except for the batch specific info'''
		raise NotImplementedError


	def new(self) -> 'AbstractSample':
		'''fork this batch, optionally with a new size'''
		raise NotImplementedError


	@property
	def plan(self) -> 'AbstractPlanner':
		'''planner for the batch'''
		raise NotImplementedError



class AbstractPlanner:
	def __init__(self, src: 'AbstractDataset', **kwargs):
		'''prepare the planner for a new dataset'''
		super().__init__(**kwargs)

	def step(self) -> Dict[str, Any]:
		'''creates new batch info for an iteration'''
		raise NotImplementedError

	def draw(self) -> Dict[str, Any]:
		'''create the info for a new batch'''
		raise NotImplementedError

	def generate(self) -> Iterator[Dict[str, Any]]:
		'''generate batch infos with given step size'''
		raise NotImplementedError

	def expected_iterations(self) -> Optional[int]:
		'''
		expected number of iterations for given batch size
		None means infinite or unknown
		'''
		raise NotImplementedError



class AbstractDataset(AbstractGadget):
	@property
	def name(self) -> str:
		raise NotImplementedError


	@property
	def size(self) -> Optional[int]:
		raise NotImplementedError


	def load(self):
		pass


	def iterate(self, *gadgets: AbstractGadget, plan: AbstractPlanner = None,
				shuffle: Optional[bool] = None, allow_draw: bool = True) -> Iterator[AbstractSample]:
		raise NotImplementedError


	def sample(self, *gadgets: AbstractGadget, shuffle: bool = True, **kwargs) -> 'AbstractSample':
		raise NotImplementedError




class AbstractSystem(AbstractDescribable, AbstractDataset):
	@property
	def dataset(self):
		raise NotImplementedError


	def announce(self) -> str:
		raise NotImplementedError


	def settings(self) -> JSONOBJ:
		raise NotImplementedError



class AbstractBenchmark:
	@property
	def name(self) -> str:
		raise NotImplementedError


	@property
	def dataset(self) -> AbstractDataset:
		raise NotImplementedError


	def gadgetry(self) -> Iterator[AbstractGadget]:
		raise NotImplementedError


	def settings(self, system: Optional[AbstractSystem] = None) -> JSONOBJ:
		raise NotImplementedError


	def announce(self, system: Optional[AbstractSystem] = None) -> str:
		raise NotImplementedError


	def save(self, name: str, data: JSONABLE) -> Path:
		raise NotImplementedError


	def run(self, system: Optional[AbstractSystem] = None, **kwargs) -> Self:
		raise NotImplementedError


	def loop(self, system: AbstractSystem) -> Iterator[AbstractSample]:
		raise NotImplementedError


	def prepare(self, **kwargs) -> AbstractSystem:
		raise NotImplementedError


	def step(self, sample: AbstractSample) -> None:
		raise NotImplementedError


	def end(self, last_sample: Optional[AbstractSample]) -> JSONOBJ:
		raise NotImplementedError



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




