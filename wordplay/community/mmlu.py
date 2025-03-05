from .imports import *
import os



@fig.component('mmlu/single')
class SingleMMLU(FileDataset):
	@property
	def name(self):
		return f'MMLU-{self.path.stem}'


	_columns = ('question', 'A', 'B', 'C', 'D', 'answer') # columns of the raw csv files
	def _load_data(self) -> dict[str, list[Any]]:
		data = super()._load_data()
		choices = list(zip(data['A'], data['B'], data['C'], data['D']))
		del data['A'], data['B'], data['C'], data['D']
		data['choices'] = choices
		order = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
		data['answer'] = [order[a] for a in data['answer']]
		self._columns = ('question', 'choices', 'answer')
		return data



@fig.component('mmlu/dataset')
class MMLU_Dataset(Dataset):
	topic = hparam('full')
	split = hparam('val') # 'val', 'dev', 'test'

	# dataroot = hparam(update=as_path)
	@hparam(update=as_path)
	def dataroot(self) -> Path:
		return Path(os.environ.get('DATAROOT', '~/local_data/')).expanduser().resolve().joinpath('MMLU')


	@property
	def name(self) -> str:
		return 'MMLU'


	@property
	def size(self) -> Optional[int]:
		return self._total_size


	_total_size = None
	subjects = None
	_subject_indices = None
	_subject_datasets = None
	_Single_Subject_Dataset = SingleMMLU
	def load(self):
		if self._subject_datasets is None:
			root = self.dataroot.joinpath(self.split)
			self._subject_datasets = {
				subject: self._Single_Subject_Dataset(root.joinpath(f'{subject}_{self.split}.csv'))
				for subject in _mmlu_subjects(self.topic, only_subjects=True)
			}
			for dataset in self._subject_datasets.values():
				dataset.load()
			self._total_size = sum(dataset.size for dataset in self._subject_datasets.values())
			import numpy as np
			self.subjects = [subject for subject in self._subject_datasets]
			self._subject_indices = np.array([dataset.size for dataset in self._subject_datasets.values()]).cumsum() - 1
		return self


	@tool('subject', 'sample_index')
	def to_subject_index(self, index: int) -> Tuple[str, int]:
		subject_index = self._subject_indices.searchsorted(index, side='left')
		subject = self.subjects[subject_index]
		sample_index = index - self._subject_indices[subject_index] - 1 if subject_index > 0 else index
		return subject, sample_index


	@tool('question')
	def get_question(self, subject: str, sample_index: int) -> str:
		return self._subject_datasets[subject].getvalue('question', sample_index)


	@tool('choices')
	def get_choices(self, subject: str, sample_index: int) -> List[str]:
		return self._subject_datasets[subject].getvalue('choices', sample_index)


	@tool('answer')
	def get_answer(self, subject: str, sample_index: int) -> int:
		return self._subject_datasets[subject].getvalue('answer', sample_index)



@fig.component('mmlu')
class MMLU(BenchmarkBase):
	topic = hparam('full')
	split = hparam('val') # 'val', 'test'


	_Dataset = MMLU_Dataset
	def __init__(self, *, correct_key: str = 'correct', include_subject: bool = True, app: dict[str,str] = None,
				 dataroot: str = None, **kwargs):
		super().__init__(dataset=None, **kwargs)
		if self._dataset is None:
			self._dataset = self._Dataset(topic=self.topic, split=self.split, dataroot=dataroot, gap=app)
		if include_subject:
			subject = self._dataset.gap('subject')
			if subject not in self._log:
				self._log.insert(0, subject)
			sample_index = self._dataset.gap('sample_index')
			if sample_index not in self._log:
				self._log.insert(1, sample_index)

		self._correct_key = correct_key
		self._subject_key = self._dataset.gap('subject')
		self._meters = {}


	@property
	def name(self) -> str:
		return 'MMLU'


	def _prepare_metrics(self, system: System) -> None:
		self._meters = {subject: self._Meter(window_size=max(1, self.dataset.size / 50))
						for subject in self.dataset.subjects}


	def _step(self, sample: 'Sample') -> Optional[Dict[str, Union[Meter, float]]]:
		self._meters[sample[self._subject_key]].mete(sample[self._correct_key])


	def _final_results(self, last_sample: Optional[AbstractSample]) -> Optional[Dict[str, Union[Meter, float]]]:
		topics = {topic: tuple(set(_mmlu_subjects(topic, only_subjects=True)))
					for topic in set(_mmlu_subjects(self.topic, only_subjects=False))}

		totals = {topic: self._Meter() for topic in topics}

		for topic, meter in totals.items():
			for sub in topics[topic]:
				meter.merge(self._meters[sub])

		totals = {f'{self.split}/{_mmlu_subject_titles[topic]}': meter for topic, meter in totals.items()}
		return totals






