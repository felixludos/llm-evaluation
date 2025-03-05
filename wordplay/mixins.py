from .imports import *
from omnibelt import Class_Registry
from .abstract import AbstractJsonable, AbstractDescribable

_primitive = (str, int, float, bool, type(None))
# PRIMITIVE = Union[None, *_primitive[:-1]]
# JSONABLE = Union[PRIMITIVE, list['JSONABLE'], dict[str, 'JSONABLE']]
# JSONOBJ = dict[str, JSONABLE]

# DEPOSIT = dict[str, JSONABLE]



class Describable(AbstractDescribable):
	def __str__(self):
		return self.display('multi')


	def __repr__(self):
		return self.display('single')


	def display(self, level: str = None, **kwargs) -> str:
		name = self.__class__.__name__
		desc = self.describe()

		content = [line for key, value in desc.items() for line in
			f'{key}={display(value, level=_display_level_progression.get(level, level), **kwargs)},'.split('\n')]
		if not len(content):
			return f'{name}()'
		content[-1] = content[-1][:-1] # remove last ','
		if level.startswith('multi'):
			return f'{name}(\n{_display_indent}' + f'\n{_display_indent}'.join(content) + '\n)'
		return f'{name}(' + ' '.join(content) + ')'


	def json(self) -> JSONOBJ:
		return to_json(self.describe())



_display_indent = '  '
_display_level_progression = {'multi': 'single', 'single': 'min'}
def display(obj, *, level: str = 'single', **kwargs) -> str:
	if isinstance(obj, AbstractDescribable):
		return obj.display(level=level, **kwargs)

	if isinstance(obj, Mapping):
		content = [line for key, value in obj.items() for line in
			f'{key}: {display(value, level=_display_level_progression.get(level, level), **kwargs)},'.split('\n')]
		if not len(content):
			return '{}'
		content[-1] = content[-1][:-1] # remove last ','
		if level.startswith('multi'):
			return f'{{\n{_display_indent}' + f'\n{_display_indent}'.join(content) + '\n}'
		return '{' + ' '.join(content) + '}'
	if isinstance(obj, (list, tuple)):
		s, e = '[]' if isinstance(obj, list) else '()'
		content = [line for value in obj for line in
				   f'{display(value, level=_display_level_progression.get(level, level), **kwargs)},'.split('\n')]
		if not len(content):
			return s + e
		content[-1] = content[-1][:-1] # remove last ','
		if level.startswith('multi'):
			return f'[\n{_display_indent}' + f'\n{_display_indent}'.join(content) + '\n]'
		return s + ' '.join(content) + e
	return repr(obj)
	# raise ValueError(f'Cannot display object: {obj}')



def to_json(obj: Any) -> JSONABLE:
	if isinstance(obj, AbstractJsonable):
		return obj.json()
	if isinstance(obj, Mapping):
		return {k: to_json(v) for k, v in obj.items()}
	if isinstance(obj, _primitive):
		return obj
	if isinstance(obj, Path):
		return str(obj)
	if isinstance(obj, Iterable):
		return [to_json(v) for v in obj]
	raise ValueError(f'Cannot convert object to json: {obj}')







