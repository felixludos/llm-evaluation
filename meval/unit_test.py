from .imports import *
from .endpoints import Endpoint


def test_mock_endpoint():

    ep = Endpoint.find('mock').validate()

    assert ep.ident == 'mock'

    assert isinstance(ep.get_response('hello'), str)

    cfg: fig.Configuration = fig.create_config(_type='mock')

    ep2 = cfg.create()

    assert ep2.ident == 'mock'

    assert ep is ep2




