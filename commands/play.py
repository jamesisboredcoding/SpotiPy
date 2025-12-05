import helpers.player as plr

title = "play <song> <from_playlist=1>"
alias = ["p"]
description = "plays a song from current playlist"

def main(root, song, from_playlist=1):
    player = plr.load(root)
    if not song:
        player.play()