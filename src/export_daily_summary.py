
from pathlib import Path
from datetime import date, timedelta
import argparse
import struct
import csv


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_SOURCE = (
    PROJECT_DIR / "data" / "raw" / "sd_archive" / "STR.edf"
)

DEFAULT_OUTPUT = (
    PROJECT_DIR / "data" / "pipeline_test" / "daily_summary.csv"
)


def read_text(data):
    return data.decode("latin-1", errors="replace").strip()


def read_str(source):
    """Loeb ResMedi STR.edf faili kõik päevakirjed."""

    source = Path(source).resolve()
    raw = source.read_bytes()

    if len(raw) < 256:
        raise ValueError("STR-fail on liiga lühike")

    header_size = int(read_text(raw[184:192]))
    record_count = int(read_text(raw[236:244]))
    signal_count = int(read_text(raw[252:256]))

    if record_count < 0:
        raise ValueError("STR kirjete arv on negatiivne")

    if signal_count <= 0:
        raise ValueError("STR kanalite arv ei ole korrektne")

    if header_size != 256 + signal_count * 256:
        raise ValueError("STR päise suurus ei vasta kanalitele")

    fields = [
        ("label", 16),
        ("transducer", 80),
        ("dimension", 8),
        ("physical_min", 8),
        ("physical_max", 8),
        ("digital_min", 8),
        ("digital_max", 8),
        ("prefilter", 80),
        ("samples", 8),
        ("reserved", 32),
    ]

    channels = [{} for _ in range(signal_count)]
    offset = 256

    for name, width in fields:
        for channel in channels:
            channel[name] = read_text(
                raw[offset:offset + width]
            )
            offset += width

    record_size = sum(
        int(ch["samples"]) for ch in channels
    ) * 2

    expected_size = header_size + record_count * record_size

    if len(raw) != expected_size:
        raise ValueError(
            f"STR-faili suurus ei vasta päisele: "
            f"tegelik {len(raw)}, oodatud {expected_size}"
        )

    records = []

    for record_index in range(record_count):
        position = header_size + record_index * record_size
        values = {}

        for channel in channels:
            count = int(channel["samples"])
            byte_count = count * 2

            digital_values = struct.unpack(
                f"<{count}h",
                raw[position:position + byte_count],
            )

            position += byte_count

            pmin = float(channel["physical_min"])
            pmax = float(channel["physical_max"])
            dmin = float(channel["digital_min"])
            dmax = float(channel["digital_max"])

            if dmax == dmin:
                raise ValueError(
                    f"Vigane digitaalne vahemik: "
                    f"{channel['label']}"
                )

            scale = (pmax - pmin) / (dmax - dmin)

            physical_values = [
                pmin + (value - dmin) * scale
                for value in digital_values
            ]

            values[channel["label"]] = physical_values

        records.append(values)

    return records


def export_daily_summary(source, output):
    """Ekspordib STR päevakokkuvõtted CSV-faili."""

    source = Path(source).resolve()
    output = Path(output).resolve()

    records = read_str(source)
    rows = []

    for record in records:
        day_number = round(record["Date"][0])

        therapy_date = (
            date(1970, 1, 1)
            + timedelta(days=day_number)
        )

        def get_value(name):
            values = record.get(name)

            if not values:
                return None

            value = round(values[0], 4)

            # Negatiivsed kestused, indeksid, rõhud
            # ja lekked ei ole kehtivad mõõtmised.
            if value < 0:
                return None

            return value

        leak_p95 = get_value("Leak.95")

        rows.append({
            "therapy_date": therapy_date.isoformat(),
            "usage_minutes": get_value("Duration"),
            "on_duration_minutes": get_value("OnDuration"),
            "ahi": get_value("AHI"),
            "ai": get_value("AI"),
            "hi": get_value("HI"),
            "oai": get_value("OAI"),
            "cai": get_value("CAI"),
            "uai": get_value("UAI"),
            "pressure_p95": get_value("MaskPress.95"),
            "leak_p95_l_min": (
                round(leak_p95 * 60, 2)
                if leak_p95 is not None else None
            ),
            "source_file": source.name,
        })

    if not rows:
        raise ValueError("STR-failis puuduvad päevakirjed")

    dates = [row["therapy_date"] for row in rows]

    if len(dates) != len(set(dates)):
        raise ValueError("STR sisaldab korduvaid ravikuupäevi")

    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=rows[0].keys(),
        )
        writer.writeheader()
        writer.writerows(rows)

    print("\nSTR päevakokkuvõtete eksport")
    print("-" * 65)
    print(f"Salvestatud: {output}")
    print(f"Päevi: {len(rows)}")

    def format_value(value, decimals=1):
        if value is None:
            return "N/A"
        return f"{value:.{decimals}f}"

    for row in rows:
        print(
            f"{row['therapy_date']} | "
            f"Kasutus: {format_value(row['usage_minutes'], 0)} min | "
            f"AHI: {format_value(row['ahi'])} | "
            f"Leke P95: "
            f"{format_value(row['leak_p95_l_min'])} L/min"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="STR päevakokkuvõtete eksport"
    )

    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )

    args = parser.parse_args()

    export_daily_summary(args.source, args.output)
