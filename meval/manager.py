from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations
from .errors import JobNotFound, UnknownJobType
from .util import data_root



@fig.component('tasks-manager')
class Manager(fig.Configurable):
	def __init__(self, root: Path = data_root(), config_root: Optional[Path] = None, **kwargs):
		root.mkdir(parents=True, exist_ok=True)
		super().__init__(**kwargs)
		if config_root is not None and config_root.exists():
			proj = fig.get_current_project()
			proj.register_config_dir(config_root)
		self.root = root
		self.config_root = config_root
		self.tasks = []


	@dataclass
	class _TaskFrame:
		ID: int
		name: str
		timestamp: datetime
		config: fig.Configuration
		task: Task


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


	def _create_task(self, cfg: fig.Configuration):
		task = cfg.process()
		if not isinstance(task, Task):
			# print(f'Job is not a Job: {job}')
			raise ValueError(f'Job is not a Job: {task}')

		ID = self._generate_task_id()
		now = datetime.now()
		name = task.generate_name(ID, now)

		frame = self._TaskFrame(ID=ID, name=name, timestamp=now, config=cfg, task=task)

		self.tasks.append(frame)
		return frame


	def create_job(self, cfg: str | fig.Configuration, *other, **params) -> int:
		if isinstance(cfg, str):
			cfg = fig.create_config(cfg, *other, **params)
		assert isinstance(cfg, fig.Configuration), f'Invalid config type: {cfg} ({type(cfg)})'

		frame = self._create_task(cfg)
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
		if out is not None:
			return out
		return frame.ID


	def task_status(self, ident: int | str):
		frame = self._find_frame(ident)
		return frame.task.status()


	def report(self, limit: int = 5, status: bool = False):
		limit = min(limit, len(self.tasks))
		frames = sorted(self.tasks, key=lambda j: j.timestamp, reverse=True)[:limit]
		report = [{'id': frame.ID, 'name': frame.name, 'timestamp': frame.timestamp} for frame in frames]
		if status:
			for frame, info in zip(frames, report):
				info['status'] = frame.task.status()
		return report


	def chain_tasks(self, prev_link: int | str, next_link: int | str):
		prev_frame = self._find_frame(prev_link)
		next_frame = self._find_frame(next_link)
		next_frame.task.chain(prev_frame.task)
		return next_frame
















