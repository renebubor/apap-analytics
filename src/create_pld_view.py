
from pathlib import Path
import argparse

import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB = (
    PROJECT_DIR / "data" / "pipeline_test" / "analytics.duckdb"
)

DEFAULT_PLD_DIR = (
    PROJECT_DIR / "data" / "pipeline_test" / "pld"
)


def create_pld_view(db_path, pld_dir):
    """Loob DuckDB vaate PLD Parquet-mõõtmistele."""

    db_path = Path(db_path).resolve()
    pld_dir = Path(pld_dir).resolve()

    # Kontrollime Parquet-failide olemasolu.
    files = sorted(pld_dir.rglob("*.parquet"))

    if not files:
        raise FileNotFoundError(
            f"PLD Parquet-faile ei leitud: {pld_dir}"
        )

    if not db_path.is_file():
        raise FileNotFoundError(
            f"DuckDB andmebaasi ei leitud: {db_path}"
        )

    print(f"\nLeitud Parquet-faile: {len(files)}")

    # Absoluutne failitee DuckDB jaoks.
    parquet_pattern = (
        pld_dir / "**" / "*.parquet"
    ).as_posix()

    safe_path = parquet_pattern.replace("'", "''")

    with duckdb.connect(str(db_path)) as con:

        con.execute(f"""
            CREATE OR REPLACE VIEW pld_measurements AS
            SELECT
                timestamp,
                mask_pressure,
                pressure,
                epr_pressure,
                leak_l_s,
                leak_l_s * 60 AS leak_l_min,
                resp_rate,
                tidal_volume,
                minute_ventilation,
                snore,
                flow_limitation,
                source_file
            FROM read_parquet('{safe_path}')
        """)

        result = con.execute("""
            SELECT
                COUNT(*) AS measurement_count,
                MIN(timestamp) AS first_measurement,
                MAX(timestamp) AS last_measurement,
                COUNT(DISTINCT source_file) AS file_count
            FROM pld_measurements
        """).fetchone()

        (
            measurement_count,
            first_measurement,
            last_measurement,
            file_count,
        ) = result

        print("\nPLD mõõtmiste kokkuvõte:")
        print("-" * 65)
        print(f"Mõõteridu: {measurement_count:,}")
        print(f"Esimene mõõtmine: {first_measurement}")
        print(f"Viimane mõõtmine: {last_measurement}")
        print(f"Allikafaile: {file_count}")

        rows = con.execute("""
            SELECT
                source_file,
                COUNT(*) AS measurement_count,
                MIN(timestamp) AS start_time,
                MAX(timestamp) AS end_time
            FROM pld_measurements
            GROUP BY source_file
            ORDER BY start_time
        """).fetchall()

        print("\nMõõtmised failide lõikes:")
        print("-" * 100)

        for filename, count, start, end in rows:
            print(
                f"{filename} | "
                f"{count:,} rida | "
                f"{start} -> {end}"
            )

        # Kontrollime, kas kõik Parquet-failid
        # kajastuvad analüüsivaates.
        if file_count != len(files):
            raise ValueError(
                "PLD failide arv ei vasta "
                "analüüsivaate allikafailide arvule"
            )

        if measurement_count == 0:
            raise ValueError(
                "PLD analüüsivaates puuduvad mõõtmised"
            )

        print("\nKONTROLL OK: PLD mõõtmised on loetavad.")
        print("DuckDB vaade 'pld_measurements' on loodud.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PLD mõõtmiste DuckDB vaate loomine"
    )

    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
    )

    parser.add_argument(
        "--pld-dir",
        default=str(DEFAULT_PLD_DIR),
    )

    args = parser.parse_args()

    create_pld_view(args.db, args.pld_dir)
