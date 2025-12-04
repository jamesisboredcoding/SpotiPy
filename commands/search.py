title = "search"
alias = ["query", "q", "s"]
description = "performs a search for a song from YTM"

def main(root):
    yt = root.login(root)
    root.print(yt)