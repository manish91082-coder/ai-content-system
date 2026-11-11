from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Receipt:
    sequence: int
    timestamp: str
    event: dict
    previous_hash: str
    receipt_hash: str


class ReceiptLog:
    """Append-only JSONL hash chain for a single-process local prototype."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    @staticmethod
    def _digest(body: dict) -> str:
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def verify(self) -> bool:
        with self._lock:
            if not self.path.exists():
                return True
            previous_hash = "0" * 64
            expected_sequence = 1
            try:
                for line in self.path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        return False
                    row = json.loads(line)
                    body = {
                        "sequence": row["sequence"],
                        "timestamp": row["timestamp"],
                        "event": row["event"],
                        "previous_hash": row["previous_hash"],
                    }
                    digest = self._digest(body)
                    if row["sequence"] != expected_sequence:
                        return False
                    if row["previous_hash"] != previous_hash or row["receipt_hash"] != digest:
                        return False
                    previous_hash = digest
                    expected_sequence += 1
                return True
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
                return False

    def events(self) -> list[tuple[str, dict]]:
        """Return verified timestamp/event pairs; corrupted history is never trusted."""
        with self._lock:
            if not self.verify():
                raise RuntimeError("receipt log integrity failure; history refused")
            if not self.path.exists():
                return []
            rows = [
                json.loads(line)
                for line in self.path.read_text(encoding="utf-8").splitlines()
            ]
            return [(row["timestamp"], row["event"]) for row in rows]

    def append(self, event: dict) -> Receipt:
        with self._lock:
            if not self.verify():
                raise RuntimeError("receipt log integrity failure; append refused")
            previous_hash = "0" * 64
            sequence = 1
            if self.path.exists() and self.path.stat().st_size:
                rows = [
                    json.loads(line)
                    for line in self.path.read_text(encoding="utf-8").splitlines()
                ]
                last = rows[-1]
                previous_hash = last["receipt_hash"]
                sequence = last["sequence"] + 1

            timestamp = datetime.now(timezone.utc).isoformat()
            body = {
                "sequence": sequence,
                "timestamp": timestamp,
                "event": event,
                "previous_hash": previous_hash,
            }
            digest = self._digest(body)
            receipt = Receipt(sequence, timestamp, event, previous_hash, digest)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(asdict(receipt), sort_keys=True) + "\n")
                handle.flush()
            return receipt
