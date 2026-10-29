
from pathlib import Path
from datetime import datetime, date, timedelta
import argparse
import csv

from export_daily_summary import read_str


PROJECT_DIR = Path(__file__).resolve().parent.parent

DEFAULT_SOURCE = (
    PROJECT_DIR / "data" / "raw" / "sd_archive" / "STR.edf"
)

DEFAULT_OUTPUT = (
    PROJECT_DIR / "data" / "pipeline_test" / "mask_sessions.csv"
)


def export_mask_sessions(source, output):
    """Ekspordib STR-failist maski kasutussessioonid."""

    source = Path(source).resolve()
    output = Path(output).resolve()

    records = read_str(source)
    sessions = []

    for record in records:
        day_number = round(record["Date"][0])

        therapy_date = (
            date(1970, 1, 1)
            + timedelta(days=day_number)
        )

        # ResMedi raviöö arvestuse algus on 12:00.
        day_start = datetime.combine(
            therapy_date,
            datetime.min.time(),
        ) + timedelta(hours=12)

        mask_on = record["MaskOn"]
        mask_off = record["MaskOff"]

        session_number = 0

        for on_minutes, off_minutes in zip(
            mask_on, mask_off
        ):
            # -1 tähistab kasutamata väärtust.
            if on_minutes < 0 or off_minutes < 0:
                continue

            if off_minutes <= on_minutes:
                raise ValueError(
                    f"Vigane sessioon: {therapy_date}, "
                    f"algus {on_minutes}, lõpp {off_minutes}"
                )

            session_number += 1

            start_time = day_start + timedelta(
                minutes=on_minutes
            )

            end_time = day_start + timedelta(
                minutes=off_minutes
            )

            duration_minutes = off_minutes - on_minutes

            sessions.append({
                "session_id": (
                    f"{therapy_date}_{session_number}"
                ),
                "therapy_date": therapy_date.isoformat(),
                "session_number": session_number,
                "start_time": start_time.isoformat(
                    sep=" "
                ),
                "end_time": end_time.isoformat(
                    sep=" "
                ),
                "duration_minutes": duration_minutes,
            })

    if not sessions:
        raise ValueError("STR-failist ei leitud sessioone")

    session_ids = [
        session["session_id"] for session in sessions
    ]

    if len(session_ids) != len(set(session_ids)):
        raise ValueError("Leiti korduvaid sessiooni ID-sid")

    output.parent.mkdir(parents=True, exist_ok=True)

    columns = [
        "session_id",
        "therapy_date",
        "session_number",
        "start_time",
        "end_time",
        "duration_minutes",
    ]

    with output.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
        )
        writer.writeheader()
        writer.writerows(sessions)

    print("\nMaski kasutussessioonide eksport")
    print("-" * 65)
    print(f"Salvestatud: {output}")
    print(f"Sessioone kokku: {len(sessions)}")

    total_minutes = sum(
        session["duration_minutes"] for session in sessions
    )

    print(f"Kasutusaeg kokku: {total_minutes:.0f} min")

    print("\nSessioonide nimekiri:")

    for session in sessions:
        print(
            f"{session['session_id']} | "
            f"{session['start_time']} -> "
            f"{session['end_time']} | "
            f"{session['duration_minutes']:.0f} min"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Maski kasutussessioonide eksport"
    )

    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )

    args = parser.parse_args()

    export_mask_sessions(args.source, args.output)
