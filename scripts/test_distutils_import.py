import os
import sys
from pathlib import Path

# Ensure project root is on PYTHONPATH when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

try:
    from distutils.version import LooseVersion
    print("distutils.version.LooseVersion available:", LooseVersion("1.0") < LooseVersion("2.0"))
except Exception as e:
    import traceback
    print("FAILED to import distutils.version.LooseVersion:", e)
    print(traceback.format_exc())