from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations, ManagedTask, PersistentTask
from .errors import JobNotFound, UnknownJobType
from .util import data_root



@fig.component('task-manager')
class Manager(fig.Configurable):
	def __init__(self, config_root: Optional[Path] = None, is_prime: bool = True, **kwargs):
		super().__init__(**kwargs)
		if config_root is not None and config_root.exists():
			proj = fig.get_current_project()
			proj.register_config_dir(config_root)
		if is_prime:
			ManagedTask._manager = self
		self.config_root = config_root
		self.tasks = []
		self._description = []


	def append_description(self, *args):
		self._description.extend(args)


	def describe(self):
		return self._description


	def task_meta(self, frame):
		return frame.task.meta()


	@dataclass
	class _TaskFrame:
		ID: int
		name: str
		timestamp: datetime
		config: fig.Configuration
		task: Task
		parent: int = None
		subs: list[int] = None


	def _generate_task_id(self):
		return len(self.tasks) + 1


	def _create_task(self, cfg: fig.Configuration, task_key: str = 'task', base: int | str = None):
		# task = cfg.peek_create(task_key)
		task = cfg.pull(task_key)

		if not isinstance(task, Task):
			# print(f'Job is not a Job: {job}')
			raise ValueError(f'Task is not a Task: {task}')

		ID = self._generate_task_id()
		now = datetime.now()
		name = task.generate_name(cfg, ID, now)
		meta_info = {'name': name, 'code': ID, 'timestamp': now}
		configname = cfg.pull(self._configname_key, None, silent=True)
		if configname is not None:
			meta_info['configname'] = configname
		task.update_meta_info(**meta_info)

		frame = self._TaskFrame(ID=ID, name=name, timestamp=now, config=cfg, task=task)
		if base is not None:
			base_frame = self._find_frame(base)
			frame.parent = base_frame.ID
			if base_frame.subs is None:
				base_frame.subs = []
			frame.task.add_dependency(base_frame.task)

		self.tasks.append(frame)
		return frame


	def create_sub(self, base: int | str, task_key: str):
		frame = self._find_frame(base)
		sub_frame = self._create_task(frame.config, task_key=task_key)

		sub_frame.parent = frame.ID
		if frame.subs is None:
			frame.subs = []
		frame.subs.append(sub_frame.ID)
		return sub_frame.ID


	_configname_key = 'configname'
	def create_task(self, raw: str | dict | fig.Configuration, task_key: str = 'task', base: int | str = None) -> int:
		if isinstance(raw, str):
			cfg = fig.create_config(raw)
			cfg.push(self._configname_key, raw, silent=True, overwrite=False)
		elif isinstance(raw, dict):
			cfg = fig.create_config(**raw)
		else:
			cfg = raw
		assert isinstance(cfg, fig.Configuration), f'Invalid config type: {cfg} ({type(cfg)})'

		frame = self._create_task(cfg, task_key=task_key, base=base)
		return frame.ID


	def _find_frame(self, ident: int | str):
		if isinstance(ident, int):
			matches = [j for j in self.tasks if j.ID == ident]
		elif isinstance(ident, str):
			try:
				ident = int(ident)
			except ValueError:
				matches = [j for j in self.tasks if j.name == ident]
			else:
				return self._find_frame(ident)
		else:
			raise UnknownJobType(f'Unknown job ident type: {ident} ({type(ident)})')

		if not matches:
			raise JobNotFound(f'Job not found: {ident}')

		if len(matches) > 1:
			raise JobNotFound(f'Multiple tasks found: {ident}')

		return matches[0]


	def start_task(self, ident: int | str):
		frame = self._find_frame(ident)
		out = frame.task.start()
		if out is not None:
			return out
		return frame.ID


	def terminate_task(self, ident: int | str):
		frame = self._find_frame(ident)
		out = frame.task.terminate()
		if out is not None:
			return out
		return frame.ID


	def complete_task(self, ident: int | str):
		frame = self._find_frame(ident)
		out = frame.task.complete()
		return {'code': frame.ID, 'out': out}


	def task_status(self, ident: int | str):
		frame = self._find_frame(ident)
		return frame.task.status()


	def task_response(self, ident: int | str):
		frame = self._find_frame(ident)
		return frame.task.get_response()


	def report(self, limit: int = 5, status: bool = False):
		limit = len(self.tasks) if limit is None else min(limit, len(self.tasks))
		frames = sorted(self.tasks, key=lambda j: j.timestamp, reverse=True)[:limit]
		report = [frame.task.meta().copy() for frame in frames]
		if status:
			for frame, info in zip(frames, report):
				info['status'] = frame.task.status()
		return report


	def chain_tasks(self, prev_link: int | str, next_link: int | str):
		prev_frame = self._find_frame(prev_link)
		next_frame = self._find_frame(next_link)
		next_frame.task.chain(prev_frame.task)
		return next_frame



@fig.component('persistent-manager')
class PersistenceManager(Manager):
	def __init__(self, root: Path = data_root(), is_prime: bool = True, **kwargs):
		root.mkdir(parents=True, exist_ok=True)
		super().__init__(**kwargs)
		self.root = root


	_job_id_file_name = 'job_list.csv'
	def _generate_task_id(self):
		# with path.open('a') as f:
		# 	writer = csv.writer(f)
		# 	writer.writerow([name, timestamp])
		# return sum(1 for _ in path.open('r'))
		path = self.root / self._job_id_file_name
		with path.open('r+') as f:
			val = int(f.read() or '0') + 1
			f.seek(0)
			f.write(str(val))
		return val


	def task_meta(self, frame):
		return {
			'name': frame.name,
			'id': frame.ID,
			'timestamp': frame.timestamp,
			'path': str(frame.path),
			'manager': self.describe(),
		}


	def _create_task(self, cfg: fig.Configuration):
		frame = super()._create_task(cfg)
		self._register_task(frame)
		return frame


	@dataclass
	class _TaskFrame(Manager._TaskFrame):
		path: Path = None


	def _save_task_meta(self, frame: _TaskFrame):
		frame.config.export('config', root=frame.path)
		save_json(self.task_meta(frame), frame.path / 'meta.json')


	_content_file_name = 'content'
	def _register_task(self, frame: _TaskFrame):
		task = frame.task

		assert self.root is not None, f'Root path not set: {self.root}'

		name = frame.name
		path = self.root / name
		i = 1
		while path.exists():
			path = self.root / f'{name}_{i}'
			i += 1
			if i > 100:
				raise ValueError(f'Path already exists: {path}')

		path.mkdir(parents=True, exist_ok=True)
		frame.path = path

		self._save_task_meta(frame)

		if isinstance(task, PersistentTask):
			content_path = path / self._content_file_name
			content_path.mkdir(exist_ok=True)
			task.persist(content_path)


	def reload(self, ident: int | str):
		# requires that the task is reloadable
		raise NotImplementedError













