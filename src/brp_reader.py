"""Read BRP EDF airflow using the active DuckDB file index.

Demo index paths are relative to the demo database directory.
Personal/legacy absolute paths continue to work unchanged.
"""
from pathlib import Path

import duckdb
import pandas as pd
import pyedflib

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "pipeline_test" / "analytics_fresh.duckdb"


def _resolve_brp_path(stored_path):
    path = Path(stored_path)
    if path.is_absolute():
        return path
    return Path(DB_PATH).resolve().parent / path


def find_brp_files(start_time, end_time):
    """Find indexed BRP recordings overlapping the requested period."""
    start_time = pd.Timestamp(start_time)
    end_time = pd.Timestamp(end_time)
    if end_time <= start_time:
        raise ValueError("Lõppaeg peab olema algusajast hilisem.")

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        files = con.execute("""
            SELECT file_path, file_name, file_start, file_end,
                   frequency, sample_count
            FROM brp_file_index
            WHERE status = 'ok'
              AND file_start < ?
              AND file_end > ?
            ORDER BY file_start, file_path
        """, [end_time, start_time]).df()
    return files.to_dict("records")


def load_brp_flow(start_time, end_time):
    """Read only airflow samples within the requested time range."""
    start_time = pd.Timestamp(start_time)
    end_time = pd.Timestamp(end_time)
    matching_files = find_brp_files(start_time, end_time)
    frames = []

    for item in matching_files:
        file_path = _resolve_brp_path(item["file_path"])
        if not file_path.is_file():
            print(f"BRP fail puudub: {file_path}")
            continue

        file_start = pd.Timestamp(item["file_start"])
        frequency = float(item["frequency"])
        sample_count = int(item["sample_count"])
        first = max(0, int((start_time - file_start).total_seconds() * frequency))
        last = min(sample_count, int((end_time - file_start).total_seconds() * frequency) + 1)
        if first >= last:
            continue

        try:
            with pyedflib.EdfReader(str(file_path)) as edf:
                labels = edf.getSignalLabels()
                if "Flow.40ms" not in labels:
                    continue
                signal_index = labels.index("Flow.40ms")
                flow = edf.readSignal(signal_index, start=first, n=last - first)
        except (OSError, ValueError) as exc:
            print(f"BRP lugemine ebaõnnestus: {file_path.name}: {exc}")
            continue

        timestamps = (
            file_start
            + pd.to_timedelta(pd.Series(range(first, first + len(flow))) / frequency, unit="s")
        )
        frame = pd.DataFrame({
            "timestamp": timestamps,
            "flow": flow,
            "source_file": file_path.name,
        })
        frame = frame[
            (frame["timestamp"] >= start_time)
            & (frame["timestamp"] <= end_time)
        ]
        frames.append(frame)

    if not frames:
        return pd.DataFrame(columns=["timestamp", "flow", "source_file"])

    return (
        pd.concat(frames, ignore_index=True)
        .sort_values("timestamp")
        .drop_duplicates(subset=["timestamp"])
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    print("BRP reader ready; use load_brp_flow(start_time, end_time).")
