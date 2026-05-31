import json

def load_pivot() -> float:
    try:
        with open("pivot.json", "r") as f:
            data = json.load(f)
            return data.get("last_export_timestamp", 0)
    except FileNotFoundError:
        return 0

def save_pivot(ts: float):
    with open("pivot.json", "w") as f:
        json.dump({"last_export_timestamp": ts}, f)
