class KillSwitch:
    def __init__(self, db):
        self.db = db

    def is_enabled(self) -> bool:
        flag = self.db.get_flag("system_enabled")
        if flag is None:
            return True
        return bool(flag)
