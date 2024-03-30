import torch.cuda

from .imports import *
from .errors import JobIncompleteError, DependencyError
from . import util

from threading import Thread



class AbstractTask:
	@property
	def name(self):
		raise NotImplementedError

	def meta(self):
		raise NotImplementedError

	@property
	def is_done(self):
		raise NotImplementedError
	@property
	def is_running(self):
		raise NotImplementedError
	@property
	def is_prepared(self):
		raise NotImplementedError

	def reset(self):
		raise NotImplementedError

	def terminate(self):
		raise NotImplementedError

	def start(self):
		raise NotImplementedError

	def complete(self, respond: bool = True):
		raise NotImplementedError

	def response(self):
		raise NotImplementedError

	def status(self):
		raise NotImplementedError

	def run(self):
		raise NotImplementedError

	def prepare(self):
		raise NotImplementedError

	def dispose(self):
		raise NotImplementedError



class ConfigTask(AbstractTask):
	def __init__(self, name: str = None, **kwargs):
		super().__init__(**kwargs)
		self._meta_info = {}
		self.name = name

	def update_meta_info(self, **info):
		self._meta_info.update(info)
	def meta(self):
		return self._meta_info

	@property
	def name(self):
		return self._meta_info.get('name')
	@name.setter
	def name(self, value: str):
		self._meta_info['name'] = value


	_default_name = '{config.pull("configname","task",silent=True)}-{str(ID).zfill(3)}'
	def generate_name(self, config: fig.Configuration, ID: int, timestamp: datetime):
		template = self._default_name if self.name is None else self.name
		name = pformat(template, ID=ID, timestamp=timestamp, config=config)
		self.name = name
		return name



class ThreadTask(AbstractTask):
	_task = None


	def reset(self):
		self._is_done = False
		self._task = None



class Task(AbstractTask):
	def __init__(self, name: str = None, **kwargs):
		super().__init__(**kwargs)
		self._task = None

	_is_done = False
	_is_prepared = False
	_is_disposed = False

	@property
	def is_done(self):
		return self._is_done
	@property
	def is_running(self):
		return self._task is not None and self._task.is_alive()
	@property
	def is_prepared(self):
		return self._is_prepared
	@property
	def is_disposed(self):
		return self._is_disposed


	def reset(self):
		self._is_done = False
		self._task = None


	def terminate(self):
		raise NotImplementedError # TODO: implement kill thread (?)


	def start(self): # non-blocking
		if self.is_running:
			raise RuntimeError('Job already started')
		self._task = Thread(target=self.run)
		self._task.start()


	def complete(self, respond: bool = True): # blocking
		if self.is_running:
			self._task.join()
		elif not self.is_done:
			self.run()
		if respond:
			return self.response()


	def response(self):
		if not self.is_done:
			raise JobIncompleteError('Job not complete')
		return self._get_response()


	@property
	def is_done(self):
		return self._is_done
	@property
	def is_running(self):
		return self._task is not None and self._task.is_alive()
	@property
	def is_prepared(self):
		return self._is_prepared
	@property
	def is_disposed(self):
		return self._is_disposed


	def status(self):
		return {'is_done': self.is_done, 'is_running': self.is_running,
				'is_prepared': self.is_prepared, 'is_disposed': self.is_disposed}


	def run(self):
		self.prepare()
		self._run()
		self.dispose()
		self._is_done = True


	def prepare(self):
		'''should be agnostic to multiple calls'''
		self._prepare()
		self._is_prepared = True
		return self


	def dispose(self):
		'''should be agnostic to multiple calls'''
		self._dispose()
		self._task = None
		self._is_disposed = True
		return self


	def _prepare(self):
		pass


	def _dispose(self):
		pass


	def _get_response(self):
		pass


	def _run(self):
		raise NotImplementedError



class SinglePreparation(Task):
	def prepare(self):
		'''changes prepare to only run once, and from then on be a null-op'''
		if not self.is_prepared:
			super().prepare()
		return self



class ManagedTask(Task):
	_manager = None

	@property
	def manager(self):
		if self._manager is None:
			raise RuntimeError('Manager not set')
		return self._manager



class Timestamped(Task):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.start_time = None
		self.finish_time = None


	def reset(self):
		super().reset()
		self.start_time = None
		self.finish_time = None


	def run(self):
		self.start_time = datetime.now()
		super().run()
		self.finish_time = datetime.now()


	def status(self):
		progress = super().status()
		progress['current_time'] = datetime.now()
		if self.start_time is not None:
			progress['start_time'] = self.start_time
			# progress['started'] = progress['current_time'] - self.start_time
			# progress['started_human'] = humanize.naturaldelta(progress['started'])
		if self.finish_time is not None:
			progress['finish_time'] = self.finish_time
			# progress['finished'] = progress['current_time'] - self.finish_time
			# progress['finished_human'] = humanize.naturaldelta(progress['finished'])
		if self.start_time is not None and self.finish_time is not None:
			progress['duration'] = self.finish_time - self.start_time
			# progress['duration_human'] = humanize.naturaldelta(progress['duration'])
		return progress



