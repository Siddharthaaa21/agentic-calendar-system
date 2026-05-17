import json

STORE_FILE = "store.json"


# -------- NORMALIZE --------
def normalize_title(title: str):
    return title.strip().lower()


# -------- LOAD ONCE (cache) --------
_patterns_cache = None


def get_patterns():
    global _patterns_cache

    if _patterns_cache is not None:
        return _patterns_cache

    try:
        with open(STORE_FILE, "r") as f:
            data = json.load(f).get("patterns", {})

            # normalize keys
            _patterns_cache = {
                normalize_title(k): v for k, v in data.items()
            }

            return _patterns_cache

    except Exception:
        _patterns_cache = {}
        return {}


# -------- DECISION 1 --------
def should_cancel_based_on_history(title):
    patterns = get_patterns()
    data = patterns.get(normalize_title(title))

    if not data:
        return False

    rescheduled = data.get("rescheduled", 0)
    count = data.get("count", 1)

    if count == 0:
        return False

    ratio = rescheduled / count

    return ratio > 0.6


# -------- DECISION 2 --------
def is_over_rescheduled(title):
    patterns = get_patterns()
    data = patterns.get(normalize_title(title))

    if not data:
        return False

    return data.get("rescheduled", 0) > 3