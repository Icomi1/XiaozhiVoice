import argparse
import functools
import os
import shutil
import numpy as np
import torch
from config.logger import setup_logging
from utils.reader import load_audio
from utils.record import RecordAudio
from utils.utility import add_arguments, print_arguments

TAG = __name__
logger = setup_logging()

# 初始化全局变量
person_feature = []
person_name = []

parser = argparse.ArgumentParser(description=__doc__)
add_arg = functools.partial(add_arguments, argparser=parser)
add_arg('gpu',              str,    '-1',                      '测试使用的GPU序号')
add_arg('input_shape',      str,    '(1, 257, 257)',          '数据输入的形状')
add_arg('threshold',        float,   0.67,                    '判断是否为同一个人的阈值')
add_arg('speakerdatabase',         str,    'tmp',               '音频库的路径')
add_arg('model_path',       str,    'models/resnet34_zhaidatatang_2w_th67.pth',    '预测模型的路径')
args = parser.parse_args()

# 确保tmp目录存在
os.makedirs('tmp', exist_ok=True)

logger.bind(tag=TAG).info("声纹识别配置参数:")
logger.bind(tag=TAG).info(f"GPU: {args.gpu}")
logger.bind(tag=TAG).info(f"输入形状: {args.input_shape}")
logger.bind(tag=TAG).info(f"阈值: {args.threshold}")
logger.bind(tag=TAG).info(f"音频库路径: {args.speakerdatabase}")
logger.bind(tag=TAG).info(f"模型路径: {args.model_path}")

# 设置设备
if int(args.gpu) < 0:
    device = torch.device("cpu")
else:
    device = torch.device("cuda:{}".format(args.gpu))

# 加载模型
try:
    model = torch.jit.load(args.model_path, map_location=device)
    model.to(device)
    model.eval()
    logger.bind(tag=TAG).info(f"模型加载成功，使用设备: {device}")
except Exception as e:
    logger.bind(tag=TAG).error(f"模型加载错误: {str(e)}")
    logger.bind(tag=TAG).info("尝试使用CPU加载模型...")
    device = torch.device("cpu")
    model = torch.jit.load(args.model_path, map_location=device)
    model.to(device)
    model.eval()
    logger.bind(tag=TAG).info("模型加载成功，使用CPU")

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
        logger.bind(tag=TAG).error(f"音频库目录 {audio_db_path} 不存在")
        return
        
    audios = os.listdir(audio_db_path)
    for audio in audios:
        # 只处理音频文件
        if not audio.lower().endswith(('.wav', '.mp3', '.ogg')):
            continue
            
        path = os.path.join(audio_db_path, audio)
        try:
            name = os.path.splitext(audio)[0]  # 使用splitext更安全
            # 跳过TTS生成的音频文件
            if name.startswith('tts-'):
                continue
                
            feature = infer(path)[0]
            person_name.append(name)
            person_feature.append(feature)
            logger.bind(tag=TAG).info(f"已加载用户音频: {name}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理音频文件 {audio} 时出错: {str(e)}")
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
    logger.bind(tag=TAG).info(f"声纹识别结果: 用户={name}, 相似度={pro:.2f}")
    return name, pro


# 声纹注册
def register(path, user_name, record_or_not=1):
    # 规范化路径
    path = os.path.normpath(path)
    args.speakerdatabase = os.path.normpath(args.speakerdatabase)
    
    # 使用 os.path.splitext 获取文件扩展名
    _, ext = os.path.splitext(path)
    save_path = os.path.normpath(os.path.join(args.speakerdatabase, user_name + ext))
    
    try:
        # 如果源路径和目标路径相同，直接使用源文件
        if os.path.normpath(path) == os.path.normpath(save_path):
            logger.bind(tag=TAG).info(f"源文件已在目标位置: {path}")
        else:
            if record_or_not == 0:
                shutil.copy(path, save_path)
                logger.bind(tag=TAG).info(f"复制音频文件: {path} -> {save_path}")
            elif record_or_not == 1:
                shutil.move(path, save_path)
                logger.bind(tag=TAG).info(f"移动音频文件: {path} -> {save_path}")
            
        feature = infer(save_path)[0]
        person_name.append(user_name)
        person_feature.append(feature)
        logger.bind(tag=TAG).info(f"已注册新用户: {user_name}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"注册用户失败: {str(e)}", exc_info=True)
        raise

# 初始化时加载音频库
logger.bind(tag=TAG).info("开始加载声纹数据库...")
load_audio_db(args.speakerdatabase)
logger.bind(tag=TAG).info(f"声纹数据库加载完成，共加载 {len(person_name)} 个用户")

if __name__ == '__main__':
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
                logger.bind(tag=TAG).error('请正确选择功能')
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
                logger.bind(tag=TAG).error('请正确选择功能')
                continue
            name, p = recognition(audio_path)
            os.remove(audio_path)
            if p > args.threshold:
                logger.bind(tag=TAG).info(f"识别结果: 用户 {name}，相似度: {p:.2f}")
            else:
                logger.bind(tag=TAG).info("未识别到匹配的用户")
        else:
            logger.bind(tag=TAG).error('请正确选择功能')
