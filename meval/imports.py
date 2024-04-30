from typing import List, Dict, Any, Tuple, Union, Optional, Iterable, Iterator, Generator, Self
from pathlib import Path
from omnibelt import load_json, save_json, load_csv, load_yaml, save_yaml, load_csv_rows, pformat
import omnifig as fig
from omniply import tool, Context, ToolKit
from datetime import datetime, timedelta
import json


JSONABLE = Union[str, int, float, bool, None, dict[str, 'JSONABLE'], list['JSONABLE']]











