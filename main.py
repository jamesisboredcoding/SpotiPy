import os
import colorama as c
import sys
import importlib.util as iutil
import time
import traceback
import subprocess

from pathlib import Path
from pynput import keyboard

# Prereqs

print("\033]0;SpotiPy CLI\007", end="")

buffer = []

# Classes

class AttrDict(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'AttrDict' object has no attribute '{name}'")

# Functions

def tprint(*args, **kwargs):
    text = " ".join(str(a) for a in args)
    buffer.append(text)
    print(text, **kwargs)

def tinput(c):
    result = input(c)
    buffer.append(c + result)
    return result

def ws(t, l):
    return t + " "*(l - len(t))

def clear():
    buffer.clear()
    os.system("cls" if os.name == "nt" else "clear")

def error(e, r=False):
    if r:
        return c.Fore.RED + e + c.Fore.RESET
    tprint(c.Fore.RED + e + c.Fore.RESET)

def send(content):
    tprint(c.Style.RESET_ALL)
    clear()
    tprint("")
    for line in content:
        tprint(line)
    tprint("\n   " + "—"*50)

def read_command(command):
    try:
        script_path = Path("./commands") / (command + ".py")
        if not script_path.exists():
            commands_dir = Path("./commands")
            for file in commands_dir.glob("*.py"):
                try:
                    spec = iutil.spec_from_file_location(file.stem, file)
                    temp_module = iutil.module_from_spec(spec)
                    spec.loader.exec_module(temp_module)
                    
                    if hasattr(temp_module, 'alias') and command in temp_module.alias:
                        script_path = file
                        command = file.stem
                        break
                except:
                    continue
        
        if not script_path.exists():
            error(f"Command '{command}' not found")
            return None
            
        spec = iutil.spec_from_file_location(command, script_path)
        module = iutil.module_from_spec(spec)

        sys.modules[command] = module
        spec.loader.exec_module(module)
        return module
        
    except Exception as e:
        error(f"cmd read fail: {e}")
        return None

def pick(choices):
    last = buffer.copy()
    def land(x):
        for i, choice in enumerate(choices):
            if i == x:
                tprint(c.Fore.LIGHTCYAN_EX + f"> {choice}" + c.Fore.RESET)
            else:
                tprint(c.Fore.LIGHTBLACK_EX + f"> {choice}" + c.Fore.RESET)

    returned = False
    target = 0

    def on_press(key):
        nonlocal target, returned

        if key == keyboard.Key.enter:
            returned = True
            return False

        if key == keyboard.Key.up:
            target = (target - 1) % len(choices)
            clear()
            for l in last: tprint(l)
            land(target)
        elif key == keyboard.Key.down:
            target = (target + 1) % len(choices)
            clear()
            for l in last: tprint(l)
            land(target)

    land(target)

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
    return target

def upd():
    send([
        f"   Currently playing:\n",
        f"   {ws("Title:", 10)}Music",
        f"   {ws("Artist:", 10)}Eminem",
        f"   {ws("Time:", 10)}{c.Fore.LIGHTCYAN_EX + "—"*20 + c.Fore.LIGHTBLACK_EX + "—"*10 + c.Fore.RESET} 2:45 / 6:52"
    ]); tprint("")

# Loop

queued_logs = []
while True:
    upd()

    for log in queued_logs:
        tprint("   " + str(log))
    if len(queued_logs) > 0: tprint("")

    command = tinput(c.Fore.LIGHTGREEN_EX + "  > " + c.Fore.WHITE)
    module = read_command(command)

    if module:
        try:
            if not hasattr(module, "main"):
                error(f"cmd init fail: {command} has no main init function")
            else:
                module.main(AttrDict({
                    "print": lambda content: queued_logs.append(content),
                    "error": lambda e: queued_logs.append(error(e, True)),
                    "read_command": lambda command: read_command(command),
                    "getenv": lambda c: os.getenv(c),
                    "pick": lambda c: pick(c),
                    "clear": lambda: clear(),
                    "clear_logs": lambda: queued_logs.clear(),
                    "login": lambda root: read_command("sync").login(root)
                }))
        except Exception as e:
            queued_logs.append(error(f"module err: {e}", True))