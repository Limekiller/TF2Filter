import time
import requests
import threading
import keyboard
import psutil
import json

import teams


class GameStateObject:
    """
    This object controls a bunch of stuff so we don't have to use globals
    """
    def __init__(self):
        # Load items from the config file
        config = json.load(open('config.json', 'r'))
        self.api_key = config['api_key']
        self.swears_whitelist = config['whitelist']

        self.tf2_is_running = False
        self.tf2_has_run = False

        self.chat_is_open = False
        self.last_comment_received_time = time.clock()
        self.username = ''

        self.window = None
        self.app = None
        self.label_dict = {}
        self.message_queue = []


class TailFileThread(threading.Thread):
    """
    This thread monitors the console.log file and calls the corresponding functions when actions occur.
    Takes a path to a log file and a list of words to look for.
    """
    def __init__(self, path, chars, game_state):
        threading.Thread.__init__(self, daemon=True)
        self.path = path
        self.chars = chars
        self.game_state = game_state

    def run(self):
        while True:
            # Watch file for new text chat lines
            for hit_word, hit_sentence in watch(self.path, self.chars):
                if hit_word == ' : ':
                    handle_new_comment(hit_sentence, self.game_state)
                elif hit_word == ' killed ':
                    teams.handle_player_interaction(hit_sentence)
                else:
                    handle_server_exit(self.game_state)
                time.sleep(0.01)


class ShowCommentTimerThread(threading.Thread):
    """
    A new instance of this thread is created whenever a new comment comes in. It waits 10 seconds and then hides
    the chat window if the last message was sent more than 10 seconds ago.
    """
    def __init__(self, game_state):
        threading.Thread.__init__(self)
        self.game_state = game_state

    def run(self):
        time.sleep(10)
        if time.clock() - self.game_state.last_comment_received_time > 10:
            self.game_state.window.setWindowOpacity(0)


class KeyListenerThread(threading.Thread):
    """
    This thread listens for key presses and manipulates the chat window accordingly.
    It hides the custom chat window when y or u is pressed, and shows it if there are new messages
    when esc is pressed. It also allows a user to hit shift+t to reverse team colors
    """
    def __init__(self, game_state):
        threading.Thread.__init__(self, daemon=True)
        self.game_state = game_state

    def run(self):
        switching_teams = False
        while True:
            if self.game_state.tf2_is_running:
                if keyboard.is_pressed('y') or keyboard.is_pressed('u'):
                    self.game_state.chat_is_open = True
                    self.game_state.window.setWindowOpacity(0)
                elif keyboard.is_pressed('enter') or keyboard.is_pressed('esc'):
                    self.game_state.chat_is_open = False
                elif keyboard.is_pressed('shift') and keyboard.is_pressed('t') and not switching_teams:
                    switching_teams = True
                    for player in teams.teams_dict.keys():
                        if teams.teams_dict[player] == 'red':
                            teams.teams_dict[player] = 'blue'
                        else:
                            teams.teams_dict[player] = 'red'
                    for i in range(7):
                        try:
                            if teams.teams_dict[self.game_state.message_queue[i][0]] == 'red':
                                self.game_state.label_dict['line' + str(i)][0].set_color('#d95858')
                            else:
                                self.game_state.label_dict['line' + str(i)][0].set_color('#5884d9')
                        except KeyError:
                            pass
                    time.sleep(1)
                    switching_teams = False
            time.sleep(0.01)


