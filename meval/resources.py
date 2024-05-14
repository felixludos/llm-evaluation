from .imports import *

import psutil


def gpu_snapshot():
	import pynvml

	pynvml.nvmlInit()

	device_count = pynvml.nvmlDeviceGetCount()

	gpu_info = []

	for i in range(device_count):
		handle = pynvml.nvmlDeviceGetHandleByIndex(i)
		info = pynvml.nvmlDeviceGetMemoryInfo(handle)
		# utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
		gpu_info.append({
			"name": pynvml.nvmlDeviceGetName(handle),
			"total_memory_GB": info.total / (1024 ** 3),
			"memory_allocated_GB": info.used / (1024 ** 3),
			# "memory_cached_GB": info.free / (1024 ** 3),
			# 'utilization_gpu_pct': utilization.gpu,
			# 'utilization_mem_pct': utilization.memory,
		})

	pynvml.nvmlShutdown()

	return gpu_info



def resource_snapshot(*, cpu_interval: Optional[int] = None, include_gpu: bool = True):
	system_info = {}

	# GPU information (if CUDA is available)
	if include_gpu:
		import torch
		from pynvml.smi import nvidia_smi
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
		# "percentage_used": ram_info.percent,
		"proc_used_GB": proc.memory_info().rss / (1024 ** 3),
	}

	return system_info









