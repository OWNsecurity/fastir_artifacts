import sys


def get_operating_system():
    if sys.platform == 'linux':
        return 'Linux'
    elif sys.platform == 'darwin':
        return 'Darwin'
    elif sys.platform.startswith('win'):
        return 'Windows'

    raise ValueError(f"Unsupported Operating System: '{sys.platform}'")
