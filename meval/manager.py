from .imports import *

from .tasks import Task, ResourceAware, ExpectedResources, ExpectedIterations
from .errors import JobNotFound, UnknownJobType
from .util import data_root



@fig.component('job-manager')
class Manager(fig.Configurable):
	def __init__(self, root: Path = data_root(), config_root: Optional[Path] = None, **kwargs):
		root.mkdir(parents=True, exist_ok=True)
		super().__init__(**kwargs)
		if config_root is not None and config_root.exists():
			proj = fig.get_current_project()
			proj.register_config_dir(config_root)
		self.root = root
		self.config_root = config_root
		self.jobs = []


	@dataclass
	class _JobFrame:
		ID: int
		name: str
		timestamp: datetime
		config: fig.Configuration
		job: Task


	_job_id_file_name = 'job_list.csv'
	def _generate_job_id(self):
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


	def _create_job(self, cfg: fig.Configuration):
		job = cfg.process()
		if not isinstance(job, Task):
			# print(f'Job is not a Job: {job}')
			raise ValueError(f'Job is not a Job: {job}')

		ID = self._generate_job_id()
		now = datetime.now()
		name = job.generate_name(ID, now)

		frame = self._JobFrame(ID=ID, name=name, timestamp=now, config=cfg, job=job)

		self.jobs.append(frame)
		return frame


	def create_job(self, cfg: str | fig.Configuration, *other, **params) -> int:
		if isinstance(cfg, str):
			cfg = fig.create_config(cfg, *other, **params)
		assert isinstance(cfg, fig.Configuration), f'Invalid config type: {cfg} ({type(cfg)})'

		frame = self._create_job(cfg)
		return frame.ID


	def _find_job_frame(self, ident: int | str):
		if isinstance(ident, int):
			matches = [j for j in self.jobs if j.ID == ident]
		elif isinstance(ident, str):
			try:
				ident = int(ident)
			except ValueError:
				matches = [j for j in self.jobs if j.name == ident]
			else:
				return self._find_job_frame(ident)
		else:
			raise UnknownJobType(f'Unknown job ident type: {ident} ({type(ident)})')

		if not matches:
			raise JobNotFound(f'Job not found: {ident}')

		if len(matches) > 1:
			raise JobNotFound(f'Multiple jobs found: {ident}')

		return matches[0]


	def start_job(self, ident: int | str):
		frame = self._find_job_frame(ident)
		out = frame.job.start()
		if out is not None:
			return out
		return frame.ID


	def terminate_job(self, ident: int | str):
		frame = self._find_job_frame(ident)
		out = frame.job.terminate()
		if out is not None:
			return out
		return frame.ID


	def complete_job(self, ident: int | str):
		frame = self._find_job_frame(ident)
		out = frame.job.complete()
		if out is not None:
			return out
		return frame.ID


	def job_status(self, ident: int | str):
		frame = self._find_job_frame(ident)
		return frame.job.status()


	def report(self, limit: int = 5, status: bool = False):
		limit = min(limit, len(self.jobs))
		frames = sorted(self.jobs, key=lambda j: j.timestamp, reverse=True)[:limit]
		report = [{'id': frame.ID, 'name': frame.name, 'timestamp': frame.timestamp} for frame in frames]
		if status:
			for frame, info in zip(frames, report):
				info['status'] = frame.job.status()
		return report


	def chain_jobs(self, prev_link: int | str, next_link: int | str):
		prev_frame = self._find_job_frame(prev_link)
		next_frame = self._find_job_frame(next_link)
		next_frame.job.chain(prev_frame.job)
		return next_frame
















