"""Generate fully synthetic APAP demo data; never reads real therapy files.

Run from project root: python demo/generate_demo_data.py
Requires: duckdb, numpy, pandas, pyedflib (existing project requirements).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import random
import shutil

import duckdb
import numpy as np
import pandas as pd
import pyedflib

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'demo' / 'data'
DB = OUTPUT / 'apap_demo.duckdb'
PLD = OUTPUT / 'pld'
BRP = OUTPUT / 'brp'
SEED = 20261029
EVENT_TYPES = ('Obstructive Apnea', 'Central Apnea', 'Hypopnea')


def generate() -> None:
    # Refuse to overwrite an existing directory, except our explicitly designated demo/data.
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    PLD.mkdir(parents=True)
    BRP.mkdir(parents=True)
    rng = random.Random(SEED)
    np_rng = np.random.default_rng(SEED)
    nights = []
    sessions = []
    events = []
    brp_specs = []
    # Deliberately chosen scenarios; other nights have low-to-moderate event counts.
    scenarios = {4: ('obstructive', 60), 10: ('central', 34),
                 17: ('hypopnea', 45), 23: ('mixed', 48)}
    start_day = datetime(2026, 9, 1)
    event_counter = 0
    all_pld = []

    for day_no in range(30):
        therapy_date = (start_day + timedelta(days=day_no)).date()
        night_start = datetime.combine(therapy_date, datetime.min.time()) + timedelta(hours=22, minutes=40)
        split = day_no in (7, 18, 26)
        total_minutes = 420 if not split else 390
        if split:
            parts = [(night_start, 170), (night_start + timedelta(minutes=195), 220)]
        else:
            parts = [(night_start, total_minutes)]
        scenario, target = scenarios.get(day_no, ('ordinary', rng.randint(4, 16)))
        assigned = 0
        for session_number, (session_start, duration) in enumerate(parts, 1):
            sid = f'DEMO-{therapy_date:%Y%m%d}-{session_number:02d}'
            session_end = session_start + timedelta(minutes=duration)
            sessions.append((sid, therapy_date, session_number, session_start, session_end, float(duration)))
            count = round(target * duration / total_minutes)
            if session_number == len(parts):
                count = target - assigned
            # Leave at least 3 minutes on each side, avoid overlapping events.
            offsets = sorted(rng.sample(range(180, duration * 60 - 180, 45), count))
            for offset in offsets:
                length = rng.randint(11, 24)
                end = session_start + timedelta(seconds=offset)
                if scenario == 'obstructive':
                    kind = rng.choices(EVENT_TYPES, weights=[0.80, 0.05, 0.15])[0]
                elif scenario == 'central':
                    kind = rng.choices(EVENT_TYPES, weights=[0.10, 0.80, 0.10])[0]
                elif scenario == 'hypopnea':
                    kind = rng.choices(EVENT_TYPES, weights=[0.10, 0.05, 0.85])[0]
                else:
                    kind = rng.choices(EVENT_TYPES, weights=[0.45, 0.15, 0.40])[0]
                event_counter += 1
                events.append((f'DEMO-E{event_counter:05d}', f'demo_{therapy_date:%Y%m%d}_EVE.edf',
                               session_start, float(offset), end, kind, float(length)))
                assigned += 1

            # Missing PLD for one session: intentional data quality case.
            if day_no == 18 and session_number == 1:
                continue
            ticks = np.arange(0, duration * 60, 10, dtype=np.int32)
            elapsed = ticks.astype(float)
            pressure = (7.0 + 1.2 * np.sin(elapsed / 1800) +
                        0.5 * np.sin(elapsed / 270) + np_rng.normal(0, 0.12, len(ticks)))
            if scenario != 'ordinary':
                pressure += 1.2
            pressure = np.clip(pressure, 5.5, 13)
            leak = np.clip(4.5 + 2.0 * np.sin(elapsed / 900) + np_rng.normal(0, 0.8, len(ticks)), 0, None)
            if day_no == 12:
                leak += 15 * ((elapsed > 4200) & (elapsed < 6900))
            resp = np.clip(14.5 + 1.2 * np.sin(elapsed / 430) + np_rng.normal(0, 0.6, len(ticks)), 8, 22)
            tidal = np.clip(0.46 + 0.04 * np.sin(elapsed / 250) + np_rng.normal(0, 0.018, len(ticks)), 0.25, 0.8)
            file_name = f'demo_{therapy_date:%Y%m%d}_{session_number:02d}_PLD.edf'
            df = pd.DataFrame({
                'timestamp': pd.Timestamp(session_start) + pd.to_timedelta(ticks, unit='s'),
                'mask_pressure': pressure + np_rng.normal(0, 0.07, len(ticks)),
                'pressure': pressure,
                'epr_pressure': np.maximum(4, pressure - 2.0),
                'leak_l_s': leak / 60.0,
                'resp_rate': resp,
                'tidal_volume': tidal,
                'minute_ventilation': tidal * resp,
                'snore': np.clip(np_rng.normal(0.06, 0.05, len(ticks)), 0, 1),
                'flow_limitation': np.clip(np_rng.normal(0.10 if scenario == 'ordinary' else 0.30, 0.08, len(ticks)), 0, 1),
                'source_file': file_name,
            })
            all_pld.append(df)

        # Daily AHI derives from the same event count and total mask-use minutes.
        # Better scope: events for this night only, regardless of midnight rollover.
        nightly = [e for e in events if night_start <= e[4] < night_start + timedelta(hours=10)]
        counts = {k: sum(e[5] == k for e in nightly) for k in EVENT_TYPES}
        hrs = total_minutes / 60.0
        oai, cai, hi = (counts[k] / hrs for k in EVENT_TYPES)
        ahi = oai + cai + hi
        # One intentionally incomplete STR row, no fabricated negative clinical values.
        missing = day_no == 21
        nights.append((therapy_date, float(total_minutes), float(total_minutes),
                       None if missing else round(ahi, 3), round(oai + cai, 3), round(hi, 3),
                       round(oai, 3), round(cai, 3), 0.0,
                       None if missing else 9.6 + (1 if scenario != 'ordinary' else 0),
                       8.0 if day_no != 12 else 22.0, f'demo_{therapy_date:%Y%m%d}_STR.edf'))
        if day_no in (4, 10, 17, 23):
            # BRP excerpt around one representative event per scenario, not entire night.
            chosen = next(e for e in nightly if e[5] ==
                          {'obstructive': 'Obstructive Apnea', 'central': 'Central Apnea',
                           'hypopnea': 'Hypopnea', 'mixed': 'Obstructive Apnea'}[scenario])
            brp_specs.append((chosen[4] - timedelta(seconds=chosen[6] + 75),
                              chosen[4] + timedelta(seconds=75),
                              chosen[4] - timedelta(seconds=chosen[6]), chosen[4], chosen[5]))

    with duckdb.connect(str(DB)) as con:
        con.execute('''CREATE TABLE daily_summary (
            therapy_date DATE PRIMARY KEY, usage_minutes DOUBLE, on_duration_minutes DOUBLE,
            ahi DOUBLE, ai DOUBLE, hi DOUBLE, oai DOUBLE, cai DOUBLE, uai DOUBLE,
            pressure_p95 DOUBLE, leak_p95_l_min DOUBLE, source_file VARCHAR)''')
        con.executemany('INSERT INTO daily_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?)', nights)
        con.execute('''CREATE TABLE mask_sessions (
            session_id VARCHAR PRIMARY KEY, therapy_date DATE, session_number INTEGER,
            start_time TIMESTAMP, end_time TIMESTAMP, duration_minutes DOUBLE)''')
        con.executemany('INSERT INTO mask_sessions VALUES (?,?,?,?,?,?)', sessions)
        con.execute('''CREATE TABLE events (
            event_id VARCHAR PRIMARY KEY, source_file VARCHAR, file_start_time TIMESTAMP,
            onset_seconds DOUBLE, event_time TIMESTAMP, event_type VARCHAR, duration_seconds DOUBLE)''')
        con.executemany('INSERT INTO events VALUES (?,?,?,?,?,?,?)', events)
        con.execute('''CREATE OR REPLACE VIEW events_timeline AS SELECT
            event_id, source_file, file_start_time, onset_seconds, event_type, duration_seconds,
            event_time AS event_end,
            event_time - duration_seconds * INTERVAL '1 second' AS event_start FROM events''')
        con.execute('''CREATE OR REPLACE VIEW session_analysis AS SELECT
            s.session_id, s.therapy_date, s.session_number, s.start_time, s.end_time,
            s.duration_minutes, COUNT(e.event_id) AS total_events,
            COUNT(e.event_id) FILTER (WHERE e.event_type='Obstructive Apnea') AS obstructive_events,
            COUNT(e.event_id) FILTER (WHERE e.event_type='Central Apnea') AS central_events,
            COUNT(e.event_id) FILTER (WHERE e.event_type='Hypopnea') AS hypopnea_events,
            ROUND(COUNT(e.event_id) FILTER (WHERE e.event_type IN
                ('Obstructive Apnea','Central Apnea','Hypopnea')) * 60.0 /
                NULLIF(s.duration_minutes,0),2) AS calculated_ahi
            FROM mask_sessions s LEFT JOIN events e
              ON e.event_time >= s.start_time AND e.event_time < s.end_time
            GROUP BY s.session_id,s.therapy_date,s.session_number,s.start_time,s.end_time,s.duration_minutes''')
        # DuckDB writes Parquet without requiring pyarrow.
        con.register('synthetic_pld', pd.concat(all_pld, ignore_index=True))
        out = (PLD / 'synthetic_pld.parquet').as_posix().replace("'", "''")
        con.execute(f"COPY synthetic_pld TO '{out}' (FORMAT PARQUET)")
        con.unregister('synthetic_pld')
        parquet_path = (PLD / '*.parquet').as_posix().replace("'", "''")
        con.execute(f'''CREATE TABLE pld_measurements AS SELECT timestamp,mask_pressure,
            pressure,epr_pressure,leak_l_s,leak_l_s*60 AS leak_l_min,resp_rate,
            tidal_volume,minute_ventilation,snore,flow_limitation,source_file
            FROM read_parquet('{parquet_path}')''')
        con.execute('''CREATE VIEW pld_session_measurements AS
            WITH candidates AS (SELECT s.session_id,s.therapy_date,s.session_number,
                p.timestamp,p.mask_pressure,p.pressure,p.epr_pressure,p.leak_l_min,
                p.resp_rate,p.tidal_volume,p.minute_ventilation,p.snore,p.flow_limitation,
                p.source_file,ROW_NUMBER() OVER (PARTITION BY p.source_file,p.timestamp
                ORDER BY CASE WHEN p.timestamp < s.start_time THEN
                date_diff('second',p.timestamp,s.start_time)
                WHEN p.timestamp > s.end_time THEN date_diff('second',s.end_time,p.timestamp)
                ELSE 0 END,s.start_time,s.session_id) AS rn
            FROM pld_measurements p JOIN mask_sessions s
            ON p.timestamp >= s.start_time - INTERVAL 60 SECOND
            AND p.timestamp <= s.end_time + INTERVAL 60 SECOND)
            SELECT session_id,therapy_date,session_number,timestamp,mask_pressure,
                pressure,epr_pressure,leak_l_min,resp_rate,tidal_volume,
                minute_ventilation,snore,flow_limitation,source_file
            FROM candidates WHERE rn=1''')
        con.execute('''CREATE VIEW pld_session_summary AS
            WITH measurements AS (SELECT session_id,COUNT(*) AS measurement_count,
                ROUND(AVG(pressure),2) AS avg_pressure,
                ROUND(QUANTILE_CONT(pressure,0.95),2) AS pressure_p95,
                ROUND(AVG(leak_l_min),2) AS avg_leak,
                ROUND(QUANTILE_CONT(leak_l_min,0.95),2) AS leak_p95,
                ROUND(AVG(resp_rate),2) AS avg_resp_rate,
                ROUND(AVG(tidal_volume),3) AS avg_tidal_volume,
                ROUND(AVG(minute_ventilation),2) AS avg_minute_ventilation
                FROM pld_session_measurements GROUP BY session_id)
            SELECT s.session_id,s.therapy_date,s.session_number,s.duration_minutes,
                s.total_events,s.obstructive_events,s.central_events,s.hypopnea_events,
                s.calculated_ahi,m.measurement_count,m.avg_pressure,m.pressure_p95,
                m.avg_leak,m.leak_p95,m.avg_resp_rate,m.avg_tidal_volume,m.avg_minute_ventilation
            FROM session_analysis s LEFT JOIN measurements m ON s.session_id=m.session_id''')
        con.execute('''CREATE TABLE brp_file_index (file_path VARCHAR PRIMARY KEY,
            file_name VARCHAR,file_size BIGINT,modified_ns BIGINT,file_start TIMESTAMP,
            file_end TIMESTAMP,frequency DOUBLE,sample_count BIGINT,status VARCHAR,
            error_message VARCHAR)''')

    for i, (file_start, file_end, event_start, event_end, kind) in enumerate(brp_specs, 1):
        frequency = 25
        n = round((file_end - file_start).total_seconds() * frequency)
        seconds = np.arange(n) / frequency
        # Illustration only; NOT physiologically validated or real device output.
        signal = 0.32 * np.sin(2 * np.pi * 0.24 * seconds)
        start_offset = (event_start - file_start).total_seconds()
        end_offset = (event_end - file_start).total_seconds()
        # Apply attenuation to EVERY labelled event overlapping this excerpt.
        # Otherwise a user can select a nearby event and see normal airflow
        # beneath its highlighted region (a misleading demo visualization).
        overlapping = [e for e in events
                       if e[4] > file_start
                       and e[4] - timedelta(seconds=e[6]) < file_end]
        for e in overlapping:
            onset = (e[4] - timedelta(seconds=e[6]) - file_start).total_seconds()
            offset = (e[4] - file_start).total_seconds()
            inside = (seconds >= onset) & (seconds < offset)
            signal[inside] *= 0.35 if e[5] == 'Hypopnea' else 0.025
        signal += np_rng.normal(0, 0.004, n)
        file_path = BRP / f'demo_{i:02d}_BRP.edf'
        header = pyedflib.highlevel.make_header(startdate=file_start)
        signal_header = pyedflib.highlevel.make_signal_header(
            'Flow.40ms', sample_frequency=frequency, physical_min=-1.0,
            physical_max=1.0, digital_min=-32768, digital_max=32767,
            dimension='L/s')
        pyedflib.highlevel.write_edf(str(file_path), [signal], [signal_header], header=header)
        stat = file_path.stat()
        with duckdb.connect(str(DB)) as con:
            con.execute('''INSERT INTO brp_file_index VALUES (?,?,?,?,?,?,?,?,?,?)''',
                        [f'brp/{file_path.name}',file_path.name,stat.st_size,stat.st_mtime_ns,
                         file_start,file_end,float(frequency),int(n),'ok',None])

    with duckdb.connect(str(DB), read_only=True) as con:
        counts = con.execute('''SELECT (SELECT COUNT(*) FROM daily_summary),
            (SELECT COUNT(*) FROM mask_sessions),(SELECT COUNT(*) FROM events),
            (SELECT COUNT(*) FROM pld_measurements),
            (SELECT COUNT(*) FROM brp_file_index)''').fetchone()
        assert counts[0] == 30 and counts[1] == 33 and counts[4] == 4
        assert con.execute('SELECT COUNT(*) FROM session_analysis').fetchone()[0] == 33
        assert con.execute('SELECT COUNT(*) FROM pld_session_summary').fetchone()[0] == 33
        assert con.execute('SELECT SUM(total_events) FROM session_analysis').fetchone()[0] == counts[2]
    print('Demo generated:', DB)
    print('Nights / sessions / events / PLD samples / BRP files:', counts)
    print('WARNING: All values and signals are synthetic; not clinically validated.')


if __name__ == '__main__':
    generate()
