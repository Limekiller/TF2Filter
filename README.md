# TF2Filter
Uses Perspective API to filter hate speech from TF2 (and other Source Engine games)

This program can be started before or after launching TF2, but it is recommended to start it before TF2—otherwise, some options may not be applied correctly.
The following launch options must be specified:


`-condebug -sw -noborder -novid -h 1080 -w 1920`

Modify -h and -w to match your resolution. These launch options will run TF2 in a borderless window, allowing this program to remain on top and display this custom chat (instead of modifying dll files or what-have-you). It will also tell TF2 to dump everything logged to the in-game console to a text file that the program will then read; this is how the program monitors the game state, receives incoming messages, etc. Doing it this way keeps the program from being detected as malicious by VAC—the process itself is not modified in any way.
