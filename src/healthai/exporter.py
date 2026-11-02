"""Local, streaming raw Apple Health conversion; no third-party dependencies."""
from __future__ import annotations

from collections import Counter
from contextlib import ExitStack, contextmanager
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Callable
import xml.etree.ElementTree as ET
import zipfile


TABLES = {
    "Record": "records",
    "Workout": "workouts",
    "ActivitySummary": "activity_summary",
}
PREFERRED_COLUMNS = (
    "type", "unit", "value", "sourceName", "sourceVersion", "device",
    "creationDate", "startDate", "endDate", "workoutActivityType",
    "duration", "durationUnit", "totalDistance", "totalDistanceUnit",
    "totalEnergyBurned", "totalEnergyBurnedUnit", "dateComponents",
)


@contextmanager
def _open_xml(path: Path):
    if path.is_dir():
        direct = path / "export.xml"
        path = direct if direct.is_file() else path / "apple_health_export" / "export.xml"
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            candidates = [
                entry for entry in archive.infolist()
                if not entry.is_dir() and Path(entry.filename).name == "export.xml"
                and not entry.filename.startswith("__MACOSX/")
            ]
            if len(candidates) != 1:
                raise ValueError("ZIP must contain exactly one export.xml")
            # Read the member directly: never extract archive paths to disk.
            with archive.open(candidates[0]) as stream:
                yield stream
    else:
        with path.open("rb") as stream:
            yield stream


class _HashedReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.bytes_read = 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.digest.update(data)
        self.bytes_read += len(data)
        return data


def _elements(reader):
    """Retain at most one top-level element plus the parser's read buffer."""
    depth = 0
    root = None
    for event, element in ET.iterparse(reader, events=("start", "end")):
        if event == "start":
            depth += 1
            if depth == 1:
                root = element
                if root.tag != "HealthData":
                    raise ValueError("Expected an Apple Health <HealthData> document")
        else:
            if depth == 2:
                yield element
                root.remove(element)
                element.clear()
            depth -= 1


def _child(element):
    result = {"tag": element.tag, "attributes": dict(element.attrib)}
    if element.text and element.text.strip():
        result["text"] = element.text
    if len(element):
        result["children"] = [_child(child) for child in element]
    return result


def _row(element):
    row = element.attrib
    if "metadata" in row or "children" in row:
        raise ValueError("XML attribute conflicts with reserved metadata/children output fields")
    if not len(element):
        return row
    row = dict(row)
    metadata = {
        entry.get("key"): entry.get("value")
        for entry in element.iter("MetadataEntry") if entry.get("key") is not None
    }
    if metadata:
        row["metadata"] = metadata
    if len(element):
        # Preserve statistics, route references, events and repeated metadata
        # as structured child elements, alongside the convenient metadata map.
        row["children"] = [_child(child) for child in element]
    return row


def _csv_row(row):
    if "metadata" not in row and "children" not in row:
        return row
    flattened = {key: value for key, value in row.items() if key not in {"metadata", "children"}}
    for key, value in row.get("metadata", {}).items():
        column = f"metadata:{key}"
        if column in flattened:
            raise ValueError(f"XML attribute conflicts with metadata column: {column}")
        flattened[column] = value
    if "children" in row:
        flattened["children"] = json.dumps(row["children"], ensure_ascii=False, separators=(",", ":"))
    return flattened


def _columns(keys):
    return [key for key in PREFERRED_COLUMNS if key in keys] + sorted(set(keys) - set(PREFERRED_COLUMNS))


