# pg.__init__.py
from sqlmodel import SQLModel
import tkinter as tk
from enum import StrEnum

from .utils.visual import clear_screen

from .data.database import engine
from .data.models import *

from .controller.auth import connect
from .view.auth import create_login_screen

__version__ = "3.141"
__author__ = "CUISSET Mattéo"
__email__ = "matteo.cuisset@gmail.com"
__license__ = "MIT"
__project_page__ = "https://github.com/Flyns157/PG"


def init():
    SQLModel.metadata.create_all(engine)

class Mode(StrEnum):
    CONSOLE = "console"
    GUI = "gui"
    TUI = "tui"

def run_app(mode: Mode = Mode.GUI):
    init()
    if mode == Mode.GUI:
        run_gui()
    elif mode == Mode.TUI:
        run_tui()
    else:
        run_console()

def run_gui():
    root = tk.Tk()
    create_login_screen(root)
    root.mainloop()

def run_tui():
    """Run the Textual TUI interface"""
    from .console import PasswordManagerApp
    app = PasswordManagerApp()
    app.run()

def run_console():
    clear_screen()
    print("Bienvenue dans Password Gestion!")
    connect()
