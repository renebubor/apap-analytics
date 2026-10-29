from pathlib import Path
import argparse
import sys
import duckdb

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_DIR / 'data' / 'pipeline_test' / 'analytics_fresh.duckdb'


def validate_event_sessions(db_path):
    """Kontrollib EVE sündmuste sidumist STR maskisessioonidega."""
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f'Andmebaasi ei leitud: {db_path}')

    with duckdb.connect(str(db_path), read_only=True) as con:
        matches = con.execute('''
            SELECT e.event_id, e.event_end, e.event_type,
                   e.duration_seconds, COUNT(s.session_id) AS match_count
            FROM events_timeline e
            LEFT JOIN mask_sessions s
              ON e.event_end >= s.start_time AND e.event_end < s.end_time
            GROUP BY e.event_id, e.event_end, e.event_type, e.duration_seconds
            ORDER BY e.event_end
        ''').fetchall()
        unmatched = [r for r in matches if r[4] == 0]
        multiple = [r for r in matches if r[4] > 1]
        print('\nSündmuste ja sessioonide kontroll')
        print('-' * 65)
        print(f'Sündmusi kokku: {len(matches)}')
        print(f'Ühe sessiooniga seotud: {sum(r[4] == 1 for r in matches)}')
        print(f'Sessioonita sündmusi: {len(unmatched)}')
        print(f'Mitme sessiooniga seotud: {len(multiple)}')
        for r in unmatched:
            print(f'SESSIOONITA: {r[1]} | {r[2]} | ID: {r[0]}')
        for r in multiple:
            print(f'MITU SESSIOONI: {r[1]} | {r[2]} | seoseid: {r[4]}')

        # STR sessiooniajad on minutitäpsusega; piiripealsus on hoiatus.
        boundary = con.execute('''
            SELECT e.event_id, e.event_type, e.event_end,
                   e.duration_seconds, s.session_id
            FROM events_timeline e
            JOIN mask_sessions s
              ON e.event_end >= s.start_time AND e.event_end < s.end_time
            WHERE e.event_start < s.start_time
            ORDER BY e.event_end
        ''').fetchall()
        print(f'Sessiooni piiridest väljuvaid sündmusi: {len(boundary)}')
        for r in boundary:
            print(f'PIIRIPEALNE: {r[2]} | {r[1]} | {r[3]} s | sessioon {r[4]}')

        rows = con.execute('''
            SELECT s.session_id, s.duration_minutes,
                   COUNT(e.event_id),
                   COUNT(e.event_id) FILTER (WHERE e.event_type = 'Obstructive Apnea'),
                   COUNT(e.event_id) FILTER (WHERE e.event_type = 'Central Apnea'),
                   COUNT(e.event_id) FILTER (WHERE e.event_type = 'Hypopnea')
            FROM mask_sessions s
            LEFT JOIN events_timeline e
              ON e.event_end >= s.start_time AND e.event_end < s.end_time
            GROUP BY s.session_id, s.duration_minutes, s.start_time
            ORDER BY s.start_time
        ''').fetchall()
        print('\nSessioonide kokkuvõte:')
        for sid, duration, total, oa, ca, h in rows:
            ahi = (oa + ca + h) * 60 / duration if duration is not None and duration > 0 else None
            d = f'{duration:.0f}' if duration is not None else 'N/A'
            a = f'{ahi:.2f}' if ahi is not None else 'N/A'
            print(f'{sid} | {d} min | OA {oa} | CA {ca} | H {h} | AHI {a}')

        if unmatched or multiple:
            print('\nKONTROLL EBAÕNNESTUS')
            return False
        print('\nKONTROLL LÄBITUD HOIATUSEGA' if boundary else '\nKONTROLL EDUKALT LÄBITUD')
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='EVE sündmuste ja STR sessioonide kontroll')
    parser.add_argument('--db', default=str(DEFAULT_DB))
    args = parser.parse_args()
    try:
        sys.exit(0 if validate_event_sessions(args.db) else 1)
    except (OSError, duckdb.Error) as error:
        print(f'VIGA: {error}')
        sys.exit(1)
