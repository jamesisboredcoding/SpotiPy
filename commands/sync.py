from ytmusicapi import YTMusic, setup_oauth, setup
import os
import colorama as c

title = "sync"
description = "syncs your YT Music account to SpotiPy"

AUTH_FILE = "browser.json"
FULL_PATH = os.path.join(os.getcwd(), AUTH_FILE)

def login(root):
    try:
        if os.path.exists(FULL_PATH):
            return YTMusic(FULL_PATH)
        else:
            op = root.pick([
                "Authorize via browser",
                "Authorize manually"
            ])

            if op == 0:
                setup_oauth(
                    client_id=root.getenv("CLIENT_ID"),
                    client_secret=root.getenv("CLIENT_SECRET"),
                    filepath=FULL_PATH,
                    open_browser=True
                )
            else:
                headers = input("Paste request headers: ")
                setup(filepath=FULL_PATH, headers_raw=headers)
            return YTMusic(FULL_PATH)
    except Exception as e:
        root.error(f"login err: {e}")
    
def main(root):
    yt = login(root)
    if yt == None:
        root.error("YTMusic was None, aborted.")
        return
    try:
        account_info = yt.get_account_info()
        root.print(f"Already logged in as: {c.Fore.LIGHTBLUE_EX} {account_info["accountName"]} ({account_info["channelHandle"]}) {c.Fore.RESET}")
    except Exception as e:
        root.error(f"ytm err: {e}")