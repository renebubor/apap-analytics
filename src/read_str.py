
from pathlib import Path
from tempfile import TemporaryDirectory

import pyedflib


SOURCE_FILE = Path("data/raw/sd_initial/STR.edf")


def create_compatible_copy(source, destination):
    """Asendab EDF-päise UTF-8 mõõtühikud ASCII-ga."""

    raw = bytearray(source.read_bytes())

    signal_count = int(
        raw[252:256].decode("ascii").strip()
    )

    # EDF mõõtühikute välja algus
    dimension_offset = 256 + signal_count * (16 + 80)

    replacements = 0

    for i in range(signal_count):
        start = dimension_offset + i * 8
        end = start + 8

        original = bytes(raw[start:end])

        if b"\xc2\xb0C" in original:
            updated = original.replace(
                b"\xc2\xb0C", b"degC"
            )

            raw[start:end] = updated.ljust(8, b" ")
            replacements += 1

    destination.write_bytes(raw)

    return replacements


def read_str():
    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(SOURCE_FILE)

    with TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / "STR_compatible.edf"

        replacements = create_compatible_copy(
            SOURCE_FILE,
            temp_file,
        )

        print(f"Parandatud mõõtühikuid: {replacements}")

        with pyedflib.EdfReader(str(temp_file)) as edf:
            print(f"Algusaeg: {edf.getStartdatetime()}")
            print(f"Kirje kestus: {edf.getFileDuration()} s")
            print(f"Kanaleid: {edf.signals_in_file}")

            labels = edf.getSignalLabels()

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

            print("\nValitud kanalite väärtused:")
            print("-" * 75)

            for label in selected:
                if label not in labels:
                    continue

                index = labels.index(label)
                values = edf.readSignal(index)

                print(f"\n{label}:")
                print(values)


if __name__ == "__main__":
    read_str()
