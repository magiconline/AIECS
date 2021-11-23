import time

import torch
from torch.utils.data import DataLoader, TensorDataset
import epics_set
import epics_get

# TODO 显示loss accuracy epoch batch

def call(kwargs: dict, **kwargs_):
    kwargs.update(kwargs_)
    f = eval(kwargs.pop('func'))
    return f(**kwargs)


def set_seed(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def set_device(gpu):
    if gpu and torch.cuda.is_available():
        device = torch.device('cuda')
    else:
        device = torch.device('cpu')
    return device


def build_net(net_model):
    layers = [call(net_model['kwargs'])]

    while net_model['in_items'][0]['dtype'] == 'model':
        net_model = net_model['in_items'][0]
        layers.append(call(net_model['kwargs']))

    net = torch.nn.Sequential(*layers[::-1])

    x_train = build_data(net_model['in_items'][0])

    return net, x_train


def cat(**kwargs):
    kwargs['tensors'] = tuple(kwargs.pop('in_items'))
    return torch.cat(**kwargs)


def build_data(model):
    # model: data 或 preprocess
    if model['dtype'] == 'preprocess':
        in_items = [build_data(in_item) for in_item in model['in_items']]
        return call(model['kwargs'], in_items=in_items)
    elif model['dtype'] == 'data':
        return call(model['kwargs'])


def DL(*args, **kwargs):
    models = args[0]

    for model in models:
        if model['dtype'] == 'hyperparameters':
            hyperparameters_model = model
        elif model['dtype'] == 'optimizer':
            optimizer_model = model

    # hyperparameter
    EPOCH = hyperparameters_model['kwargs']['epoch']
    BATCH_SIZE = hyperparameters_model['kwargs']['batch_size']
    SHUFFLE = hyperparameters_model['kwargs']['shuffle']
    GPU = hyperparameters_model['kwargs']['gpu']
    SEED = hyperparameters_model['kwargs']['seed']
    MODEL_PATH = hyperparameters_model['kwargs']['model_path']
    set_seed(SEED)
    device = set_device(GPU)


    # build model
    if len(optimizer_model['in_items']) == 1 and optimizer_model['in_items'][0]['dtype'] == 'loss':
        loss_model = optimizer_model['in_items'][0]
    else:
        raise Exception('Wrong in_items of optimizer.')

    # 构建loss
    if len(loss_model['in_items']) != 2:
        raise Exception('Wrong in_items of optimizer.')

    for model in loss_model['in_items']:
        if model['dtype'] in ['data', 'preprocess']:
            y_true = build_data(model)
        elif model['dtype'] == 'model':
            net, x_true = build_net(model)

    net.to(device)

    optimizer = call(optimizer_model['kwargs'], params=net.parameters())
    loss_func = call(loss_model['kwargs'])

    # dataloader
    dataset = TensorDataset(x_true.to(device), y_true.to(device))
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=SHUFFLE)

    for epoch in range(EPOCH):
        tic = time.time()
        total_loss = 0
        net.train()

        for x_train, y_train in dataloader:
            y_pred = net(x_train)

            loss = loss_func(y_pred, y_train)
            total_loss += loss.item()

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        toc = time.time()
        print(f"epoch: {epoch}, loss: {total_loss}, time used: {toc - tic}")

    # result
    torch.save(net.state_dict(), MODEL_PATH)
    print('训练完成')
