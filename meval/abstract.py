from .imports import *



class AbstractEndpoint:
    @property
    def ident(self) -> str:
        raise NotImplementedError

    def describe(self) -> Dict[str, JSONABLE]:
        raise NotImplementedError
    
    def wrap_prompt(self, prompt: str) -> JSONOBJ:
        raise NotImplementedError
    
    def wrap_chat(self, chat: List[Dict[str, str]]) -> JSONOBJ:
        raise NotImplementedError

    def send_no_wait(self, data: JSONOBJ) -> JSONOBJ:
        raise NotImplementedError
    
    def send(self, data: JSONOBJ) -> JSONOBJ:
        raise NotImplementedError
    
    def get_response(self, prompt: Union[str, List[Dict[str, str]]]) -> str:
        raise NotImplementedError

    def extract_response(self, data: JSONOBJ) -> str:
        raise NotImplementedError

    def count_tokens(self, message: str) -> int:
        raise NotImplementedError






