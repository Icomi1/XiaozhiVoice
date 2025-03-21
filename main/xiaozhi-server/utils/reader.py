import librosa
import numpy as np
import h5py
from torch.utils import data
import torch


# 加载并预处理音频
def load_audio(audio_path, mode='train', win_length=400, sr=16000, hop_length=160, n_fft=512, spec_len=257):
    # 读取音频数据
    wav, sr_ret = librosa.load(audio_path, sr=sr)
    # 数据拼接
    if mode == 'train':
        extended_wav = np.append(wav, wav)
        if np.random.random() < 0.3:
            extended_wav = extended_wav[::-1]
    else:
        extended_wav = np.append(wav, wav[::-1])
    # 计算短时傅里叶变换
    linear = librosa.stft(extended_wav, n_fft=n_fft, win_length=win_length, hop_length=hop_length)
    mag, _ = librosa.magphase(linear)
    freq, freq_time = mag.shape
    assert freq_time >= spec_len, "非静音部分长度不能低于1.3s"
    if mode == 'train':
        # 随机裁剪
        rand_time = np.random.randint(0, freq_time - spec_len)
        spec_mag = mag[:, rand_time:rand_time + spec_len]
    else:
        spec_mag = mag[:, :spec_len]
    mean = np.mean(spec_mag, 0, keepdims=True)
    std = np.std(spec_mag, 0, keepdims=True)
    spec_mag = (spec_mag - mean) / (std + 1e-5)
    spec_mag = spec_mag[np.newaxis, :]
    return spec_mag


# 数据加载器
class CustomDataset(data.Dataset):
    def __init__(self, h5_data_path):
        super(CustomDataset, self).__init__()
        h5file = h5py.File(h5_data_path, "r")
        self.x = h5file["x"][()]
        self.y = h5file["y"][()]

    def __getitem__(self, idx):
        label = torch.LongTensor([self.y[idx]])
        spec_mag = torch.from_numpy(self.x[idx]).float()
        return spec_mag, label

    def __len__(self):
        return len(self.x)
