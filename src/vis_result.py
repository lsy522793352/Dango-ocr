# -*- coding: utf-8 -*-

from os.path import dirname
from time import localtime, time, strftime
from docx import Document
import numpy as np
from traceback import format_exc
from cv2 import imread, cvtColor, COLOR_BGR2RGB, imwrite
import sys

from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRect
from PyQt5.QtWidgets import QTextEdit, QPushButton, QFileDialog, QApplication, QWidget, QLabel
from PyQt5.QtGui import QPixmap, QImage, QPalette, QBrush, QPainter, QPen, QColor, QPolygonF, QIcon

sys.path.append(".")
from configs import folder_path
from src.api import write_error


class VisResult(QWidget):
    result_signal = pyqtSignal(str, dict, str, str)

    def __init__(self, np_img, result, configs, translate_result, save_path):
        super(VisResult, self).__init__()
        self.setWindowState(Qt.WindowActive)
        # 窗口置顶
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("修改识别结果")
        # 窗口图标
        self.icon = QIcon()
        self.icon.addPixmap(QPixmap(folder_path + "/config/logo.ico"), QIcon.Normal, QIcon.On)
        self.setWindowIcon(self.icon)

        self.np_img = np_img
        self.results = result
        img = cvtColor(self.np_img, COLOR_BGR2RGB)
        img_h, img_w, img_c = img.shape
        self.img_w = img_w

        img_show_h, img_show_w = max(50, img_h), max(200, img_w)
        img_show = np.zeros((img_show_h * 3, img_show_w * 2, img_c), dtype=np.uint8) + 255
        img_show[:img_h, :img_w, :] = img
        img_show[0:img_h, img_w, :] = 128

        self.setMinimumHeight(img_show_h + 60)
        self.setMinimumWidth(img_show_w * 2)
        self.setMaximumHeight(img_show_h + 60)
        self.setMaximumWidth(img_show_w * 2)

        frame = QImage(img_show.data, img_show.shape[1], img_show.shape[0], img_show.shape[1] * img_show.shape[2],
                       QImage.Format_RGB888)
        pix = QPixmap(frame)
        palette1 = QPalette()
        palette1.setBrush(self.backgroundRole(), QBrush(pix))  # 背景图片
        self.setPalette(palette1)
        self.setAutoFillBackground(False)
        self.draw_text(img_w)

        # 设置保存按钮
        self.SaveButton = QPushButton(self)
        self.SaveButton.setGeometry(QRect(img_show_w - 170, img_show_h + 20, 90, 30))
        self.SaveButton.setStyleSheet("background: rgba(255, 255, 255, 0.4);font: 12pt;")
        self.SaveButton.setText("确 定")
        self.SaveButton.clicked.connect(self.send_text)

        # 设置导出按钮
        self.SaveButton = QPushButton(self)
        self.SaveButton.setGeometry(QRect(img_show_w - 45, img_show_h + 20, 90, 30))
        self.SaveButton.setStyleSheet("background: rgba(255, 255, 255, 0.4);font: 12pt;")
        self.SaveButton.setText("导 出")
        self.SaveButton.clicked.connect(self.save_text)

        # 设置返回按钮
        self.CancelButton = QPushButton(self)
        self.CancelButton.setGeometry(QRect(img_show_w + 175 - 90, img_show_h + 20, 90, 30))
        self.CancelButton.setStyleSheet("background: rgba(255, 255, 255, 0.4);font: 12pt")
        self.CancelButton.setText("取 消")
        self.CancelButton.clicked.connect(self.close)

        self.configs = configs
        self.translate_result = translate_result
        self.default_save_path = save_path

    # 绘制事件
    def paintEvent(self, event):
        painter = QPainter(self)

        # 在左边原图上画多边形
        pen = QPen(QColor(255, 0, 0))  # set lineColor
        pen.setWidth(1)  # set lineWidth
        brush = QBrush(QColor(143, 143, 143, 100))  # set fillColor
        painter.setPen(pen)
        painter.setBrush(brush)
        self.draw_polygon(painter, 0)

        # 在右边画结果
        # pen = QPen(QColor(0, 0, 0))  # set lineColor
        # pen.setWidth(1)  # set lineWidth
        # brush = QBrush(QColor(143, 143, 143, 0))  # set fillColor
        # painter.setPen(pen)
        # painter.setBrush(brush)
        # self.draw_polygon(painter, self.img_w)

        painter.end()

    def draw_polygon(self, qp, img_w):
        # 绘制多边形
        for res in self.results:
            text_region = res["text_region"]

            polygon = QPolygonF()
            for region in text_region:
                polygon.append(QPointF(img_w + region[0], region[1]))
            qp.drawPolygon(polygon)

    def draw_text(self, img_w):
        self.vis_text_result = []
        for res in self.results:
            text = res['text']
            text_region = res["text_region"]

            box_h = text_region[2][1] - text_region[0][1]
            box_w = text_region[2][0] - text_region[0][0]
            box_h = max(20, box_h)

            vis_text = QTextEdit(self)
            vis_text.setGeometry(QRect(img_w + text_region[0][0], text_region[0][1], box_w, box_h))
            vis_text.setStyleSheet("QTextEdit {""border-width:1; border-style:outset""}"
                                   "QTextEdit:focus {""border: 2px dashed #9265d1;""}")
            vis_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            vis_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            vis_text.setPlainText(text)
            self.vis_text_result.append(vis_text)

    def send_text(self):
        sentence = []
        for vis_text in self.vis_text_result:
            sentence.append(vis_text.toPlainText())
        sentence = " ".join(sentence)
        self.result_signal.emit(sentence, self.configs, 'original', self.translate_result)
        self.close()

    def save_text(self):
        try:
            time_array = localtime(int(time()))
            str_date = strftime("DangoOCR_%Y-%m-%d_%H-%M-%S", time_array)
            default_name = self.default_save_path[0] + "/" + str_date
            save_p, extend = QFileDialog.getSaveFileName(self, 'save file', default_name, "txt (*.txt);;docx (*.docx)")

            if '.txt' in extend:
                if save_p[-4:] != '.txt':
                    save_p += '.txt'
                imwrite(save_p[:-4] + ".jpg", self.np_img)
                with open(save_p, 'w', encoding='utf-8') as f:
                    for vis_text in self.vis_text_result:
                        f.write(vis_text.toPlainText() + "\n")
            elif '.docx' in extend:
                if save_p[-5:] != '.docx':
                    save_p += '.docx'
                imwrite(save_p[:-5] + ".jpg", self.np_img)
                document = Document()
                for vis_text in self.vis_text_result:
                    document.add_paragraph(vis_text.toPlainText())
                document.save(save_p)
            if save_p != '':
                self.default_save_path[0] = dirname(save_p)
        except Exception:
            write_error(format_exc())


