# pg.__main__.py
from pg import run_app, Mode
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Password Gestion")
    parser.add_argument("-m", "--mode", choices=["console", "gui", "tui"], default="gui", help="Mode d'exécution (console, gui, ou tui)")
    args = parser.parse_args()

    run_app(Mode(args.mode))
