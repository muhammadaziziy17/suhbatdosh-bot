"""Botni qulay ishga tushirish fayli."""
import os
import sys
import subprocess

# Agar joriy Python muhitida aiogram topilmasa va loyiha ichida venv mavjud bo'lsa,
# avtomatik ravishda venv ichidagi Python orqali ishga tushirish
try:
    import aiogram
except ImportError:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python_win = os.path.join(base_dir, "venv", "Scripts", "python.exe")
    venv_python_nix = os.path.join(base_dir, "venv", "bin", "python")
    target_python = venv_python_win if os.path.exists(venv_python_win) else (
        venv_python_nix if os.path.exists(venv_python_nix) else None
    )
    if target_python and os.path.abspath(sys.executable) != os.path.abspath(target_python):
        sys.exit(subprocess.call([target_python] + sys.argv))

import asyncio
from src.main import main

if __name__ == "__main__":
    asyncio.run(main())
