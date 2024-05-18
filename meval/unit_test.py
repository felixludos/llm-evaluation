
from .imports import *


from .calculations import Calculation



class _Kit(ToolKit):
	@tool('a')
	def get_a(self, b, c):
		return b + c


class _Source(ToolKit):
	@tool('b')
	def get_b(self):
		return 11

	@tool('c')
	def get_c(self):
		return 22



def test_calc():

	world = [_Kit(), _Source()]


	pass








