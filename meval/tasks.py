import torch.cuda

from .imports import *

from threading import Thread


class Task(fig.Configurable):
	def __init__(self, name: str = None, **kwargs):
		super().__init__(**kwargs)
		self.name = name
		self._task = None
		self._is_done = False


	def generate_name(self, ID: int, timestamp: datetime):
		if self.name is None:
			# self.name = f'task{str(ID).zfill(3)}_{timestamp.strftime("%Y%m%d-%H%M%S")}'
			self.name = f'task{str(ID).zfill(3)}'
		return self.name


	def reset(self):
		self._is_done = False
		self._task = None


	def terminate(self):
		raise NotImplementedError


	def start(self): # non-blocking
		if self.is_running:
			raise RuntimeError('Job already started')
		self._task = Thread(target=self.run)
		self._task.start()


	def complete(self): # blocking
		if self.is_running:
			self._task.join()
		elif not self.is_done:
			self.run()


	@property
	def is_done(self):
		return self._is_done
	@property
	def is_running(self):
		return self._task is not None and self._task.is_alive()


	def status(self):
		return {'is_done': self.is_done, 'is_running': self.is_running}


	def run(self):
		self._run()
		self.cleanup()
		self._is_done = True


	def cleanup(self):
		self._task = None


	def _run(self):
		raise NotImplementedError



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
		progress['start_time'] = self.start_time
		progress['finish_time'] = self.finish_time
		if self.start_time is not None:
			progress['started'] = progress['current_time'] - self.start_time
			progress['started_human'] = humanize.naturaldelta(progress['started'])
		if self.finish_time is not None:
			progress['finished'] = progress['current_time'] - self.finish_time
			progress['finished_human'] = humanize.naturaldelta(progress['finished'])
		if self.start_time is not None and self.finish_time is not None:
			progress['duration'] = self.finish_time - self.start_time
			progress['duration_human'] = humanize.naturaldelta(progress['duration'])
		return progress



class ResourceAware(Timestamped):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.start_snapshot = None
		self.end_snapshot = None

	@staticmethod
	def resource_snapshot(fast: bool = False):
		system_info = {}

		# GPU information (if CUDA is available)
		if torch.cuda.is_available():
			gpu_info = []
			for i in range(torch.cuda.device_count()):
				gpu_info.append({
					"name": torch.cuda.get_device_name(i),
					"total_memory_GB": torch.cuda.get_device_properties(i).total_memory / (1024 ** 3),
					"memory_allocated_GB": torch.cuda.memory_allocated(i) / (1024 ** 3),
					"memory_cached_GB": torch.cuda.memory_reserved(i) / (1024 ** 3),
					'utilization': torch.cuda.utilization(i),
				})

			mem_usage = nvidia_smi.getInstance().DeviceQuery('memory.free, memory.total')
			for g, m in zip(gpu_info, mem_usage['gpu']):
				g['smi_free_GB'] = m['fb_memory_usage']['free'] / (1024)
				g['smi_total_GB'] = m['fb_memory_usage']['total'] / (1024)

			system_info["gpu"] = gpu_info
		else:
			system_info["gpu"] = None

		# CPU information
		system_info["cpu"] = {
			"physical_cores": psutil.cpu_count(logical=False),
			"total_cores": psutil.cpu_count(logical=True),
			"max_frequency_MHz": psutil.cpu_freq().max,
			"min_frequency_MHz": psutil.cpu_freq().min,
			"current_frequency_MHz": psutil.cpu_freq().current,
		}
		if not fast:
			system_info["cpu"].update({
				"cpu_usage_per_core": psutil.cpu_percent(percpu=True, interval=1),
				"total_cpu_usage": psutil.cpu_percent(interval=1)
			})

		# RAM information
		ram_info = psutil.virtual_memory()
		proc = psutil.Process()
		system_info["ram"] = {
			"total_GB": ram_info.total / (1024 ** 3),
			"available_GB": ram_info.available / (1024 ** 3),
			"total_used_GB": ram_info.used / (1024 ** 3),
			"percentage_used": ram_info.percent,
			"proc_used_GB": proc.memory_info().rss / (1024 ** 3),
		}

		return system_info


	def reset(self):
		super().reset()
		self.start_snapshot = None
		self.end_snapshot = None


	def status(self, fast: bool = True):
		progress = super().status()

		current = self.resource_snapshot(fast=fast)

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
			self.start_snapshot = self.resource_snapshot()
		super().run()
		self.end_snapshot = self.resource_snapshot()



