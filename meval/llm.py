from .imports import *


from .util import App, post, get

# from tensorflow.keras.models import load_model  # For loading Keras models

app = FastAPI()

# Global variable to hold the model
model = None


class ModelPath(BaseModel):
    model_path: str


class Data(BaseModel):
    data: list  # This should be tailored to the expected input format for your model


@app.post("/load-model")
def load_model(model_path: ModelPath):
    global model
    try:
        # For scikit-learn models
        model = joblib.load(model_path.model_path)

        # For Keras models
        # model = load_model(model_path.model_path)

        return {"message": "Model loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/run-model")
def run_model(data: Data):
    global model
    if model is None:
        raise HTTPException(status_code=400, detail="No model is loaded")

    try:
        # Prediction logic here depends on the type of model and the data format
        # For example, for a scikit-learn classifier:
        prediction = model.predict(data.data)

        # For a Keras model, ensure data is preprocessed correctly
        # prediction = model.predict(preprocessed_data)

        return {"prediction": prediction.tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@fig.component('llm-app')
class LLM_App(App):
    def __init__(self, model_id='microsoft/phi-2', model_args=None, tokenizer_args=None, **kwargs):
        model_args = {} if model_args is None else model_args
        tokenizer_args = {} if tokenizer_args is None else tokenizer_args
        super().__init__(**kwargs)
        self.model_id = model_id
        self.model_args = model_args
        self.tokenizer_args = tokenizer_args

        self.model = None
        self.tokenizer = None

    class nullop(BaseModel):
        nothing: str = None
    @get
    async def ping(self, payload: nullop):
        return 'pong'

    class loader(BaseModel):
        model_id: str = None
        model_args: dict = None
        tokenizer_args: dict = None
    @post
    async def load(self, payload: loader):
        return {'message': 'hello'}

        model_id = payload.model_id or self.model_id

        status = 'loaded' if self.model is None else 'null'

        if self.model is None:

            model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, **self.model_args)
            tokenizer = AutoTokenizer.from_pretrained(model_id, **self.tokenizer_args)

            self.model = model
            self.tokenizer = tokenizer

        elif self.model_id != model_id:
            raise ValueError(f"Model already loaded: {self.model_id}")

        return {'model_id': model_id, 'status': status}



@fig.script('llm')
def start_llm(cfg: fig.Configuration):
    # app = FastAPI()
    # @app.get("/")
    # async def root():
    #     return {"message": "Hello World"}
    # uvicorn.run(app, host='localhost', port=8000)

    cfg.push('app._type', 'llm-app', overwrite=False, silent=True)
    app = cfg.pull('app')

    app.run()














