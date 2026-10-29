
from pathlib import Path
from collections import Counter
import csv
import sys


def inspect_sd(sd_path: Path):
    if not sd_path.is_dir():
        raise FileNotFoundError(f"Kaarti ei leitud: {sd_path}")

    files = []

    for path in sd_path.rglob("*"):
        if path.is_file():
            info = path.stat()

            files.append({
                "relative_path": str(path.relative_to(sd_path)),
                "extension": path.suffix.lower(),
                "size_bytes": info.st_size,
                "modified_timestamp": info.st_mtime,
            })

    output = Path("data/reports/sd_inventory.csv")
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "relative_path",
                "extension",
                "size_bytes",
                "modified_timestamp",
            ],
        )
        writer.writeheader()
        writer.writerows(files)

    extensions = Counter(f["extension"] for f in files)

    print(f"Faile kokku: {len(files)}")
    print(f"Kogumaht: {sum(f['size_bytes'] for f in files) / 1024**2:.2f} MB")
    print("\nFailitüübid:")

    for ext, count in extensions.most_common():
        print(f"  {ext or '(laiendita)'}: {count}")

    print(f"\nInventuur salvestatud: {output}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Kasutus: python src/inspect_sd.py E:\\"
        )

    inspect_sd(Path(sys.argv[1]))
