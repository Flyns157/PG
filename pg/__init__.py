# pg.__init__.py
from sqlmodel import SQLModel
import tkinter as tk
from enum import StrEnum

from .utils.visual import clear_screen

from .data.database import engine
from .data.models import *

from .controller.auth import connect
from .view.auth import create_login_screen


def init():
    SQLModel.metadata.create_all(engine)

class Mode(StrEnum):
    CONSOLE = "console"
    GUI = "gui"

def run_app(mode: Mode = Mode.GUI):
    init()
    if mode == Mode.GUI:
        run_gui()
    else:
        run_console()

def run_gui():
    root = tk.Tk()
    create_login_screen(root)
    root.mainloop()

def run_console():
    clear_screen()
    print("Bienvenue dans Password Gestion!")
    connect()
