import json
import os
import time

import numpy as np
from torch.nn import *
from torch.utils.data import DataLoader, TensorDataset

from test_IO import *


def str2func(d, func='func', params={}):
    s = d[func] + '('

    for k, v in params.items():
        if k != func:
            s = s + k + '=' + v + ','

    for k, v in d.items():
        if k != func:
            s = s + k + '=' + v + ','
    s = s + ')'

    print('拼接命令: ' + s)

    return s


def run(json_path):
    t1 = time.time()

    # 读取json文件
    with open(json_path) as f:
        js = json.load(f)

    device = torch.device("cuda" if torch.cuda.is_available() and js['gpu'] else "cpu")
    print(device)

    # 读取数据
    input_data = []
    output_data = []

    for f in js['input']:
        input_data.append(eval(f + '()'))

    for f in js['output']:
        output_data.append(eval(f + '()'))

    # 预处理
    # 拼接数据
    input_data = np.array(input_data)
    input_data = np.transpose(input_data, (1, 0))
    print('输入数据形状: ', input_data.shape)
    print('输入数据类型: ', input_data.dtype)

    output_data = np.array(output_data)
    output_data = np.transpose(output_data, (1, 0))
    print('输出数据形状: ', output_data.shape)
    print('输出数据类型: ', output_data.dtype)

    # 构建DataLoader
    dataset = TensorDataset(torch.Tensor(input_data).to(device), torch.Tensor(output_data).to(device))
    data_loader = DataLoader(dataset, batch_size=js['batch_size'], shuffle=js['shuffle'])

    # 构建模型
    class MyModule(Module):
        def __init__(self):
            super(MyModule, self).__init__()
            self.model = Sequential()

            for i, d in enumerate(js['model']):
                self.model.add_module(f"layer{i}", eval(str2func(d)))

        def forward(self, x):
            return self.model(x)

    model = MyModule().to(device)
    print(model)

    optimizer = eval(str2func(js['optimizer'], params={'params': 'model.parameters()'}))

    loss_func = eval(str2func(js['loss_func']))

    t2 = time.time()

    # 训练
    train_loss_history = []
    for epoch in range(js['epoch']):
        for i, (x_train, y_train) in enumerate(data_loader):
            y_pred = model(x_train)
            loss = loss_func(y_pred, y_train)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            train_loss_history.append(loss.item())

    # 输出结果
    t3 = time.time()
    print(f'预处理用时：{t2 - t1}，训练用时：{t3 - t2}')

    return train_loss_history


if __name__ == '__main__':
    run(os.path.join('save', 'test1.json'))
