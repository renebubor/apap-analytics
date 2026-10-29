
from pathlib import Path
import argparse
import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB = (
    PROJECT_DIR / "data" / "pipeline_test" / "analytics_fresh.duckdb"
)

DEFAULT_CSV = (
    PROJECT_DIR / "data" / "pipeline_test" / "daily_summary.csv"
)


def format_value(value, decimals=1):
    """Vormindab arvu või puuduva väärtuse."""
    if value is None:
        return "N/A"

    return f"{value:.{decimals}f}"


def load_daily_summary(db_path, csv_path):
    """Laeb päevakokkuvõtted DuckDB-sse."""

    db_path = Path(db_path).resolve()
    csv_path = Path(csv_path).resolve()

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"CSV-faili ei leitud: {csv_path}"
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS daily_summary (
                therapy_date DATE PRIMARY KEY,
                usage_minutes DOUBLE,
                on_duration_minutes DOUBLE,
                ahi DOUBLE,
                ai DOUBLE,
                hi DOUBLE,
                oai DOUBLE,
                cai DOUBLE,
                uai DOUBLE,
                pressure_p95 DOUBLE,
                leak_p95_l_min DOUBLE,
                source_file VARCHAR
            )
        """)

        con.execute("""
            CREATE OR REPLACE TEMP TABLE incoming_daily AS
            SELECT
                CAST(therapy_date AS DATE) AS therapy_date,
                CAST(usage_minutes AS DOUBLE) AS usage_minutes,
                CAST(on_duration_minutes AS DOUBLE)
                    AS on_duration_minutes,
                CAST(ahi AS DOUBLE) AS ahi,
                CAST(ai AS DOUBLE) AS ai,
                CAST(hi AS DOUBLE) AS hi,
                CAST(oai AS DOUBLE) AS oai,
                CAST(cai AS DOUBLE) AS cai,
                CAST(uai AS DOUBLE) AS uai,
                CAST(pressure_p95 AS DOUBLE)
                    AS pressure_p95,
                CAST(leak_p95_l_min AS DOUBLE)
                    AS leak_p95_l_min,
                source_file
            FROM read_csv_auto(
                ?,
                header = true,
                all_varchar = true
            )
        """, [str(csv_path)])

        incoming_count = con.execute("""
            SELECT COUNT(*) FROM incoming_daily
        """).fetchone()[0]

        # Uuendab olemasolevaid ravipäevi
        # ning lisab uued.
        con.execute("""
            INSERT OR REPLACE INTO daily_summary
            BY NAME
            SELECT * FROM incoming_daily
        """)

        result = con.execute("""
            SELECT
                therapy_date,
                usage_minutes,
                ahi,
                leak_p95_l_min
            FROM daily_summary
            ORDER BY therapy_date
        """).fetchall()

        print("\nDuckDB päevapõhised andmed")
        print("-" * 65)
        print(f"CSV päevakirjeid: {incoming_count}")

        for day, usage, ahi, leak in result:
            print(
                f"{day} | "
                f"Kasutus: {format_value(usage, 0)} min | "
                f"AHI: {format_value(ahi)} | "
                f"Leke P95: {format_value(leak)} L/min"
            )

        print(f"\nPäevi andmebaasis: {len(result)}")
        print(f"Andmebaas: {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="STR päevakokkuvõtete laadimine DuckDB-sse"
    )

    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
    )

    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
    )

    args = parser.parse_args()

    load_daily_summary(args.db, args.csv)
