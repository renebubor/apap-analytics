
from pathlib import Path

import duckdb
import pyedflib
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent.parent

BRP_DIR = (
    PROJECT_DIR
    / "data"
    / "raw"
    / "sd_archive"
    / "DATALOG"
)

DB_PATH = (
    PROJECT_DIR
    / "data"
    / "pipeline_test"
    / "analytics_fresh.duckdb"
)


def index_brp_files():

    if not BRP_DIR.exists():
        raise FileNotFoundError(
            f"BRP kausta ei leitud: {BRP_DIR}"
        )

    records = []

    files = sorted(
        BRP_DIR.rglob("*_BRP.edf")
    )

    for file_path in files:

        stat = file_path.stat()

        record = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": stat.st_size,
            "modified_ns": stat.st_mtime_ns,
            "file_start": None,
            "file_end": None,
            "frequency": None,
            "sample_count": None,
            "status": "error",
            "error_message": None,
        }

        try:
            with pyedflib.EdfReader(
                str(file_path)
            ) as edf:

                labels = edf.getSignalLabels()

                if "Flow.40ms" not in labels:
                    record["status"] = "no_flow"

                else:
                    index = labels.index("Flow.40ms")

                    frequency = float(
                        edf.getSampleFrequency(index)
                    )

                    sample_count = int(
                        edf.getNSamples()[index]
                    )

                    file_start = pd.Timestamp(
                        edf.getStartdatetime()
                    )

                    file_end = (
                        file_start
                        + pd.Timedelta(
                            seconds=sample_count / frequency
                        )
                    )

                    record.update({
                        "file_start": file_start,
                        "file_end": file_end,
                        "frequency": frequency,
                        "sample_count": sample_count,
                        "status": "ok",
                    })

        except (OSError, ValueError) as exc:
            record["error_message"] = str(exc)

        records.append(record)

    df = pd.DataFrame(
        records,
        columns=[
            "file_path",
            "file_name",
            "file_size",
            "modified_ns",
            "file_start",
            "file_end",
            "frequency",
            "sample_count",
            "status",
            "error_message",
        ],
    )

    with duckdb.connect(str(DB_PATH)) as con:

        con.execute("""
            CREATE TABLE IF NOT EXISTS brp_file_index (
                file_path VARCHAR PRIMARY KEY,
                file_name VARCHAR,
                file_size BIGINT,
                modified_ns BIGINT,
                file_start TIMESTAMP,
                file_end TIMESTAMP,
                frequency DOUBLE,
                sample_count BIGINT,
                status VARCHAR,
                error_message VARCHAR
            )
        """)

        # Uuendame indeksi vastavalt arhiivi hetkeseisule.
        # Tühja arhiivi korral jääb tabel tühjaks.
        con.execute("DELETE FROM brp_file_index")

        if not df.empty:
            con.register("brp_records", df)

            con.execute("""
                INSERT INTO brp_file_index
                SELECT
                    file_path,
                    file_name,
                    file_size,
                    modified_ns,
                    file_start,
                    file_end,
                    frequency,
                    sample_count,
                    status,
                    error_message
                FROM brp_records
            """)

        summary = con.execute("""
            SELECT
                status,
                COUNT(*) AS files
            FROM brp_file_index
            GROUP BY status
            ORDER BY status
        """).df()

        errors = con.execute("""
            SELECT
                file_name,
                file_size,
                error_message
            FROM brp_file_index
            WHERE status = 'error'
            ORDER BY file_name
        """).df()

    print(f"BRP-faile kokku: {len(df)}")
    print("\nFailide staatus:")
    print(summary.to_string(index=False))

    if not errors.empty:
        print("\nVigased failid:")
        print(errors.to_string(index=False))


if __name__ == "__main__":
    index_brp_files()
