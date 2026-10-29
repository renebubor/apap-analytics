from pathlib import Path
import argparse
import duckdb

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_DIR / 'data' / 'pipeline_test' / 'analytics_fresh.duckdb'


def create_views(db_path):
    """Loob sessioonipõhise hingamissündmuste analüüsivaate."""
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f'Andmebaasi ei leitud: {db_path}')
    with duckdb.connect(str(db_path)) as con:
        con.execute('''
            CREATE OR REPLACE VIEW session_analysis AS
            SELECT s.session_id, s.therapy_date, s.session_number,
                   s.start_time, s.end_time, s.duration_minutes,
                   COUNT(e.event_id) AS total_events,
                   COUNT(e.event_id) FILTER (
                       WHERE e.event_type = 'Obstructive Apnea'
                   ) AS obstructive_events,
                   COUNT(e.event_id) FILTER (
                       WHERE e.event_type = 'Central Apnea'
                   ) AS central_events,
                   COUNT(e.event_id) FILTER (
                       WHERE e.event_type = 'Hypopnea'
                   ) AS hypopnea_events,
                   ROUND(COUNT(e.event_id) FILTER (
                       WHERE e.event_type IN (
                           'Obstructive Apnea', 'Central Apnea', 'Hypopnea'
                       )
                   ) * 60.0 / NULLIF(s.duration_minutes, 0), 2) AS calculated_ahi
            FROM mask_sessions s
            LEFT JOIN events e
              ON e.event_time >= s.start_time AND e.event_time < s.end_time
            GROUP BY s.session_id, s.therapy_date, s.session_number,
                     s.start_time, s.end_time, s.duration_minutes
        ''')
        rows = con.execute('''
            SELECT session_id, duration_minutes, total_events, calculated_ahi
            FROM session_analysis ORDER BY start_time
        ''').fetchall()
        source_count = con.execute('SELECT COUNT(*) FROM mask_sessions').fetchone()[0]
        event_count = con.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        view_event_count = sum(row[2] for row in rows)
        print('\nSessioonipõhine analüüs:')
        print('-' * 75)
        for sid, duration, events, ahi in rows:
            d = f'{duration:.0f}' if duration is not None else 'N/A'
            a = f'{ahi:.2f}' if ahi is not None else 'N/A'
            print(f'{sid} | {d} min | {events} sündmust | AHI {a}')
        print('\nKontroll:')
        print(f'Sessioone lähteandmetes: {source_count}')
        print(f'Sessioone analüüsivaates: {len(rows)}')
        print(f'Sündmusi lähteandmetes: {event_count}')
        print(f'Sündmusi analüüsivaates: {view_event_count}')
        if len(rows) != source_count:
            raise ValueError('Sessioonide arv ei vasta lähteandmetele')
        if view_event_count != event_count:
            raise ValueError('Sündmuste arv ei vasta lähteandmetele')
        print('\nKONTROLL OK')
        print("DuckDB vaade 'session_analysis' on loodud.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sessioonipõhise analüüsivaate loomine')
    parser.add_argument('--db', default=str(DEFAULT_DB))
    args = parser.parse_args()
    create_views(args.db)
