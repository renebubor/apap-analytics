
from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import os

import duckdb
import pandas as pd
import pyedflib


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_RAW = (
    PROJECT_DIR / "data" / "raw" / "sd_archive" / "DATALOG"
)

DEFAULT_OUTPUT = (
    PROJECT_DIR / "data" / "pipeline_test" / "pld"
)

DEFAULT_DB = (
    PROJECT_DIR / "data" / "pipeline_test" / "analytics.duckdb"
)


def file_hash(path):
    """Arvutab SHA-256 kontrollsumma."""
    sha = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha.update(chunk)

    return sha.hexdigest()


def create_registry(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS pld_file_registry (
            source_file VARCHAR PRIMARY KEY,
            sha256 VARCHAR NOT NULL,
            output_file VARCHAR NOT NULL,
            row_count BIGINT NOT NULL,
            processed_at TIMESTAMP NOT NULL
        )
    """)


def is_empty_edf(file_path):
    """Kontrollib, kas EDF-failis puuduvad andmekirjed."""

    with file_path.open("rb") as file:
        header = file.read(256)

    if len(header) < 256:
        return False

    try:
        header_size = int(
            header[184:192].decode("ascii").strip()
        )
        record_count = int(
            header[236:244].decode("ascii").strip()
        )
    except (ValueError, UnicodeDecodeError):
        return False

    file_size = file_path.stat().st_size

    return (
        record_count in (-1, 0)
        and header_size >= 256
        and file_size == header_size
    )


def export_file(file_path, raw_dir, output_dir):
    """Teisendab ühe PLD-faili Parquet-failiks."""

    with pyedflib.EdfReader(str(file_path)) as edf:
        start_time = edf.getStartdatetime()
        labels = edf.getSignalLabels()

        selected = {
            "MaskPress.2s": "mask_pressure",
            "Press.2s": "pressure",
            "EprPress.2s": "epr_pressure",
            "Leak.2s": "leak_l_s",
            "RespRate.2s": "resp_rate",
            "TidVol.2s": "tidal_volume",
            "MinVent.2s": "minute_ventilation",
            "Snore.2s": "snore",
            "FlowLim.2s": "flow_limitation",
        }

        data = {}

        for original, renamed in selected.items():
            if original not in labels:
                continue

            index = labels.index(original)
            frequency = edf.getSampleFrequency(index)

            if abs(frequency - 0.5) > 0.001:
                raise ValueError(
                    f"Ootamatu sagedus: {original} = {frequency}"
                )

            data[renamed] = edf.readSignal(index)

        if not data:
            raise ValueError("Mõõtmiskanaleid ei leitud")

        lengths = {len(values) for values in data.values()}

        if len(lengths) != 1:
            raise ValueError(
                "Kanalite mõõtepunktide arv ei ühti"
            )

        count = lengths.pop()

        timestamps = pd.date_range(
            start=start_time,
            periods=count,
            freq="2s",
        )

        df = pd.DataFrame(data)
        df.insert(0, "timestamp", timestamps)

        relative_path = file_path.relative_to(raw_dir).as_posix()
        df["source_file"] = relative_path

        # Säilitame lähtefaili alamkaustade struktuuri.
        output_file = (
            output_dir / Path(relative_path)
        ).with_suffix(".parquet")

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = output_file.with_name(
            output_file.name + ".tmp"
        )

        try:
            df.to_parquet(temporary, index=False)
            os.replace(temporary, output_file)
        finally:
            if temporary.exists():
                temporary.unlink()

        return count, output_file


def export_all(raw_dir, output_dir, db_path):
    raw_dir = Path(raw_dir).resolve()
    output_dir = Path(output_dir).resolve()
    db_path = Path(db_path).resolve()

    if not raw_dir.is_dir():
        raise FileNotFoundError(
            f"Lähtekausta ei leitud: {raw_dir}"
        )

    files = sorted(raw_dir.rglob("*_PLD.edf"))

    if not files:
        raise FileNotFoundError(
            f"PLD-faile ei leitud: {raw_dir}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    errors = 0
    total_rows = 0
    empty_files = 0

    with duckdb.connect(str(db_path)) as con:
        create_registry(con)

        for file_path in files:
            relative_path = file_path.relative_to(
                raw_dir
            ).as_posix()

            expected_output = (
                output_dir / Path(relative_path)
            ).with_suffix(".parquet")

            try:
                if is_empty_edf(file_path):
                    empty_files += 1
                    print(f"TÜHI EDF: {file_path.name}")
                    continue

                sha256 = file_hash(file_path)

                previous = con.execute("""
                    SELECT sha256, row_count
                    FROM pld_file_registry
                    WHERE source_file = ?
                """, [relative_path]).fetchone()

                if (
                    previous is not None
                    and previous[0] == sha256
                    and expected_output.is_file()
                ):
                    skipped += 1
                    total_rows += previous[1]
                    print(f"VAHELE: {file_path.name}")
                    continue

                rows, output_file = export_file(
                    file_path,
                    raw_dir,
                    output_dir,
                )

                con.execute("""
                    INSERT INTO pld_file_registry (
                        source_file,
                        sha256,
                        output_file,
                        row_count,
                        processed_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (source_file)
                    DO UPDATE SET
                        sha256 = excluded.sha256,
                        output_file = excluded.output_file,
                        row_count = excluded.row_count,
                        processed_at = excluded.processed_at
                """, [
                    relative_path,
                    sha256,
                    str(output_file),
                    rows,
                    datetime.now(),
                ])

                processed += 1
                total_rows += rows

                print(
                    f"TÖÖDELDUD: {file_path.name} "
                    f"({rows:,} rida)"
                )

            except (
                OSError,
                ValueError,
                duckdb.Error,
            ) as error:
                errors += 1
                print(f"VIGA: {file_path.name}: {error}")

    print("\n" + "=" * 55)
    print("PLD inkrementaalse ekspordi kokkuvõte")
    print("-" * 55)
    print(f"Leitud PLD-faile: {len(files)}")
    print(f"Töödeldud: {processed}")
    print(f"Vahele jäetud: {skipped}")
    print(f"Vigu: {errors}")
    print(f"Mõõteridu kokku: {total_rows:,}")
    print(f"Väljundkaust: {output_dir}")
    print(f"Tühjad EDF-failid: {empty_files}")

    if errors:
        raise RuntimeError(
            f"{errors} PLD-faili töötlemine ebaõnnestus"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PLD inkrementaalne eksport"
    )

    parser.add_argument(
        "--raw",
        default=str(DEFAULT_RAW),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
    )

    args = parser.parse_args()

    export_all(args.raw, args.output, args.db)
