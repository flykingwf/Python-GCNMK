import os
#os.environ["CUDA_VISIBLE_DEVICES"] = "0" # 0 for GPU
import os.path as osp
import sys
import time
import random
import joblib
import argparse
import torch
import pandas as pd
import numpy as np
from numpy import genfromtxt
import matplotlib.pyplot as plt
from sklearn import preprocessing
import sklearn.metrics as metrics
from sklearn.metrics import roc_auc_score,average_precision_score, roc_curve, auc, precision_recall_curve, f1_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn import metrics as sklearnmetrics
from sklearn.metrics.cluster import normalized_mutual_info_score
from sklearn.metrics.cluster import adjusted_rand_score
import torch_geometric.transforms as Trans
from torch_geometric.nn import GCNConv, GAE, VGAE
from torch_geometric.utils import train_test_split_edges
import torch.nn.functional as F
import torch.nn as nn
import math
from torch.nn.parameter import Parameter
from torch.nn.modules.module import Module
min_max_scaler = preprocessing.MinMaxScaler()
device = torch.device('cuda')
loss_fct = torch.nn.BCELoss()
Sigm = torch.nn.Sigmoid()

'''
####################################################     features
'''

#my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\adjacentDDI613.csv',delimiter=',')
#adjacentDD = my_data.astype('int')
'''
####################################################     increased and decreased DDIs
'''
my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\adjacentDDI_TWOSIDE.csv',delimiter=',')
adjacentTWO = my_data.astype('int')
print(np.sum(adjacentTWO))
my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\adjacentDDI613drugbank_part_IN.csv',delimiter=',')
adjacentIN = my_data.astype('int')
my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\adjacentDDI613drugbank_part_DE.csv',delimiter=',')
adjacentDE = my_data.astype('int')
print(np.sum(adjacentIN))
print(np.sum(adjacentDE))
for i in range(0,613):
    for j in range(0,613):
        if(adjacentTWO[i,j]==1 and adjacentIN[i,j]==1):
            adjacentTWO[i,j]=0
        elif(adjacentTWO[i,j]==1 and adjacentDE[i,j]==1):
            adjacentTWO[i,j]=0
print(np.sum(adjacentTWO))



nD = adjacentIN.shape[0]
DDlist = list()
for i in range(0,adjacentIN.shape[0]-1):
    for j in range(i+1,adjacentIN.shape[0]):
        if(adjacentIN[i,j]==1):
            DDlist.append([i,j])
for i in range(0,adjacentDE.shape[0]-1):
    for j in range(i+1,adjacentDE.shape[0]):
        if(adjacentDE[i,j]==1):
            DDlist.append([i,j])
print(len(DDlist))
random.shuffle(DDlist)

adjacentDD_decrease = adjacentIN+adjacentDE

NonDDlist = list()
for i in range(0,adjacentDD_decrease.shape[0]-1):
    for j in range(i+1,adjacentDD_decrease.shape[0]):
        if(adjacentDD_decrease[i,j]==0):
            NonDDlist.append([i,j])
print(len(NonDDlist))
random.shuffle(NonDDlist)


adj = torch.Tensor(adjacentIN).type(torch.float)
adj = adj.to(device)
adj2 = torch.Tensor(adjacentDE).type(torch.float)
adj2 = adj2.to(device)

'''
####################################################     features
'''
my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\drug_881fingerprint.csv',delimiter=',')
drug_feature_fingerprint = my_data.astype('int')
nF = drug_feature_fingerprint.shape[1]

my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_target\\adjacentDTI_drugbank.csv',delimiter=',')
drug_feature_target = my_data.astype('int')
nT = drug_feature_target.shape[1]

my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\adjacent_drug_pathway.csv',delimiter=',')
drug_feature_pathway = my_data.astype('int')
nP = drug_feature_pathway.shape[1]

