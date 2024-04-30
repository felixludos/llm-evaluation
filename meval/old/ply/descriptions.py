from typing import Union, Optional, Any, Self
from collections.abc import Mapping, Iterable
from omnibelt import Class_Registry, pformat


_primitive = (str, int, float, bool, type(None))
PRIMITIVE = Union[None, *_primitive[:-1]]
JSONABLE = Union[PRIMITIVE, list['JSONABLE'], dict[str, 'JSONABLE']]
JSONOBJ = dict[str, JSONABLE]

DESCRIBABLE = Union[JSONABLE, 'DescribableBase']
DESCRIPTION = dict[str, DESCRIBABLE]


class AbstractDescribable:
	def describe(self) -> DESCRIPTION:
		raise NotImplementedError


	@classmethod
	def display(cls, desc: DESCRIPTION, *, detail: int | None = None) -> str:
		raise NotImplementedError


class DescriptionRegistry(Class_Registry):
	def _default_registration_name(self, payload: type):
		if payload.__module__ is None:
			return payload.__name__
		return f'{payload.__module__}:{payload.__name__}'


	def register(self, cls: type[AbstractDescribable], name: Optional[str] = None) -> Self:
		name = name or self._default_registration_name(cls)
		self.new(name, cls)
		return self


	def recover(self, deposit: JSONABLE) -> DESCRIBABLE:
		if isinstance(deposit, dict):
			if len(deposit) == 2 and self._desc_content_key in deposit and self._desc_type_key in deposit:
				name = deposit[self._desc_type_key]
				desc = deposit[self._desc_content_key]
				cls = self.get_class(name)
				return cls.from_description(self.recover(desc))
			return {k: self.recover(v) for k, v in deposit.items()}
		if isinstance(deposit, list):
			return [self.recover(v) for v in deposit]
		if isinstance(deposit, _primitive):
			return deposit
		raise ValueError(f'Cannot recover object: {deposit}')


	def display(self, obj: DESCRIBABLE, *, detail: int | None = None) -> str:
		if isinstance(obj, AbstractDescribable):
			return obj.display(obj.describe(), detail=detail)
		if isinstance(obj, Mapping):
			return '{' + ', '.join(f'{k}: {self.display(v, detail=detail)}' for k, v in obj.items()) + '}'
		if isinstance(obj, Iterable):
			return '[' + ', '.join(self.display(v, detail=detail) for v in obj) + ']'
		if isinstance(obj, _primitive):
			return str(obj)
		raise ValueError(f'Cannot display object: {obj}')


	_desc_content_key = '_description'
	_desc_type_key = '_desc_type'
	def deposit(self, obj: DESCRIBABLE) -> JSONABLE:
		# TODO: check for reference cycles and handle memory dicts
		if isinstance(obj, AbstractDescribable):
			return {self._desc_content_key: self.deposit(obj.describe()),
					self._desc_type_key: self.get_name(obj.__class__)}
		if isinstance(obj, _primitive):
			return obj
		if isinstance(obj, Mapping):
			assert all(isinstance(k, str) for k in obj.keys()), f'Keys must be strings: {obj}'
			if len(obj) == 2 and self._desc_content_key in obj and self._desc_type_key in obj:
				raise NotImplementedError(f'Cannot describe object: {obj}')
			return {k: self.deposit(v) for k, v in obj.items()}
		if isinstance(obj, Iterable):
			return [self.deposit(v) for v in obj]
		raise ValueError(f'Cannot describe object: {obj}')


	def describe(self, obj: DESCRIBABLE) -> DESCRIPTION:
		if isinstance(obj, AbstractDescribable):
			return obj.describe()
		if isinstance(obj, Mapping):
			return {k: self.describe(v) for k, v in obj.items()}
		if isinstance(obj, Iterable):
			return [self.describe(v) for v in obj]
		if isinstance(obj, _primitive):
			return obj
		raise ValueError(f'Cannot describe object: {obj}')



describables_registry = DescriptionRegistry()



class RegisteredDescribable(AbstractDescribable):
	'''can be loaded from a description'''
	def __init_subclass__(cls, name: str = None, **kwargs):
		super().__init_subclass__(**kwargs)
		describables_registry.register(cls, name=name)


	def deposit(self) -> JSONOBJ:
		'''recursively describe to produce a jsonable representation'''
		return describables_registry.deposit(self)



class AbstractRecoverable(AbstractDescribable):
	'''can be loaded from a deposit'''
	@classmethod
	def from_description(cls, description: DESCRIPTION) -> 'AbstractDescribable':
		raise NotImplementedError



class Describable(RegisteredDescribable):
	def display_self(self, detail: int | None = None) -> str:
		'''how many levels of detail to display'''
		return describables_registry.display(self, detail=detail)


	def __str__(self) -> str:
		return self.display_self()


	def __repr__(self) -> str:
		return self.display_self(detail=1)


	# _display_template: str = ('{cls.__name__}({'
	# 						  '", ".join(f"{k}={v}" for k, v in desc.items()) '
	# 						  'if detail is None or detail > 0 '
	# 						  'else f"{len(desc)} detail" + "s" if len(desc) != 1 else ""'
	# 						  '})')
	@classmethod
	def display(cls, desc: DESCRIPTION, *, detail: int | None = None) -> str:
		if detail is not None:
			desc = {k: describables_registry.display(v, detail=detail - 1) for k, v in desc.items()}
		# return pformat(cls._display_template, cls=cls, desc=desc, detail=detail, **desc)
		items = ', '.join(f'{k}={v!r}' for k, v in desc.items())
		return f'{cls.__name__}({items})'


	def describe(self) -> DESCRIBABLE:
		'''
		should be overridden to include any necessary data
		(values don't have to be jsonable, as long as attrs are describable)
		'''
		return {}


def describe(obj: DESCRIBABLE) -> DESCRIPTION:
	return describables_registry.describe(obj)


def display(obj: DESCRIBABLE, *, detail: int | None = None) -> str:
	return describables_registry.display(obj, detail=detail)


def deposit(obj: DESCRIBABLE) -> JSONABLE:
	return describables_registry.deposit(obj)


def recover(description: JSONABLE) -> DESCRIBABLE:
	return describables_registry.recover(description)






