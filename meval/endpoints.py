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
                print(f'Warning: Endpoint "{name}" is already registered. Replacing: {cls._registered[name].__name__} with {cls.__name__}')
            cls._registered_endpoints[name] = cls
            cls._endpoint_name = name
        return super().__init_subclass__()


    @classmethod
    def connect(cls, ident: Union[str, 'Endpoint']) -> 'Endpoint':
        if isinstance(ident, Endpoint):
            return ident
        name = ident.split('-')[0]
        if name not in cls._registered_endpoints:
            raise ValueError(f'Endpoint "{name}" is not registered.')
        return cls._registered_endpoints[name](ident=ident)


    @classmethod
    def active_endpoints(cls) -> Iterator['Endpoint']:
        yield from cls._active.values()


    _active = {}
    def __new__(cls, ident: str, **kwargs):
        if cls._endpoint_name is None:
            return cls.connect(ident)
        if ident in cls._active:
            return cls._active[ident]
        new = super().__new__(cls)
        cls._active[ident] = new
        return new


    def __init__(self, ident: str, **kwargs):
        super().__init__(**kwargs)
        self._ident = ident


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
    def __init__(self, ident: str, **kwargs):
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



class ChatGPT(Endpoint, name='gpt'):
    def __init__(self, ident: str, **kwargs):
        super().__init__(ident=ident, **kwargs)
        self.tokenizer = tiktoken.encoding_for_model(ident)


    def count_tokens(self, message: str) -> int:
        return len(self.tokenizer.encode(message))