my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\adjacent_drug_enzyme.csv',delimiter=',')
drug_feature_enzyme = my_data.astype('int')
nE = drug_feature_enzyme.shape[1]

my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\adjacent_drug_side.csv',delimiter=',')
drug_feature_side = my_data.astype('int')
nS = drug_feature_side.shape[1]

my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\chemical613_PRL.csv',delimiter=',')
my_data = my_data.astype('float32')
my_data.shape
drug613PRL = min_max_scaler.fit_transform(my_data.T)
drug_feature_PRL = drug613PRL.T

node2vec_representation = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\node2vec_representation.csv',delimiter=',')

my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\chemical613_PRL.csv',delimiter=',')
my_data = my_data.astype('float32')
my_data.shape
drug613PRL = min_max_scaler.fit_transform(my_data.T)
drug613PRL = drug613PRL.T
my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\drug_drug\\drug_drug_PRLspearmanSIM.csv',delimiter=',')
drug_SIM_PRLspearman = my_data.astype('float32')

nddi_pos = int(len(DDlist))
ddiedges_pos = np.zeros([nddi_pos,2])
nddi_neg = int(len(NonDDlist))
ddiedges_neg = np.zeros([nddi_neg,2])
z=-1
for i in range(0,nD-1):
    for j in range(i+1,nD):
        if(adjacentDD_decrease[i,j]>0):
            z=z+1
            ddiedges_pos[z,0]=i
            ddiedges_pos[z,1]=j
randedge_pos = np.arange(nddi_pos)
np.random.shuffle(randedge_pos)
ddiedgeP = ddiedges_pos[randedge_pos,:]
ddiedgeP = ddiedgeP.astype(int)
z=-1
for i in range(0,nD-1):
    for j in range(i+1,nD):
        if(adjacentDD_decrease[i,j]==0):
            z=z+1
            ddiedges_neg[z,0]=i
            ddiedges_neg[z,1]=j
randedge_neg = np.arange(nddi_neg)
np.random.shuffle(randedge_neg)
ddiedgeN = ddiedges_neg[randedge_neg,:]
ddiedgeN = ddiedgeN.astype(int)
'''
####################################################     model
'''

Hdim1 = 256
d = 64
Hdim3 = 32
Hdim4 = 16
drop = 0.2
class GraphConvolution(Module):
    """
    Simple GCN layer, similar to https://arxiv.org/abs/1609.02907
    """

    def __init__(self, in_features, out_features, bias=True):
        super(GraphConvolution, self).__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = Parameter(torch.FloatTensor(in_features, out_features))
        if bias:
            self.bias = Parameter(torch.FloatTensor(out_features))
        else:
            self.register_parameter('bias', None)
        self.reset_parameters()

    def reset_parameters(self):
        stdv = 1. / math.sqrt(self.weight.size(1))
        self.weight.data.uniform_(-stdv, stdv)
        if self.bias is not None:
            self.bias.data.uniform_(-stdv, stdv)

    def forward(self, input, adj):
        support = torch.mm(input, self.weight)
        output = torch.spmm(adj, support)
        if self.bias is not None:
            return output + self.bias
        else:
            return output

    def __repr__(self):
        return self.__class__.__name__ + ' (' \
               + str(self.in_features) + ' -> ' \
               + str(self.out_features) + ')'

def reset_parameters(w):
    stdv = 1. / math.sqrt(w.size(0))
    w.data.uniform_(-stdv, stdv)

