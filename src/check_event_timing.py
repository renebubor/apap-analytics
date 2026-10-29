
from pathlib import Path
import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "analytics.duckdb"


def check_event_timing():
    with duckdb.connect(str(DB_PATH), read_only=True) as con:

        columns = con.execute("""
            DESCRIBE events
        """).fetchall()

        print("Events tabeli veerud:")
        print("-" * 60)

        for column in columns:
            print(f"{column[0]:25} {column[1]}")

        print("\nSündmused 03:25–03:35:")
        print("-" * 80)

        events = con.execute("""
            SELECT *
            FROM events
            WHERE event_time BETWEEN
                TIMESTAMP '2026-10-26 03:25:00'
                AND
                TIMESTAMP '2026-10-26 03:35:00'
            ORDER BY event_time
        """).df()

        if events.empty:
            print("Sündmusi ei leitud.")
        else:
            print(events.to_string(index=False))


if __name__ == "__main__":
    check_event_timing()
