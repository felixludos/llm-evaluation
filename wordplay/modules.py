import inspect

from .imports import *
from .mixins import Describable, DESCRIPTION



class hparam(gem):
	def __init__(self, *args, update: Callable[[Any], Any] = None, **kwargs):
		super().__init__(*args, **kwargs)
		self._update_fn = update
		self._update_method = None


	def from_config(self, cfg: fig.Configuration) -> Any:
		if self._default is self._no_value:
			return cfg.pull(self._name)
		return cfg.pull(self._name, self._default)


	def update(self, _dec_method: Callable = None, /, method: Callable = None, *, fn: Callable = None):
		n = int(_dec_method is not None) + int(method is not None) + int(fn is not None)
		assert n == 1, f'Exactly one of dec_method, method, or fn must be specified'
		if _dec_method is not None:
			self._update_method = _dec_method
			return _dec_method # decorator needs to get the method back
		if method is not None:
			self._update_method = method
		if fn is not None:
			self._update_fn = fn
		return self


	def revise(self, instance, value):
		if self._update_method is not None:
			value = self._update_method.__get__(instance, type(instance))(value)
		elif self._update_fn is not None:
			value = self._update_fn(value)
		return super().revise(instance, value)



class Hparamed(fig.Configurable, Geologist):
	@classmethod
	def hparams(cls) -> Iterator[str]:
		yield from reversed(cls._gems)


	@classmethod
	def _get_hparam(cls, key: str) -> hparam:
		return inspect.getattr_static(cls, key)


	@classmethod
	def init_from_config(cls, config: fig.Configuration, args: Optional[Tuple] = None, kwargs: Optional[Dict[str, Any]] = None, *,
	                     silent: Optional[bool] = None) -> Any:
		if kwargs is None:
			kwargs = {}
		for key in cls.hparams():
			if key not in kwargs:
				param = cls._get_hparam(key)
				kwargs[key] = param.from_config(config)
		return super().init_from_config(config, args, kwargs, silent=silent)



class Module(Hparamed, Describable, ToolKit):
	@fig.config_aliases(gap='app')
	def __init__(self, *args, gap: Dict[str, str] = None, **kwargs):
		super().__init__(*args, gap=gap, **kwargs)


	def describe(self) -> DESCRIPTION:
		return {key: getattr(self, key) for key in self.hparams()}


	def json(self) -> JSONOBJ:
		data = super().json()
		if self._gauge is not None and len(self._gauge) > 0:
			data['app'] = dict(self._gauge)
		return data

