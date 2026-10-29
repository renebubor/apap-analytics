
from pathlib import Path


FILE_PATH = Path("data/raw/sd_initial/STR.edf")


def read_text(data):
    return data.decode("latin-1", errors="replace").strip()


def check_limits():
    raw = FILE_PATH.read_bytes()

    signal_count = int(read_text(raw[252:256]))

    # EDF-päise väljade algusaadressid
    offsets = {
        "label": 256,
        "physical_min": 256 + signal_count * (16 + 80 + 8),
        "physical_max": 256 + signal_count * (16 + 80 + 8 + 8),
        "digital_min": 256 + signal_count * (16 + 80 + 8 + 8 + 8),
        "digital_max": 256 + signal_count * (16 + 80 + 8 + 8 + 8 + 8),
    }

    problems = []

    for i in range(signal_count):
        label = read_text(
            raw[offsets["label"] + i * 16:
                offsets["label"] + (i + 1) * 16]
        )

        values = {}

        for field in [
            "physical_min",
            "physical_max",
            "digital_min",
            "digital_max",
        ]:
            start = offsets[field] + i * 8
            values[field] = read_text(raw[start:start + 8])

        try:
            pmin = float(values["physical_min"])
            pmax = float(values["physical_max"])
            dmin = int(values["digital_min"])
            dmax = int(values["digital_max"])

            if pmin >= pmax or dmin >= dmax:
                problems.append((label, values, "Piirväärtuste järjekord"))

        except ValueError:
            problems.append((label, values, "Vigane arvuvorming"))

    print(f"Kontrollitud kanaleid: {signal_count}")
    print(f"Probleemseid kanaleid: {len(problems)}")

    for label, values, reason in problems:
        print(f"\nKanal: {label}")
        print(f"Põhjus: {reason}")

        for field, value in values.items():
            print(f"  {field}: {value!r}")


if __name__ == "__main__":
    check_limits()