class IterativeTask(Task):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self._stream = None
		self._kill_flag = False
		self._run_iterations = None
		self.num_iterations = 0


	def reset(self):
		self.terminate()
		self._stream = None
		self._run_iterations = None
		self.num_iterations = 0
		super().reset()


	def terminate(self):
		self._kill_flag = True


	def initialize(self):
		if self._stream is None:
			self._stream = self._generate_stream()


	def start(self, n: Optional[int] = None): # non-blocking
		self._kill_flag = False
		self._run_iterations = n
		super().start()


	def _run(self):
		self.initialize()
		i = 0
		while (self._stream is not None and not self._kill_flag
			   and (self._run_iterations is None or i < self._run_iterations)):
			self._take_steps(1)
			i += 1


	def step(self, n: Optional[int] = 1): # user-level blocking
		'''takes at most n steps'''
		if self._stream is None:
			self.initialize()
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


	def complete(self, finish: bool = False): # blocking
		super().complete()
		if finish and not self.is_done:
			self.step(None)


	@property
	def is_done(self):
		return self._is_done and self._stream is None


	def cleanup(self):
		super().cleanup()
		self._run_iterations = None


	def status(self):
		progress = super().status()
		progress['num_iterations'] = self.num_iterations
		return progress


	def _generate_stream(self): # generator
		raise NotImplementedError



class TimedIterative(Timestamped, IterativeTask):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.init_time = None


	def initialize(self):
		if self.init_time is None:
			self.init_time = datetime.now()
		super().initialize()


	def reset(self):
		super().reset()
		self.init_time = None


	def status(self):
		progress = super().status()
		progress['init_time'] = self.init_time

		if self.init_time is not None:
			progress['rate'] = self.num_iterations / (progress['current_time'] - self.init_time).total_seconds()
		if self.is_running and self.start_time is not None:
			progress['run_rate'] = self.num_iterations / (progress['current_time'] - self.start_time).total_seconds()
		return progress



class ExpectedTiming(Timestamped):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.expected_duration = None

	def status(self):
		progress = super().status()
		if self.expected_duration is not None:
			if self.start_time is not None:
				progress['expected_finish_time'] = self.start_time + self.expected_duration
			if 'duration' in progress:
				progress['expected_duration_delta'] = progress['duration'] - self.expected_duration
				progress['expected_relative_duration'] = (progress['duration'].total_seconds()
														  / self.expected_duration.total_seconds())
				# progress['expected_duration'] = self.expected_duration
				progress['expected_duration_human'] = humanize.naturaldelta(self.expected_duration)
				diff = progress['expected_duration_delta'].total_seconds()
				progress['expected_duration_delta_human'] = (humanize.naturaldelta(timedelta(seconds=abs(diff)))
													   + (' longer' if diff > 0 else ' shorter'))
			elif 'started' in progress:
				progress['expected_progress'] = (progress['started'].total_seconds()
												 / self.expected_duration.total_seconds())
				remaining = self.expected_duration - progress['started']
				if remaining.total_seconds() > 0:
					progress['expected_remaining'] = remaining
					progress['expected_remaining_human'] = humanize.naturaldelta(progress['expected_remaining'])
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



class PersistentTask(Task):
	_root = None
	def persist(self, root: Path):
		self._root = root



class ReloadableTask(PersistentTask):
	def reload(self, root: Path):
		pass



class Chainable(Task):
	def chain(self, task: Task):
		raise NotImplementedError



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
	def __init__(self, tasks: list[Task] = (), parallel: bool = False, **kwargs):
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