_mmlu_subject_titles = {
	'full': 'MMLU', 'STEM': 'STEM', 'humanities': 'Humanities', 'social sciences': 'Social Sciences',
	'other (business, health, misc.)': 'Business/Health/Misc', 'math': 'Mathematics', 'physics': 'Physics',
	'chemistry': 'Chemistry', 'biology': 'Biology', 'computer science': 'Computer Science', 'engineering': 'Engineering',
	'history': 'History', 'philosophy': 'Philosophy', 'law': 'Law', 'politics': 'Politics', 'culture': 'Culture',
	'economics': 'Economics', 'geography': 'Geography', 'psychology': 'Psychology', 'other': 'Other', 'business': 'Business',
	'health': 'Health',
	'abstract_algebra': 'Abstract Algebra', 'anatomy': 'Anatomy', 'astronomy': 'Astronomy', 'business_ethics': 'Business Ethics',
	'clinical_knowledge': 'Clinical Knowledge', 'college_biology': 'College Biology', 'college_chemistry': 'College Chemistry',
	'college_computer_science': 'College Computer Science', 'college_mathematics': 'College Mathematics',
	'college_medicine': 'College Medicine', 'college_physics': 'College Physics', 'computer_security': 'Computer Security',
	'conceptual_physics': 'Conceptual Physics', 'econometrics': 'Econometrics', 'electrical_engineering': 'Electrical Engineering',
	'elementary_mathematics': 'Elementary Mathematics', 'formal_logic': 'Formal Logic', 'global_facts': 'Global Facts',
	'high_school_biology': 'High School Biology', 'high_school_chemistry': 'High School Chemistry',
	'high_school_computer_science': 'High School Computer Science', 'high_school_european_history': 'High School European History',
	'high_school_geography': 'High School Geography', 'high_school_government_and_politics': 'High School Government and Politics',
	'high_school_macroeconomics': 'High School Macroeconomics', 'high_school_mathematics': 'High School Mathematics',
	'high_school_microeconomics': 'High School Microeconomics', 'high_school_physics': 'High School Physics',
	'high_school_psychology': 'High School Psychology', 'high_school_statistics': 'High School Statistics',
	'high_school_us_history': 'High School US History', 'high_school_world_history': 'High School World History',
	'human_aging': 'Human Aging', 'human_sexuality': 'Human Sexuality', 'international_law': 'International Law',
	'jurisprudence': 'Jurisprudence', 'logical_fallacies': 'Logical Fallacies', 'machine_learning': 'Machine Learning',
	'management': 'Management', 'marketing': 'Marketing', 'medical_genetics': 'Medical Genetics', 'miscellaneous': 'Miscellaneous',
	'moral_disputes': 'Moral Disputes', 'moral_scenarios': 'Moral Scenarios', 'nutrition': 'Nutrition', 'prehistory': 'Prehistory',
	'professional_accounting': 'Professional Accounting', 'professional_law': 'Professional Law', 'professional_medicine': 'Professional Medicine',
	'professional_psychology': 'Professional Psychology', 'public_relations': 'Public Relations', 'security_studies': 'Security Studies',
	'sociology': 'Sociology', 'us_foreign_policy': 'US Foreign Policy', 'virology': 'Virology', 'world_religions': 'World Religions',
}


_mmlu_topics = {
	'full': ['STEM', 'humanities', 'social sciences', 'other (business, health, misc.)'],
	"STEM": ["physics", "chemistry", "biology", "computer science", "math", "engineering"],
	"humanities": ["history", "philosophy", "law"],
	"social sciences": ["politics", "culture", "economics", "geography", "psychology"],
	"other (business, health, misc.)": ["other", "business", "health"],
}

_mmlu_subject_leaves = {
	'math': ['abstract_algebra',
  'college_mathematics',
  'elementary_mathematics',
  'high_school_mathematics',
  'high_school_statistics'],
 'health': ['anatomy',
  'clinical_knowledge',
  'college_medicine',
  'human_aging',
  'medical_genetics',
  'nutrition',
  'professional_medicine',
  'virology'],
 'physics': ['astronomy',
  'college_physics',
  'conceptual_physics',
  'high_school_physics'],
 'business': ['business_ethics', 'management', 'marketing'],
 'biology': ['college_biology', 'high_school_biology'],
 'chemistry': ['college_chemistry', 'high_school_chemistry'],
 'computer science': ['college_computer_science',
  'computer_security',
  'high_school_computer_science',
  'machine_learning'],
 'economics': ['econometrics',
  'high_school_macroeconomics',
  'high_school_microeconomics'],
 'engineering': ['electrical_engineering'],
 'philosophy': ['formal_logic',
  'logical_fallacies',
  'moral_disputes',
  'moral_scenarios',
  'philosophy',
  'world_religions'],
 'other': ['global_facts', 'miscellaneous', 'professional_accounting'],
 'history': ['high_school_european_history',
  'high_school_us_history',
  'high_school_world_history',
  'prehistory'],
 'geography': ['high_school_geography'],
 'politics': ['high_school_government_and_politics',
  'public_relations',
  'security_studies',
  'us_foreign_policy'],
 'psychology': ['high_school_psychology', 'professional_psychology'],
 'culture': ['human_sexuality', 'sociology'],
 'law': ['international_law', 'jurisprudence', 'professional_law']}



def _mmlu_subjects(topic: str, only_subjects: bool = False) -> Iterator[str]:
	if topic not in _mmlu_topics and topic not in _mmlu_subject_leaves:
		yield topic

	elif topic in _mmlu_topics:
		if not only_subjects:
			yield topic
		for sub in _mmlu_topics[topic]:
			yield from _mmlu_subjects(sub, only_subjects)

	elif topic in _mmlu_subject_leaves:
		if not only_subjects:
			yield topic
		yield from _mmlu_subject_leaves[topic]
