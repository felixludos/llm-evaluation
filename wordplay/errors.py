from .imports import *


class InteractionFailed(GadgetFailed):
	def __init__(self, context: Union[str, List[Dict[str,str]]], resp: JSONOBJ = None, *, msg: str = None):
		super().__init__(msg)
		self.context = context
		self.resp = resp



class NoMoreSamplesError(IndexError):
	pass


class NoNewSamplesError(ValueError):
	pass



