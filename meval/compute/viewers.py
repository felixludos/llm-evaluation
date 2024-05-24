from .imports import *

from .calculations import StickyCalculation, MultiSelector, SYSTEM



@fig.component('printer')
class PrinterCalculation(fig.Configurable, StickyCalculation, MultiSelector):
	def __init__(self, keys: Iterable[str] | Mapping[str, bool] | str, print_available: bool = False):
		if isinstance(keys, str):
			assert keys == 'all', f'Invalid key: {keys!r}'
			keys = None
		if isinstance(keys, Mapping):
			keys = set(key for key, value in keys.items() if value)
		super().__init__(products=keys)
		self._print_available = print_available


	def setup(self, system: SYSTEM = None) -> SYSTEM:
		system = super().setup(system)
		if self.products is None:
			self.products = set(system.gizmos())
		if self._print_available:
			print(f'Available products: {system.gizmos()}')
		print(f'Printing: {self.products}')
		return system


	def finish(self, system: SYSTEM) -> JSONABLE:
		out = super().finish(system)
		# pretty print
		print(json.dumps(out, indent=4, sort_keys=isinstance(self.products, set)))
		return out




