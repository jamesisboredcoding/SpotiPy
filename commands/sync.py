from ytmusicapi import YTMusic, OAuthCredentials, setup, setup_oauth
import os
import colorama as c

title = "sync <force_new=False>"
description = "syncs your YT Music account to SpotiPy"

AUTH_FILE = "oauth.json"
BROWSER_FILE = "browser.json"

FULL_PATH = lambda file: os.path.join(os.getcwd(), file)

def login(root, force=False):
    try:
        auth = FULL_PATH(AUTH_FILE)
        browser = FULL_PATH(BROWSER_FILE)
        validFile = auth if os.path.exists(auth) else browser if os.path.exists(browser) else None

        if not force and validFile is not None:
            if validFile == auth:
                oauth_creds = OAuthCredentials(
                    client_id=root.getenv("CLIENT_ID"),
                    client_secret=root.getenv("CLIENT_SECRET")
                )
                return YTMusic(auth, oauth_credentials=oauth_creds)
            else:
                return YTMusic(browser)
        else:
            if validFile is not None and force:
                os.remove(validFile)

            op = root.pick([
                "Authorize via browser",
                "Authorize manually"
            ])

            if op == 0:
                oauth_creds = OAuthCredentials(
                    client_id=root.getenv("CLIENT_ID"),
                    client_secret=root.getenv("CLIENT_SECRET")
                )
                setup_oauth(open_browser=True, filepath=auth)
                return YTMusic(auth, oauth_credentials=oauth_creds)
            else:
                headers = root.input(f"{c.Fore.YELLOW}Paste request headers: {c.Fore.RESET}", ml=True)
                
                if not headers or len(headers) < 100:
                    root.error("Headers seem too short. Please copy the full headers.")
                    return None
                setup(filepath=browser, headers_raw=headers)
                return YTMusic(browser)
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