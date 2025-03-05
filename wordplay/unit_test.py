from .imports import *
from .endpoints import Endpoint
from .datasets import TableDataset, DataCollection


def test_mock_endpoint():

    ep = Endpoint.find('mock').validate()

    assert ep.ident == 'mock'

    assert isinstance(ep.get_response('hello'), str)

    cfg: fig.Configuration = fig.create_config(_type='mock')

    ep2 = cfg.create()

    assert ep2.ident == 'mock'

    assert ep is ep2



def test_data_collection():
    ls = [1,2,3]
    ds = TableDataset({'a': ls, 'b': ['x', 'y', 'z']})

    col = DataCollection([ds, ds])
    col.load()

    for i, x in enumerate(col.iterate()):
        idx = x['index']
        assert idx == i
        y = x['a']
        assert y == ls[i % 3]
        assert x['index'] == i






