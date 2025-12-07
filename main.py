import os
import colorama as c
import sys
import importlib.util as iutil
import shlex
import time
import threading
import termios
import re

from dotenv import load_dotenv

from pathlib import Path
from pynput import keyboard

# Prereqs

load_dotenv()
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
        arg_pattern = r'<([^>]+)>'
        arg_definitions = re.findall(arg_pattern, title)
        
        args_info = []
        for arg_def in arg_definitions:
            type_hint = None
            if ':' in arg_def:
                arg_def, type_hint = arg_def.split(':', 1)
                type_hint = type_hint.strip().lower()
            
            if '=' in arg_def:
                name, default = arg_def.split('=', 1)
                args_info.append((name.strip(), default.strip(), type_hint))
            else:
                args_info.append((arg_def.strip(), None, type_hint))
        
        parts = shlex.split(command_input)
        command_name = parts[0] if parts else ""
        provided_args = parts[1:] if len(parts) > 1 else []
        
        def convert_value(value, type_hint=None, default=None, is_default=False):
            if is_default and value == "None":
                return None
            
            if type_hint:
                if type_hint in ('int', 'integer', 'number'):
                    try:
                        return int(value)
                    except ValueError:
                        raise ValueError(f"Expected integer, got '{value}'")
                
                elif type_hint in ('float', 'decimal', 'double'):
                    try:
                        return float(value)
                    except ValueError:
                        raise ValueError(f"Expected float, got '{value}'")
                
                elif type_hint in ('bool', 'boolean'):
                    if value.lower() in ('true', 'yes', '1', 'on'):
                        return True
                    elif value.lower() in ('false', 'no', '0', 'off'):
                        return False
                    else:
                        raise ValueError(f"Expected boolean, got '{value}'")
                
                elif type_hint in ('str', 'string', 'text'):
                    return str(value)
                
                elif type_hint == 'none':
                    return None
            
            if default is not None and default != "None":
                if default.lower() in ('true', 'false', 'yes', 'no', 'on', 'off'):
                    if value.lower() in ('true', 'yes', '1', 'on'):
                        return True
                    elif value.lower() in ('false', 'no', '0', 'off'):
                        return False
                
                try:
                    int(default)
                    return int(value)
                except ValueError:
                    pass
                
                try:
                    float(default)
                    return float(value)
                except ValueError:
                    pass
            
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
        for i, (arg_name, default, type_hint) in enumerate(args_info):
            if i < len(provided_args):
                try:
                    kwargs[arg_name] = convert_value(provided_args[i], type_hint, default, is_default=False)
                except ValueError as e:
                    error(f"Argument '{arg_name}': {e}")
                    kwargs[arg_name] = None
            elif default is not None:
                if default == "None":
                    kwargs[arg_name] = None
                else:
                    kwargs[arg_name] = convert_value(default, type_hint, default, is_default=True)
            else:
                kwargs[arg_name] = None
        
        return kwargs
    except Exception as e:
        import traceback
        traceback.print_exc()
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

def pick(choices, visible_lines=10):
    target = 0
    scroll_offset = 0
    
    def land():
        nonlocal scroll_offset
        
        if len(choices) <= visible_lines:
            start = 0
            end = len(choices)
            scroll_offset = 0
        else:
            middle = visible_lines // 2
            
            if target < middle:
                start = 0
                end = visible_lines
                scroll_offset = 0
            elif target >= len(choices) - middle:
                start = len(choices) - visible_lines
                end = len(choices)
                scroll_offset = start
            else:
                start = target - middle
                end = target + (visible_lines - middle)
                scroll_offset = start
        
        if scroll_offset > 0:
            tprint(c.Fore.YELLOW + "   ▲ More above..." + c.Fore.RESET)
        
        for i in range(start, end):
            choice = choices[i]
            if i == target:
                tprint(c.Fore.LIGHTCYAN_EX + f"   > {choice}" + c.Fore.RESET)
            else:
                tprint(c.Fore.LIGHTBLACK_EX + f"   > {choice}" + c.Fore.RESET)
        
        if end < len(choices):
            tprint(c.Fore.YELLOW + "   ▼ More below..." + c.Fore.RESET)
        
        tprint(c.Fore.LIGHTBLACK_EX + f"\n   [{target + 1}/{len(choices)}]" + c.Fore.RESET)

    returned = False

    def on_press(key):
        nonlocal target, returned

        if key == keyboard.Key.enter:
            returned = True
            return False

        if key == keyboard.Key.up:
            target = (target - 1) % len(choices)
            redraw_screen()
            land()
        elif key == keyboard.Key.down:
            target = (target + 1) % len(choices)
            redraw_screen()
            land()
        elif key == keyboard.Key.page_up:
            target = max(0, target - visible_lines)
            redraw_screen()
            land()
        elif key == keyboard.Key.page_down:
            target = min(len(choices) - 1, target + visible_lines)
            redraw_screen()
            land()
        elif key == keyboard.Key.home:
            target = 0
            redraw_screen()
            land()
        elif key == keyboard.Key.end:
            target = len(choices) - 1
            redraw_screen()
            land()

    redraw_screen()
    land()

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

    redraw_screen()
    termios.tcflush(sys.stdin, termios.TCIFLUSH)

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

def _input(prompt, multiline=False):
    global in_input
    in_input = True

    redraw_screen()
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
        if multiline:
            print("   " + prompt + c.Fore.YELLOW + " (press Ctrl+D or type 'END' on a new line)" + c.Fore.RESET)
            lines = []
            while True:
                try:
                    line = input()
                    if line.strip() == "END":
                        break
                    lines.append(line)
                except EOFError:
                    break
            result = "\n".join(lines)
            return result
        else:
            result = input("   " + prompt)
            return result
    finally:
        in_input = False
        redraw_screen()


# Loop

def update_thread():
    while True:
        if current_song["is_playing"] and current_song["position"] < current_song["duration"]:
            current_song["position"] += 1
        if in_input:
            update_header()
        else:
            pass
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
                    "input": lambda c, ml=False: _input(c, ml)
                }), **kwargs)
        except Exception as e:
            queued_logs.append(error(f"module err: {e}", True))

    redraw_screen()