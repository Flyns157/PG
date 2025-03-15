pip install -r requirements.txt
pip install -U pyinstaller
pyinstaller --hidden-import=cryptography --icon utils\Icon.ico main.py