class GCNMK(nn.Module):
    def __init__(self, nfeat, nhid1, nhid2, nhid_decode1, nhid_decode2, dropout):
        super(GCNMK, self).__init__()
        
        # Increase
        self.i_gc1 = GraphConvolution(nfeat, nhid1)
        self.i_gc2 = GraphConvolution(nhid1, nhid2)
        
        # Increase to Decrease
        self.i_gc1_d = GraphConvolution(nfeat, nhid1)

        #Decrease
        self.d_gc1 = GraphConvolution(nfeat, nhid1)
        self.d_gc2 = GraphConvolution(nhid1, nhid2)
        
        #Decrease to Increase
        self.d_gc1_i = GraphConvolution(nfeat, nhid1)
               
        self.dropout = dropout
        
        self.decoder1 = nn.Linear(nhid2 * 2, nhid_decode1)
        self.decoder2 = nn.Linear(nhid_decode1, nhid_decode2)
        self.decoder3 = nn.Linear(nhid_decode2, 1)
        
    def reparametrize(self, mu, logstd):
        if self.training:
            return mu + torch.randn_like(logstd) * torch.exp(logstd)
        else:
            return mu

    def forward(self, x, i_adj, d_adj, idx):
        
        i_x = F.relu(self.i_gc1(x, i_adj) + self.d_gc1_i(x, d_adj))       
        d_x = F.relu(self.d_gc1(x, d_adj) + self.i_gc1_d(x, i_adj))
        
        i_x = F.dropout(i_x, self.dropout, training = self.training)
        d_x = F.dropout(d_x, self.dropout, training = self.training)
        
        x = F.relu(self.i_gc2(i_x, i_adj) + self.d_gc2(d_x, d_adj))
        
        #x = self.reparametrize(self.conv_mu(x, o_adj), self.conv_logstd(x, o_adj))
        feat_p1 = x[idx[0]] # the first biomedical entity embedding retrieved
        feat_p2 = x[idx[1]] # the second biomedical entity embedding retrieved
        feat = torch.cat((feat_p1, feat_p2), dim = 1)
        o = F.relu(self.decoder1(feat))
        o = F.dropout(o,self.dropout)
        oo = F.relu(self.decoder2(o))
        #o = F.dropout(o,self.dropout)
        o = torch.sigmoid(self.decoder3(oo))
        return o, x, oo
'''
model = GCNMK(nfeat=Nfeature,nhid1=Hdim1,nhid2=d,nhid_decode1 = Hdim3,nhid_decode2=Hdim4, dropout=drop)
optimizer = torch.optim.Adam(model.parameters(),lr=0.001, weight_decay=0.0005)
model = model.to(device)
model.eval()
print(next(model.parameters()).device)
'''
foldN = 5
foldrange = int(nddi_pos/foldN)
sampleT = np.arange(nddi_pos)
np.random.shuffle(sampleT)
sampleT = sampleT[0:foldrange*foldN].reshape((foldrange,foldN))

label_test = torch.Tensor(np.concatenate((np.zeros([foldrange,]),np.ones([foldrange,]))))
label_train = torch.Tensor(np.concatenate((np.zeros([foldrange*(foldN-1),]),np.ones([foldrange*(foldN-1),]))))

#label_test = torch.Tensor(np.concatenate((np.ones([foldrange,]),np.zeros([foldrange,]))))
#label_train = torch.Tensor(np.concatenate((np.ones([foldrange*(foldN-1),]),np.zeros([foldrange*(foldN-1),]))))

label_train = label_train.to(device)
label_test = label_test.to(device)
label_trainCPU = label_train.cpu().numpy()
label_testCPU = label_test.cpu().numpy()

max_auc = 0
def test(DDx, adj, adj2, inptest):
    model.eval()
    label_test_pred = []
    output, _, _ = model(DDx, adj, adj2, inptest)
    n = torch.squeeze(Sigm(output))
    loss = loss_fct(n, label_test)
    label_test_pred = label_test_pred + output.flatten().tolist()
    outputs = np.asarray([1 if i else 0 for i in (np.asarray(label_test_pred) >= 0.5)])
    label_test_pred = np.array(label_test_pred)
    roc = roc_auc_score(label_testCPU, label_test_pred)
    ap = average_precision_score(label_testCPU, label_test_pred)
    f1s = f1_score(label_testCPU, outputs)
    return roc, ap, f1s, loss
