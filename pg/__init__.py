# pg.__init__.py
from sqlmodel import SQLModel

from .utils.visual import clear_screen

from .data.database import engine
from .data.models import *

from .controller.auth import connect


def init():
    clear_screen()
    print("Bienvenue dans Password Gestion!")
    SQLModel.metadata.create_all(engine)

def run_app():
    init()
    connect()