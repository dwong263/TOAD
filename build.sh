pyinstaller --windowed --name="TOAD" --icon="frog.icns" --add-data="main.ui:." --add-data="dialog.ui:." --target-arch='universal2' main.py