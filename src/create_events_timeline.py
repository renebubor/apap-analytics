
import argparse
from pathlib import Path

import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB = (
    PROJECT_DIR
    / "data"
    / "pipeline_test"
    / "analytics_fresh.duckdb"
)


def create_events_timeline(db_path):
    if not db_path.is_file():
        raise FileNotFoundError(
            f"Andmebaasi ei leitud: {db_path}"
        )

    with duckdb.connect(str(db_path)) as con:

        con.execute("""
            CREATE OR REPLACE VIEW events_timeline AS
            SELECT
                event_id,
                source_file,
                file_start_time,
                onset_seconds,
                event_type,
                duration_seconds,

                event_time AS event_end,

                event_time
                    - duration_seconds * INTERVAL '1 second'
                    AS event_start

            FROM events
        """)

        total = con.execute("""
            SELECT COUNT(*)
            FROM events_timeline
        """).fetchone()[0]

        event_types = con.execute("""
            SELECT
                event_type,
                COUNT(*) AS event_count
            FROM events_timeline
            GROUP BY event_type
            ORDER BY event_type
        """).fetchall()

        print("\nHingamissündmuste ajatelg")
        print("-" * 55)

        for event_type, count in event_types:
            print(f"{event_type:25} | {count} sündmust")

        print("-" * 55)
        print(f"Sündmusi kokku: {total}")
        print("DuckDB vaade 'events_timeline' on loodud.")


def main():
    parser = argparse.ArgumentParser(
        description="Loob hingamissündmuste ajatelje."
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help="DuckDB andmebaasi asukoht",
    )

    args = parser.parse_args()

    create_events_timeline(args.db)


if __name__ == "__main__":
    main()
