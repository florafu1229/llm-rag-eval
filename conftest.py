import os
import sys
from pathlib import Path

# Ensure the project root is importable so `from src.agent import ...` works.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# --- Windows console fix -------------------------------------------------- #
# DeepEval's rich console prints emoji; the legacy Windows cp1252 console
# cannot encode them and raises UnicodeEncodeError. Force UTF-8 output.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

# --- DeepEval runtime tuning ---------------------------------------------- #
# Local CPU models are slow; give each metric task plenty of time so the
# async gather does not time out, and opt out of anonymous telemetry.
os.environ.setdefault("DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE", "1200")
os.environ.setdefault("DEEPEVAL_TASK_GATHER_BUFFER_SECONDS_OVERRIDE", "600")
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
