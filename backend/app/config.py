from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_URL = f"sqlite:///{DATA_DIR / 'mekah.db'}"

WCAG_PENALTY_LAMBDA = 2.0

REWARD_WEIGHTS = {
    "task": 0.4,
    "time": 0.2,
    "error": 0.2,
    "trust": 0.2,
}

HITL_CONFIDENCE_THRESHOLD = 0.60
HITL_TIMEOUT_SECONDS = 30
HITL_REJECT_PENALTY = -0.5

LINUCB_ALPHA = 0.30
