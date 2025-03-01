from .imports import *



def repo_root():
	return Path(__file__).parent.parent



@fig.autocomponent('default-config-root')
def config_job_root():
	return repo_root() / 'job-config'



def config_model_root():
	return repo_root() / 'config' / 'models'



def config_data_root():
	return repo_root() / 'config' / 'data'



def data_root():
	return repo_root() / 'out-data'



class _hook:
	def __init__(self, fn=None, *args, **kwargs):
		super().__init__()
		self.fn = fn
		self.name = None if fn is None else fn.__name__
		self._got_called = False
		self.args, self.kwargs = args, kwargs

	def __call__(self, fn):
		self._got_called = True
		self.name = self.fn or fn.__name__
		self.fn = fn

	def package(self, app):
		assert self.name is not None
		self.name = f'/{self.name}'
		return self.fn.__get__(app, type(app))


class post(_hook):
	pass


class get(_hook):
	pass


class App(fig.Configurable):
	def __init__(self, *, host='localhost', port=8000):
		app = FastAPI()
		self.app = app
		self.host = host
		self.port = port

		for item in dir(type(self)):
			if item.startswith('_'):
				continue
			attr = getattr(self, item)
			if isinstance(attr, _hook):
				fn = attr.package(self)
				if isinstance(attr, post):
					app.post(attr.name, *attr.args, **attr.kwargs)(fn)
				elif isinstance(attr, get):
					app.get(attr.name, *attr.args, **attr.kwargs)(fn)
				else:
					raise TypeError(f"Unknown hook type: {type(attr)}")

	def run(self):
		# self.cfg.print('Starting server')
		uvicorn.run(self.app, host=self.host, port=self.port)



def deep_update(info1: dict, info2: dict, *other: dict):
	if len(other):
		merged = deep_update(info1, info2)
		return deep_update(merged, *other)

	merged = {}
	for k1, v1 in info1.items():
		if k1 in info2:
			v2 = info2[k1]
			if isinstance(v1, dict) and isinstance(v2, dict):
				merged[k1] = deep_update(v1, v2)
			merged[k1] = v2
		else:
			merged[k1] = v1
	for k2, v2 in info2.items():
		if k2 not in info1:
			merged[k2] = v2
	return merged



def resource_snapshot(cpu_interval: Optional[int] = None):
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
	if cpu_interval is not None:
		system_info["cpu"]["cpu_usage_per_core"] = psutil.cpu_percent(percpu=True, interval=cpu_interval)
		system_info["cpu"]["total_cpu_usage"] = (sum(system_info["cpu"]["cpu_usage_per_core"])
												 / len(system_info["cpu"]["cpu_usage_per_core"]))

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




