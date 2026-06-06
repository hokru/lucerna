from .utils import helper


class MyClass:
    def __init__(self, val: int):
        self.val = val

    def do_work(self) -> str:
        return helper(self.val)
