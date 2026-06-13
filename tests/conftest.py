"""
测试套件 conftest：自动切到 backend 目录并把它加入 sys.path，
确保 `from services.xxx import ...` 和 `from main import ...` 都能用。
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

os.chdir(BACKEND)
for p in (str(ROOT), str(BACKEND)):
    if p not in sys.path:
        sys.path.insert(0, p)
