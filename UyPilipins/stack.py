#  Exceptions


class StackError(Exception):
    pass

#  Generic LIFO Stack

class Stack:
    def __init__(self):
        self._items: list = []

    # ── Mutating operations ───────────────────

    def push(self, item) -> None:
        self._items.append(item)

    def pop(self):
        if self.is_empty():
            raise StackError("Stack underflow: pop() called on an empty stack.")
        return self._items.pop()

    # ── Non-mutating operations ───────────────

    def peek(self):
        if self.is_empty():
            raise StackError("Stack is empty: peek() has nothing to return.")
        return self._items[-1]

    def is_empty(self) -> bool:
        return len(self._items) == 0

    def size(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()

    def to_list(self) -> list:
        return list(self._items)

    # ── Dunder helpers ────────────────────────

    def __len__(self):
        return len(self._items)

    def __bool__(self):
        return not self.is_empty()

    def __iter__(self):
        return reversed(self._items)

    def __repr__(self):
        if self.is_empty():
            return "Stack([])"
        items_str = ", ".join(repr(i) for i in reversed(self._items))
        return f"Stack([top → {items_str}])"

#  Activation Record

class ActivationRecord:
    def __init__(self, name: str, level: int):
        self.name    = name
        self.level   = level
        self.members: dict[str, int | None] = {}

    # ── Dict-like access ──────────────────────

    def __setitem__(self, name: str, value):
        self.members[name] = value

    def __getitem__(self, name: str):
        return self.members[name]

    def __contains__(self, name: str) -> bool:
        return name in self.members

    def get(self, name: str, default=None):
        return self.members.get(name, default)

    def is_declared(self, name: str) -> bool:
        return name in self.members

    def is_initialized(self, name: str) -> bool:
        return self.members.get(name) is not None

    # ── Representation ────────────────────────

    def __repr__(self):
        header = (f"\n{'='*46}\n"
                  f" ACTIVATION RECORD : {self.name!r} (scope level {self.level})\n"
                  f"{'='*46}")
        if not self.members:
            return header + "\n  (empty frame)\n"
        rows = "\n".join(
            f"  {k:<20} = {v!r}" for k, v in self.members.items()
        )
        return header + "\n" + rows + "\n"

#  Call Stack

class CallStack:
    def __init__(self):
        self._stack: Stack = Stack()

    # ── Stack operations ──────────────────────

    def push(self, record: ActivationRecord) -> None:
        self._stack.push(record)

    def pop(self) -> ActivationRecord:
        return self._stack.pop()

    def peek(self) -> ActivationRecord:
        return self._stack.peek()

    def is_empty(self) -> bool:
        return self._stack.is_empty()

    def depth(self) -> int:
        return self._stack.size()

    # ── Variable lookup across scopes ────────

    def lookup(self, name: str):
        for record in self._stack:        # iterates top → bottom
            if name in record:
                return record, record[name]
        return None, None

    # ── Representation ────────────────────────

    def __repr__(self):
        if self.is_empty():
            return "CallStack(empty)"
        lines = [f"CallStack (depth={self.depth()}):"]
        for record in self._stack:        # top → bottom
            lines.append(repr(record))
        return "\n".join(lines)
