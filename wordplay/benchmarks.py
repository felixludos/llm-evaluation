import csv

from .imports import *
from .abstract import AbstractSystem, AbstractBenchmark, AbstractDataset, AbstractSample
from .datasets import System, Planner, Sample, DataCollection
from .meters import Meter
from .modules import Hparamed
from .util import fixed_width_format_value
from .mixins import to_json, Describable, DESCRIPTION



@fig.component('simple')
class BenchmarkBase(Hparamed, Describable, AbstractBenchmark):
	@fig.config_aliases(aggregate='agg')
	def __init__(self, dataset: AbstractDataset, *, env: Dict[str, AbstractGadget] = None,
				 log: Optional[Iterable[str]] = None, out_dir: Path = None, pause_after: Optional[int] = None,
				 selection: Iterable[str] = None, include_cached: bool = True, project_format: str = '{dataset.name}',
				 use_wandb: bool = None, show_first: Optional[int] = 1, use_pbar: bool = None, show_metrics: int = 3,
				 name_format: str = '{dataset.name}_{now.strftime("%y%m%d-%H%M%S")}', **kwargs):
		if env is None: env = {}
		if out_dir is not None:
			out_dir = Path(out_dir)
		if use_wandb is None:
			try:
				import wandb
			except ImportError:
				use_wandb = False
			else:
				use_wandb = True
		super().__init__(**kwargs)
		self._dataset = dataset
		self._env = env
		self._past_iterations = None
		self._name_format = name_format
		self._now = datetime.now()
		self._out_dir = out_dir
		self._log = None if log is None else list(log)
		self._log_writer = None
		self._run_env = where_am_i()
		self._use_pbar = use_pbar or (use_pbar is None and self._run_env != 'cluster')
		self._pbar = None
		self._show_metrics = show_metrics

		self._use_wandb = use_wandb
		self._selection = None if selection is None else list(selection)
		self._include_cached = include_cached
		self._wandb_run = None
		self._pause_after = pause_after
		self._check_confirmation = None
		self._show_first = show_first
		self._project_format = project_format


	def settings(self, system: AbstractSystem = None) -> JSONOBJ:
		data = {'datetime': self._now.isoformat(), 'name': self.name,
				'show-first': self._show_first, 'pause-after': self._pause_after}
		if system is not None:
			data.update(system.json())
		return data


	@property
	def name(self):
		if self._wandb_run is None:
			return pformat(self._name_format, now=self._now, benchmark=self, dataset=self.dataset, **self._env)
		return self._wandb_run.name


	@property
	def dataset(self) -> AbstractDataset:
		return self._dataset


	@property
	def root(self) -> Optional[Path]:
		if self._wandb_run is not None:
			return Path(self._wandb_run.dir)
		if self._out_dir is not None:
			root = self._out_dir / self.name
			root.mkdir(exist_ok=True)
			return root


	@property
	def project_name(self):
		return pformat(self._project_format, benchmark=self, dataset=self.dataset, **self._env)


	def gadgetry(self) -> Iterator[AbstractGadget]:
		yield from self._env.values()


	def save(self, data: JSONABLE, *, name: str = None, path: Path = None, overwrite: bool = False) -> Path:
		if (name is None) == (path is None):
			raise ValueError('name or path is required (not both)')
		if path is None:
			root = self.root
			if root is None:
				raise ValueError('no root provided')
			if not name.endswith('.json'):
				name += '.json'
			path = root / name
		elif not path.suffix == '.json':
			raise ValueError('path is not .json')
		if not overwrite and path.exists():
			raise FileExistsError(path)
		save_json(data, path)
		return path


	def run(self, system: System = None, **kwargs) -> Any:
		if system is None:
			system = self.prepare(**kwargs)
		sample = None
		for sample in self.loop(system):
			self.step(sample)
		return self.end(sample)


	_Planner = Planner
	def loop(self, system: AbstractSystem) -> Iterator[AbstractSample]:
		plan = self._Planner(system)
		N = plan.expected_iterations()
		itr = system.iterate(plan=plan)
		if self._use_pbar:
			pbar = tqdm.notebook if self._run_env == 'jupyter' else tqdm.tqdm
			itr = pbar(itr, total=N)
			self._pbar = itr
		for sample in itr:
			yield sample
			self._past_iterations += 1


	def announce(self, system: Optional[System] = None) -> str:
		lines = [f'Name: {self.name}']
		if system is not None:
			lines.append('')
			lines.append(system.announce())
		return '\n'.join(lines)


	_Meter = Meter
	_System = System
	def prepare(self, **kwargs) -> System:
		self._past_iterations = 0
		self.dataset.load()
		system = self._System(self.dataset, env=self._env)
		if self._use_wandb:
			if self._out_dir is not None and not self._out_dir.exists():
				print(f'WARNING: WandB dir {self._out_dir} does not exist (creating it now)')
				self._out_dir.mkdir(exist_ok=True)
			import wandb
			self._wandb_run = wandb.init(project=self.project_name, config=self.settings(system), dir=self._out_dir)
			if self._pause_after is not None:
				addr = f'{self._wandb_run.entity}/{self._wandb_run.project}/{self._wandb_run.id}'
				self._check_confirmation = lambda: 'confirm' in wandb.apis.public.Api().run(addr).tags
		root = self.root
		if root is not None:
			with root.joinpath('omnifig.yml').open('w', encoding='utf-8') as file:
				file.write(str(self._my_config.root))
			self.save(self.settings(system), name='settings')
			if self._log:
				path = root.joinpath('results.csv')
				exists_already = path.exists()
				if exists_already:
					check = csv.DictReader(path.open('r')) # TODO: test this
					fields = check.fieldnames
					if fields != self._log:
						raise ValueError('log files do not match')
				self._log_writer = csv.DictWriter(path.open('a', encoding='utf-8', newline=''),
												  fieldnames=self._log)
				if not exists_already:
					self._log_writer.writeheader()
		self._prepare_metrics(system)
		return system


	def _prepare_metrics(self, system: System) -> None:
		pass


	def _step(self, sample: AbstractSample) -> Optional[Dict[str, Union[Meter, float]]]:
		pass


	def _final_results(self, last_sample: Optional[AbstractSample]) -> Optional[Dict[str, Union[Meter, float]]]:
		pass


	_pause_signal = '--- PAUSING {now} for confirmation through WandB ---'
	_confirm_signal = '--- CONTINUING {now} after having received confirmation on WandB ---'
	def _pause(self):
		if self._pause_signal is not None:
			if self._pbar is not None:
				print()
			print(self._pause_signal.format(now=datetime.now().strftime("%d %b %Y %H:%M:%S")))
			self._pause_signal = None

		self._wandb_run.alert('Pausing', 'Change add "confirm" to the tags to continue this job.')
		while self._check_confirmation is not None and not self._check_confirmation():
			time.sleep(5)
		self._wandb_run.alert('Continuing', 'Received "confirm" signal, and now continuing.')

		if self._confirm_signal is not None:
			if self._pbar is not None:
				print()
			print(self._confirm_signal.format(now=datetime.now().strftime("%d %b %Y %H:%M:%S")))
		self._pause_after = None


	def step(self, sample: AbstractSample):
		itr = self._past_iterations + 1
		if self._wandb_run is not None:
			if self._pause_after is not None and self._pause_after == 0:
				self._pause()

		results = self._step(sample)

		if self._pbar is not None and results:
			self._pbar.set_description(', '.join(f'{key}={fixed_width_format_value(meter.smooth, 5)}'
										for (key, meter), _ in zip(results.items(), range(self._show_metrics))) )
		if self._log is not None and self._log_writer is not None:
			self._log_writer.writerow({key: sample[key] for key in self._log})

		if self._wandb_run is not None and self._show_first is not None and self._show_first >= itr:
			if self._selection:
				for key in self._selection:
					sample.grab(key)
			content = {key: self._format_wandb_value(key, sample[key]) for key in sample.cached()
					   if self._selection is None or key in self._selection}
			if not self._include_cached and self._selection is not None:
				content = {key: value for key, value in content.items() if key in self._selection}
			content = {key: str(value) for key, value in content.items() if value is not None}
			if content:
				import wandb
				self._wandb_run.log({f'report': wandb.Table(data=list(content.items()), columns=['Key', 'Value'])})

		if self._wandb_run is not None and self._pause_after is not None and self._pause_after == itr:
			self._pause()


	def _format_wandb_value(self, key: str, value: Any) -> Any:
		if isinstance(value, Meter):
			return value.avg
		return value


	def end(self, last_sample: Optional[AbstractSample]) -> JSONOBJ:
		if self._pbar is not None:
			self._pbar.close()
		out = self._final_results(last_sample)
		json_out = to_json(out)
		if self._out_dir is not None and len(out):
			self.save(json_out, name='summary')
		if self._wandb_run is not None:
			means = {key: self._format_wandb_value(key, value) for key, value in out.items()}
			if means:
				self._wandb_run.summary.update(means)
				# self._wandb_run.log(means, step=self._past_iterations)
			self._wandb_run.finish()
		return json_out



@fig.component('generic')
class SimpleBenchmark(BenchmarkBase):
	@fig.config_aliases(aggregate='agg')
	def __init__(self, dataset: AbstractDataset, *, env: Dict[str, AbstractGadget] = None,
				 aggregate: Iterable[str] = None, **kwargs):
		super().__init__(dataset=dataset, env=env, **kwargs)
		self._metrics = aggregate or []
		self._meters = {}


	_no_meters_found_msg = 'WARNING: No metrics have been specified'
	def _prepare_metrics(self, system: System) -> None:
		if not self._metrics:
			print(self._no_meters_found_msg)
		self._meters = {key: self._Meter(window_size=max(1, self.dataset.size / 50)) for key in self._metrics}


	def _step(self, sample: AbstractSample) -> Optional[Dict[str, Union[Meter, float]]]:
		for key, meter in self._meters.items():
			value = sample[key]
			if isinstance(value, (float, int)):
				meter.mete(value)
		return self._meters


	def _final_results(self, last_sample: Optional[AbstractSample]) -> Optional[Dict[str, Union[Meter, float]]]:
		out = {key: meter.json() for key, meter in self._meters.items()}
		return out









