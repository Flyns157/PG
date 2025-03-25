# pg.view.__init__.py
from tkinter import Tk


def init_view(root: Tk):
    root.title("Gestionnaire de mots de passe")
    root.geometry("600x400")

def clear_screen(root: Tk):
    for widget in root.winfo_children():
        widget.destroy()
