
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import argparse
import csv
import hashlib


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_RAW_DIR = (
    PROJECT_DIR / "data" / "raw" / "sd_archive" / "DATALOG"
)

DEFAULT_OUTPUT = (
    PROJECT_DIR / "data" / "pipeline_test" / "events.csv"
)


def read_ascii(data):
    return data.decode("ascii", errors="replace").strip()


def parse_annotations(data):
    """Loeb EDF+ annotatsioonikanali andmed."""
    events = []

    for segment in data.split(b"\x00"):
        if not segment:
            continue

        text = segment.decode("latin-1", errors="replace")
        parts = text.split("\x14")

        timing = parts[0]
        descriptions = [p for p in parts[1:] if p.strip()]

        if not descriptions:
            continue

        if "\x15" in timing:
            onset, duration = timing.split("\x15", 1)
        else:
            onset, duration = timing, ""

        try:
            onset_seconds = float(onset)
            duration_seconds = (
                float(duration) if duration else None
            )
        except ValueError:
            continue

        for description in descriptions:
            events.append({
                "onset_seconds": onset_seconds,
                "duration_seconds": duration_seconds,
                "event_type": description.strip(),
            })

    return events


def read_eve_file(file_path, raw_dir):
    """Loeb ühe ResMedi EVE-faili sündmused."""
    raw = file_path.read_bytes()

    header_size = int(read_ascii(raw[184:192]))
    record_count = int(read_ascii(raw[236:244]))
    signal_count = int(read_ascii(raw[252:256]))

    start_date = read_ascii(raw[168:176])
    start_time = read_ascii(raw[176:184])

    start_dt = datetime.strptime(
        f"{start_date} {start_time}",
        "%d.%m.%y %H.%M.%S",
    )

    labels = [
        read_ascii(raw[256 + i * 16:256 + (i + 1) * 16])
        for i in range(signal_count)
    ]

    samples_offset = 256 + signal_count * 216

    samples = [
        int(read_ascii(raw[
            samples_offset + i * 8:
            samples_offset + (i + 1) * 8
        ]))
        for i in range(signal_count)
    ]

    if "EDF Annotations" not in labels:
        raise ValueError("Annotatsioonikanalit ei leitud")

    annotation_index = labels.index("EDF Annotations")

    record_size = sum(samples) * 2
    annotation_start = sum(samples[:annotation_index]) * 2
    annotation_size = samples[annotation_index] * 2

    if record_count < 0:
        raise ValueError("Negatiivne kirjete arv")

    expected_size = header_size + record_count * record_size

    if len(raw) < expected_size:
        raise ValueError("EDF-fail on oodatust lühem")

    events = []
    relative_path = file_path.relative_to(raw_dir).as_posix()

    for record_index in range(record_count):
        record_start = header_size + record_index * record_size

        start = record_start + annotation_start
        end = start + annotation_size

        annotations = parse_annotations(raw[start:end])

        for annotation in annotations:
            event_type = annotation["event_type"]

            if event_type.lower() == "recording starts":
                continue

            event_time = start_dt + timedelta(
                seconds=annotation["onset_seconds"]
            )

            identity = (
                f"{relative_path}|"
                f"{annotation['onset_seconds']}|"
                f"{annotation['duration_seconds']}|"
                f"{event_type}"
            )

            event_id = hashlib.sha256(
                identity.encode("utf-8")
            ).hexdigest()[:24]

            events.append({
                "event_id": event_id,
                "source_file": relative_path,
                "file_start_time": start_dt.isoformat(sep=" "),
                "onset_seconds": annotation["onset_seconds"],
                "event_time": event_time.isoformat(sep=" "),
                "event_type": event_type,
                "duration_seconds": annotation["duration_seconds"],
            })

    return events


def export_events(raw_dir, output_file):
    """Koondab EVE-failide sündmused CSV-tabeliks."""
    raw_dir = Path(raw_dir).resolve()
    output_file = Path(output_file).resolve()

    if not raw_dir.is_dir():
        raise FileNotFoundError(
            f"Lähtekausta ei leitud: {raw_dir}"
        )

    files = sorted(raw_dir.rglob("*_EVE.edf"))

    if not files:
        raise FileNotFoundError(
            f"EVE-faile ei leitud: {raw_dir}"
        )

    all_events = []
    errors = []

    for file_path in files:
        try:
            events = read_eve_file(file_path, raw_dir)
            all_events.extend(events)

            print(
                f"{file_path.name}: "
                f"{len(events)} sündmust"
            )

        except (OSError, ValueError, UnicodeError) as error:
            errors.append((str(file_path), str(error)))
            print(f"VIGA: {file_path.name}: {error}")

    unique_events = {
        event["event_id"]: event
        for event in all_events
    }

    rows = sorted(
        unique_events.values(),
        key=lambda x: (x["event_time"], x["event_id"]),
    )

    columns = [
        "event_id",
        "source_file",
        "file_start_time",
        "onset_seconds",
        "event_time",
        "event_type",
        "duration_seconds",
    ]

    # Vigaste failide korral ei kirjuta varasemat
    # korrektset eksporti üle.
    if errors:
        print("\nVigaseid faile:", len(errors))
        print("CSV eksporti ei uuendatud.")
        return False

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + "=" * 55)
    print(f"Töödeldud faile: {len(files)}")
    print(f"Unikaalseid sündmusi: {len(rows)}")
    print(f"Salvestatud: {output_file}")

    counts = Counter(
        event["event_type"] for event in rows
    )

    print("\nSündmuste jaotus:")
    for event_type, count in counts.most_common():
        print(f"  {event_type}: {count}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ResMedi EVE sündmuste eksport"
    )

    parser.add_argument(
        "--raw",
        default=str(DEFAULT_RAW_DIR),
        help="EVE-failide lähtekaust",
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Väljundi CSV-fail",
    )

    args = parser.parse_args()

    success = export_events(args.raw, args.output)

    if not success:
        raise SystemExit(1)
