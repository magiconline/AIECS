import json
import os
import torch
from test_IO import *
from torch.nn import *
from torch.optim import *
from torch.utils.data import DataLoader, Dataset, TensorDataset
from torch import cat

class CLSRUN():
    def __init__(self):
        pass

def str_dict(d, func='func', params={}):
    s = d[func] + '('
    for k, v in params.items():
        if k != func:
            if isinstance(v, dict):
                v = str_dict(v)
            s = s + k + '=' + v + ','

    for k, v in d.items():
        if k != func:
            if isinstance(v, dict):
                v = str_dict(v)
            elif isinstance(v, list):
                v = tuple([str_dict(i) for i in v])
            s = s + k + '=' + v + ','

    return s

def run(json_path):
    with open(json_path) as f:
        js = json.load(f)

    EPOCH = js['main']['hyperparameters']['epoch']
    BATCH_SIZE = js['main']['hyperparameters']['batch_size']
    SHUFFLE = js['main']['hyperparameters']['shuffle']
    SEED = js['main']['hyperparameters']['seed']
    GPU = js['main']['hyperparameters']['gpu']

    optimizer = eval(str_dict(js['main']['optimizer']))

    loss_func = eval(str_dict(js['main']['']))

    y = eval(str_dict(js['main']['loss']['y']))

    models = []
    for js_model in js['main']['loss']['models']:
        model = Sequential()
        for layer in js_model['model']:
            model.add_module(eval(str_dict(layer)))

        x = eval(str_dict(js_model['x']))
        models.append([model, x])



if __name__ == '__main__':
    run(json_path=os.path.join('save', 'test2.py'))