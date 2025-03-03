from .imports import *

from .abstract import AbstractTask



class Client(AbstractTask):
	@property
	def category(self):
		return 'client'


	@property
	def quiet(self):
		return True






