from .imports import *
from .abstract import AbstractSystem, AbstractBenchmark, AbstractDataset, AbstractSample
from .datasets import System, Planner, Sample
from .meters import Meter


class BenchmarkBase(fig.Configurable, AbstractBenchmark):
	def __init__(self, dataset: AbstractDataset, env: Dict[str, AbstractGadget] = None, **kwargs):
		super().__init__(**kwargs)
		self._dataset = dataset
		self._env = env
		self._past_iterations = None


	@property
	def dataset(self) -> AbstractDataset:
		return self._dataset


	def gadgetry(self) -> Iterator[AbstractGadget]:
		yield from self._env.values()


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
		for sample in system.iterate(plan=plan):
			yield sample
			self._past_iterations += 1


	def announce(self, system: Optional[System] = None) -> str:
		if system is not None:
			return system.announce()


	_System = System
	def prepare(self, **kwargs) -> System:
		self._past_iterations = 0
		self.dataset.load()
		return self._System(self.dataset, env=self._env)


	def step(self, sample: AbstractSample):
		raise NotImplementedError


	def end(self, last_sample: Optional[AbstractSample]) -> JSONOBJ:
		pass



@fig.component('simple')
class SimpleBenchmark(BenchmarkBase):
	def __init__(self, dataset: AbstractDataset, *, metrics: Iterable[str] = None, **kwargs):
		super().__init__(dataset, **kwargs)
		self._metrics = metrics or []
		self._meters = None


	_Meter = Meter
	_no_meters_found_msg = 'WARNING: No metrics have been specified'
	def prepare(self, **kwargs) -> System:
		system = super().prepare(**kwargs)
		if not self._metrics:
			print(self._no_meters_found_msg)
		self._meters = {key: self._Meter(window_size=max(1, self.dataset.size/50)) for key in self._metrics}
		return system


	def step(self, sample: Sample) -> None:
		for key, meter in self._meters.items():
			meter.mete(sample[key])


	def end(self, last_sample: Optional[AbstractSample]) -> JSONOBJ:
		return {key: meter.json() for key, meter in self._meters.items()}



@fig.modifier('wandb')
class WandB(BenchmarkBase):
	def __init__(self, *, selection: Iterable[str] = None, use_wandb: bool = None, pause_after: Optional[int] = None,
				 show_first: Optional[int] = 1, wandb_dir: Union[str, Path] = None, **kwargs):
		if use_wandb is None:
			try:
				import wandb
			except ImportError:
				use_wandb = False
			else:
				use_wandb = True
		super().__init__(**kwargs)
		self._use_wandb = use_wandb
		self._selection = set(selection)
		self._wandb_dir = wandb_dir
		self._pause_after = pause_after
		self._show_first = show_first


	def prepare(self, **kwargs) -> System:
		system = super().prepare(**kwargs)
		if self._use_wandb:
			if self._wandb_dir is not None and not self._wandb_dir.exists():
				print(f'WARNING: WandB dir {self._wandb_dir} does not exist (creating it now)')
			self._wandb_dir.mkdir(exist_ok=True)
			import wandb
			wandb.init(project=self.name, config=self.settings(system), dir=self._wandb_dir)
			if self._pause_after is not None:
				wandb.config.confirmed = False
		return system


	_pause_signal = '-- PAUSING {now} for confirmation through WandB ---'
	def _pause(self):
		import wandb
		if self._pause_signal is not None:
			print(self._pause_signal.format(now=datetime.now().strftime("%d %b %Y %H:%M:%S")))
			self._pause_signal = None
			wandb.alert('Pausing', 'Change "confirm" in the config to true to continue.')
		while not wandb.config.confirmed:
			wandb.config.update()
			time.sleep(5)
		self._pause_after = None


	def step(self, sample: Sample) -> None:
		if self._use_wandb and self._pause_after is not None and self._pause_after == 0:
			self._pause()
		out = super().step(sample)
		itr = self._past_iterations + 1
		if self._use_wandb and self._show_first is not None and self._show_first >= itr:
			if self._selection is not None:
				for key in self._selection:
					sample.grab(key)

			content = {key: self._format_wandb_value(key, sample[key]) for key in sample.cached()
					   if self._selection is None or key in self._selection}

			import wandb
			wandb.log(content, step=itr)

		if self._pause_after is not None and self._pause_after == itr:
			self._pause()

		return out


	def _format_wandb_value(self, key: str, value: Any) -> Any:
		return value


	def end(self, last_sample: Optional[AbstractSample]) -> JSONOBJ:
		out = super().end(last_sample)
		if self._use_wandb:
			import wandb
			wandb.finish()
		return out



















