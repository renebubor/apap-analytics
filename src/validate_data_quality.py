from pathlib import Path
import argparse
import duckdb

PROJECT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_DIR / 'data' / 'pipeline_test' / 'analytics_fresh.duckdb'


def validate_data_quality(db_path):
    """Kontrollib CPAP andmete kvaliteeti."""
    db_path = Path(db_path).resolve()
    if not db_path.is_file():
        raise FileNotFoundError(f'Andmebaasi ei leitud: {db_path}')
    warnings, errors = [], []
    with duckdb.connect(str(db_path), read_only=True) as con:
        missing_days = con.execute('''
            SELECT therapy_date FROM daily_summary
            WHERE usage_minutes IS NULL OR ahi IS NULL
               OR leak_p95_l_min IS NULL OR pressure_p95 IS NULL
               OR usage_minutes < 0 OR ahi < 0
               OR leak_p95_l_min < 0 OR pressure_p95 < 0
            ORDER BY therapy_date
        ''').fetchall()
        for (day,) in missing_days:
            warnings.append(f'Puudulik või vigane STR-päevakirje: {day}')

        invalid_brp = con.execute('''
            SELECT file_name, status FROM brp_file_index
            WHERE status IS NULL OR status <> 'ok'
            ORDER BY file_name
        ''').fetchall()
        for file_name, status in invalid_brp:
            warnings.append(f'BRP-fail: {file_name}, staatus: {status}')

        missing_pld = con.execute('''
            SELECT s.session_id
            FROM mask_sessions s
            LEFT JOIN pld_session_summary p ON s.session_id = p.session_id
            GROUP BY s.session_id
            HAVING COUNT(p.session_id) = 0
                OR COALESCE(SUM(p.measurement_count), 0) = 0
            ORDER BY s.session_id
        ''').fetchall()
        for (sid,) in missing_pld:
            warnings.append(f'PLD mõõtmised puuduvad: {sid}')

        # Üks sündmus peab kuuluma täpselt ühte sessiooni.
        matches = con.execute('''
            SELECT e.event_id, COUNT(s.session_id) AS match_count
            FROM events_timeline e
            LEFT JOIN mask_sessions s
              ON e.event_end >= s.start_time AND e.event_end < s.end_time
            GROUP BY e.event_id
        ''').fetchall()
        unmatched = sum(count == 0 for _, count in matches)
        multiple = sum(count > 1 for _, count in matches)
        if unmatched or multiple:
            errors.append(
                'Hingamissündmuste ja sessioonide vastavus ei klapi: '
                f'{unmatched} sidumata, {multiple} mitme seosega'
            )

        pld_total = con.execute('SELECT COUNT(*) FROM pld_measurements').fetchone()[0]
        pld_matched = con.execute('SELECT COUNT(*) FROM pld_session_measurements').fetchone()[0]
        if pld_total != pld_matched:
            errors.append(
                'PLD mõõtmiste ja sessioonide vastavus ei klapi: '
                f'{pld_total} mõõtmist, {pld_matched} seost'
            )

    print('\n' + '=' * 65)
    print('CPAP ANDMEKVALITEEDI KONTROLL')
    print('=' * 65)
    print(f'Andmebaas: {db_path}')
    print(f'\nHoiatusi: {len(warnings)}')
    for warning in warnings:
        print(f'  HOIATUS: {warning}')
    print(f'\nVigu: {len(errors)}')
    for error in errors:
        print(f'  VIGA: {error}')
    print('\n' + '-' * 65)
    if errors:
        print('TULEMUS: ANDMEKVALITEEDI KONTROLL EI LÄBITUD')
        return False
    print('TULEMUS: KONTROLL LÄBITUD HOIATUSTEGA' if warnings else 'TULEMUS: KONTROLL LÄBITUD')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='CPAP andmekvaliteedi kontroll')
    parser.add_argument('--db', default=str(DEFAULT_DB))
    args = parser.parse_args()
    try:
        success = validate_data_quality(args.db)
    except (OSError, duckdb.Error) as error:
        print(f'ANDMEKVALITEEDI VIGA: {error}')
        raise SystemExit(1) from error
    raise SystemExit(0 if success else 1)
