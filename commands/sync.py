from ytmusicapi import YTMusic, setup_oauth, setup
import os
import colorama as c

title = "sync <force_new=False>"
description = "syncs your YT Music account to SpotiPy"

AUTH_FILE = "browser.json"
FULL_PATH = os.path.join(os.getcwd(), AUTH_FILE)

def login(root, force):
    try:
        if not force and os.path.exists(FULL_PATH):
            return YTMusic(FULL_PATH)
        else:
            if os.path.exists(FULL_PATH) and force:
                os.remove(FULL_PATH)
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
                headers = root.input("Paste request headers: ")
                root.print(headers)
                setup(filepath=FULL_PATH, headers_raw=headers)
            return YTMusic(FULL_PATH)
    except Exception as e:
        root.error(f"login err: {e}")
    
def main(root, force_new=False):
    yt = login(root, force_new)
    if yt == None:
        root.error("YTMusic was None, aborted.")
        return
    try:
        account_info = yt.get_account_info()
        root.print(f"Already logged in as: {c.Fore.LIGHTBLUE_EX} {account_info["accountName"]} ({account_info["channelHandle"]}) {c.Fore.RESET}")
    except Exception as e:
        root.error(f"ytm err: {e}")