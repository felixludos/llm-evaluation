from .imports import *



@fig.component('equals')
class IsEqual(Module):
	@tool('isequal')
	def check(self, a, b):
		return a == b

