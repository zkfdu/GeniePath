import time
import numpy as np
import torch
from torch import optim

from models import GeniePath
from utils import (
        adj_to_bias, load_data, preprocess_features)

dataset = 'cora'

# training params
batch_size = 1
n_epochs = 10000
patience = 200
lr = 0.005
l2_coef = 0.0005
attn_dropout = 0.4
ff_dropout = 0.4
hidden_units = 128
n_layer = 3
nonlinearity = torch.tanh
model = GeniePath

print('Dataset: ' + dataset)
print('----- Opt. hyperparams -----')
print('lr: {}'.format(lr))
print('l2_coef: {}'.format(l2_coef) )
print('feed forward dropout: {}'.format(ff_dropout))
print('attention dropout: {}'.format(attn_dropout))
print('patience: {}'.format(patience))
print('----- Archi. hyperparams -----')
print('no. layers: {}'.format(n_layer))
print('no. hidden units: {}'.format(hidden_units))
print('nonlinearity: {}'.format(nonlinearity))
print('model: {}'.format(model))
device = torch.device('cuda:1' if torch.cuda.is_available() else 'cpu')
adj, features, y_train, y_val, y_test, train_mask, val_mask, test_mask = load_data(dataset)
features, spars = preprocess_features(features)

n_node = features.shape[0]# 2708
ft_size = features.shape[1]#1433
n_class = y_train.shape[1]#7

adj = adj.todense()

features = torch.from_numpy(features)
y_train = torch.from_numpy(y_train)
y_val = torch.from_numpy(y_val)
y_test = torch.from_numpy(y_test)
train_mask = torch.from_numpy(np.array(train_mask, dtype=np.uint8))
val_mask = torch.from_numpy(np.array(val_mask, dtype=np.uint8))
test_mask = torch.from_numpy(np.array(test_mask, dtype=np.uint8))

bias_mtx = torch.from_numpy(adj_to_bias(adj[np.newaxis], [n_node], n_neigh=1))[0]
bias_mtx = bias_mtx.type(torch.FloatTensor)

model = GeniePath(ft_size, n_class, hidden_units, n_layer, 
                  attn_dropout=attn_dropout, ff_dropout=ff_dropout)
optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=l2_coef)
loss_function = torch.nn.CrossEntropyLoss()

_, y_train = y_train.max(dim=-1)
_, y_val = y_val.max(dim=-1)
_, y_test = y_test.max(dim=-1)

print('---------- Training Info --------------')
print('Training node number: %d' % train_mask.sum().item())
print('Validation node number: %d' % val_mask.sum().item())
print('Test node number: %d' % test_mask.sum().item())

#for epoch in range(n_epochs):
val_loss_min = 100.0
val_accu_max = 0.0
n_waiting_step = 0

for epoch in range(n_epochs):
    model.zero_grad()
    optimizer.zero_grad()

    class_pred = model(features, n_node, train_mask, bias_mtx=bias_mtx)

    train_pred = class_pred[train_mask, :]
    train_label = y_train[train_mask]

    train_loss = loss_function(train_pred, train_label)

    train_loss.backward()
    optimizer.step()

    with torch.no_grad():
        # presave train related label
        train_label = model.predict()

        val_class_pred = model(features, n_node, val_mask, bias_mtx=bias_mtx, training=False)

        val_pred = class_pred[val_mask, :]
        val_label = y_val[val_mask]
        
        val_loss = loss_function(val_pred, val_label)

        class_label = model.predict()
        val_accu = model.masked_accu(class_label, y_val, val_mask)
        val_loss = val_loss.item()
        print('Epoch: %d, train_loss, %.5f, train_accu: %.5f, val_loss: %.5f, val_accu: %.5f' % (
            epoch+1, train_loss.item(), model.masked_accu(train_label, y_train, train_mask),
            val_loss, val_accu))
        
        if val_accu >= val_accu_max or val_loss <= val_loss_min:
            if val_accu >= val_accu_max and val_loss <= val_loss_min:
                print('best one, saved')
                # torch.save(model.state_dict(), './pretrained_model/genie.pt')
                torch.save(model.state_dict(), '/disk4/zk/charmsftp/ali_attention/GeniePath/pretrained_model/genie.pt')
                # torch.save(model, './pretrained_model/entire_model.pt')
                torch.save(model, '/disk4/zk/charmsftp/ali_attention/GeniePath/pretrained_model/entire_model.pt')
            val_accu_max = max([val_accu_max, val_accu])
            val_loss_min = min([val_loss_min, val_loss])
            n_waiting_step = 0
        else:
            n_waiting_step += 1
            if n_waiting_step == patience:
                print('Early Stop! Epoch: %d, max val_accu: %.5f, min val_loss: %.5f' % (
                    epoch+1, val_accu_max, val_loss_min))
                break

with torch.no_grad():
    class_pred = model(features, n_node, test_mask, bias_mtx=bias_mtx, training=False)

    test_pred = class_pred[test_mask, :]
    test_label = y_test[test_mask]
    
    test_loss = loss_function(test_pred, test_label)

    class_label = model.predict()
    print('test_loss: %.4f, accu: %.4f' % (
        test_loss.item(), model.masked_accu(class_label, y_test, test_mask)))
    
"""
model = GeniePath(ft_size, n_class, hidden_units, n_layer)
model.load_state_dict(torch.load('./pretrained_model/genie.pt'))
model.eval()
"""
model = torch.load('./pretrained_model/entire_model.pt')

with torch.no_grad():
    class_pred = model(features, n_node, test_mask, bias_mtx=bias_mtx, training=False)

    test_pred = class_pred[test_mask, :]
    test_label = y_test[test_mask]
    
    test_loss = loss_function(test_pred, test_label)

    class_label = model.predict()
    print('test_loss: %.4f, accu: %.4f' % (
        test_loss.item(), model.masked_accu(class_label, y_test, test_mask)))
    



"""

Epoch: 1130, train_loss, 0.83493, train_accu: 0.93571, val_loss: 1.20672, val_accu: 0.79000
Epoch: 1131, train_loss, 0.81651, train_accu: 0.90714, val_loss: 1.20858, val_accu: 0.79000
Epoch: 1132, train_loss, 0.80928, train_accu: 0.92143, val_loss: 1.21561, val_accu: 0.79000
Epoch: 1133, train_loss, 0.86071, train_accu: 0.90000, val_loss: 1.24665, val_accu: 0.78800
Epoch: 1134, train_loss, 0.82350, train_accu: 0.89286, val_loss: 1.20337, val_accu: 0.78200
Epoch: 1135, train_loss, 0.76964, train_accu: 0.93571, val_loss: 1.22676, val_accu: 0.78400
Epoch: 1136, train_loss, 0.93940, train_accu: 0.90000, val_loss: 1.23290, val_accu: 0.78200
Epoch: 1137, train_loss, 0.77829, train_accu: 0.90000, val_loss: 1.24006, val_accu: 0.78400
Epoch: 1138, train_loss, 0.88972, train_accu: 0.90000, val_loss: 1.19601, val_accu: 0.78000
Epoch: 1139, train_loss, 0.81592, train_accu: 0.90000, val_loss: 1.22529, val_accu: 0.78000
Epoch: 1140, train_loss, 0.80481, train_accu: 0.92857, val_loss: 1.23562, val_accu: 0.78200
Early Stop! Epoch: 1140, max val_accu: 0.80400, min val_loss: 1.14783
test_loss: 1.0858, accu: 0.7870
test_loss: 1.1846, accu: 0.7890

"""