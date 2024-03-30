from typing import Iterable, Any
from omniply import Context, ToolKit, AbstractGaggle, AbstractGig, AbstractGadget
from .tasks import Task, Chainable



class AbstractStructuredTask:
	def gadgetry(self):
		raise NotImplementedError



class AbstractContextual(AbstractStructuredTask):
	'''tasks that revolve around a single context'''
	@property
	def context(self):
		raise NotImplementedError



class ContextTask(Chainable, AbstractStructuredTask):
	_context_type = Context
	def _create_context(self):
		return self._context_type().extend(self.gadgetry())

	def __init__(self, tools: Iterable[AbstractGadget] | dict[str, AbstractGadget] = (),
				 data: dict[str, Any] = None, chain_context=False, **kwargs):
		if data is None:
			data = {}
		super().__init__(**kwargs)
		self._context = None
		self._tools = tools
		self._data = data
		self._chain_context = chain_context
		self._history = []


	def _prepare(self):
		super()._prepare()
		if self._context is None:
			self._context = self._create_context()


	def chain(self, task: 'ContextTask'):
		if self._chain_context:

		self._tools.extend(task.gadgetry())
		return self




class PlyTask(Chainable, Plied):
	def __init__(self, target: Iterable[str] | str = None, data: dict[str, Any] = None,
				 tools: Iterable[AbstractGadget] | dict[str, AbstractGadget] = (), **kwargs):
		if target is not None and not isinstance(target, str):
			target = tuple(target)
		if data is None:
			data = {}
		super().__init__(**kwargs)
		self._target = target
		self._tools = tools
		self._data = data
		self._additional_gadgetry = []
		self._context = None


	def gadgetry(self):
		yield from self._tools if isinstance(self._tools, list) \
			else (value for _, value in sorted(self._tools.items(), key=lambda x: x[0]))
		yield from self._additional_gadgetry


	def chain(self, task: 'PlyTask'):
		assert self._context is None, 'Cannot chain tasks with different existing contexts'
		if task._context is not None:
			self._context = task.context
			self._context.extend(self.gadgetry())
		self._additional_gadgetry.extend(task.gadgetry())
		return self



	@property
	def context(self):
		if self._context is None:
			self._context = self._create_context()
		return self._context


	def _run(self):
		ctx = self.context

		if self._target is None:
			raise ValueError(f'No target specified for {self.__class__.__name__}')

		if isinstance(self._target, str):
			return ctx[self._target]
		else:
			return {key: ctx[key] for key in self._target}



















