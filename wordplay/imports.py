from typing import List, Dict, Any, Tuple, Union, Mapping, Optional, Iterable, Iterator, Generator, Self, Callable
from pathlib import Path
from omnibelt import load_json, save_json, load_csv, load_yaml, save_yaml, load_csv_rows, pformat, where_am_i
import omnifig as fig
from omniply import AbstractGadget#, Selection, Scope
from omniply.apps.gaps import tool, Context, ToolKit, DictGadget, Table as TableBase
from omniply.gems import Geologist, gem
# from omniply.apps import DictGadget
from omniply.core.abstract import AbstractMutable
# from omniply.apps.staging import AbstractStaged, Staged, StagedGaggle, AbstractPlan
from omniply import GadgetFailed
# from omniply.apps.guides import Guru, MutableGuru, AbstractMogul, AbstractGuru
# from omniply.apps.training import Frame
from datetime import datetime, timedelta
from humanize import naturalsize
from functools import cached_property, lru_cache
import requests, socket
from tabulate import tabulate
import json, csv, re, random, time, tqdm


JSONABLE = Union[str, int, float, bool, None, dict[str, 'JSONABLE'], list['JSONABLE']]
JSONOBJ = dict[str, JSONABLE]

DESCRIBABLE = Union[JSONABLE, 'AbstractDescribable']
DESCRIPTION = dict[str, DESCRIBABLE]






