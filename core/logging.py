import time


def log_event(db, event: str, payload: dict):
    db.insert_log(
        {
            "timestamp": int(time.time()),
            "event": event,
            "payload": payload,
        }
    )

