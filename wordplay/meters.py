from .imports import *
import math
from .abstract import AbstractJsonable



class Meter(AbstractJsonable):
	def __init__(self, alpha: float = None, window_size: float = None, **kwargs):
		# assert alpha is None or window_size is None, 'cannot specify both alpha and window_size'
		if window_size is None and alpha is None:
			window_size = 10
		if window_size is not None:
			alpha = self.window_size_to_alpha(window_size)
		super().__init__(**kwargs)
		self._alpha = alpha
		self.reset()

	@staticmethod
	def window_size_to_alpha(window_size: float) -> float:
		assert window_size >= 1, f'window_size {window_size} must be >= 1'
		return 2 / (window_size + 1)

	@property
	def alpha(self):
		return self._alpha

	def reset(self):
		self.last = None
		self.avg = None
		self.sum = 0.
		self.count = 0
		self.max = None
		self.min = None
		self.smooth = None
		self.var = None
		self.std = None
		self.S = 0.
		self.timestamp = None

	def mete(self, val: float, *, n=1):
		self.timestamp = time.time()
		self.last = val
		self.sum += val * n
		prev_count = self.count
		self.count += n
		self.avg = self.sum / self.count
		delta = val - self.avg
		self.S += delta ** 2 * n * prev_count / self.count
		self.max = val if self.max is None else max(self.max, val)
		self.min = val if self.min is None else min(self.min, val)
		self.var = self.S / self.count
		self.std = math.sqrt(self.var)
		alpha = self.alpha
		if alpha is not None:
			self.smooth = val if self.smooth is None else (self.smooth * (1 - alpha) + val * alpha)
		return val

	def merge(self, other: "Meter"):
		if other.count == 0:
			return  # Nothing to merge

		if self.count == 0:
			# If self is empty, just copy other's values
			self.__dict__.update(other.__dict__)
			return

		new_count = self.count + other.count
		new_sum = self.sum + other.sum
		new_avg = new_sum / new_count

		delta = other.avg - self.avg
		new_S = self.S + other.S + delta ** 2 * self.count * other.count / new_count

		self.count = new_count
		self.sum = new_sum
		self.avg = new_avg
		self.S = new_S
		self.var = new_S / new_count
		self.std = math.sqrt(self.var)
		self.max = max(self.max, other.max) if self.max is not None else other.max
		self.min = min(self.min, other.min) if self.min is not None else other.min

		# Exponential smoothing update
		if self.smooth is None:
			self.smooth = other.smooth
		elif other.smooth is not None:
			alpha = self.alpha
			self.smooth = self.smooth * (1 - alpha) + other.smooth * alpha

		# Update timestamp to the latest
		self.timestamp = max(self.timestamp, other.timestamp) if self.timestamp and other.timestamp else (
					self.timestamp or other.timestamp)


	def json(self) -> JSONOBJ:
		return {'avg': self.avg, 'count': self.count, 'max': self.max, 'min': self.min,
				'smooth': self.smooth, 'std': self.std}

	@property
	def current(self):
		return self.last if self.smooth is None else self.smooth

	@property
	def estimate(self):
		return self.avg if self.smooth is None else self.smooth

	def __len__(self):
		return self.count

	def __float__(self):
		return self.current



