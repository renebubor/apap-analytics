
from pathlib import Path
import sys


def inspect_header(file_path: Path):
    """Loeb EDF-faili fikseeritud päiseväljad binaarkujul."""

    with file_path.open("rb") as f:
        header = f.read(256)

    fields = {
        "Version": header[0:8],
        "Start date": header[168:176],
        "Start time": header[176:184],
        "Header bytes": header[184:192],
        "Reserved": header[192:236],
        "Data records": header[236:244],
        "Record duration": header[244:252],
        "Signals": header[252:256],
    }

    print(f"\nFail: {file_path.name}")
    print("-" * 60)

    for name, value in fields.items():
        print(
            f"{name:18}: "
            f"{value.decode('ascii', errors='replace').strip()}"
        )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Kasutus: python src/inspect_edf_header.py <failitee>"
        )

    inspect_header(Path(sys.argv[1]))
