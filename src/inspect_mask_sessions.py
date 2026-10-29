
from pathlib import Path
import struct
from datetime import date, timedelta


SOURCE = Path("data/raw/sd_initial/STR.edf")


def read_text(data):
    return data.decode("latin-1", errors="replace").strip()


def inspect_mask_sessions():
    raw = SOURCE.read_bytes()

    header_size = int(read_text(raw[184:192]))
    record_count = int(read_text(raw[236:244]))
    signal_count = int(read_text(raw[252:256]))

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
            channel[name] = read_text(raw[offset:offset + width])
            offset += width

    record_size = sum(
        int(ch["samples"]) for ch in channels
    ) * 2

    for record_index in range(record_count):
        position = header_size + record_index * record_size
        values = {}

        for channel in channels:
            count = int(channel["samples"])
            byte_count = count * 2

            digital = struct.unpack(
                f"<{count}h",
                raw[position:position + byte_count],
            )

            position += byte_count

            pmin = float(channel["physical_min"])
            pmax = float(channel["physical_max"])
            dmin = float(channel["digital_min"])
            dmax = float(channel["digital_max"])

            scale = (pmax - pmin) / (dmax - dmin)

            physical = [
                pmin + (value - dmin) * scale
                for value in digital
            ]

            if channel["label"] in [
                "Date", "MaskOn", "MaskOff",
                "Duration", "OnDuration", "MaskEvents"
            ]:
                values[channel["label"]] = physical

        day_number = round(values["Date"][0])
        therapy_date = (
            date(1970, 1, 1)
            + timedelta(days=day_number)
        )

        print(f"\nRaviöö: {therapy_date}")
        print("-" * 65)

        for name in [
            "Duration",
            "OnDuration",
            "MaskEvents",
            "MaskOn",
            "MaskOff",
        ]:
            print(f"{name:<15}: {values.get(name)}")


if __name__ == "__main__":
    inspect_mask_sessions()
