import teams
import sys

import tf2
import qt
import game

"""
This program monitors a Source Engine console log file and feeds voice chat lines into Google's Perspective API.
For a Source game to output a log file, the launch option -condebug must be enabled

Created by Bryce Yoder, 2020
"""


if __name__ == "__main__":
    game_state = game.GameStateObject()

    # Do some preliminary operations on the game itself
    console_path, autoexec_path = tf2.locate_install()
    tf2.disable_tf2_chat(autoexec_path)
    game_state.username = tf2.get_username()
    teams.teams_dict[game_state.username] = 'red'

    open(console_path, 'w').close()
    game_state.message_queue = [['', ''] for i in range(7)]

    game_state.window, game_state.app, game_state.label_dict = qt.init_qt()

    game.TailFileThread(console_path, [' : ', 'Lobby destroyed', ' killed '], game_state).start()
    game.KeyListenerThread(game_state).start()
    game.MonitorProcessesThread(autoexec_path, game_state).start()

    game_state.app.exec()
    sys.exit()
