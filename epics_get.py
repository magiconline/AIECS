from functools import wraps

import torch
from sklearn.datasets import load_boston


def tensor_wrapper(func):
    @wraps(func)
    def f(*args, **kwargs):
        tensor = torch.Tensor(func(*args, **kwargs))
        if tensor.dim() == 1:
            # tensor为向量则添加一维 > N * 1
            tensor = tensor.unsqueeze(-1)
        return tensor
    return f


@tensor_wrapper
def get_boston_CRIM():
    return torch.Tensor(load_boston()['data'][:, 0])


@tensor_wrapper
def get_boston_ZN():
    return load_boston()['data'][:, 1]


@tensor_wrapper
def get_boston_INDUS():
    return load_boston()['data'][:, 2]


@tensor_wrapper
def get_boston_CHAS():
    return load_boston()['data'][:, 3]


@tensor_wrapper
def get_boston_NOX():
    return load_boston()['data'][:, 4]


@tensor_wrapper
def get_boston_RM():
    return load_boston()['data'][:, 5]


@tensor_wrapper
def get_boston_AGE():
    return load_boston()['data'][:, 6]


@tensor_wrapper
def get_boston_DIS():
    return load_boston()['data'][:, 7]


@tensor_wrapper
def get_boston_RAD():
    return load_boston()['data'][:, 8]


@tensor_wrapper
def get_boston_TAX():
    return load_boston()['data'][:, 9]


@tensor_wrapper
def get_boston_PTRATIO():
    return load_boston()['data'][:, 10]


@tensor_wrapper
def get_boston_B():
    return load_boston()['data'][:, 11]


@tensor_wrapper
def get_boston_LSTAT():
    return load_boston()['data'][:, 12]


@tensor_wrapper
def get_boston_PRICE():
    return load_boston()['target']
