import argparse
import functools

import numpy as np
import torch
from tqdm import tqdm

from utils.reader import load_audio, CustomDataset
from utils.utility import add_arguments, print_arguments
from torch.utils.data import DataLoader
import h5py

parser = argparse.ArgumentParser(description=__doc__)
add_arg = functools.partial(add_arguments, argparser=parser)
add_arg('gpu',                  str,    '3',                      '测试使用的GPU序号')
add_arg('test_data_h5_path',    str,    'pack_data/testdata.h5',  '测试数据的数据列表路径')
add_arg('input_shape',          str,    '(1, 257, 257)',          '数据输入的形状')
add_arg('model_path',           str,    'Models/models/resnet34.pth',    '预测模型的路径')
args = parser.parse_args()

print_arguments(args)

device = torch.device("cuda:{}".format(args.gpu))

# 加载模型
model = torch.jit.load(args.model_path)
# print(model)
model.to(device)
model.eval()


# 根据对角余弦值计算准确率
def cal_accuracy(y_score, y_true):
    y_score = np.asarray(y_score)
    y_true = np.asarray(y_true)
    best_accuracy = 0
    best_threshold = 0
    for i in tqdm(range(0, 100)):
        threshold = i * 0.01
        y_test = (y_score >= threshold)
        acc = np.mean((y_test == y_true).astype(int))
        if acc > best_accuracy:
            best_accuracy = acc
            best_threshold = threshold

    return best_accuracy, best_threshold


# 预测音频
def infer(mfcc_feature):
    feature = model(mfcc_feature)
    return feature.data.cpu().numpy()[0]


def get_all_audio_feature(h5_data_path):
    features, labels = [], []
    test_dataset = CustomDataset(h5_data_path)
    test_loader = DataLoader(dataset=test_dataset, batch_size=1, num_workers=0)
    for data in test_loader:
        x, y = data
        logits = infer(x.to(device))
        label = y.squeeze(1).data.cpu().numpy()
        features.append(logits)
        labels.append(label)
        # print(x.shape, logits.shape)
    return features, labels


# 计算对角余弦值
def cosin_metric(x1, x2):
    return np.dot(x1, x2) / (np.linalg.norm(x1) * np.linalg.norm(x2))


def main():
    features, labels = get_all_audio_feature(args.test_data_h5_path)
    scores = []
    y_true = []
    print('开始两两对比音频特征...')
    for i in tqdm(range(len(features))):
        feature_1 = features[i]
        for j in range(i, len(features)):
            feature_2 = features[j]
            score = cosin_metric(feature_1, feature_2)
            scores.append(score)
            y_true.append(int(labels[i] == labels[j]))
    accuracy, threshold = cal_accuracy(scores, y_true)
    print('当阈值为%f, 准确率最大，为：%f' % (threshold, accuracy))


if __name__ == '__main__':
    main()