class MonitorProcessesThread(threading.Thread):
    """
    This thread watches all of the computers processes to determine if the game has been opened.
    Before the game is opened, the chat window is always hidden. Once the game has been opened, normal behavior
    begins. When the game is then closed, the program exits.
    """
    def __init__(self, autoexec, game_state):
        threading.Thread.__init__(self, daemon=True)
        self.autoexec = autoexec
        self.game_state = game_state

    def run(self):
        while True:
            if "hl2.exe" in (p.name() for p in psutil.process_iter()):
                if not self.game_state.tf2_is_running:
                    self.game_state.window.setWindowOpacity(1)
                self.game_state.tf2_is_running = True
                self.game_state.tf2_has_run = True
            else:
                if self.game_state.tf2_has_run:
                    with open(self.autoexec, "r") as f:
                        lines = f.readlines()
                    with open(self.autoexec, "w") as f:
                        for line in lines:
                            if line.strip("\n") != "hud_saytext_time 0":
                                f.write(line)
                                self.game_state.window.close()

                self.game_state.tf2_is_running = False
                self.game_state.window.setWindowOpacity(0)
            time.sleep(1)


def handle_player_connection(hit_sentence, game_state):
    game_state.message_queue.append([None, hit_sentence])
    advance_messages(game_state)


def handle_new_comment(hit_sentence, game_state):
    """
    This function is called every time a new comment comes in.
    It analyzes the comment and does all the proper formatting before adding it to the message queue.
    :param hit_sentence: string
    :param game_state:  GameStateObject
    """
    original_chat_string = hit_sentence[hit_sentence.index(':') + 2:]
    username = hit_sentence[:hit_sentence.index(':') - 1]
    print(original_chat_string)
    print(username)

    real_chat_string_list = original_chat_string.split()
    real_chat_string = ' '.join(
        [word for word in real_chat_string_list if word.lower() not in game_state.swears_whitelist])
    toxicity_rating = analyze_comment(real_chat_string, game_state)

    if game_state.message_queue:
        game_state.message_queue.pop(0)

    if toxicity_rating < .91:
        game_state.message_queue.append([username, original_chat_string])
    else:
        game_state.message_queue.append([None, "Message from " + username + " filtered for possible hate speech\n"])

    advance_messages(game_state)
    game_state.last_comment_received_time = time.clock()

    print(game_state.message_queue)
    if not game_state.chat_is_open:
        game_state.window.setWindowOpacity(1)
        ShowCommentTimerThread(game_state).start()


def advance_messages(game_state):
    """
    This function is called when the message queue is updated. It causes the UI labels to advance.
    :param game_state: GameStateObject
    :return:
    """
    for i in range(7):
        username = game_state.message_queue[i][0]
        try:
            game_state.label_dict['line' + str(i)][0].setText(game_state.message_queue[i][0]+':\n')

            if "*DEAD* " in game_state.message_queue[i][0]:
                username = game_state.message_queue[i][0].split('*DEAD* ')[1]

        except TypeError:
            game_state.label_dict['line' + str(i)][0].setText('\n')
            game_state.label_dict['line' + str(i)][0].recalculate_width()

        try:
            if teams.teams_dict[username] == 'red':
                game_state.label_dict['line' + str(i)][0].set_color('#d95858')
            else:
                game_state.label_dict['line' + str(i)][0].set_color('#5884d9')
        except KeyError:
            game_state.label_dict['line' + str(i)][0].set_color('#ffffff')

        game_state.label_dict['line' + str(i)][1].setText(game_state.message_queue[i][1])
        game_state.label_dict['line' + str(i)][0].recalculate_width()
        game_state.label_dict['line' + str(i)][1].recalculate_width()


def handle_server_exit(game_state):
    """
    This function is called when the server is disconnected. It clears the labels.
    :param game_state: GameStateObject
    :return:
    """
    for i in range(7):
        game_state.label_dict['line' + str(i)][0].setText('')
        game_state.label_dict['line' + str(i)][1].setText('')


def watch(fn, words):
    """
    Monitor a file for new lines matching a string. Python version of tail -f | grep
    """
    fp = open(fn, 'r', errors='replace')
    while True:
        new = fp.readline()
        if new:
            for word in words:
                if word in new:
                    yield(word, new)
        else:
            time.sleep(0.5)


def analyze_comment(comment, game_state):
    """
    Call Google's Perspective API on some string and return summary toxicity score
    """
    url = ('https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze' + '?key=' + game_state.api_key)
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
