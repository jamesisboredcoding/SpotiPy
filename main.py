import os
import colorama as c
import sys
import importlib.util as iutil
import shlex
import time
import threading

from pathlib import Path
from pynput import keyboard

# Prereqs

print("\033]0;SpotiPy CLI\007", end="")

buffer = []
queued_logs = []
saved_globals = {}
in_input = False
current_song = {
    "title": "Nothing playing",
    "artists": ["—"],
    "position": 0,
    "duration": 0,
    "is_playing": False,
    "looped": False,
    "looped_playlist": False,
}

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

def parse_arguments(command_input, title):
    try:
        import re
        arg_pattern = r'<([^>]+)>'
        arg_definitions = re.findall(arg_pattern, title)
        
        args_info = []
        for arg_def in arg_definitions:
            if '=' in arg_def:
                name, default = arg_def.split('=', 1)
                args_info.append((name, default))
            else:
                args_info.append((arg_def, None))
        
        parts = shlex.split(command_input)
        command_name = parts[0] if parts else ""
        provided_args = parts[1:] if len(parts) > 1 else []
        
        def convert_value(value):
            if value.lower() in ('true', 'yes', '1', 'on'):
                return True
            if value.lower() in ('false', 'no', '0', 'off'):
                return False
            
            try:
                return int(value)
            except ValueError:
                pass
            
            try:
                return float(value)
            except ValueError:
                pass
            
            return value
        
        kwargs = {}
        for i, (arg_name, default) in enumerate(args_info):
            if i < len(provided_args):
                kwargs[arg_name] = convert_value(provided_args[i])
            elif default is not None:
                kwargs[arg_name] = convert_value(default)
            else:
                kwargs[arg_name] = None
        
        return kwargs
    except Exception as e:
        error(f"arg parse fail: {e}")
        return {}

def read_command(command_input):
    try:
        command = shlex.split(command_input)[0] if command_input else ""
        
        script_path = Path("./commands") / (command + ".py")
        actual_command_name = command
        
        if not script_path.exists():
            commands_dir = Path("./commands")
            for file in commands_dir.glob("*.py"):
                try:
                    spec = iutil.spec_from_file_location(file.stem, file)
                    temp_module = iutil.module_from_spec(spec)
                    spec.loader.exec_module(temp_module)
                    
                    if hasattr(temp_module, 'alias') and command in temp_module.alias:
                        script_path = file
                        actual_command_name = file.stem
                        break
                except:
                    continue
        
        if not script_path.exists():
            error(f"Command '{command}' not found")
            return None, {}
            
        spec = iutil.spec_from_file_location(actual_command_name, script_path)
        module = iutil.module_from_spec(spec)

        sys.modules[actual_command_name] = module
        spec.loader.exec_module(module)
        
        kwargs = {}
        if hasattr(module, 'title'):
            kwargs = parse_arguments(command_input, module.title)
        
        return module, kwargs
        
    except Exception as e:
        error(f"cmd read fail: {e}")
        return None, {}

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
            redraw_screen()
            land(target)
        elif key == keyboard.Key.down:
            target = (target + 1) % len(choices)
            redraw_screen()
            land(target)

    redraw_screen()
    land(target)

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

    redraw_screen()
    time.sleep(.5)
    return target

# 

def format_time(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"

def get_progress_bar(position, duration, width=30):
    if duration == 0:
        return c.Fore.LIGHTBLACK_EX + "—" * width + c.Fore.RESET
    
    progress = position / duration
    filled = int(progress * width)
    
    bar = (c.Fore.LIGHTCYAN_EX + "—" * filled + 
           c.Fore.LIGHTBLACK_EX + "—" * (width - filled) + 
           c.Fore.RESET)
    return bar

def render_header():
    pos_str = format_time(current_song["position"])
    dur_str = format_time(current_song["duration"])
    progress_bar = get_progress_bar(current_song["position"], current_song["duration"])
    
    lines = [
        "",
        f"{c.Fore.RESET}  Currently playing: {c.Fore.YELLOW}{"(looped)" if current_song["looped"] else "(looped playlist)" if current_song["looped_playlist"] else ""}{c.Fore.RESET}",
        "",
        f"  {ws('Title:', 15)}{current_song['title']}",
        f"  {ws('Artist(s):', 15)}{", ".join(current_song['artists'])}",
        f"  {ws('Time:', 15)}{progress_bar} {pos_str} / {dur_str}",
        "",
        f"  {'—'*50}",
    ]
    return lines

def update_header():
    sys.stdout.write("\033[s")
    sys.stdout.write("\033[H")
    
    for line in render_header():
        sys.stdout.write("\033[2K" + line + "\n")
    
    sys.stdout.write("\033[2K\n")
    
    sys.stdout.write("\033[u")
    sys.stdout.flush()

def redraw_screen():
    clear()
    
    for line in render_header():
        print(line)
    print()
    
    for log in queued_logs:
        print("   " + str(log))
    if len(queued_logs) > 0:
        print()

def setg(g, v):
    saved_globals[g] = v

def _input(c):
    in_input = True
    c = tinput(c)
    in_input = False
    return c

# Loop

def update_thread():
    while True:
        if current_song["is_playing"] and current_song["position"] < current_song["duration"]:
            current_song["position"] += 1
        if in_input:
            update_header()
        time.sleep(1)

threading.Thread(target=update_thread, daemon=True).start()
redraw_screen()

while True:
    in_input = True
    command = tinput(c.Fore.LIGHTGREEN_EX + "  > " + c.Fore.WHITE)
    module, kwargs = read_command(command)
    in_input = False

    if module:
        try:
            if not hasattr(module, "main"):
                error(f"cmd init fail: {command} has no main init function")
            else:
                module.main(AttrDict({
                    "send": lambda s: send(s),
                    "print": lambda content: queued_logs.append(content),
                    "error": lambda e: queued_logs.append(error(e, True)),
                    "read_command": lambda command: read_command(command),
                    "getenv": lambda c: os.getenv(c),
                    "pick": lambda c: pick(c),
                    "clear": lambda: clear(),
                    "clear_logs": lambda: queued_logs.clear(),
                    "getg": lambda g: saved_globals.get(g),
                    "setg": lambda g, v: setg(g, v),
                    "set_song": lambda title, artists, pos, dur: current_song.update({
                        "title": title, "artists": artists, "position": pos, "duration": dur, "is_playing": True
                    }),
                    "stop_song": lambda: current_song.update({
                        "title": "Nothing playing", "artists": ["—"], "position": 0, "duration": 0, "is_playing": False,
                    }),
                    "pause_song": lambda paused: current_song.update({"is_playing": not paused}),
                    "edit_song": lambda e: current_song.update(e),
                    "current": lambda: current_song.copy(),
                    "redraw": lambda: redraw_screen(),
                    "input": lambda c: _input(c)
                }), **kwargs)
        except Exception as e:
            queued_logs.append(error(f"module err: {e}", True))

    redraw_screen()