def train(DDx, adj, adj2, inptrain):
    model.train()
    optimizer.zero_grad()
    output, _, _ = model(DDx, adj, adj2, inptrain)
    n = torch.squeeze(Sigm(output))
    loss_train = loss_fct(n, label_train)
    loss_train.backward()
    optimizer.step()
    label_train_pred = output.flatten().tolist()
    return float(loss_train),label_train_pred
loss_history = []



'''
randedge_pos = np.arange(nddi_pos)
np.random.shuffle(randedge_pos)
ddiedgeP = ddiedges_pos[randedge_pos,:]
ddiedgeP = ddiedgeP.astype(int)
randedge_neg = np.arange(nddi_neg)
np.random.shuffle(randedge_neg)
ddiedgeN = ddiedges_neg[randedge_neg,:]
ddiedgeN = ddiedgeN.astype(int)
np.savetxt('D:\\Datasets\\DDI_DTI_datasets\\PosNet_NegNet_ddiedgeN.csv',ddiedgeN,delimiter=",")
np.savetxt('D:\\Datasets\\DDI_DTI_datasets\\PosNet_NegNet_ddiedgeP.csv',ddiedgeP,delimiter=",")
np.savetxt('D:\\Datasets\\DDI_DTI_datasets\\PosNet_NegNet_sampleT.csv',sampleT,delimiter=",")
'''


'''
DDx = torch.from_numpy(ad1).type(torch.float)
DDx = DDx.to(device)
#drug_feature_fingerprint,drug_feature_target,drug_feature_pathway,drug_feature_enzyme,drug_feature_side
DDx = torch.from_numpy(np.concatenate((drug_feature_side,drug_feature_target),axis = 1)).type(torch.float)
DDx = DDx.to(device)

my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\PosNet_NegNet_ddiedgeN.csv',delimiter=',')
ddiedgeN = my_data.astype('int')
my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\PosNet_NegNet_ddiedgeP.csv',delimiter=',')
ddiedgeP = my_data.astype('int')
my_data = genfromtxt('D:\\Datasets\\DDI_DTI_datasets\\PosNet_NegNet_sampleT.csv',delimiter=',')
sampleT = my_data.astype('int')
'''


'''
DDx = torch.from_numpy(drug_feature_enzyme).type(torch.float)
DDx = DDx.to(device)
DDx = torch.from_numpy(drug_feature_side).type(torch.float)
DDx = DDx.to(device)
DDx = torch.from_numpy(drug_feature_pathway).type(torch.float)
DDx = DDx.to(device)
DDx = torch.from_numpy(drug_feature_target).type(torch.float)
DDx = DDx.to(device)
DDx = torch.from_numpy(drug_feature_PRL).type(torch.float)
DDx = DDx.to(device)
DDx = torch.from_numpy(adjacentDD).type(torch.float)
DDx = DDx.to(device)
DDx = torch.from_numpy(drug_feature_fingerprint).type(torch.float)
DDx = DDx.to(device)
DDx = torch.from_numpy(node2vec_representation).type(torch.float)
DDx = DDx.to(device)



'''
DDx2 = np.concatenate((drug_feature_enzyme,drug_feature_pathway,drug_feature_target,drug_feature_fingerprint),1)
DDx3 = np.concatenate((DDx2,adjacentDD_decrease),1)

DDx = torch.from_numpy(DDx3).type(torch.float)
DDx = DDx.to(device)

