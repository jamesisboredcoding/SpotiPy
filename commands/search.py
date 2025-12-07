import helpers.player as plr
import commands.sync as sync

title = "search <query>:string <results_num=30>:number <songs_only=True>:boolean"
alias = ["query", "q", "s"]
description = "performs a search for a song from YTM"

def main(root, query=None, results_num=30, songs_only=True):
    yt = sync.login(root)
    if yt == None:
        root.error("Must be logged in with YTM to continue")
        return
    
    songs = yt.search(query=query, filter="songs", limit=results_num)
    videos = yt.search(query=query, filter="videos", limit=results_num)

    results = songs if songs_only else songs + videos
    choices = []

    for song in results:
        choices.append(f"{song["title"]} by {song["artist"] if hasattr(song, "artist") else ", ".join([artist["name"] for artist in song["artists"]])}")

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