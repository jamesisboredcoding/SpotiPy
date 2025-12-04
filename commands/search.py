from ytmusicapi import YTMusic
import subprocess
import helpers.player as plr

title = "search <query> <results_num=30>"
alias = ["query", "q", "s"]
description = "performs a search for a song from YTM"

def main(root, query=None, results_num=30):
    yt = root.login(root)
    if yt == None:
        root.error("Must be logged in with YTM to continue")
        return
    results = yt.search(query=query, filter="songs", limit=results_num)
    
    choices = []
    for song in results:
        choices.append("\n".join([
            f"Title: {song["title"]}",
            f"Duration: {song["duration"]}",
            f"Artist(s): {song["artist"] if hasattr(song, "artist") else ", ".join([artist["name"] for artist in song["artists"]])}"
        ]))

    choice = root.pick(choices)
    song = results[choice]

    if song:
        actions = [
            "Play now",
            "Play next",
            "Add to queue",
            "Like",
            "Add to playlist",
            "Exit"
        ]

        action = root.pick(actions)
        if action != len(actions):
            if action == actions.index("Play now"):
                player = plr.load(root)
                player.play(song["videoId"])
    else:
        root.error("invalid song")