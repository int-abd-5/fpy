from __future__ import annotations

import hashlib
from pathlib import Path


class ContentAddressedObjectStore:
    def __init__(self, root: str | Path) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def put(self, content: bytes, *, shared: bool, user_id: str | None) -> tuple[str, Path]:
        digest = hashlib.sha256(content).hexdigest()
        if shared:
            namespace = self._root / "shared"
        else:
            if not user_id:
                raise ValueError("private dataset storage requires a user ID")
            user_namespace = hashlib.sha256(user_id.encode()).hexdigest()[:24]
            namespace = self._root / "users" / user_namespace
        path = namespace / digest[:2] / digest[2:4] / digest
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(content)
        return digest, path
