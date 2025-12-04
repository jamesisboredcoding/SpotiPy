import os
import colorama as c
import sys
import importlib.util as iutil
import shlex

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
        
        kwargs = {}
        for i, (arg_name, default) in enumerate(args_info):
            if i < len(provided_args):
                value = provided_args[i]
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                kwargs[arg_name] = value
            elif default is not None:
                try:
                    kwargs[arg_name] = int(default)
                except ValueError:
                    try:
                        kwargs[arg_name] = float(default)
                    except ValueError:
                        kwargs[arg_name] = default
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

    clear()
    for l in last: tprint(l)
    return target

def upd():
    send([
        f"   Currently playing:\n",
        f"   {ws("Title:", 10)}Music",
        f"   {ws("Artist:", 10)}Eminem",
        f"   {ws("Time:", 10)}{c.Fore.LIGHTCYAN_EX + "—"*20 + c.Fore.LIGHTBLACK_EX + "—"*10 + c.Fore.RESET} 2:45 / 6:52"
    ]); tprint("")

def _login(root):
    module, _ = read_command("sync")
    return module.login(root)

def setg(g, v):
    saved_globals[g] = v

# Loop

queued_logs = []
saved_globals = {}

while True:
    upd()

    for log in queued_logs:
        tprint("   " + str(log))
    if len(queued_logs) > 0: tprint("")

    command = tinput(c.Fore.LIGHTGREEN_EX + "  > " + c.Fore.WHITE)
    module, kwargs = read_command(command)

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
                    "login": lambda root: _login(root),
                    "getg": lambda g: saved_globals.get(g),
                    "setg": lambda g, v: setg(g, v),
                }), **kwargs)
        except Exception as e:
            queued_logs.append(error(f"module err: {e}", True))