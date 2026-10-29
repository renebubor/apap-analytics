
from pathlib import Path
import argparse

import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB = (
    PROJECT_DIR / "data" / "pipeline_test" / "analytics.duckdb"
)


def create_pld_session_view(db_path):
    """Seob PLD mõõtmised maski kasutussessioonidega."""

    db_path = Path(db_path).resolve()

    if not db_path.is_file():
        raise FileNotFoundError(
            f"Andmebaasi ei leitud: {db_path}"
        )

    with duckdb.connect(str(db_path)) as con:

        con.execute("""
            CREATE OR REPLACE VIEW pld_session_measurements AS

            WITH candidates AS (
                SELECT
                    s.session_id,
                    s.therapy_date,
                    s.session_number,

                    p.timestamp,
                    p.mask_pressure,
                    p.pressure,
                    p.epr_pressure,
                    p.leak_l_min,
                    p.resp_rate,
                    p.tidal_volume,
                    p.minute_ventilation,
                    p.snore,
                    p.flow_limitation,
                    p.source_file,

                    ROW_NUMBER() OVER (
                        PARTITION BY
                            p.source_file,
                            p.timestamp

                        ORDER BY
                            CASE
                                WHEN p.timestamp < s.start_time
                                THEN date_diff(
                                    'second',
                                    p.timestamp,
                                    s.start_time
                                )

                                WHEN p.timestamp > s.end_time
                                THEN date_diff(
                                    'second',
                                    s.end_time,
                                    p.timestamp
                                )

                                ELSE 0
                            END,
                            s.start_time,
                            s.session_id
                    ) AS rn

                FROM pld_measurements p

                JOIN mask_sessions s
                    ON p.timestamp >=
                        s.start_time - INTERVAL 60 SECOND
                   AND p.timestamp <=
                        s.end_time + INTERVAL 60 SECOND
            )

            SELECT
                session_id,
                therapy_date,
                session_number,
                timestamp,
                mask_pressure,
                pressure,
                epr_pressure,
                leak_l_min,
                resp_rate,
                tidal_volume,
                minute_ventilation,
                snore,
                flow_limitation,
                source_file

            FROM candidates
            WHERE rn = 1
        """)

        rows = con.execute("""
            SELECT
                session_id,
                COUNT(*) AS measurement_count,
                MIN(timestamp) AS first_measurement,
                MAX(timestamp) AS last_measurement

            FROM pld_session_measurements
            GROUP BY session_id
            ORDER BY session_id
        """).fetchall()

        print("\nPLD mõõtmised sessioonide lõikes:")
        print("-" * 100)

        for session_id, count, first, last in rows:
            print(
                f"{session_id} | "
                f"{count:,} mõõterida | "
                f"{first} -> {last}"
            )

        total = con.execute("""
            SELECT COUNT(*)
            FROM pld_measurements
        """).fetchone()[0]

        linked = con.execute("""
            SELECT COUNT(*)
            FROM pld_session_measurements
        """).fetchone()[0]

        unmatched = con.execute("""
            SELECT COUNT(*)
            FROM pld_measurements p

            WHERE NOT EXISTS (
                SELECT 1
                FROM pld_session_measurements ps
                WHERE ps.timestamp = p.timestamp
                  AND ps.source_file = p.source_file
            )
        """).fetchone()[0]

        duplicates = con.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT
                    source_file,
                    timestamp
                FROM pld_session_measurements
                GROUP BY source_file, timestamp
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        print("\nKontrollide kokkuvõte:")
        print("-" * 65)

        print(f"PLD mõõteridu kokku: {total:,}")
        print(f"Sessioonidega seotud: {linked:,}")
        print(f"Sidumata mõõteridu: {unmatched:,}")
        print(f"Mitmekordseid vasteid: {duplicates}")

        if linked + unmatched != total:
            raise ValueError(
                "Seotud ja sidumata mõõteridade summa "
                "ei vasta lähteandmetele"
            )

        if duplicates > 0:
            raise ValueError(
                "Mõni mõõterida on seotud mitu korda"
            )

        print("\nKONTROLL OK")
        print(
            "DuckDB vaade 'pld_session_measurements' "
            "on loodud."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PLD mõõtmiste sidumine sessioonidega"
    )

    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
    )

    args = parser.parse_args()

    create_pld_session_view(args.db)
