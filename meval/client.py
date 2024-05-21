from .imports import *

from .abstract import AbstractTask, AbstractEnvironment

from functools import lru_cache, cached_property
import socket, requests

from .tasks import start_task
from .calculations import AbstractCalculation


class Client(AbstractTask):
	@property
	def category(self):
		return 'client'


	@property
	def quiet(self):
		return True