class ResourceAware(Timestamped):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.start_snapshot = None
		self.end_snapshot = None


	def reset(self):
		super().reset()
		self.start_snapshot = None
		self.end_snapshot = None


	def status(self, fast: bool = True):
		progress = super().status()

		current = util.resource_snapshot(cpu_interval=None if fast else 1)

		if 'total_cpu_usage' in current.get('cpu', {}):
			progress['cpu_util'] = current['cpu']['total_cpu_usage']
			if self.start_snapshot is not None and 'total_cpu_usage' in self.start_snapshot.get('cpu', {}):
				progress['cpu_util_delta'] = (current['cpu']['total_cpu_usage']
											  - self.start_snapshot['cpu']['total_cpu_usage'])

		if 'available_GB' in current.get('ram', {}) and 'proc_used_GB' in current.get('ram', {}):
			progress['ram_available'] = current['ram']['available_GB']
			progress['ram_used'] = current['ram']['proc_used_GB']
			if (self.start_snapshot is not None and 'available_GB' in self.start_snapshot.get('ram', {})
					and 'proc_used_GB' in self.start_snapshot.get('ram', {})):
				progress['ram_used_since_start'] = (current['ram']['proc_used_GB']
													- self.start_snapshot['ram']['proc_used_GB'])

		if current.get('gpu') is not None:
			progress['gpu_available'] = sum(g['smi_free_GB'] for g in current['gpu'])
			progress['gpu_used'] = sum(g['memory_cached_GB'] for g in current['gpu'])
			progress['gpu_util'] = sum(g['utilization'] for g in current['gpu']) / len(current['gpu'])
			if self.start_snapshot is not None and self.start_snapshot.get('gpu') is not None:
				progress['gpu_used_since_start'] = (sum(g['memory_cached_GB'] for g in current['gpu'])
													- sum(g['memory_cached_GB'] for g in self.start_snapshot['gpu']))

		return progress


	def start(self):
		self.end_snapshot = None
		super().start()


	def run(self):
		if self.start_snapshot is None:
			self.start_snapshot = util.resource_snapshot()
		super().run()
		self.end_snapshot = util.resource_snapshot()



class IterativeTask(Task):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self._stream = None
		self._kill_flag = False
		self._run_iterations = None
		self.num_iterations = 0
		self._batch_num_iterations = 0


	def reset(self):
		self.terminate()
		self._stream = None
		self._run_iterations = None
		self.num_iterations = 0
		self._batch_num_iterations = 0
		super().reset()


	def terminate(self):
		self._kill_flag = True


	def prepare(self):
		super().prepare()
		if self._stream is None:
			self._stream = self._generate_stream()


	def start(self, n: Optional[int] = None): # non-blocking
		self._kill_flag = False
		self._run_iterations = n
		super().start()


	def _run(self):
		self._batch_num_iterations = 0
		while (self._stream is not None and not self._kill_flag
			   and (self._run_iterations is None or self._batch_num_iterations < self._run_iterations)):
			self._take_steps(1)
			self._batch_num_iterations += 1


	def step(self, n: Optional[int] = 1): # user-level blocking
		'''takes at most n steps'''
		self.prepare()
		return self._take_steps(n)


	def _take_steps(self, n: Optional[int] = None): # blocking
		while n is None or n > 0:
			try:
				next(self._stream)
			except StopIteration:
				self._stream = None
				self._is_done = True
				break
			else:
				self.num_iterations += 1
				n -= 1


	def complete(self, respond: bool = True, finish: bool = False): # blocking
		super().complete(respond=False)
		if finish and not self.is_done:
			self.step(None)
		if respond:
			return self._get_response()


	@property
	def is_done(self):
		return self._is_done and self._stream is None


	def dispose(self):
		super().dispose()
		self._run_iterations = None


	def status(self):
		progress = super().status()
		progress['num_iterations'] = self.num_iterations
		return progress


	def _generate_stream(self): # generator
		raise NotImplementedError



class TimedIterative(Timestamped, IterativeTask):
	def status(self):
		progress = super().status()
		if self.is_running and 'start_time' in progress and 'current_time' in progress:
			progress['itr_per_sec'] = (self._batch_num_iterations
									   / (progress['current_time'] - progress['start_time']).total_seconds())
		return progress



