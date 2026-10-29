
from pathlib import Path
from datetime import datetime
import argparse
import subprocess
import sys
import time


PROJECT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_DIR / "src"

ARCHIVE_DIR = PROJECT_DIR / "data" / "raw" / "sd_archive"
TEST_DIR = PROJECT_DIR / "data" / "pipeline_test"

DB_PATH = TEST_DIR / "analytics_fresh.duckdb"
EVENTS_PATH = TEST_DIR / "events.csv"
PLD_DIR = TEST_DIR / "pld"


def run_step(name, script, arguments):
    """Käivitab ühe töövoo etapi."""

    print("\n" + "=" * 65, flush=True)
    print(f"ETAPP: {name}", flush=True)
    print("=" * 65, flush=True)

    command = [
        sys.executable,
        str(SRC_DIR / script),
        *[str(arg) for arg in arguments],
    ]

    started = time.perf_counter()

    result = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        check=False,
    )

    elapsed = time.perf_counter() - started

    if result.returncode != 0:
        raise RuntimeError(
            f"Etapp '{name}' ebaõnnestus "
            f"(veakood {result.returncode})"
        )

    print(
        f"\nETAPP VALMIS: {name} "
        f"({elapsed:.2f} sekundit)",
        flush=True,
    )


def run_pipeline(sd_path=None):
    """Käivitab CPAP andmetöötluse."""

    started = datetime.now()

    print("\nCPAP andmetöötluse pipeline")
    print(f"Algus: {started:%Y-%m-%d %H:%M:%S}")

    if sd_path is not None:
        run_step(
            "SD-kaardi sünkroonimine",
            "sync_sd.py",
            [
                sd_path,
                "--db", DB_PATH,
                "--archive", ARCHIVE_DIR,
            ],
        )
    if not (ARCHIVE_DIR / "DATALOG").is_dir():
        raise FileNotFoundError(
            f"SD arhiivi DATALOG kausta ei leitud: {ARCHIVE_DIR}"
        )
    steps = [
        (
            "EVE sündmuste eksport",
            "export_events.py",
            [
                "--raw", ARCHIVE_DIR / "DATALOG",
                "--output", EVENTS_PATH,
            ],
        ),
        (
            "EVE sündmuste laadimine DuckDB-sse",
            "create_database.py",
            [
                "--db", DB_PATH,
                "--events", EVENTS_PATH,
            ],
        ),
        (
            "Hingamissündmuste ajatelje loomine",
            "create_events_timeline.py",
            [
                "--db", DB_PATH,
            ],
        ),
        (
            "PLD mõõtmiste eksport",
            "export_pld.py",
            [
                "--raw", ARCHIVE_DIR / "DATALOG",
                "--output", PLD_DIR,
                "--db", DB_PATH,
            ],
        ),
        (
            "PLD mõõtmiste DuckDB vaate loomine",
            "create_pld_view.py",
            [
                "--db", DB_PATH,
                "--pld-dir", TEST_DIR / "pld",
            ],
        ),
        (
            "BRP failide indekseerimine",
            "index_brp.py",
            [],
        ),
        (
            "STR päevakokkuvõtete eksport",
            "export_daily_summary.py",
            [
                "--source", ARCHIVE_DIR / "STR.edf",
                "--output", TEST_DIR / "daily_summary.csv",
            ],
        ),
        (
            "STR päevakokkuvõtete laadimine DuckDB-sse",
            "load_daily_summary.py",
            [
                "--db", DB_PATH,
                "--csv", TEST_DIR / "daily_summary.csv",
            ],
        ),
        (
            "Maski kasutussessioonide eksport",
            "export_mask_sessions.py",
            [
                "--source", ARCHIVE_DIR / "STR.edf",
                "--output", TEST_DIR / "mask_sessions.csv",
            ],
        ),
        (
            "Maski kasutussessioonide laadimine DuckDB-sse",
            "load_mask_sessions.py",
            [
                "--db", DB_PATH,
                "--csv", TEST_DIR / "mask_sessions.csv",
            ],
        ),
        (
            "Sündmuste ja sessioonide valideerimine",
            "validate_event_sessions.py",
            [
                "--db", DB_PATH,
            ],
        ),
        (
            "Sessioonipõhise analüüsivaate loomine",
            "create_views.py",
            [
                "--db", DB_PATH,
            ],
        ),
        (
            "PLD mõõtmiste sidumine sessioonidega",
            "create_pld_session_view.py",
            [
                "--db", DB_PATH,
            ],
        ),
        (
            "PLD sessioonide koondnäitajate loomine",
            "create_pld_summary.py",
            [
                "--db", DB_PATH,
            ],
        ),
        (
            "Andmekvaliteedi kontroll",
            "validate_data_quality.py",
            [
                "--db", DB_PATH,
            ],
        ),
    ]

    for name, script, arguments in steps:
        run_step(name, script, arguments)

    finished = datetime.now()
    duration = (finished - started).total_seconds()

    print("\n" + "=" * 65)
    print("PIPELINE EDUKALT LÕPETATUD")
    print("=" * 65)
    print(f"Algus: {started:%Y-%m-%d %H:%M:%S}")
    print(f"Lõpp:  {finished:%Y-%m-%d %H:%M:%S}")
    print(f"Kestus: {duration:.2f} sekundit")
    print(f"Andmebaas: {DB_PATH}")
    print(f"PLD andmed: {PLD_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CPAP andmetöötluse töövoog"
    )

    parser.add_argument(
        "--sd",
        type=Path,
        default=None,
        help="SD-kaardi juurkaust, nt E:\\",
    )

    args = parser.parse_args()

    try:
        run_pipeline(sd_path=args.sd)
    except (OSError, RuntimeError) as error:
        print(f"\nPIPELINE KATKES: {error}", file=sys.stderr)
        sys.exit(1)
