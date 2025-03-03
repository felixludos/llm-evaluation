from .imports import *



class Module(fig.Configurable, ToolKit):
	@fig.config_aliases(gap='app')
	def __init__(self, *args, gap: Dict[str, str] = None, **kwargs):
		super().__init__(*args, gap=gap, **kwargs)

