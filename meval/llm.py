from .imports import *

from .util import App, post, get, config_data_root, data_root

import asyncio
import threading


@fig.component('llm-app')
class LLM_App(App):
    def __init__(self, *, meta_root=None, out_root=None, **kwargs):
        if meta_root is None:
            meta_root = config_data_root()
        if out_root is None:
            out_root = data_root()
        super().__init__(**kwargs)
        self.meta_root = meta_root
        self.out_root = out_root
        self.outdir = None
        self.runner = None

        self.task_name = None
        self.index = 0


    @get
    async def starting_task(self, ident: str):
        '''start loading without blocking'''
        # self.task = asyncio.create_task(self.dummy_task(ident))

        # start task thread
        self.task = threading.Thread(target=self.dummy_task, args=(ident,))
        self.task.start()

        return f'started {ident}'


    def dummy_task(self, ident: str, num: int = 10):
        self.task_name = ident
        while self.index < num:
            time.sleep(1)
            self.index += 1


    @get
    async def progress(self):
        '''check if the task is done'''
        return {'task': self.task_name, 'index': self.index}


    @get
    async def result(self):
        '''get the result of the task'''
        return {'task': self.task_name, 'result': self.task.join()}


    @get
    async def ping(self):
        return 'pong'


    @get
    async def resources(self):
        stats = self._get_resource_info()
        return stats


    def _get_resource_info(self):
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
                })
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
            "cpu_usage_per_core": psutil.cpu_percent(percpu=True, interval=1),
            "total_cpu_usage": psutil.cpu_percent(interval=1)
        }

        # RAM information
        ram_info = psutil.virtual_memory()
        system_info["ram"] = {
            "total_GB": ram_info.total / (1024 ** 3),
            "available_GB": ram_info.available / (1024 ** 3),
            "used_GB": ram_info.used / (1024 ** 3),
            "percentage_used": ram_info.percent
        }

        return system_info


    @get
    async def meta(self, ident: str):
        meta = self._load_meta_config(ident)
        out = meta.payload
        return out


    def _load_meta_config(self, ident: str):
        options = list(self.meta_root.glob(f'{ident}*'))
        if not options:
            raise HTTPException(status_code=500, detail=f"Meta file not found: {ident}")
        if len(options) > 1:
            raise HTTPException(status_code=500,
                                 detail=f"Multiple meta files found: {', '.join(o.name for o in options)}")

        meta = fig.create_config(options[0])
        meta.push('ident', ident, overwrite=True, silent=True)
        meta.push('config-path', str(options[0]), overwrite=False, silent=True)
        return meta


    @staticmethod
    def create_outdir(ident: str, root: Path):
        now = datetime.now().strftime(f"%Y%m%d-%H%M%S")
        outdir = root / f"{ident}_{now}"
        outdir.mkdir(exist_ok=True)
        return outdir


    @get
    async def track(self, ident: str, force: bool = False):
        if self.outdir is None or force:
            self.outdir = self.create_outdir(ident, self.out_root)
        return {'outdir': str(self.outdir)}


    @post
    async def load(self, ident: str, force: bool = False):
        if self.runner is None or force:

            meta = self._load_meta_config(ident)

            meta.push('runner._type', 'default', overwrite=False, silent=True)
            self.runner = meta.pull('runner')

        if not self.runner.is_loaded():

            if self.outdir is not None:
                save_json(self._get_resource_info(), self.outdir / 'preload-resources.json')

            self.runner.load()

            if self.outdir is not None:
                save_json(self._get_resource_info(), self.outdir / 'postload-resources.json')



        pass


        model_id = payload.name or self.model_id

        status = 'loaded' if self.model is None else 'null'

        if self.model is None:

            model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, **self.model_args)
            tokenizer = AutoTokenizer.from_pretrained(model_id, **self.tokenizer_args)

            self.model = model
            self.tokenizer = tokenizer

        elif self.model_id != model_id:
            raise ValueError(f"Model already loaded: {self.model_id}")

        return {'model_id': model_id, 'status': status}


    @get
    async def autocomplete(self, text: str, max_length: int = 50, num_return_sequences: int = 1):
        if self.model is None:
            raise ValueError("Model not loaded")

        input_ids = self.tokenizer.encode(text, return_tensors='pt')
        input_ids = input_ids.to(self.model.device)

        output = self.model.generate(input_ids, max_length=max_length, num_return_sequences=num_return_sequences)

        return [self.tokenizer.decode(o, skip_special_tokens=True) for o in output]



@fig.script('llm')
def start_llm(cfg: fig.Configuration):

    cfg.push('app._type', 'llm-app', overwrite=False, silent=True)
    app = cfg.pull('app')

    app.run()














