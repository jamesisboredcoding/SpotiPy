import colorama as c
from pathlib import Path

title = "help"
alias = ["h"]
description = "shows a list of all commands"

def main(root):
    out = lambda x: root.print(c.Fore.LIGHTBLUE_EX + x + c.Fore.RESET)
    
    folder = Path("./commands")
    files = list(folder.glob("*.py"))

    for file_path in files:
        module = root.read_command(file_path.name.replace(".py", ""))
        if not module == None:
            out(module.title + f"{ f" ({", ".join(module.alias)})" if hasattr(module, "alias") else "" }" + " - " + module.description)