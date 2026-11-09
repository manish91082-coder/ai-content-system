from __future__ import annotations

import hashlib
import json
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
    """Append-only JSONL hash chain for local demonstration and auditability."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: dict) -> Receipt:
        previous_hash = "0" * 64
        sequence = 1
        if self.path.exists() and self.path.stat().st_size:
            rows = [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]
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
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        receipt = Receipt(sequence, timestamp, event, previous_hash, digest)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(receipt), sort_keys=True) + "\n")
        return receipt
