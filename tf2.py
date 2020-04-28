import winreg

"""
This file handles any 'interactions' with the actual game.
"""


def locate_install():
    """
    This function searches the registry for the Steam install path, and then uses that to find the TF2 install
    location. Then, from that, we get the console.log and autoexec.cfg file locations.
    Returns an array containing the console log file path and the autoexec config file path.
    """

    steam_path = "Steam install could not be found"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\Valve\\Steam")
        steam_path = winreg.QueryValueEx(key, "SteamPath")[0]
    except FileNotFoundError:
        print(steam_path)
        exit()

    console_path = steam_path + '/steamapps/common/Team Fortress 2/tf/console.log'
    autoexec_path = steam_path + '/steamapps/common/Team Fortress 2/tf/cfg/autoexec.cfg'

    return console_path, autoexec_path


def disable_tf2_chat(autoexec_path):
    """
    Searches the given autoexec file for a line that will disable the in-game text chat.
    If this line is not found, it is appended to the file.
    Takes a string autoexec_path representing the location of the autoexec config file,
    and returns nothing
    """

    line_found = False
    with open(autoexec_path, 'r') as f:
        for line in f:
            if line == "hud_saytext_time 0":
                line_found = True
                break
    f.close()

    if not line_found:
        with open(autoexec_path, 'a') as f:
            f.write("\nhud_saytext_time 0")
        f.close()
