#!/usr/bin/env python3
"""PyInstaller entry point for the AMG65 local backend."""
import os
import sys

ROOT = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'panel'))
sys.path.insert(0, os.path.join(ROOT, 'tool'))

from server import main  # noqa: E402

if __name__ == '__main__':
    main()
