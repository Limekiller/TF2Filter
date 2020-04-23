import time
import json
import requests
import threading
import keyboard
import psutil
import sys

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
    """
    This thread monitors the console.log file and calls the corresponding functions when actions occur.
    Takes a path to a log file and a list of words to look for.
    """
    def __init__(self, path, chars):
        threading.Thread.__init__(self, daemon=True)
        self.path = path
        self.chars = chars

    def run(self):
        while True:
            # Watch file for new text chat lines
            for hit_word, hit_sentence in watch(self.path, self.chars):
                if self.chars == [' : ']:
                    handle_new_comment(hit_sentence)
                else:
                    handle_server_exit()
                time.sleep(0.01)


class ShowCommentTimerThread(threading.Thread):
    """
    A new instance of this thread is created whenever a new comment comes in. It waits 10 seconds and then hides
    the chat window if the last message was sent more than 10 seconds ago.
    """
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global last_comment_received_time
        time.sleep(10)
        if time.clock() - last_comment_received_time > 10:
            window.setWindowOpacity(0)


class KeyListenerThread(threading.Thread):
    """
    This thread listens for key presses and manipulates the chat window accordingly. Right now, it simply hides
    the chat if y or u is pressed.
    """
    def __init__(self):
        threading.Thread.__init__(self, daemon=True)

    def run(self):
        global tf2_is_running
        while True:
            if tf2_is_running:
                if keyboard.is_pressed('y') or keyboard.is_pressed('u'):
                    window.setWindowOpacity(0)
            time.sleep(0.01)


class MonitorProcessesThread(threading.Thread):
    """
    This thread watches all of the computers processes to determine if the game has been opened.
    Before the game is opened, the chat window is always hidden. Once the game has been opened, normal behavior
    begins. When the game is then closed, the program exits.
    """
    def __init__(self, autoexec):
        threading.Thread.__init__(self, daemon=True)
        self.autoexec = autoexec

    def run(self):
        global tf2_is_running
        global tf2_has_run
        while True:
            if "hl2.exe" in (p.name() for p in psutil.process_iter()):
                if not tf2_is_running:
                    window.setWindowOpacity(1)
                tf2_is_running = True
                tf2_has_run = True
            else:
                if tf2_has_run:
                    with open(self.autoexec, "r") as f:
                        lines = f.readlines()
                    with open(self.autoexec, "w") as f:
                        for line in lines:
                            if line.strip("\n") != "hud_saytext_time 0":
                                f.write(line)
                    window.close()

                tf2_is_running = False
                window.setWindowOpacity(0)
            time.sleep(1)


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
        self.setStyleSheet('color: white; font-size: 15px;')


def handle_new_comment(hit_sentence):
    global last_comment_received_time

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
        message_queue.append("Message from " + username + " filtered for possible hate speech\n")

    for i in range(7):
        label_dict['line' + str(i)].setText(message_queue[i])

    last_comment_received_time = time.clock()

    window.setWindowOpacity(1)
    ShowCommentTimerThread().start()


def handle_server_exit():
    for i in range(7):
        label_dict['line' + str(i)].setText('')


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
    tf2_is_running = False
    tf2_has_run = False
    last_comment_received_time = time.clock()

    # Do some preliminary operations on the game itself
    console_path, autoexec_path = tf2.locate_install()
    tf2.disable_tf2_chat(autoexec_path)

    # Load items from the config file
    config = json.load(open('config.json', 'r'))
    api_key = config['api_key']
    swears_whitelist = config['whitelist']

    open(console_path, 'w').close()
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

    TailFileThread(console_path, [' : ']).start()
    TailFileThread(console_path, ['Lobby destroyed']).start()
    KeyListenerThread().start()
    MonitorProcessesThread(autoexec_path).start()

    app.exec()
    sys.exit()
