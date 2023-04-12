class AddIterableItem:
    def __init__(self, path: list[str | int], value):
        self.path = path
        self.value = value


class DelIterableItem:
    def __init__(self, path: list[str | int]):
        self.path = path


class EditItem:
    def __init__(self, path: list[str | int], new_value, session_id: str, ts: int):
        self.path = path
        self.new_value = new_value
        self.session_id = session_id
        self.ts = ts


class AddDictItem:
    def __init__(self, path: list[str | int], value, session_id: str):
        self.path = path
        self.value = value
        self.session_id = session_id


class DelDictItem:
    def __init__(self, path: list[str | int], session_id: str):
        self.path = path
        self.session_id = session_id