class ExpectedTiming(Timestamped):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.expected_duration = None

	def status(self):
		progress = super().status()
		if self.expected_duration is not None:
			progress['expected_duration'] = self.expected_duration
			if self.start_time is not None:
				progress['expected_finish_time'] = self.start_time + self.expected_duration
			if 'duration' in progress:
				pass
				# progress['expected_duration_delta'] = progress['duration'] - self.expected_duration
				# progress['expected_relative_duration'] = (progress['duration'].total_seconds()
				# 										  / self.expected_duration.total_seconds())
				# # progress['expected_duration'] = self.expected_duration
				# progress['expected_duration_human'] = humanize.naturaldelta(self.expected_duration)
				# diff = progress['expected_duration_delta'].total_seconds()
				# progress['expected_duration_delta_human'] = (humanize.naturaldelta(timedelta(seconds=abs(diff)))
				# 									   + (' longer' if diff > 0 else ' shorter'))
			elif 'current_time' in progress and 'start_time' in progress:
				progress['expected_progress'] = ((progress['current_time'] - progress['start_time']).total_seconds()
												 / progress['expected_duration'].total_seconds())
				remaining = self.expected_duration - (progress['current_time'] - progress['start_time'])
				if remaining.total_seconds() > 0:
					progress['expected_remaining'] = remaining
					# progress['expected_remaining_human'] = humanize.naturaldelta(progress['expected_remaining'])
		return progress



class ExpectedResources(ResourceAware, ExpectedTiming):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.expected_ram_usage = 0
		self.expected_gpu_usage = 0


	def status(self, fast: bool = False):
		progress = super().status(fast=fast)

		if self.expected_ram_usage > 0 and 'ram_used' in progress:
			progress['expected_ram_usage'] = self.expected_ram_usage
			progress['expected_ram_remaining'] = self.expected_ram_usage - progress['ram_used']
			progress['expected_ram_progress'] = progress['ram_used'] / self.expected_ram_usage

		if self.expected_gpu_usage > 0 and 'gpu_used' in progress:
			progress['expected_gpu_usage'] = self.expected_gpu_usage
			progress['expected_gpu_remaining'] = self.expected_gpu_usage - progress['gpu_used']
			progress['expected_gpu_progress'] = progress['gpu_used'] / self.expected_gpu_usage

		return progress



class ExpectedIterations(TimedIterative):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.expected_num_iterations = None


	def status(self):
		progress = super().status()
		if self.expected_num_iterations is not None:
			progress['expected_num_iterations'] = self.expected_num_iterations
			progress['expected_num_remaining'] = self.expected_num_iterations - self.num_iterations
			progress['expected_num_progress'] = self.num_iterations / self.expected_num_iterations

			if 'rate' in progress:
				current = progress['current_time'] if 'current_time' in progress else datetime.now()
				progress['expected_finish_time_from_rate'] = (current
										+ timedelta(seconds=progress['expected_num_remaining'] / progress['rate']))
				progress['expected_remaining_time_from_rate'] = progress['expected_finish_time_from_rate'] - current

		return progress



class Chainable(Task):
	def chain(self, task: Task):
		raise NotImplementedError



class Subtask(Chainable):
	def __init__(self, *, strict: bool = True, wait: bool = True, **kwargs):
		super().__init__(**kwargs)
		self._dependency = []
		self._strict = strict
		self._wait = wait


	def add_dependency(self, task: Task):
		self._dependency.append(task)
		return self


	def status(self):
		progress = super().status()
		if len(self._dependency):
			progress['waiting_for'] = [t.meta() for t in self._dependency if not t.is_done]
		return progress


	def run(self):
		for dep in self._dependency:
			if self._strict and not dep.is_done:
				if self._wait:
					dep.complete()
				else:
					raise DependencyError(f'Dependency not complete: {dep}')
			self.chain(dep)

		super().run()



class PersistentTask(Task):
	_root = None
	def persist(self, root: Path):
		self._root = root



class ReloadableTask(PersistentTask):
	def reload(self, root: Path):
		pass



@fig.modifier('autochain')
class AutoChained(Task):
	def __init__(self, then: Chainable = None, **kwargs):
		super().__init__(**kwargs)
		self.then = then


	def run(self):
		super().run()
		if self.then is not None:
			self.then.chain(self)
			self.then.complete()



@fig.component('multitask')
class MultiTask(Task):
	def __init__(self, tasks: list[Task] = None, parallel: bool = False, **kwargs):
		if tasks is None:
			tasks = []
		super().__init__(**kwargs)
		self.tasks = tasks
		self._parallel = parallel


	def status(self):
		progress = super().status()
		progress['completed'] = sum(t.is_done for t in self.tasks)
		progress['running'] = sum(t.is_running for t in self.tasks)
		progress['subtasks'] = [t.status() for t in self.tasks]
		return progress


	def _run(self):
		if self._parallel:
			for task in self.tasks:
				task.start()
		for task in self.tasks:
			task.complete()


