
from pathlib import Path
import duckdb


DB_PATH = Path("data/analytics.duckdb")


def validate_events():
    with duckdb.connect(str(DB_PATH), read_only=True) as con:

        query = """
        WITH event_dates AS (
            SELECT
                CASE
                    WHEN CAST(event_time AS TIME) <
                         TIME '12:00:00'
                    THEN CAST(event_time AS DATE)
                         - INTERVAL 1 DAY
                    ELSE CAST(event_time AS DATE)
                END AS therapy_date,
                event_type
            FROM events
        ),

        event_counts AS (
            SELECT
                CAST(therapy_date AS DATE) AS therapy_date,

                COUNT(*) AS total_events,

                COUNT(*) FILTER (
                    WHERE event_type = 'Obstructive Apnea'
                ) AS obstructive_events,

                COUNT(*) FILTER (
                    WHERE event_type = 'Central Apnea'
                ) AS central_events,

                COUNT(*) FILTER (
                    WHERE event_type = 'Hypopnea'
                ) AS hypopnea_events

            FROM event_dates
            GROUP BY 1
        )

        SELECT
            d.therapy_date,
            d.usage_minutes,
            d.ahi AS device_ahi,

            COALESCE(e.total_events, 0) AS total_events,
            COALESCE(e.obstructive_events, 0)
                AS obstructive_events,
            COALESCE(e.central_events, 0)
                AS central_events,
            COALESCE(e.hypopnea_events, 0)
                AS hypopnea_events,

            ROUND(
                COALESCE(e.total_events, 0) * 60.0
                / NULLIF(d.usage_minutes, 0),
                2
            ) AS calculated_ahi,

            ROUND(
                COALESCE(e.total_events, 0) * 60.0
                / NULLIF(d.usage_minutes, 0)
                - d.ahi,
                2
            ) AS ahi_difference

        FROM daily_summary d
        LEFT JOIN event_counts e
            ON d.therapy_date = e.therapy_date

        ORDER BY d.therapy_date
        """

        rows = con.execute(query).fetchall()

        print("\nEVE vs STR – AHI kontroll")
        print("-" * 100)

        for row in rows:
            (
                day,
                usage,
                device_ahi,
                total,
                obstructive,
                central,
                hypopnea,
                calculated_ahi,
                difference,
            ) = row

            print(
                f"{day} | "
                f"Kasutus {usage:5.0f} min | "
                f"EVE {total:3} "
                f"(OA {obstructive}, "
                f"CA {central}, "
                f"H {hypopnea}) | "
                f"AHI {calculated_ahi:5.2f} | "
                f"STR {device_ahi:4.1f} | "
                f"Vahe {difference:+.2f}"
            )


if __name__ == "__main__":
    validate_events()
