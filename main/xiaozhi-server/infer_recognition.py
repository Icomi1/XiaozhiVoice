import argparse
import functools
import os
import shutil

import numpy as np
import torch

from utils.reader import load_audio
from utils.record import RecordAudio
from utils.utility import add_arguments, print_arguments

# 初始化全局变量
person_feature = []
person_name = []

parser = argparse.ArgumentParser(description=__doc__)
add_arg = functools.partial(add_arguments, argparser=parser)
add_arg('gpu', str, '-1', '测试使用的GPU序号')
add_arg('input_shape', str, '(1, 257, 257)', '数据输入的形状')
add_arg('threshold', float, 0.67, '判断是否为同一个人的阈值')
add_arg('speakerdatabase', str, 'tmp', '音频库的路径')
add_arg('model_path', str, 'Models/resnet34_zhaidatatang_2w_th67.pth', '预测模型的路径')
args = parser.parse_args()

# 确保tmp目录存在
os.makedirs('tmp', exist_ok=True)

print_arguments(args)

# 设置设备
if int(args.gpu) < 0:
    device = torch.device("cpu")
else:
    device = torch.device("cuda:{}".format(args.gpu))

#-----------------------------------------------------------------
# try:
#     model = torch.jit.load(args.model_path, map_location=device)
#     model.to(device)
#     model.eval()
# except Exception as e:
#     print(f"模型加载错误: {str(e)}")
#     print("尝试使用CPU加载模型...")
#     device = torch.device("cpu")
#     model = torch.jit.load(args.model_path, map_location=device)
#     model.to(device)
#     model.eval()
#-----------------------------------------------------------
# 加载模型
try:
    model = torch.jit.load(args.model_path, map_location=device)
    model.to(device)
    model.eval()
except Exception as e:
    print(f"模型加载错误: {str(e)}")
    print("尝试使用CPU加载模型...")
    device = torch.device("cpu")
    model = torch.jit.load(args.model_path, map_location=device)
    model.to(device)
    model.eval()


def infer(audio_path):
    input_shape = eval(args.input_shape)
    data = load_audio(audio_path, mode='infer', spec_len=input_shape[2])
    data = data[np.newaxis, :]
    data = torch.tensor(data, dtype=torch.float32, device=device)
    # 执行预测
    feature = model(data)
    return feature.data.cpu().numpy()


# 加载要识别的音频库
def load_audio_db(audio_db_path):
    if not os.path.exists(audio_db_path):
        print(f"音频库目录 {audio_db_path} 不存在")
        return

    audios = os.listdir(audio_db_path)
    for audio in audios:
        # 只处理音频文件
        if not audio.lower().endswith(('.wav', '.mp3', '.ogg')):
            continue

        path = os.path.join(audio_db_path, audio)
        try:
            name = os.path.splitext(audio)[0]  # 使用splitext更安全
            feature = infer(path)[0]
            person_name.append(name)
            person_feature.append(feature)
            print("Loaded %s audio." % name)
        except Exception as e:
            print(f"处理音频文件 {audio} 时出错: {str(e)}")
            continue


def recognition(path):
    name = ''
    pro = 0
    feature = infer(path)[0]
    for i, person_f in enumerate(person_feature):
        dist = np.dot(feature, person_f) / (np.linalg.norm(feature) * np.linalg.norm(person_f))
        if dist > pro:
            pro = dist
            name = person_name[i]
    return name, pro


# 声纹注册
def register(path, user_name, record_or_not=1):
    save_path = os.path.join(args.speakerdatabase, user_name + os.path.basename(path)[-4:])
    if record_or_not == 0:
        shutil.copy(path, save_path)
    elif record_or_not == 1:
        shutil.move(path, save_path)
    feature = infer(save_path)[0]
    person_name.append(user_name)
    person_feature.append(feature)


if __name__ == '__main__':
    load_audio_db(args.speakerdatabase)
    record_audio = RecordAudio()

    while True:
        select_fun = int(input("请选择功能，0为注册音频到声纹库，1为执行声纹识别："))
        if select_fun == 0:
            record_or_not = int(input("请选择：0加载已有音频，1录制音频："))
            if record_or_not == 0:
                audio_path = input("请输入音频路径：")
            elif record_or_not == 1:
                audio_path = record_audio.record()
            else:
                print('请正确选择功能')
                continue
            name = input("请输入该音频用户的名称：")
            if name == '': continue
            register(audio_path, name, record_or_not)
        elif select_fun == 1:
            record_or_not = int(input("请选择：0加载已有音频，1录制音频："))
            if record_or_not == 0:
                audio_path = input("请输入音频路径：")
            elif record_or_not == 1:
                audio_path = record_audio.record()
            else:
                print('请正确选择功能')
                continue
            name, p = recognition(audio_path)
            os.remove(audio_path)
            if p > args.threshold:
                print("识别说话的为：%s，相似度为：%f" % (name, p))
            else:
                print("音频库没有该用户的语音")
        else:
            print('请正确选择功能')
