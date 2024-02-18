



class JobNotFound(Exception):
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)


class UnknownJobType(Exception):
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)