if __name__ == '__main__':
    img = imread(folder_path + '/config/image.jpg')
    print(folder_path)
    result = [{'text': '钢琴家傅聪确诊新冠系傅雷之子', 'confidence': 0.9817190170288086,
               'text_region': [[4, 12], [205, 11], [205, 28], [4, 29]]},
              {'text': '中英间定期客运航线航班暂停运行', 'confidence': 0.9990035891532898,
               'text_region': [[5, 44], [216, 44], [216, 60], [5, 60]]},
              {'text': '蚂蚁回应被约谈：成立整改工作组', 'confidence': 0.9838894605636597,
               'text_region': [[3, 74], [207, 75], [207, 94], [3, 93]]},
              {'text': '深圳新增1例无症状曾2次来京出差', 'confidence': 0.9958600997924805,
               'text_region': [[5, 108], [221, 108], [221, 124], [5, 124]]},
              {'text': '女童成老赖案：监控拍下其父藏户', 'confidence': 0.981416642665863,
               'text_region': [[5, 141], [209, 141], [209, 156], [5, 156]]},
              {'text': '北京3例确诊者曾在全聚德聚餐', 'confidence': 0.9947283864021301,
               'text_region': [[4, 171], [197, 172], [197, 188], [4, 187]]},
              {'text': '日本全面限制新入境不含中国大陆', 'confidence': 0.9981253743171692,
               'text_region': [[5, 203], [221, 203], [221, 222], [5, 222]]},
              {'text': '2020最特别的一件衣服', 'confidence': 0.9995226263999939,
               'text_region': [[4, 235], [151, 235], [151, 254], [4, 254]]},
              {'text': '央行副行长就约谈蚂蚁集团答记者问', 'confidence': 0.9819984436035156,
               'text_region': [[5, 268], [232, 268], [232, 284], [5, 284]]},
              {'text': '降温预报图冷到发紫', 'confidence': 0.9980568289756775,
               'text_region': [[3, 298], [133, 298], [133, 317], [3, 317]]}]

    app = QApplication(sys.argv)
    win = VisResult(np_img=img, result=result, configs={}, translate_result='', save_path=[folder_path])
    win.show()

    app.exec_()
