import time
import json
import requests
import threading
import keyboard
import psutil
import sys

import tf2
import qt
import teams

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
                if hit_word == ' : ':
                    handle_new_comment(hit_sentence)
                elif hit_word == ' killed ':
                    teams.handle_player_interaction(hit_sentence)
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
        global chat_is_open
        while True:
            if tf2_is_running:
                if keyboard.is_pressed('y') or keyboard.is_pressed('u'):
                    chat_is_open = True
                    window.setWindowOpacity(0)
                elif keyboard.is_pressed('enter') or keyboard.is_pressed('esc'):
                    chat_is_open = False
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


def handle_new_comment(hit_sentence):
    global last_comment_received_time
    global chat_is_open

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
        message_queue.append([username, original_chat_string])
    else:
        message_queue.append([None, "Message from " + username + " filtered for possible hate speech\n"])

    for i in range(7):
        try:
            label_dict['line' + str(i)][0].setText(message_queue[i][0]+':\n')
        except (TypeError):
            label_dict['line' + str(i)][0].setText('\n')
        label_dict['line' + str(i)][0].recalculate_width()
        try:
            if teams.teams_dict[message_queue[i][0]] == 'red':
                label_dict['line' + str(i)][0].set_color('#d95858')
            else:
                label_dict['line' + str(i)][0].set_color('#5884d9')
        except KeyError:
            pass

        label_dict['line' + str(i)][1].setText(message_queue[i][1])
        label_dict['line' + str(i)][1].recalculate_width()

    last_comment_received_time = time.clock()

    if not chat_is_open:
        window.setWindowOpacity(1)
        ShowCommentTimerThread().start()


def handle_server_exit():
    for i in range(7):
        label_dict['line' + str(i)][0].setText('')
        label_dict['line' + str(i)][1].setText('')


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
    chat_is_open = False
    last_comment_received_time = time.clock()

    # Do some preliminary operations on the game itself
    console_path, autoexec_path = tf2.locate_install()
    tf2.disable_tf2_chat(autoexec_path)

    # Load items from the config file
    config = json.load(open('config.json', 'r'))
    api_key = config['api_key']
    swears_whitelist = config['whitelist']

    open(console_path, 'w').close()
    message_queue = [['', ''] for i in range(7)]

    window, app, label_dict = qt.init_qt()

    TailFileThread(console_path, [' : ', 'Lobby destroyed', ' killed ']).start()
    KeyListenerThread().start()
    MonitorProcessesThread(autoexec_path).start()

    app.exec()
    sys.exit()
