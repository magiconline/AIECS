import torch

import epics_get

# hyperparameters
EPOCH = 100
BATCH_SIZE = 32
SHUFFLE = True

RANDOM_SEED = 1
torch.manual_seed(RANDOM_SEED)
torch.cuda.manual_seed_all(RANDOM_SEED)

GPU = True
if GPU and torch.cuda.is_available():
    device = torch.device('cuda')
else:
    device = torch.device('cpu')

# get data
x0 = epics_get.get_boston_AGE()
x1 = epics_get.get_boston_B()
x2 = epics_get.get_boston_CHAS()

y0 = epics_get.get_boston_PRICE()

# preprocess 
x = torch.cat([x0, x1, x2], dim=1).to(device)
y = torch.cat([y0, ], dim=1).to(device)

# dataloader 
dataset = torch.utils.data.TensorDataset(x, y)
dataloader = torch.utils.data.DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=SHUFFLE)

# build model 
model = torch.nn.Sequential()
model.add_module('Linear_1', torch.nn.Linear(in_features=3, out_features=20, bias=True))
model.add_module('ReLU_2', torch.nn.ReLU())
model.add_module('Linear_3', torch.nn.Linear(in_features=20, out_features=20, bias=True))
model.add_module('ReLU_2', torch.nn.ReLU())
model.add_module('Linear_3', torch.nn.Linear(in_features=20, out_features=1, bias=True))

model.to(device)

loss_fc = torch.nn.MSELoss()
optimizer = torch.optim.SGD(params=model.parameters(), lr=0.1)

# run model 
for epoch in range(EPOCH):
    total_loss = 0.0
    for x_train, y_train in dataloader:
        y_pred = model(x_train)

        loss = loss_fc(y_train, y_pred)
        total_loss += loss.item()

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    print(f"epoch:{epoch}, loss:{total_loss}")

print('done')
