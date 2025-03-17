pip install -r requirements.txt
pip install -U pyinstaller
pyinstaller --onefile --name "PGApp" --icon=pg/utils/Icon.ico pg/__main__.py
