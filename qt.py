from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class CustomWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(QDesktopWidget().screenGeometry().width() * 0.328125,
                          QDesktopWidget().screenGeometry().height() * 0.25)
        self.frame = QFrame(self)

    def location_on_screen(self):
        self.move(QDesktopWidget().screenGeometry().width() * 0.012,
                  QDesktopWidget().screenGeometry().height() * 0.574)


class CustomLabel(QLabel):
    def __init__(self, text=''):
        super().__init__()

        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(5)
        effect.setColor(QColor("#000"))
        effect.setOffset(1, 1)
        self.setGraphicsEffect(effect)

        self.setStyleSheet('color: white; font-size: 15px;')
        self.setText(text)
        self.setFixedWidth(self.fontMetrics().width(self.text()) + 10)

    def recalculate_width(self):
        self.setFixedWidth(self.fontMetrics().width(self.text()) + 10)


class UsernameLabel(CustomLabel):
    def __init__(self):
        super().__init__()
        self.setStyleSheet('font-size: 15px; font-weight: bold; color: white;')

    def set_color(self, color):
        self.setStyleSheet('font-size: 15px; font-weight: bold; color: '+color +';')


def init_qt():
    app = QApplication([])
    window = CustomWindow()
    window.location_on_screen()
    window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    window.setAttribute(Qt.WA_TranslucentBackground)

    layout = QVBoxLayout()

    label_dict = {}
    for i in range(7):
        label_dict['line'+str(i)] = (UsernameLabel(), CustomLabel())
        sub_layout = QHBoxLayout()
        sub_layout.addWidget(label_dict['line'+str(i)][0])
        sub_layout.addWidget(label_dict['line'+str(i)][1])
        sub_layout.addStretch()
        layout.addLayout(sub_layout)

    window.setLayout(layout)
    window.show()
    return window, app, label_dict
