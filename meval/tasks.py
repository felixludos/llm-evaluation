from .imports import *
from .abstract import AbstractTask, AbstractEnvironment




@fig.script('start')
def start_task(cfg: fig.Configuration, *, task_key='task', reporter_key='reporter'):
	reporter: AbstractEnvironment = cfg.pull(reporter_key)
	reporter.record_config(cfg.to_python())

	task: AbstractTask = cfg.pull(task_key)
	task.prepare(reporter)

	working_dir = reporter.prepare(task)
	launch_info = task.launch(working_dir)
	if not task.quiet:
		reporter.report_launch(task, launch_info)

	while True:
		try:
			exit_info = task.monitor(reporter)
		except Exception as error:
			error_info = task.handle(error)
			if error_info is not None:
				if not task.quiet:
					reporter.report_error(task, error_info)
				raise error
		else:
			assert exit_info is not None, f'Monitor must return some exit info: {task}'
			if not task.quiet:
				reporter.report_exit(task, exit_info)
			break

	code = exit_info.get('code', None)
	return code








