"""
Data Export functionality for the Adaptive Network Emulator.

Provides CSV and JSON export of performance logs, protocol behavior logs,
and Wireshark-compatible packet trace capture.

Validates: Requirements 10.5, 10.6
"""

import csv
import json
import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Wireshark / PCAP-compatible record
# ─────────────────────────────────────────────

class DataExporter:
    """
    Exports performance and protocol logs to CSV and JSON formats,
    and captures Wireshark-compatible packet traces.

    Features:
    - Export any list of dicts / dataclass instances to CSV or JSON
    - Validate exported files are parseable
    - Capture packet traces in PCAP-like JSON format (readable by analysis tools)
    - All exports timestamped and written to configurable output directory

    Validates: Requirements 10.5, 10.6
    """

    def __init__(self, export_dir: str = "exports"):
        self._export_dir = Path(export_dir)
        self._export_dir.mkdir(parents=True, exist_ok=True)

    # ── JSON export ───────────────────────────────────────────────────────

    def export_json(
        self,
        data: List[Any],
        filename: Optional[str] = None,
        label: str = "export",
    ) -> Path:
        """
        Export a list of records to a JSON file.

        Each record can be a dict or a dataclass instance.

        Validates: Requirement 10.5
        """
        fname = filename or f"{label}_{self._ts()}.json"
        path  = self._export_dir / fname

        serializable = [self._to_dict(r) for r in data]
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(serializable, fh, indent=2, default=str)

        logger.info("JSON export: %s (%d records)", path, len(serializable))
        return path

    def export_jsonl(
        self,
        data: List[Any],
        filename: Optional[str] = None,
        label: str = "export",
    ) -> Path:
        """
        Export records to a JSON Lines file (one JSON object per line).

        Validates: Requirement 10.5
        """
        fname = filename or f"{label}_{self._ts()}.jsonl"
        path  = self._export_dir / fname

        with open(path, "w", encoding="utf-8") as fh:
            for record in data:
                fh.write(json.dumps(self._to_dict(record), default=str) + "\n")

        logger.info("JSONL export: %s (%d records)", path, len(data))
        return path

    # ── CSV export ────────────────────────────────────────────────────────

    def export_csv(
        self,
        data: List[Any],
        filename: Optional[str] = None,
        label: str = "export",
        fieldnames: Optional[List[str]] = None,
    ) -> Path:
        """
        Export a list of records to a CSV file.

        Validates: Requirement 10.5
        """
        if not data:
            fname = filename or f"{label}_{self._ts()}.csv"
            path  = self._export_dir / fname
            path.write_text("", encoding="utf-8")
            return path

        rows  = [self._to_dict(r) for r in data]
        fname = filename or f"{label}_{self._ts()}.csv"
        path  = self._export_dir / fname

        # Flatten nested dicts to dot-notation keys
        flat_rows = [self._flatten(row) for row in rows]
        cols      = fieldnames or list(flat_rows[0].keys())

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(flat_rows)

        logger.info("CSV export: %s (%d rows)", path, len(flat_rows))
        return path

    # ── Packet trace (Wireshark-compatible JSON) ──────────────────────────

    def capture_packet_trace(
        self,
        packets: List[Dict],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save a Wireshark-compatible JSON packet trace.

        Each packet dict should contain at minimum:
            packet_id, timestamp, source, destination,
            protocol, size_bytes, layer, payload (optional)

        The output format matches Wireshark's JSON export schema so it
        can be imported into Wireshark or analysed with tshark/pyshark.

        Validates: Requirement 10.6
        """
        fname = filename or f"packet_trace_{self._ts()}.json"
        path  = self._export_dir / fname

        trace = []
        for i, pkt in enumerate(packets):
            frame_num = i + 1
            ts        = pkt.get("timestamp", time.time())

            # Build Wireshark-compatible frame structure
            ws_pkt = {
                "_index": "packets",
                "_source": {
                    "layers": {
                        "frame": {
                            "frame.number":     str(frame_num),
                            "frame.time":       datetime.fromtimestamp(
                                                    ts, tz=timezone.utc
                                                ).isoformat(),
                            "frame.len":        str(pkt.get("size_bytes", 0)),
                            "frame.protocols":  pkt.get("protocol", "unknown"),
                        },
                        "ip": {
                            "ip.src": pkt.get("source", "0.0.0.0"),
                            "ip.dst": pkt.get("destination", "0.0.0.0"),
                        },
                        pkt.get("protocol", "data").lower(): {
                            "packet_id":   pkt.get("packet_id", ""),
                            "layer":       pkt.get("layer", ""),
                            "sequence":    str(pkt.get("sequence_num", 0)),
                            "payload_len": str(len(pkt.get("payload", ""))),
                        },
                    }
                },
            }
            # Attach any extra fields
            for k, v in pkt.items():
                if k not in ("source", "destination", "protocol",
                             "size_bytes", "timestamp", "packet_id"):
                    ws_pkt["_source"]["layers"]["frame"][f"emulator.{k}"] = str(v)

            trace.append(ws_pkt)

        with open(path, "w", encoding="utf-8") as fh:
            json.dump(trace, fh, indent=2, default=str)

        logger.info("Packet trace: %s (%d packets)", path, len(trace))
        return path

    # ── Validation ────────────────────────────────────────────────────────

    def validate_json(self, path: Path) -> bool:
        """
        Verify a JSON file is valid and parseable.

        Validates: Requirement 10.5
        """
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read().strip()
                if not content:
                    return True   # empty file is technically valid
                json.loads(content)
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            return False

    def validate_jsonl(self, path: Path) -> bool:
        """Verify every line in a JSONL file is valid JSON."""
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        json.loads(line)
            return True
        except (json.JSONDecodeError, FileNotFoundError):
            return False

    def validate_csv(self, path: Path) -> bool:
        """
        Verify a CSV file has a header row and consistent columns.

        Validates: Requirement 10.5
        """
        try:
            with open(path, "r", encoding="utf-8", newline="") as fh:
                reader  = csv.DictReader(fh)
                headers = reader.fieldnames
                if not headers:
                    return False
                for row in reader:
                    if len(row) != len(headers):
                        return False
            return True
        except (csv.Error, FileNotFoundError, StopIteration):
            return False

    def validate_packet_trace(self, path: Path) -> bool:
        """Verify packet trace is valid Wireshark-compatible JSON."""
        if not self.validate_json(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if not isinstance(data, list):
                return False
            for pkt in data:
                if "_source" not in pkt or "layers" not in pkt["_source"]:
                    return False
                if "frame" not in pkt["_source"]["layers"]:
                    return False
            return True
        except Exception:
            return False

    # ── Query ─────────────────────────────────────────────────────────────

    def list_exports(self) -> List[Path]:
        """Return all files in the export directory."""
        return sorted(self._export_dir.iterdir())

    def get_export_dir(self) -> Path:
        return self._export_dir

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _to_dict(obj: Any) -> Dict:
        if isinstance(obj, dict):
            return obj
        try:
            return asdict(obj)
        except TypeError:
            return obj.__dict__ if hasattr(obj, "__dict__") else {"value": str(obj)}

    @staticmethod
    def _flatten(d: Dict, parent_key: str = "", sep: str = ".") -> Dict:
        """Flatten nested dicts to dot-notation for CSV columns."""
        items: Dict = {}
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(DataExporter._flatten(v, new_key, sep))
            else:
                items[new_key] = v
        return items

    @staticmethod
    def _ts() -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
