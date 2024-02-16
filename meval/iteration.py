import torch.cuda

from .imports import *

from threading import Thread


class Job:
	_task: Thread = None
	_is_done: bool = False

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
		elif self._task is None:
			self.run()


	@property
	def is_done(self):
		return self._is_done
	@property
	def is_running(self):
		return self._task is not None and self._task.is_alive()


	def progress(self):
		return {'is_done': self.is_done, 'is_running': self.is_running}


	def run(self):
		self._run_job()
		self.cleanup()
		self._is_done = True


	def cleanup(self):
		self._task = None


	def _run_job(self):
		raise NotImplementedError



class Timestamped(Job):
	start_time: datetime = None
	finish_time: datetime = None


	def reset(self):
		super().reset()
		self.start_time = None
		self.finish_time = None


	def run(self):
		self.start_time = datetime.now()
		super().run()
		self.finish_time = datetime.now()


	def progress(self):
		progress = super().progress()
		progress['current_time'] = datetime.now()
		progress['start_time'] = self.start_time
		progress['finish_time'] = self.finish_time
		if self.start_time is not None:
			progress['started'] = progress['current_time'] - self.start_time
			progress['started_human'] = humanize.naturaldelta(progress['started'])
		if self.finish_time is not None:
			progress['finished'] = self.finish_time - self.current_time
			progress['finished_human'] = humanize.naturaldelta(progress['finished'])
		if self.start_time is not None and self.finish_time is not None:
			progress['duration'] = self.finish_time - self.start_time
			progress['duration_human'] = humanize.naturaldelta(progress['duration'])
		return progress



class ResourceAware(Timestamped):
	init_snapshot: Dict[str, Any] = None
	end_snapshot: Dict[str, Any] = None

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
		self.init_snapshot = None
		self.end_snapshot = None


	def progress(self, fast: bool = False):
		progress = super().progress()

		current = self.resource_snapshot(fast=fast)

		progress['ram_available'] = current['ram']['available_GB']
		progress['ram_used'] = current['ram']['proc_used_GB']

		if current['gpu'] is None:
			progress['gpu_available'] = 0
			progress['gpu_used'] = 0
			progress['gpu_util'] = 0
		else:
			progress['gpu_available'] = sum(g['smi_free_GB'] for g in current['gpu'])
			progress['gpu_used'] = sum(g['memory_cached_GB'] for g in current['gpu'])
			progress['gpu_util'] = sum(g['utilization'] for g in current['gpu']) / len(current['gpu'])


		return progress


	def run(self):
		if self.init_snapshot is None:
			self.init_snapshot = self.resource_snapshot()
		super().run()
		self.end_snapshot = self.resource_snapshot()



class IterativeJob(Job):
	_stream = None
	_kill_flag: bool = False
	_run_iterations: Optional[int] = None
	num_iterations: int = 0


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


	def _run_job(self):
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


	def progress(self):
		progress = super().progress()
		progress['num_iterations'] = self.num_iterations
		return progress


	def _generate_stream(self): # generator
		raise NotImplementedError



class TimedIterative(Timestamped, IterativeJob):
	init_time = None
	def initialize(self):
		if self._stream is None:
			self.init_time = datetime.now()


	def reset(self):
		super().reset()
		self.init_time = None


	def progress(self):
		progress = super().progress()
		progress['init_time'] = self.init_time

		if self.init_time is not None:
			progress['rate'] = self.num_iterations / (datetime.now() - self.init_time).total_seconds()
		if self.start_time is not None:
			progress['run_rate'] = self.num_iterations / (datetime.now() - self.start_time).total_seconds()
		return progress














