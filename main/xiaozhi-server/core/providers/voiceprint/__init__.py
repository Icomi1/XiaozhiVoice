import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from infer_recognition import register, recognition, load_audio_db, args
from utils.record import RecordAudio
from utils.reader import load_audio

__all__ = ['register', 'recognition', 'load_audio_db', 'RecordAudio', 'load_audio', 'args'] 