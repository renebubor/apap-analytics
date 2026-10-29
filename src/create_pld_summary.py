
from pathlib import Path
import argparse

import duckdb


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_DB = (
    PROJECT_DIR / "data" / "pipeline_test" / "analytics.duckdb"
)


def create_pld_summary(db_path):
    """Loob sessioonipõhise CPAP koondnäitajate vaate."""

    db_path = Path(db_path).resolve()

    if not db_path.is_file():
        raise FileNotFoundError(
            f"Andmebaasi ei leitud: {db_path}"
        )

    with duckdb.connect(str(db_path)) as con:

        con.execute("""
            CREATE OR REPLACE VIEW pld_session_summary AS

            WITH measurements AS (
                SELECT
                    session_id,
                    COUNT(*) AS measurement_count,

                    ROUND(AVG(pressure), 2)
                        AS avg_pressure,

                    ROUND(
                        QUANTILE_CONT(pressure, 0.95), 2
                    ) AS pressure_p95,

                    ROUND(AVG(leak_l_min), 2)
                        AS avg_leak,

                    ROUND(
                        QUANTILE_CONT(leak_l_min, 0.95), 2
                    ) AS leak_p95,

                    ROUND(AVG(resp_rate), 2)
                        AS avg_resp_rate,

                    ROUND(AVG(tidal_volume), 3)
                        AS avg_tidal_volume,

                    ROUND(AVG(minute_ventilation), 2)
                        AS avg_minute_ventilation

                FROM pld_session_measurements
                GROUP BY session_id
            )

            SELECT
                s.session_id,
                s.therapy_date,
                s.session_number,
                s.duration_minutes,
                s.total_events,
                s.obstructive_events,
                s.central_events,
                s.hypopnea_events,
                s.calculated_ahi,

                m.measurement_count,
                m.avg_pressure,
                m.pressure_p95,
                m.avg_leak,
                m.leak_p95,
                m.avg_resp_rate,
                m.avg_tidal_volume,
                m.avg_minute_ventilation

            FROM session_analysis s

            LEFT JOIN measurements m
                ON s.session_id = m.session_id
        """)

        rows = con.execute("""
            SELECT
                session_id,
                calculated_ahi,
                avg_pressure,
                pressure_p95,
                avg_leak,
                leak_p95,
                avg_resp_rate
            FROM pld_session_summary
            ORDER BY therapy_date, session_number
        """).fetchall()

        source_sessions = con.execute("""
            SELECT COUNT(*)
            FROM mask_sessions
        """).fetchone()[0]

        source_measurements = con.execute("""
            SELECT COUNT(*)
            FROM pld_session_measurements
        """).fetchone()[0]

        summary_measurements = con.execute("""
            SELECT COALESCE(SUM(measurement_count), 0)
            FROM pld_session_summary
        """).fetchone()[0]

        print("\nPLD sessioonide koondnäitajad:")
        print("-" * 110)

        def fmt(value):
            return (
                f"{value:.2f}"
                if value is not None else "N/A"
            )

        for row in rows:
            (
                session_id,
                ahi,
                avg_pressure,
                pressure_p95,
                avg_leak,
                leak_p95,
                resp_rate,
            ) = row

            print(
                f"{session_id} | "
                f"AHI {fmt(ahi):>5} | "
                f"Rõhk {fmt(avg_pressure):>5} | "
                f"P95 {fmt(pressure_p95):>5} | "
                f"Leke {fmt(avg_leak):>5} | "
                f"Leke P95 {fmt(leak_p95):>5} | "
                f"Hingamissagedus {fmt(resp_rate):>5}"
            )

        print("\nKontrollide kokkuvõte:")
        print("-" * 65)

        print(f"Sessioone lähteandmetes: {source_sessions}")
        print(f"Sessioone koondvaates: {len(rows)}")
        print(f"PLD mõõteridu lähteandmetes: {source_measurements:,}")
        print(f"PLD mõõteridu koondvaates: {summary_measurements:,}")

        if len(rows) != source_sessions:
            raise ValueError(
                "Sessioonide arv ei vasta lähteandmetele"
            )

        if summary_measurements != source_measurements:
            raise ValueError(
                "PLD mõõteridade arv ei vasta lähteandmetele"
            )

        print("\nKONTROLL OK")
        print("DuckDB vaade 'pld_session_summary' on loodud.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CPAP sessioonide koondnäitajate loomine"
    )

    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB),
    )

    args = parser.parse_args()

    create_pld_summary(args.db)
