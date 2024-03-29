from typing import Iterable
from omniply import Context, ToolKit, AbstractGaggle, AbstractGig, AbstractGadget
from .tasks import Task, Chainable


class Plied:
	def gadgetry(self):
		raise NotImplementedError



class PlyTask(Chainable, Plied):
	def __init__(self, target: Iterable[str] | str = None, indicator: Iterable[str] = None,
				 content: Iterable[AbstractGadget] | dict[str, AbstractGadget] = (), **kwargs):
		if target is not None and not isinstance(target, str):
			target = tuple(target)
		super().__init__(**kwargs)
		self._target = target
		self._content = content
		self._additional_gadgetry = []
		self._context = None


	def gadgetry(self):
		yield from self._content if isinstance(self._content, list) \
			else (value for _, value in sorted(self._content.items(), key=lambda x: x[0]))
		yield from self._additional_gadgetry


	def chain(self, task: 'PlyTask'):
		assert self._context is None, 'Cannot chain tasks with different existing contexts'
		if task._context is not None:
			self._context = task.context
			self._context.extend(self.gadgetry())
		self._additional_gadgetry.extend(task.gadgetry())
		return self


	def _create_context(self):
		return Context().extend(self.gadgetry())


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



















