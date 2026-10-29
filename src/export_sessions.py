
from pathlib import Path
from datetime import datetime, timedelta
import csv

import pyedflib


RAW_DIR = Path("data/raw/sd_initial/DATALOG")
OUTPUT_FILE = Path("data/processed/sessions.csv")


def read_ascii(data):
    return data.decode("ascii", errors="replace").strip()


def read_session(file_path):
    """Loeb BRP-faili metaandmed ja kontrollib kirjete arvu."""

    raw = file_path.read_bytes()

    header_size = int(read_ascii(raw[184:192]))
    declared_records = int(read_ascii(raw[236:244]))
    record_duration = float(read_ascii(raw[244:252]))
    signal_count = int(read_ascii(raw[252:256]))

    start_date = read_ascii(raw[168:176])
    start_clock = read_ascii(raw[176:184])

    start_time = datetime.strptime(
        f"{start_date} {start_clock}",
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

    record_size = sum(samples) * 2

    if record_size <= 0 or header_size > len(raw):
        raise ValueError("Vigane EDF-faili struktuur")

    data_size = len(raw) - header_size
    actual_records, remainder = divmod(
        data_size, record_size
    )

    if remainder != 0:
        raise ValueError(
            f"Mittetäielik andmekirje: {remainder} baiti"
        )

    if actual_records == 0:
        status = "EMPTY"
        duration_seconds = 0.0

    elif (
        declared_records >= 0
        and declared_records != actual_records
    ):
        raise ValueError(
            "Päise kirjete arv ei vasta tegelikule arvule"
        )

    else:
        status = "VALID"
        duration_seconds = actual_records * record_duration

        # Kontrollime ka pyedflib abil, kui päis seda lubab
        if declared_records >= 0:
            with pyedflib.EdfReader(str(file_path)) as edf:
                duration_seconds = edf.getFileDuration()

    end_time = start_time + timedelta(
        seconds=duration_seconds
    )

    return {
        "source_file": str(file_path.relative_to(RAW_DIR)),
        "start_time": start_time.isoformat(sep=" "),
        "end_time": end_time.isoformat(sep=" "),
        "duration_seconds": duration_seconds,
        "duration_hours": round(duration_seconds / 3600, 4),
        "declared_records": declared_records,
        "actual_records": actual_records,
        "validation_status": status,
    }


def export_sessions():
    files = sorted(RAW_DIR.rglob("*_BRP.edf"))

    sessions = []
    errors = []

    for file_path in files:
        try:
            session = read_session(file_path)
            sessions.append(session)

            print(
                f"{file_path.name}: "
                f"{session['validation_status']} | "
                f"{session['duration_hours']:.2f} h"
            )

        except (OSError, ValueError) as error:
            errors.append((str(file_path), str(error)))
            print(f"INVALID: {file_path.name}: {error}")

            sessions.append({
                "source_file": str(file_path.relative_to(RAW_DIR)),
                "start_time": "",
                "end_time": "",
                "duration_seconds": "",
                "duration_hours": "",
                "declared_records": "",
                "actual_records": "",
                "validation_status": "INVALID",
            })

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    columns = [
        "source_file",
        "start_time",
        "end_time",
        "duration_seconds",
        "duration_hours",
        "declared_records",
        "actual_records",
        "validation_status",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
        )
        writer.writeheader()
        writer.writerows(sessions)

    valid_sessions = [
        s for s in sessions
        if s["validation_status"] == "VALID"
    ]

    total_hours = sum(
        s["duration_seconds"] for s in valid_sessions
    ) / 3600

    print("\n" + "=" * 50)
    print(f"Faile kokku: {len(files)}")
    print(f"VALID: {len(valid_sessions)}")
    print(
        f"EMPTY: "
        f"{sum(s['validation_status'] == 'EMPTY' for s in sessions)}"
    )
    print(f"INVALID: {len(errors)}")
    print(f"BRP kogukestus: {total_hours:.2f} tundi")
    print(f"Salvestatud: {OUTPUT_FILE}")


if __name__ == "__main__":
    export_sessions()
