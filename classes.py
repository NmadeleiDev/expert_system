from __future__ import annotations
from ctypes import Union

class AskerStack():
    padding_unit_len = 2

    def __init__(self, stack: Union[list, None] = None) -> None:
        self.stack = [] if stack is None else stack

    def __len__(self) -> int:
        return len(self.stack)

    def grow(self, val: str) -> AskerStack:
        return AskerStack(self.stack + [val])

    def has(self, val: str) -> bool:
        return val in self.stack

    def to_path(self) -> str:
        return ' -> '.join(self.stack)

    def latest_asker(self) -> Union[str, None]:
        l = len(self.stack)
        if l > 0:
            return self.stack[l - 1]
        else:
            return None