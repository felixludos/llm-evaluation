from .imports import *
from .abstract import AbstractEndpoint
import tiktoken, time


class Endpoint(fig.Configurable, AbstractEndpoint):
    """
    Endpoints define how requests are sent

    They should generally use info that is *required* for requests to be sent, but they should *not* handle
    hyperparameters or details of a send request (as those should be handled upstream).
    """
    _endpoint_name = None
    _registered_endpoints = {}
    def __init_subclass__(cls, name=None, **kwargs):
        if name is not None:
            if '-' in name:
                raise ValueError(f'Invalid name: "{name}". Name cannot contain "-".')
            if name in cls._registered_endpoints:
                print(f'Warning: Endpoint "{name}" is already registered. Replacing: '
                      f'{cls._registered_endpoints[name].__name__} with {cls.__name__}')
            cls._registered_endpoints[name] = cls
            cls._endpoint_name = name
        return super().__init_subclass__()


    @classmethod
    def find(cls, ident: str) -> 'Endpoint':
        name = ident.split('-')[0]
        if name not in cls._registered_endpoints:
            raise ValueError(f'Endpoint "{name}" is not registered.')
        return cls._registered_endpoints[name](ident=ident)


    @classmethod
    def active_endpoints(cls) -> Iterator['Endpoint']:
        yield from cls._active.values()


    _active = {}
    def __init__(self, ident: str = None, **kwargs):
        if ident is None: ident = self._endpoint_name
        super().__init__(**kwargs)
        self._ident = ident


    def validate(self) -> 'Endpoint':
        return self._active.setdefault(self._ident, self)


    def __repr__(self):
        return f'<{self.__class__.__name__} {self.ident}>'


    def __str__(self):
        return self.ident


    @property
    def ident(self) -> str:
        return self._ident


    def wrap_prompt(self, prompt: str) -> JSONOBJ:
        return self.wrap_chat([{'role': 'user', 'content': prompt}])
    

    def get_response(self, prompt: Union[str, List[Dict[str, str]]]) -> str:
        if isinstance(prompt, str):
            prompt = self.wrap_prompt(prompt)
        else:
            prompt = self.wrap_chat(prompt)
        full = self.send(prompt)
        return self.extract_response(full)


    def _record_send(self, data: JSONOBJ) -> JSONOBJ:
        pass

    def _record_send_no_wait(self, data: JSONOBJ) -> JSONOBJ:
        return self._record_send(data)

    def _record_response(self, data: JSONOBJ, resp: JSONOBJ) -> JSONOBJ:
        pass

    def _record_step(self, data: JSONOBJ, step: JSONOBJ) -> JSONOBJ:
        pass


    def send(self, data: JSONOBJ) -> JSONOBJ:
        self._record_send(data)
        resp = self._send(data)
        self._record_response(data, resp)
        return resp


    def _send(self, data: JSONOBJ) -> JSONOBJ:
        raise NotImplementedError


    def send_no_wait(self, data: JSONOBJ) -> Iterator[JSONOBJ]:
        self._record_send_no_wait(data)
        for resp in self._send_no_wait(data):
            self._record_step(data, resp)
            yield resp


    def _send_no_wait(self, data: JSONOBJ) -> Iterator[JSONOBJ]:
        raise NotImplementedError


@fig.component('mock')
class MockEndpoint(Endpoint, name='mock'):
    def __init__(self, ident: str = None, **kwargs):
        super().__init__(ident=ident, **kwargs)
        self.tokenizer = tiktoken.get_encoding("cl100k_base")


    def count_tokens(self, message: str) -> int:
        return len(self.tokenizer.encode(message))


    def wrap_chat(self, chat: List[Dict[str, str]]) -> JSONOBJ:
        return {'chat': chat}


    def extract_response(self, data):
        return data['response']


    def _send(self, data: JSONOBJ) -> JSONOBJ:
        assert 'chat' in data
        chat = data['chat']
        return {'response': f'This is the mock response to a chat with {len(chat)} messages.'}


    def _send_no_wait(self, data):
        resp = self._send(data)
        for token in resp['response'].split():
            time.sleep(0.03)
            yield {'response': token}


import openai

class ChatGPT(Endpoint, name='gpt'):
    # def __init__(self, ident: str = 'gpt-4o', temperature: float = 0.7, top_p: float = 1.0, #seed: int = 1000000007,
    #              frequency_penalty: float = 0., presence_penalty: float = 0., **kwargs):
    def __init__(self, ident: str = 'gpt-4o', **kwargs):
        super().__init__(ident=ident, **kwargs)
        self.tokenizer = tiktoken.encoding_for_model(ident)


    def count_tokens(self, message: str) -> int:
        return len(self.tokenizer.encode(message))


    def wrap_chat(self, chat: List[Dict[str, str]], model: str = None) -> JSONOBJ:
        if model is None:
            model = self.ident
        return {'messages': chat, 'model': model}


    def _send(self, data: JSONOBJ) -> openai.ChatCompletion:
        response = openai.ChatCompletion.create(**data)
        return response


    def _send_no_wait(self, data: JSONOBJ) -> Iterator[openai.ChatCompletion]:
        response = openai.ChatCompletion.create(stream=True, **data)
        yield response


    def extract_response(self, data: openai.ChatCompletion) -> str:
        return data.choices[0].message['content']







