from .imports import *

from omnibelt import colorize

from .calculations import StickyCalculation, MultiSelector, SYSTEM



@fig.component('printer')
class PrinterCalculation(fig.Configurable, StickyCalculation, MultiSelector):
	_color_order = ['blue', 'green', 'yellow', 'red', 'magenta', 'cyan']

	def __init__(self, keys: Iterable[str] | Mapping[str, bool] | str, print_available: bool = False,
				 color: bool = False):
		if isinstance(keys, str):
			assert keys == 'all', f'Invalid key: {keys!r}'
			keys = None
		if isinstance(keys, Mapping):
			keys = set(key for key, value in keys.items() if value)
		super().__init__(products=keys)
		self._print_available = print_available
		self._pretty_print = color


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

		if self._pretty_print:
			print('*'*50)
			for i, key in enumerate(self.products):
				print(f'{key}: {colorize(str(out[key]), self._color_order[i % len(self._color_order)])}')
			print('*'*50)
			print()

		print('Products:')
		print(json.dumps(out, indent=4, sort_keys=isinstance(self.products, set)))
		return out




