
from pathlib import Path


FILE_PATH = Path("data/raw/sd_initial/STR.edf")


def read_text(data):
    return data.decode("latin-1", errors="replace").strip()


def inspect_str():
    raw = FILE_PATH.read_bytes()

    header_size = int(read_text(raw[184:192]))
    record_count = int(read_text(raw[236:244]))
    record_duration = read_text(raw[244:252])
    signal_count = int(read_text(raw[252:256]))

    print(f"\nFail: {FILE_PATH.name}")
    print(f"Faili suurus: {len(raw)} baiti")
    print(f"Päise suurus: {header_size}")
    print(f"Andmekirjeid: {record_count}")
    print(f"Kirje kestus: {record_duration}")
    print(f"Kanaleid: {signal_count}")

    # EDF päises on iga kanali omadused
    # salvestatud väljade kaupa.
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

    for field_name, field_width in fields:
        for channel in channels:
            value = raw[offset:offset + field_width]
            channel[field_name] = read_text(value)
            offset += field_width

    print("\nKanalite nimekiri:")
    print("-" * 80)

    for i, channel in enumerate(channels, start=1):
        print(
            f"{i:2}. "
            f"{channel['label']:<25} "
            f"Ühik: {channel['dimension']:<10} "
            f"Näite/kirje: {channel['samples']}"
        )
        print("\nMõõtühikute toorväärtused:")
    print("-" * 80)

    for i, channel in enumerate(channels, start=1):
        dimension = channel["dimension"]

        if any(ord(char) > 127 for char in dimension):
            print(
                f"{i:2}. {channel['label']:<25} "
                f"Ühik: {dimension!r}"
            )
        print("\nTemperatuurikanalite ühikute baidid:")

    dimension_offset = 256 + signal_count * (16 + 80)

    for i, channel in enumerate(channels):
        if "Temp" in channel["label"]:
            start = dimension_offset + i * 8
            dimension_bytes = raw[start:start + 8]

            print(
                f"{channel['label']:<25} "
                f"{dimension_bytes!r} "
                f"HEX: {dimension_bytes.hex(' ')}"
            )


if __name__ == "__main__":
    inspect_str()
