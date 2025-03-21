import json
import os
from random import sample
from tqdm import tqdm
import librosa
import numpy as np
from pydub import AudioSegment
from utils.reader import load_audio
import pickle
import h5py

import warnings
warnings.filterwarnings("ignore")

# 生成数据列表
def get_data_list(dataset_path, data_list_dir):
    speaker_list = [os.path.join(dataset_path, x) for x in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, x))]

    speaker_list.sort()
    print("Num of speaker : {}".format(len(speaker_list)))
    data_list_train = []
    data_list_test = []
    cnt = 0
    for idx in range(len(speaker_list)):
        speaker = speaker_list[idx]
        audio_path_list = [os.path.join(speaker, x) for x in os.listdir(speaker) if x.endswith(".mp3")]
        for i in range(int(len(audio_path_list)/1)):
            audio_path = audio_path_list[i]
            temp={"audio_path" : audio_path,
                  "speaker" : speaker.split('/')[-1],
                  'class_id': idx}
            if cnt < 9:
                cnt += 1
                data_list_train.append(temp)
            else:
                cnt = 0
                data_list_test.append(temp)
    with open(os.path.join(data_list_dir, "traindata.pkl"), "wb") as f:
        pickle.dump(data_list_train, f)

    with open(os.path.join(dataset_path, "testdata.pkl"), "wb") as f:
        pickle.dump(data_list_test, f)
    print("Num of train data : {}, Num of test data : {}".format(len(data_list_train), len(data_list_test)))





# 删除错误音频
def preprocess_and_remove_error_audio(data_list_path, mfcc_data_dir, mode="train"):
    with open(data_list_path, 'rb') as f:
        data_list = pickle.load(f)
    data_list_new = []
    mfcc_list = []
    cnt = 0
    for data in data_list:
        audio_path = data["audio_path"]
        try:
            spec_mag = load_audio(audio_path, mode=mode)
            mfcc_list.append(spec_mag)
            data_list_new.append(data)
        except Exception as e:
            print(audio_path)
            print(e)
        
        cnt += 1
        if cnt % 100 == 0:
            print("{}/{}".format(cnt, len(data_list)))
    with open(data_list_path, 'wb') as f:
        pickle.dump(data_list_new, f)
    print("Num of data : {}".format(len(data_list_new)))

    h5file_path = os.path.join(mfcc_data_dir, os.path.split(data_list_path)[-1].replace('.pkl', '.h5'))
    with h5py.File(h5file_path, 'w') as hf:
        hf.create_dataset('speaker', data=[x["speaker"] for x in data_list_new])
        hf.create_dataset('x', data=mfcc_list)
        hf.create_dataset('y', data=[x["class_id"] for x in data_list_new])
    print(h5file_path)


if __name__ == '__main__':
    dataset_path = 'audio/zhaidatatang'
    data_list_dir = 'audio/zhaidatatang'
    get_data_list(dataset_path, data_list_dir)
    preprocess_and_remove_error_audio(os.path.join(data_list_dir, "traindata.pkl"), "pack_data1", "train")
    preprocess_and_remove_error_audio(os.path.join(data_list_dir, "testdata.pkl"), "pack_data1", "test")
