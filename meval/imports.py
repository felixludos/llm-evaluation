from typing import List, Dict, Any, Tuple, Union, Mapping, Optional, Iterable, Iterator, Generator, Self, Callable
from pathlib import Path
from omnibelt import load_json, save_json, load_csv, load_yaml, save_yaml, load_csv_rows, pformat
import omnifig as fig
from omniply import AbstractGadget, Selection, Scope
from omniply.apps.gaps import tool, Context, ToolKit as _ToolKit, DictGadget, Table as TableBase
# from omniply.apps import DictGadget
from omniply.core.abstract import AbstractMutable
from omniply.apps.staging import AbstractStaged, Staged, StagedGaggle, AbstractPlan
from omniply.apps.guides import Guru, MutableGuru, AbstractMogul, AbstractGuru
from datetime import datetime, timedelta
from functools import cached_property, lru_cache
import requests, socket
import json


class ToolKit(_ToolKit, StagedGaggle):
	pass


JSONABLE = Union[str, int, float, bool, None, dict[str, 'JSONABLE'], list['JSONABLE']]
JSONOBJ = dict[str, JSONABLE]








