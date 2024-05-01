from .imports import *

from .abstract import AbstractTask, AbstractReporter
from .reporters import ReporterBase



class Client(AbstractTask):



	pass



@fig.script('start')
def start_task(cfg: fig.Configuration, *, task_key='task', reporter_key='reporter'):

	task: AbstractTask = cfg.pull(task_key)

	reporter: ReporterBase = cfg.pull(reporter_key)

	reporter.prepare(cfg)
	if task.needs_space:
		working_dir = reporter.prepare(cfg)

	launch_info = client.launch(working_dir)
	reporter.report_launch(launch_info)

	while True:
		try:
			exit_info = client.monitor(reporter)
		except Exception as error:
			error_info = client.handle(error)
			if error_info is not None:
				reporter.report_error(error_info)
				raise error
		else:
			assert exit_info is not None, f'Monitor must return some exit info: {client}'
			reporter.report_exit(exit_info)
			break

	code = exit_info.get('code', None)
	return code


















