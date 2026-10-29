
from pathlib import Path
import argparse
import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB = (
    PROJECT_DIR / "data" / "pipeline_test" / "analytics.duckdb"
)

DEFAULT_CSV = (
    PROJECT_DIR / "data" / "pipeline_test" / "mask_sessions.csv"
)


def load_mask_sessions(db_path, csv_path):
    """Laeb maski kasutussessioonid DuckDB-sse."""

    db_path = Path(db_path).resolve()
    csv_path = Path(csv_path).resolve()

    if not csv_path.is_file():
        raise FileNotFoundError(
            f"Sessioonide CSV-faili ei leitud: {csv_path}"
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS mask_sessions (
                session_id VARCHAR PRIMARY KEY,
                therapy_date DATE,
                session_number INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration_minutes DOUBLE
            )
        """)

        con.execute("""
            CREATE OR REPLACE TEMP TABLE incoming_sessions AS
            SELECT
                session_id,
                CAST(therapy_date AS DATE) AS therapy_date,
                CAST(session_number AS INTEGER)
                    AS session_number,
                CAST(start_time AS TIMESTAMP) AS start_time,
                CAST(end_time AS TIMESTAMP) AS end_time,
                CAST(duration_minutes AS DOUBLE)
                    AS duration_minutes
            FROM read_csv_auto(
                ?,
                header = true,
                all_varchar = true
            )
        """, [str(csv_path)])

        incoming_count = con.execute("""
            SELECT COUNT(*) FROM incoming_sessions
        """).fetchone()[0]

        # Uuendame olemasolevaid sessioone
        # ja lisame uued.
        con.execute("""
            INSERT OR REPLACE INTO mask_sessions
            BY NAME
            SELECT * FROM incoming_sessions
        """)

        result = con.execute("""
            SELECT
                COUNT(*) AS sessions,
                SUM(duration_minutes) AS total_minutes
            FROM mask_sessions
        """).fetchone()

        print("\nDuckDB maski kasutussessioonid")
        print("-" * 65)
        print(f"CSV sessioone: {incoming_count}")
        print(f"Sessioone andmebaasis: {result[0]}")
        print(f"Kasutusaeg kokku: {result[1]:.0f} min")
        print(f"Andmebaas: {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Maski kasutussessioonide laadimine DuckDB-sse"
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

    load_mask_sessions(args.db, args.csv)
