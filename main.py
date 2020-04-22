import time
import json
import requests
import threading
import keyboard
import atexit

import tf2

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

"""
This program monitors a Source Engine console log file and feeds voice chat lines into Google's Perspective API.
For a Source game to output a log file, the launch option -condebug must be enabled

Created by Bryce Yoder, 2020
"""


class TailFileThread(threading.Thread):
    def __init__(self, path, chars):
        threading.Thread.__init__(self)
        self.path = path
        self.chars = chars

    def run(self):
        while True:
            # Watch file for new text chat lines
            for hit_word, hit_sentence in watch(self.path, self.chars):
                # Parse the exact string from the file

                original_chat_string = hit_sentence[hit_sentence.index(':') + 2:]
                username = hit_sentence[:hit_sentence.index(':') - 1]
                print(original_chat_string)
                print(username)

                real_chat_string_list = original_chat_string.split()
                real_chat_string = ' '.join(
                    [word for word in real_chat_string_list if word.lower() not in swears_whitelist])
                toxicity_rating = analyze_comment(real_chat_string)

                if message_queue:
                    message_queue.pop(0)

                if toxicity_rating < .91:
                    message_queue.append(username + ': ' + original_chat_string)
                else:
                    message_queue.append("Message from " + username + " filtered for possible hate speech")

                for i in range(7):
                    label_dict['line' + str(i)].setText(message_queue[i])


class KeyListenerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        visible = True
        while True:
            if keyboard.is_pressed('y'):
                if visible:
                    visible = False
                    window.setWindowOpacity(0)
            elif keyboard.is_pressed('esc'):
                visible = True
                window.setWindowOpacity(1)
            elif keyboard.is_pressed('enter'):
                visible = True
                window.setWindowOpacity(1)


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
    def __init__(self):
        super().__init__()
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(5)
        effect.setColor(QColor("#000"))
        effect.setOffset(1, 1)
        self.setGraphicsEffect(effect)
        self.setStyleSheet('color: white; font-size: 15px; padding-top: 5px; padding-bottom: 5px;')


def handle_exit():
    print("ye")


def watch(fn, words):
    """Monitor a file for new lines matching a string. Python version of tail -f | grep"""
    fp = open(fn, 'r', errors='replace')
    while True:
        new = fp.readline()

        if new:
            for word in words:
                if word in new:
                    yield(word, new)

        else:
            time.sleep(0.5)


def analyze_comment(comment):
    """Call Google's Perspective API on some string and return summary toxicity score"""
    url = ('https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze' + '?key=' + api_key)
    data_dict = {
        'comment': {'text': comment},
        'languages': ['en'],
        'requestedAttributes': {'TOXICITY': {}}
    }
    response = requests.post(url=url, data=json.dumps(data_dict))
    response_dict = json.loads(response.content)
    print(response_dict)
    try:
        return response_dict['attributeScores']['TOXICITY']['summaryScore']['value']
    except KeyError:
        return 0


if __name__ == "__main__":
    # Do some preliminary operations on the game itself
    console_path, autoexec_path = tf2.locate_install()
    tf2.disable_tf2_chat(autoexec_path)

    # Load items from the config file
    config = json.load(open('config.json', 'r'))
    api_key = config['api_key']
    swears_whitelist = config['whitelist']

    # Clear the console log,
    # define the string that identifies player comments,
    # create the message queue
    open(console_path, 'w').close()
    chars_to_match = [' : ']
    message_queue = ['' for i in range(7)]

    app = QApplication([])
    window = CustomWindow()
    window.location_on_screen()
    window.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    window.setAttribute(Qt.WA_TranslucentBackground)

    layout = QVBoxLayout()

    label_dict = {}
    for i in range(7):
        label_dict['line'+str(i)] = CustomLabel()
        layout.addWidget(label_dict['line'+str(i)])

    window.setLayout(layout)
    window.show()

    TailFileThread(console_path, chars_to_match).start()
    KeyListenerThread().start()

    atexit.register(handle_exit)
    app.exec()