def convert_export(
    source: str | Path,
    destination: str | Path,
    format: str = "csv",
    progress: Callable[[str], None] | None = None,
) -> dict:
    """Write a complete raw export into a NEW directory, or publish nothing.

    CSV needs two passes to discover all attribute/metadata columns. JSON
    needs one. Memory scales with schema size and the largest XML element,
    not the total record count. No preferences or network APIs are accessed.
    """
    if format not in {"csv", "json", "both"}:
        raise ValueError("format must be csv, json or both")
    source = Path(source).expanduser().absolute()
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Output already exists; choose a new directory: {destination}")
    started = time.perf_counter()
    notify = progress or (lambda message: None)
    counts = Counter({tag: 0 for tag in TABLES})
    unsupported = Counter()
    document_metadata = Counter()
    columns = {tag: set() for tag in TABLES}
    write_csv = format in {"csv", "both"}
    write_json = format in {"json", "both"}
    destination.parent.mkdir(parents=True, exist_ok=True)

    # A private staging directory on the same filesystem allows one atomic
    # directory rename after all parsing, writing and validation succeeds.
    with tempfile.TemporaryDirectory(prefix=".healthai-export-", dir=destination.parent) as temporary:
        stage = Path(temporary) / "result"
        stage.mkdir(mode=0o700)
        notify("Reading XML and discovering columns…" if write_csv else "Converting XML to JSON…")
        with ExitStack() as stack:
            json_files = {}
            if write_json:
                for tag, filename in TABLES.items():
                    handle = stack.enter_context((stage / f"{filename}.json").open("w", encoding="utf-8"))
                    handle.write("[\n")
                    json_files[tag] = handle
            stream = stack.enter_context(_open_xml(source))
            reader = _HashedReader(stream)
            total = 0
            for element in _elements(reader):
                tag = element.tag
                if tag not in TABLES:
                    (document_metadata if tag in {"ExportDate", "Me"} else unsupported)[tag] += 1
                    continue
                if write_csv:
                    columns[tag].update(element.attrib)
                    if len(element):
                        columns[tag].add("children")
                        columns[tag].update(
                            f"metadata:{entry.get('key')}" for entry in element.iter("MetadataEntry")
                            if entry.get("key") is not None
                        )
                if write_json:
                    row = _row(element)
                    if counts[tag]:
                        json_files[tag].write(",\n")
                    json.dump(row, json_files[tag], ensure_ascii=False, separators=(",", ":"))
                counts[tag] += 1
                total += 1
                if total % 50000 == 0:
                    notify(f"Read {total:,} records ({reader.bytes_read / 1_000_000:.1f} MB XML)…")
            for handle in json_files.values():
                handle.write("\n]\n")
            digest = reader.digest.hexdigest()
            xml_bytes = reader.bytes_read

        if not sum(counts.values()):
            raise ValueError("No supported Record, Workout or ActivitySummary elements found")

        if write_csv:
            notify("Writing CSV files…")
            with ExitStack() as stack:
                writers = {}
                for tag, filename in TABLES.items():
                    handle = stack.enter_context((stage / f"{filename}.csv").open("w", encoding="utf-8", newline=""))
                    writer = csv.DictWriter(handle, fieldnames=_columns(columns[tag]) or list(PREFERRED_COLUMNS))
                    writer.writeheader()
                    writers[tag] = writer
                stream = stack.enter_context(_open_xml(source))
                reader = _HashedReader(stream)
                written = Counter({tag: 0 for tag in TABLES})
                total = 0
                for element in _elements(reader):
                    if element.tag in TABLES:
                        writers[element.tag].writerow(_csv_row(_row(element)))
                        written[element.tag] += 1
                        total += 1
                        if total % 50000 == 0:
                            notify(f"Wrote {total:,} CSV rows…")
                if reader.digest.hexdigest() != digest or written != counts:
                    raise ValueError("Input changed during conversion; no output was published. Retry with a stable copy.")

        report = {
            "schema_version": 1,
            "format": format,
            "counts": dict(counts),
            "unsupported_top_level_elements": dict(unsupported),
            "omitted_document_metadata": dict(document_metadata),
            "xml_bytes": xml_bytes,
            "xml_sha256": digest,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "data_policy": "Raw values, units, timestamps and sources preserved; no aggregation or deduplication.",
            "children_policy": "Nested XML elements retained in children; CSV encodes children as JSON. Metadata map uses last value for repeated keys; children retains every entry.",
            "files": sorted(path.name for path in stage.iterdir()),
        }
        (stage / "export_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"Output appeared during conversion; choose a new directory: {destination}")
        stage.rename(destination)
    return report
