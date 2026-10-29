
from pathlib import Path
from datetime import datetime
import hashlib
import shutil
import sys
import argparse
import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    PROJECT_DIR
    / "data"
    / "pipeline_test"
    / "analytics_fresh.duckdb"
)
ARCHIVE_DIR = PROJECT_DIR / "data" / "raw" / "sd_archive"

CHUNK_SIZE = 1024 * 1024


def calculate_hash(file_path):
    """Arvutab faili SHA-256 kontrollsumma."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def create_registry(con):
    """Loob failide registri, kui seda veel pole."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS sd_file_registry (
            relative_path VARCHAR PRIMARY KEY,
            file_size BIGINT,
            sha256 VARCHAR,
            imported_at TIMESTAMP
        )
    """)


def sync_sd(sd_path, db_path=DB_PATH, archive_dir=ARCHIVE_DIR):
    sd_path = Path(sd_path).resolve()
    db_path = Path(db_path).resolve()
    archive_dir = Path(archive_dir).resolve()

    if not sd_path.is_dir():
        raise FileNotFoundError(
            f"SD-kaardi asukohta ei leitud: {sd_path}"
        )

    archive_dir.mkdir(parents=True, exist_ok=True)

    new_files = 0
    changed_files = 0
    unchanged_files = 0
    errors = 0

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        create_registry(con)

        files = sorted(
            p for p in sd_path.rglob("*")
            if p.is_file()
        )

        print(f"\nLeitud faile: {len(files)}")
        print("-" * 65)

        for source_file in files:
            relative_path = source_file.relative_to(
                sd_path
            ).as_posix()

            destination = archive_dir / relative_path

            try:
                file_size = source_file.stat().st_size
                file_hash = calculate_hash(source_file)

                previous = con.execute("""
                    SELECT sha256
                    FROM sd_file_registry
                    WHERE relative_path = ?
                """, [relative_path]).fetchone()

                if (
                    previous is not None
                    and previous[0] == file_hash
                    and destination.is_file()
                    and destination.stat().st_size == file_size
                    and calculate_hash(destination) == file_hash
                ):
                    unchanged_files += 1
                    continue

                destination.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                # Kopeerime esmalt ajutisse faili.
                temporary = destination.with_name(
                    destination.name + ".tmp"
                )

                shutil.copy2(source_file, temporary)

                # Kontrollime kopeeritud faili terviklust.
                copied_hash = calculate_hash(temporary)

                if copied_hash != file_hash:
                    raise ValueError(
                        "Kopeeritud faili kontrollsumma ei ühti"
                    )

                temporary.replace(destination)

                con.execute("""
                    INSERT INTO sd_file_registry (
                        relative_path,
                        file_size,
                        sha256,
                        imported_at
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (relative_path)
                    DO UPDATE SET
                        file_size = excluded.file_size,
                        sha256 = excluded.sha256,
                        imported_at = excluded.imported_at
                """, [
                    relative_path,
                    file_size,
                    file_hash,
                    datetime.now()
                ])

                if previous is None:
                    new_files += 1
                    status = "UUS"
                else:
                    changed_files += 1
                    status = "MUUTUNUD"

                print(f"{status}: {relative_path}")

            except (OSError, ValueError, duckdb.Error) as error:
                errors += 1
                print(f"VIGA: {relative_path}: {error}")

    print("\n" + "=" * 65)
    print("SD-kaardi sünkroonimise kokkuvõte")
    print("-" * 65)

    print(f"Uusi faile: {new_files}")
    print(f"Muutunud faile: {changed_files}")
    print(f"Muutumata faile: {unchanged_files}")
    print(f"Vigu: {errors}")
    print(f"Kohalik arhiiv: {archive_dir}")
    if errors > 0:
        raise RuntimeError(
            f"SD-kaardi sünkroonimisel tekkis "
            f"{errors} viga. Kontrolli veateateid."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CPAP SD-kaardi failide sünkroonimine"
    )

    parser.add_argument("source", help="Lähtekaust")
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--archive", default=str(ARCHIVE_DIR))

    args = parser.parse_args()

    sync_sd(
        args.source,
        db_path=args.db,
        archive_dir=args.archive,
    )
