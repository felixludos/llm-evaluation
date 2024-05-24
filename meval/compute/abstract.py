from .imports import *

DESCRIBABLE = Union[JSONABLE, 'DescribableBase']
DESCRIPTION = dict[str, DESCRIBABLE]

SELECTION = Union[str, Iterable[str], Mapping[str, bool]]


class AbstractDescribable:
	def describe(self) -> DESCRIPTION:
		raise NotImplementedError


	@classmethod
	def display(cls, desc: DESCRIPTION, *, detail: int | None = None) -> str:
		raise NotImplementedError


class DescribableGadget(AbstractGadget, AbstractDescribable): # TODO
	pass


SYSTEM = Union[Context, AbstractGuru]
SOURCE = Iterator[Context]



class AbstractCalculation(AbstractDescribable):
	def sub(self, *, recursive: bool = False) -> Iterator['AbstractCalculation']:
		yield self


	def setup(self, system: SYSTEM = None) -> SYSTEM:
		return system


	def work(self, system: SYSTEM) -> Optional[SYSTEM]:
		raise NotImplementedError


	def finish(self, system: SYSTEM) -> JSONABLE:
		pass


