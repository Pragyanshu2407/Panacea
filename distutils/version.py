from packaging.version import Version


class LooseVersion:
    def __init__(self, v):
        self.v = Version(str(v))

    def __str__(self):
        return str(self.v)

    def _coerce(self, other):
        return other.v if isinstance(other, LooseVersion) else Version(str(other))

    def __lt__(self, other):
        return self.v < self._coerce(other)

    def __le__(self, other):
        return self.v <= self._coerce(other)

    def __eq__(self, other):
        return self.v == self._coerce(other)

    def __ne__(self, other):
        return self.v != self._coerce(other)

    def __gt__(self, other):
        return self.v > self._coerce(other)

    def __ge__(self, other):
        return self.v >= self._coerce(other)