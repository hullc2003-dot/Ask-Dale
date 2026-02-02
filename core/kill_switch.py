# core/kill_switch.py
def is_system_enabled(db) -> bool:
    # db: handle/adapter, not raw client
    row = db.get_flag("system_enabled")
    return bool(row.value) if row else False
