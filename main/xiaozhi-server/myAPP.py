from mygui import Ui_Form
from PyQt5.QtWidgets import QApplication,QWidget, QFileDialog
import sys
from PyQt5 import QtWidgets

from utils.reader import load_audio
from utils.record import RecordAudio

from infer_recognition import register, recognition, infer, load_audio_db, args, person_name
import os
import numpy as np


class myAPP(QWidget, Ui_Form):
    def __init__(self):
        super(myAPP, self).__init__()  #初始化父类
        self.setupUi(self)

        self.pushButton_2.clicked.connect(self.register_oepnaudio_pubutton_clicked)
        self.pushButton.clicked.connect(self.register_record_pubutton_clicked)
        self.pushButton_7.clicked.connect(self.register_pubutton_clicked)
        self.pushButton_4.clicked.connect(self.recognition_oepnaudio_pubutton_clicked)
        self.pushButton_3.clicked.connect(self.recognition_record_pubutton_clicked)
        self.pushButton_8.clicked.connect(self.recognition_pubutton_clicked)
        self.pushButton_5.clicked.connect(self.compare_openaduio1)
        self.pushButton_6.clicked.connect(self.compare_openaduio2)
        self.pushButton_9.clicked.connect(self.compare_pubutton_clicked)

        self.speaker_name = '未命名'
        self.record_audio = RecordAudio()
        self.register_cnt = 0
        self.recognition_cnt = 0
        self.register_audio_path = ''
        self.recognition_audio_path = ''
        self.register_record_or_not = 0
        self.recognition_record_or_not = 0

        load_audio_db(args.speakerdatabase)
        self.show_speakerdatabase()

        self.compare_audio_path1 = ''
        self.compare_audio_path2 = ''

    def show_speakerdatabase(self):
        for name in person_name:
            self.textBrowser.append(name)

    def openFile(self, caption="选择音频文件", directory="./audio"):
        file_path, file_type = QFileDialog.getOpenFileName(self, caption, directory=directory)
        return file_path

    def get_speaker_name(self):
        self.speaker_name = self.lineEdit_5.text()
        if self.speaker_name is '':
            self.speaker_name = '未命名'

    def set_register_recorder_mode(self, cnt):
        if cnt == 0:
            self.pushButton.setText("录音")
            self.label_9.setText("录音未开始")
        elif cnt == 1:
            self.pushButton.setText("Start")
            self.label_9.setText("点击Start确认开始录音3s")


    def register_record_pubutton_clicked(self):
        self.register_record_or_not = 1

        if self.register_cnt == 0:
            self.register_cnt = 1
            self.set_register_recorder_mode(self.register_cnt)
        elif self.register_cnt == 1:
            self.set_register_recorder_mode(self.register_cnt)
            self.register_audio_path = self.record_audio.record(wait=False)
            self.register_cnt = 0
            self.set_register_recorder_mode(self.register_cnt)

    def register_oepnaudio_pubutton_clicked(self):
        self.register_record_or_not = 0
        self.register_audio_path = self.openFile()
        self.lineEdit.setText(self.register_audio_path)

    def register_pubutton_clicked(self):
        if os.path.exists(self.register_audio_path):
            self.get_speaker_name()
            register(self.register_audio_path, self.speaker_name, self.register_record_or_not)
            self.textBrowser.append(self.speaker_name)
            print('注册成功')
        else:
            print("未识别到音频")

    def set_recognition_recorder_mode(self, cnt):
        if cnt == 0:
            self.pushButton_3.setText("录音")
            self.label_10.setText("录音未开始")
        elif cnt == 1:
            self.pushButton_3.setText("Start")
            self.label_10.setText("点击Start确认开始录音3s")

    def recognition_record_pubutton_clicked(self):
        self.recognition_record_or_not = 1

        if self.recognition_cnt == 0:
            self.recognition_cnt = 1
            self.set_recognition_recorder_mode(self.recognition_cnt)
        elif self.recognition_cnt == 1:
            self.set_recognition_recorder_mode(self.recognition_cnt)
            self.recognition_audio_path = self.record_audio.record(wait=False)
            self.recognition_cnt = 0
            self.set_recognition_recorder_mode(self.recognition_cnt)

    def recognition_oepnaudio_pubutton_clicked(self):
        self.recognition_record_or_not = 0
        self.recognition_audio_path = self.openFile()
        self.lineEdit_2.setText(self.recognition_audio_path)

    def recognition_pubutton_clicked(self):
        if os.path.exists(self.recognition_audio_path):
            self.get_speaker_name()
            name, p = recognition(self.recognition_audio_path)
            if self.recognition_record_or_not == 1:
                os.remove(self.recognition_audio_path)
            if p > args.threshold:
                self.lineEdit_6.setText('{}  (相似度:{:.3f})'.format(name, p))
            else:
                self.lineEdit_6.setText("声纹库没有该用户的语音")
            print('预测结束')
        else:
            print('未识别到音频')


    def compare_openaduio1(self):
        self.compare_audio_path1 = self.openFile()
        self.lineEdit_3.setText(self.compare_audio_path1)

    def compare_openaduio2(self):
        self.compare_audio_path2 = self.openFile()
        self.lineEdit_4.setText(self.compare_audio_path2)

    def compare_pubutton_clicked(self):
        if os.path.exists(self.compare_audio_path1) and os.path.exists(self.compare_audio_path2):
            feature1 = infer(self.compare_audio_path1)[0]
            feature2 = infer(self.compare_audio_path2)[0]
            dist = np.dot(feature1, feature2) / (np.linalg.norm(feature1) * np.linalg.norm(feature2))
            if dist > args.threshold:
                self.label_5.setText("二者是同一个人, 相似度:{:.3f}".format(dist))
            else:
                self.label_5.setText("二者不是同一个人, 相似度:{:.3f}".format(dist))
        else:
            print('未识别到音频')


if __name__ == '__main__':

    if __name__ == "__main__":
        app = QtWidgets.QApplication(sys.argv)
        mywindow = myAPP()
        mywindow.show()
        sys.exit(app.exec_())
