# Run fast tests (default)
& 'C:/Users/mairfani/AppData/Local/Microsoft/WindowsApps/python3.10.exe' -m pytest -q -k "not slow"

# Run slow/integration tests:
# & 'C:/Users/mairfani/AppData/Local/Microsoft/WindowsApps/python3.10.exe' -m pytest -q -m slow
