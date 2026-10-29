
from pathlib import Path
from datetime import datetime, timedelta
import struct


SOURCE = Path("data/raw/sd_initial/STR.edf")


def field_text(data):
    return data.decode("latin-1", errors="replace").strip()


def read_str():
    raw = SOURCE.read_bytes()

    header_size = int(field_text(raw[184:192]))
    record_count = int(field_text(raw[236:244]))
    signal_count = int(field_text(raw[252:256]))

    start_dt = datetime.strptime(
        field_text(raw[168:184]),
        "%d.%m.%y%H.%M.%S",
    )

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
            channel[name] = field_text(
                raw[offset:offset + width]
            )
            offset += width

    record_size = sum(
        int(ch["samples"]) for ch in channels
    ) * 2

    expected_size = header_size + record_count * record_size

    if len(raw) != expected_size:
        raise ValueError(
            f"Faili suurus ei klapi: "
            f"{len(raw)} != {expected_size}"
        )

    selected = [
        "Date",
        "Duration",
        "OnDuration",
        "AHI",
        "AI",
        "HI",
        "OAI",
        "CAI",
        "UAI",
        "Leak.95",
        "MaskPress.95",
    ]

    print(f"\nSTR-faili päevakirjeid: {record_count}")
    print("-" * 85)

    for record_index in range(record_count):
        record_start = header_size + record_index * record_size
        position = record_start

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

            scale = (pmax - pmin) / (dmax - dmin)

            physical_values = [
                pmin + (value - dmin) * scale
                for value in digital_values
            ]

            if channel["label"] in selected:
                values[channel["label"]] = physical_values

        record_date = start_dt + timedelta(
            days=record_index
        )

        print(f"\nPäev {record_index + 1}: {record_date.date()}")

        for name in selected:
            if name in values:
                print(f"  {name:<15}: {values[name]}")


if __name__ == "__main__":
    read_str()
