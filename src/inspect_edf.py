
from pathlib import Path
import sys

import pyedflib


def inspect_signals(edf):
    """Kuvab EDF-faili mõõtekanalite metaandmed."""

    print("\nMõõtekanalid:")
    print("-" * 75)

    for i in range(edf.signals_in_file):
        header = edf.getSignalHeader(i)

        print(f"\nKanal {i + 1}: {header['label']}")
        print(f"  Ühik: {header['dimension']}")
        print(f"  Sagedus: {edf.getSampleFrequency(i)} Hz")
        print(f"  Mõõtepunkte: {edf.getNSamples()[i]}")
        print(
            f"  Füüsiline vahemik: "
            f"{header['physical_min']} ... "
            f"{header['physical_max']}"
        )


def inspect_annotations(edf, limit=20):
    """Loeb ja kuvab EDF+ annotatsioonid."""

    onsets, durations, descriptions = edf.readAnnotations()

    print("\nAnnotatsioonid:")
    print("-" * 75)
    print(f"Annotatsioone kokku: {len(onsets)}")

    for onset, duration, description in zip(
        onsets[:limit],
        durations[:limit],
        descriptions[:limit],
    ):
        print(
            f"Aeg: {onset:.1f} s | "
            f"Kestus: {duration:.1f} s | "
            f"Sündmus: {description}"
        )

    if len(onsets) > limit:
        print(f"\nKuvatud esimesed {limit} annotatsiooni.")


def inspect_edf(file_path: Path):
    """Avab EDF-faili ja kuvab selle metaandmed."""

    if not file_path.is_file():
        raise FileNotFoundError(f"Faili ei leitud: {file_path}")

    print(f"\nFail: {file_path.name}")
    print(f"Suurus: {file_path.stat().st_size:,} baiti")

    with pyedflib.EdfReader(str(file_path)) as edf:
        print(f"Algusaeg: {edf.getStartdatetime()}")
        print(f"Faili kestus: {edf.getFileDuration()} sekundit")
        print(f"Signaalikanaleid: {edf.signals_in_file}")

        inspect_signals(edf)
        inspect_annotations(edf)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(
            "Kasutus: python src/inspect_edf.py <failitee>"
        )

    inspect_edf(Path(sys.argv[1]))
