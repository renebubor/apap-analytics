
from pathlib import Path
from datetime import datetime, timedelta
import sys


def read_ascii(data):
    return data.decode("ascii", errors="replace").strip()


def parse_annotation(data):
    """Teisendab EDF+ annotatsiooni struktureeritud andmeteks."""

    text = data.decode("latin-1", errors="replace")
    parts = text.split("\x14")

    timing = parts[0]
    descriptions = [p for p in parts[1:] if p.strip()]

    if not descriptions:
        return []

    if "\x15" in timing:
        onset, duration = timing.split("\x15", 1)
    else:
        onset, duration = timing, ""

    try:
        onset_seconds = float(onset)
        duration_seconds = float(duration) if duration else None
    except ValueError:
        return []

    return [
        {
            "onset_seconds": onset_seconds,
            "duration_seconds": duration_seconds,
            "description": description,
        }
        for description in descriptions
    ]


def inspect_eve(file_path: Path):
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

    samples_offset = 256 + signal_count * 216

    samples = [
        int(read_ascii(raw[
            samples_offset + i * 8:
            samples_offset + (i + 1) * 8
        ]))
        for i in range(signal_count)
    ]

    annotation_bytes = samples[0] * 2
    record_bytes = sum(samples) * 2

    events = []

    for record_index in range(record_count):
        start = header_size + record_index * record_bytes

        annotation_data = raw[
            start:start + annotation_bytes
        ]

        for segment in annotation_data.split(b"\x00"):
            if not segment.strip():
                continue

            events.extend(parse_annotation(segment))

    print(f"\nFail: {file_path.name}")
    print(f"Algusaeg: {start_dt}")
    print(f"Andmekirjeid: {record_count}")
    print(f"Sündmusi: {len(events)}")

    print("\nSündmused:")
    print("-" * 85)

    for event in events[:30]:
        event_time = start_dt + timedelta(
            seconds=event["onset_seconds"]
        )

        duration = event["duration_seconds"]

        print(
            f"{event_time} | "
            f"Kestus: {duration if duration is not None else '-'} s | "
            f"{event['description']}"
        )

    if len(events) > 30:
        print(f"\nKuvatud esimesed 30 sündmust {len(events)}-st.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Kasutus: python src/inspect_eve.py <failitee>"
        )

    inspect_eve(Path(sys.argv[1]))
