from .imports import *
from .endpoints import Endpoint


def test_mock_endpoint():

    ep = Endpoint.connect('mock')

    assert ep.ident == 'mock'

    assert isinstance(ep.get_response('hello'), str)

