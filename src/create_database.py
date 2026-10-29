
from pathlib import Path
import argparse
import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB = (
    PROJECT_DIR / "data" / "pipeline_test" / "analytics.duckdb"
)

DEFAULT_EVENTS = (
    PROJECT_DIR / "data" / "pipeline_test" / "events.csv"
)


def create_database(db_path, events_path):
    """Laeb EVE sündmused DuckDB andmebaasi."""

    db_path = Path(db_path).resolve()
    events_path = Path(events_path).resolve()

    if not events_path.is_file():
        raise FileNotFoundError(
            f"Sündmuste CSV-faili ei leitud: {events_path}"
        )

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS events (
                event_id VARCHAR PRIMARY KEY,
                source_file VARCHAR,
                file_start_time TIMESTAMP,
                onset_seconds DOUBLE,
                event_time TIMESTAMP,
                event_type VARCHAR,
                duration_seconds DOUBLE
            )
        """)

        con.execute("""
            CREATE OR REPLACE TEMP TABLE incoming_events AS
            SELECT
                event_id,
                source_file,
                CAST(file_start_time AS TIMESTAMP)
                    AS file_start_time,
                CAST(onset_seconds AS DOUBLE)
                    AS onset_seconds,
                CAST(event_time AS TIMESTAMP)
                    AS event_time,
                event_type,
                CAST(duration_seconds AS DOUBLE)
                    AS duration_seconds
            FROM read_csv_auto(
                ?,
                header = true,
                all_varchar = true
            )
        """, [str(events_path)])

        incoming_count = con.execute("""
            SELECT COUNT(*) FROM incoming_events
        """).fetchone()[0]

        before_count = con.execute("""
            SELECT COUNT(*) FROM events
        """).fetchone()[0]

        # Lisame ainult puuduvad sündmused.
        con.execute("""
            INSERT INTO events BY NAME
            SELECT *
            FROM incoming_events
            WHERE event_id NOT IN (
                SELECT event_id FROM events
            )
        """)

        after_count = con.execute("""
            SELECT COUNT(*) FROM events
        """).fetchone()[0]

        inserted_count = after_count - before_count

        print("\nDuckDB sündmuste import")
        print("-" * 55)
        print(f"CSV sündmusi: {incoming_count}")
        print(f"Uusi sündmusi: {inserted_count}")
        print(f"Andmebaasis kokku: {after_count}")

        result = con.execute("""
            SELECT
                event_type,
                COUNT(*) AS event_count,
                ROUND(AVG(duration_seconds), 1)
                    AS avg_duration_seconds
            FROM events
            GROUP BY event_type
            ORDER BY event_count DESC
        """).fetchall()

        print("\nSündmuste jaotus:")
        for event_type, count, duration in result:
            print(
                f"{event_type:25} "
                f"{count:5} sündmust | "
                f"Keskmine kestus: {duration} s"
            )

        print(f"\nAndmebaas: {db_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="EVE sündmuste laadimine DuckDB-sse"
    )

    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
        help="DuckDB andmebaasi asukoht",
    )

    parser.add_argument(
        "--events",
        default=str(DEFAULT_EVENTS),
        help="Sündmuste CSV-fail",
    )

    args = parser.parse_args()

    create_database(args.db, args.events)
