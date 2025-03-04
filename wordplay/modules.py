import inspect

from .imports import *
from .mixins import Describable, DESCRIPTION



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