Hdim1 = 128#128
Hdim3 = 32
Hdim4 = 16
dims = [224,256,288,320]
dplist=[0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9]
#learningrate = [0.1,0.01,0.001,0.0001,0.00001,0.000001]
learningrate = [5e-3,4e-3,3e-3,2e-3,1e-3,9e-4,8e-4,7e-4,6e-4,5e-4,4e-4,3e-4,2e-4,6e-3,7e-3,8e-3,9e-3]
weights = [1e-6,1e-5,2e-5,3e-5]
#weights = [0.1,0.01,0.001,0.0001,0.00001,0.000001]
dims = [160]
model_str = ['drug_feature_target','drug_feature_enzyme','drug_feature_pathway','drug_feature_side','adjacentDD_decrease','drug_feature_fingerprint','node2vec_representation','drug_feature_PRL']
model_file_str = ['target','enzyme','pathway','side','adjacentDD','fingerprint','node2vec','PRL']
drop = 0
d = 160
lrate = 0.002
mstr=0
lamda = 0.0003
for d in dims:
    DDx = torch.from_numpy(eval(model_str[mstr])).type(torch.float)
    DDx = DDx.to(device)
    Nfeature = DDx.shape[1]
    print(model_str[mstr])
    print('learning rate: ',lrate)
    print('dimension: ',d)
    print('drop: ',drop)
    print('lamda: ',lamda)
    inter_auc=list()
    inter_pr = list()
    inter_auc.append(0)
    inter_pr.append(0)
    for repeat in range(0,1):
        JK=0.5
        model = IDGCN(nfeat=Nfeature,nhid1=Hdim1,nhid2=d,nhid_decode1 = Hdim3,nhid_decode2=Hdim4,dropout=drop)
        optimizer = torch.optim.Adam(model.parameters(),lr=lrate, weight_decay=lamda) # weight_decay=0.0005
        model = model.to(device)
        print('Repeat No.: ',repeat+1)
        print('##############################')
        print('##############################')
        time_start = time.time()
        for T in range(0,5):
            
            model.eval()
            max_auc = 0.01
            max_loss = 30000
            EpochSize = 3000
            #if(T==0):
            #    EpochSize=6000
            #else:
            #    EpochSize=5000
            zpath = 'D:\\StudyTools\\GraphModels\\zzzzz\\z_d_'+str(d)+'_drug_feature_target'+'_'+str(T)+'.csv'
            lasttrainpath = 'D:\\StudyTools\\GraphModels\\zzzzz\\lta_'+str(T)+'.csv'
            lasttestpath = 'D:\\StudyTools\\GraphModels\\zzzzz\\lte_'+str(T)+'.csv'
            outpath = 'D:\\StudyTools\\GraphModels\\zzzzz\\O_'+str(T)+'.csv'
            modelpath = 'D:\\StudyTools\\GraphModels\\temp1\\modelall'+str(T)+'.pth'
            
            sampleN_test = sampleT[:,T]
            sampleN_test = sampleN_test.reshape((1,foldrange))
            sampleN_test = sampleN_test[0]
            sampleN_train = np.delete(sampleT,T,axis=1)
            sampleN_train = sampleN_train.reshape((1,foldrange*(foldN-1)))
            sampleN_train = sampleN_train[0]
            
            inptrain=[0,1]
            inptrain[0] = np.concatenate((ddiedgeP[sampleN_train,0],ddiedgeN[sampleN_train,0]))
            inptrain[1] = np.concatenate((ddiedgeP[sampleN_train,1],ddiedgeN[sampleN_train,1]))
            inptrain = torch.Tensor(inptrain).type(torch.LongTensor)
            inptrain = inptrain.to(device)
            inptest = [0,1]
            inptest[0] = np.concatenate((ddiedgeP[sampleN_test,0],ddiedgeN[sampleN_test,0]))
            inptest[1] = np.concatenate((ddiedgeP[sampleN_test,1],ddiedgeN[sampleN_test,1]))
            inptest = torch.Tensor(inptest).type(torch.LongTensor)
            inptest = inptest.to(device)
            adj[inptrain[0,:],inptrain[1,:]]=0
            adj2[inptrain[0,:],inptrain[1,:]]=0
            adj[inptest[0,:],inptest[1,:]]=0
            adj2[inptest[0,:],inptest[1,:]]=0
            
            loss_train_history = np.ones([EpochSize,])*100
            loss_test_history = np.ones([EpochSize,])*100
            xaxis = np.arange(0,EpochSize,1)
            roc_train = np.zeros([EpochSize,])
            roc_test = np.zeros([EpochSize,])
            for epoch in range(0,EpochSize):
                loss_train,label_train_pred = train(DDx, adj, adj2, inptrain)
                label_train_pred = torch.Tensor(label_train_pred)
                loss_train_history[epoch]=loss_train
                label_train_predCPU = label_train_pred.cpu().numpy()
                roc_train[epoch] = roc_auc_score(label_trainCPU, label_train_predCPU)
                roc_val, prc_val, f1_val, loss_val = test(DDx, adj, adj2, inptest)
                loss_test_history[epoch] = loss_val
                roc_test[epoch]=roc_val
                #if(roc_val>max_auc):
                if(loss_val<max_loss):
                    max_loss = loss_val
                    max_auc = roc_val
                    torch.save(model.state_dict(),modelpath)
                    #print("Save model at {:03d}th epoch, LossTrain: {:.5f}, LossTest: {:.5f}, RocTest: {:.5f}".format(epoch+1, loss_train, loss_val, roc_val))
                #print('Epoch: {:03d}, LossTrain: {:.5f}, LossTest: {:.5f}, RocTest: {:.5f}'.format(epoch+1, loss_train, loss_val, roc_val))
            print('T=',T)
            print('aucroc: ',max_auc)
            model_loaded = model.load_state_dict(torch.load(modelpath))
            output, codelayer, lastTE = model(DDx, adj, adj2, inptrain)
            np.savetxt(lasttestpath,lastTE,delimiter=",")
            output, codelayer, last2 = model(DDx, adj, adj2, inptest)
            zz=codelayer.detach().to('cpu').numpy()
            last = last2.detach().to('cpu').numpy()
            np.savetxt(lasttrainpath,last,delimiter=",")
            np.savetxt(outpath,output,delimiter=",")
            #np.savetxt(zpath,zz,delimiter=",")
            if(T==0):
                label_p = output
            else:
                label_p = torch.cat((label_p,output),0)
            print('time cost: ',time.time()-time_start,'s')
        #label_test = torch.Tensor(np.concatenate((np.zeros([foldrange,]),np.ones([foldrange,]))))
        #label_test = label_test.to(device)
        label_t = torch.cat((label_test,label_test,label_test,label_test,label_test))
        #label_t = label_test
        label_t = label_t.cpu().numpy().tolist()
        label_p = label_p.cpu().detach().numpy()
        label_p = label_p.reshape(len(label_t),)
        label_p = list(label_p)
        print('Repeat No.: ',repeat+1)
        #from sklearn.metrics import roc_auc_score,average_precision_score, roc_curve, auc, precision_recall_curve
        fpr,tpr,threshold = roc_curve(label_t, label_p, pos_label=1)
        roc_auc = sklearnmetrics.auc(fpr, tpr)
        print('AUCROC: ', roc_auc)
        precision, recall, thresholdPR = precision_recall_curve(label_t, label_p)
        pr_auc = sklearnmetrics.auc(recall,precision)
        print('AUCPR', pr_auc)
        print('##############################')
        inter_auc.append(roc_auc)
        inter_pr.append(pr_auc)
        print('##############################')
    inter_auc1 = np.array(inter_auc).reshape((len(inter_auc),1))
    inter_pr1 = np.array(inter_pr).reshape((len(inter_pr),1))
    inter = np.concatenate([inter_auc1,inter_pr1],axis=1)
    np.savetxt('D:\\StudyTools\\GraphModels\\zzzzz\\'+model_file_str[mstr]+'_lr'+str(lrate)+'_lamda'+str(lamda)+'_d'+str(d)+'.csv',np.array(inter),delimiter=",")
print('END')
