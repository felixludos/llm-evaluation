from typing import Any, Optional, Iterator
import omnifig as fig

from omniply import Context, ToolKit as _ToolKit, tool
from omniply.apps.staging import Staged, StagedGaggle



class ToolKit(_ToolKit, StagedGaggle, fig.Configurable):
	pass

