from pathlib import Path
from datetime import datetime
import queue
import json
import os
import socket
import string
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import webbrowser
from urllib.parse import urlencode

import customtkinter as ctk

ROOT = Path(__file__).resolve().parent
PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
PIPELINE = ROOT / 'src' / 'pipeline.py'
DASHBOARD = ROOT / 'dashboard' / 'app.py'
DB = ROOT / 'data' / 'pipeline_test' / 'analytics_fresh.duckdb'
URL = 'http://localhost:8501'

NAVY = '#132B48'
BLUE = '#1769D2'
GREEN = '#09824B'
BG = '#F4F7FB'
TEXT = '#172B46'
MUTED = '#63758A'
TRANSLATIONS = {'home': {'et': 'Avaleht', 'en': 'Home'}, 'import': {'et': 'Andmete laadimine', 'en': 'Import data'}, 'analysis': {'et': 'Andmete vaatamine', 'en': 'View analytics'}, 'info': {'et': 'Info ja tulevik', 'en': 'About & roadmap'}, 'hero': {'et': 'Raviandmed, visualiseerimine ja kvaliteedikontroll ühes kohas.', 'en': 'Therapy data, visualization and quality checks in one place.'}, 'import_title': {'et': 'Laadi APAP andmed', 'en': 'Import APAP data'}, 'import_desc': {'et': 'Tuvasta SD-kaart, kopeeri uued failid ja käivita 15-etapiline andmetöötlus.', 'en': 'Detect an SD card, synchronize new files and run the 15-step pipeline.'}, 'import_button': {'et': 'Andmete laadimine', 'en': 'Import data'}, 'view_title': {'et': 'Ava andmete ülevaade', 'en': 'Open analytics overview'}, 'view_desc': {'et': 'Vaata raviöid, sündmusi ja hingamissignaali Streamliti dashboardis.', 'en': 'Explore therapy nights, events and breathing signals in Streamlit.'}, 'view_button': {'et': 'Ava analüüs', 'en': 'Open analytics'}, 'database': {'et': 'Andmebaas', 'en': 'Database'}, 'exists': {'et': 'Olemas', 'en': 'Available'}, 'missing': {'et': 'Puudub', 'en': 'Missing'}, 'db_missing': {'et': 'Andmebaasi ei leitud', 'en': 'Database not found'}, 'sd_card': {'et': 'SD-kaart', 'en': 'SD card'}, 'sd_check': {'et': 'Kontrolli laadimise vaates', 'en': 'Check on import page'}, 'sd_search': {'et': 'Automaatne otsing enne importi', 'en': 'Auto-detection before import'}, 'last_import': {'et': 'Viimane import', 'en': 'Last import'}, 'never': {'et': 'Pole veel imporditud', 'en': 'No imports recorded'}, 'session': {'et': 'Salvestatud viimase impordi tulemus', 'en': 'Saved result of latest import'}, 'import_sub': {'et': 'SD-kaardi automaatne tuvastamine ja andmetöötluse jälgimine', 'en': 'Automatic SD card detection and pipeline monitoring'}, 'not_searched': {'et': 'SD-kaarti pole veel otsitud.', 'en': 'SD card not yet scanned.'}, 'detect': {'et': 'Otsi SD-kaarti', 'en': 'Find SD card'}, 'start': {'et': 'Käivita import', 'en': 'Start import'}, 'working': {'et': 'Import käib...', 'en': 'Import in progress...'}, 'ready': {'et': 'Valmis', 'en': 'Ready'}, 'view_sub': {'et': 'Interaktiivne APAP ravi analüüs Streamlitiga', 'en': 'Interactive APAP therapy analysis with Streamlit'}, 'view_features': {
    'et': 'Raviööde ülevaade  •  Sessiooni detailanalüüs  •  Hingamise detailanalüüs', 'en': 'Therapy nights  •  Session details  •  Breathing details'}, 'open_browser': {'et': 'Ava dashboard brauseris', 'en': 'Open dashboard in browser'}, 'stop_dashboard': {'et': 'Peata rakenduse käivitatud dashboard', 'en': 'Stop dashboard started by this app'}, 'lock_note': {'et': 'Märkus: andmete importimise ajaks peab dashboard olema suletud.', 'en': 'Note: Stop the dashboard before importing data.'}, 'about_title': {'et': 'Projektist', 'en': 'About the project'}, 'about_sub': {'et': 'Ühine platvorm APAP ja tulevastele Samsung Healthi andmetele', 'en': 'One platform for APAP and future Samsung Health data'}, 'samsung_desc': {'et': 'Planeeritud laiendus. Andmete eksport ja ajatempli täpsus tuleb eraldi kontrollida.', 'en': 'Planned extension. Export format and timestamp precision still need verification.'}, 'privacy': {'et': 'Andmekaitse', 'en': 'Data privacy'}, 'privacy_desc': {'et': 'Isiklikud raviandmed jäävad kohalikku arvutisse; avalikku GitHubi ainult kood ja näidisandmed.', 'en': 'Personal therapy data stays on the local computer; only code and sample data go to public GitHub.'}, 'planned': {'et': 'ResMed APAP  •  Samsung Health (plaanis)', 'en': 'ResMed APAP  •  Samsung Health (planned)'}, 'summary': {'et': 'Raviandmete lühikokkuvõte', 'en': 'Therapy summary'}, 'nights': {'et': 'Raviöid', 'en': 'Therapy nights'}, 'sessions': {'et': 'Sessioone', 'en': 'Sessions'}, 'events': {'et': 'Sündmusi', 'en': 'Events'}, 'latest_night': {'et': 'Viimane raviöö', 'en': 'Latest therapy night'}, 'no_summary': {'et': 'Kokkuvõtet ei saa praegu lugeda.', 'en': 'Summary is currently unavailable.'}, 'last_success': {'et': 'Viimane edukas import', 'en': 'Last successful import'}, 'last_failed': {'et': 'Viimane import ebaõnnestus', 'en': 'Last import failed'}, 'found': {'et': 'Leitud', 'en': 'Found'}, 'not_found': {'et': 'Ühtegi sobivat SD-kaarti ei leitud.', 'en': 'No suitable SD card found.'}, 'future': {'et': 'Samsung Health (tulevikus)', 'en': 'Samsung Health (future)'}}
STATE_FILE = ROOT / "data" / "app_state.json"


def read_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(
        state, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(STATE_FILE)


ctk.set_appearance_mode('light')
ctk.set_default_color_theme('blue')


def port_open(port=8501):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=0.3):
            return True
    except OSError:
        return False


def find_cards():
    matches = []
    for letter in string.ascii_uppercase:
        drive = Path(f'{letter}:\\')
        try:
            if (drive / 'DATALOG').is_dir() and (drive / 'STR.edf').is_file():
                matches.append(drive)
        except (OSError, PermissionError):
            continue
    return matches


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Sleep & PAP Analytics')
        self.geometry('1180x760')
        self.minsize(960, 650)
        self.configure(fg_color=BG)
        self.state_data = read_state()
        self.language = self.state_data.get('language', 'et')
        if self.language not in ('et', 'en'):
            self.language = 'et'
        self.events = queue.Queue()
        self.running = False
        self.dashboard_process = None
        self.dashboard_mode = None
        self.import_process = None
        self.page = None
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self, width=235, corner_radius=0, fg_color='#E8F0F9')
        self.sidebar.grid(row=0, column=0, sticky='nsw')
        self.sidebar.grid_propagate(False)
        ctk.CTkLabel(self.sidebar, text='◉  Sleep & PAP', font=(
            'Segoe UI', 21, 'bold'), text_color=NAVY).pack(anchor='w', padx=20, pady=(30, 5))
        ctk.CTkLabel(self.sidebar, text='ANALYTICS', font=(
            'Segoe UI', 11, 'bold'), text_color=MUTED).pack(anchor='w', padx=48, pady=(0, 34))
        self.nav = {}
        self.nav_icons = {'home': '⌂', 'import': '⇪',
                          'analysis': '▥', 'info': 'ⓘ'}
        for key in ('home', 'import', 'analysis', 'info'):
            title = self.nav_icons[key] + '   ' + self.t(key)
            btn = ctk.CTkButton(self.sidebar, text=title, anchor='w', height=46, corner_radius=10,
                                fg_color='transparent', hover_color='#D5E5F7', text_color=NAVY,
                                font=('Segoe UI', 14), command=lambda k=key: self.show_page(k))
            btn.pack(fill='x', padx=12, pady=4)
            self.nav[key] = btn
        self.sidebar_footer = ctk.CTkLabel(self.sidebar, text=self.t('planned') + '\nVersion 0.3',
                     font=('Segoe UI', 11), text_color=MUTED, justify='left')
        self.sidebar_footer.pack(side='bottom', anchor='w', padx=20, pady=25)

        self.lang_row = ctk.CTkFrame(self.sidebar, fg_color='transparent')
        self.lang_row.pack(side='bottom', fill='x', padx=16, pady=(0, 8))
        self.lang_choice = ctk.CTkSegmentedButton(
            self.lang_row, values=['ET', 'EN'], command=self.set_language, height=30)
        self.lang_choice.pack(fill='x')
        self.lang_choice.set(self.language.upper())

        self.content = ctk.CTkScrollableFrame(
            self, fg_color=BG, corner_radius=0)
        self.content.grid(row=0, column=1, sticky='nsew')
        self.content.grid_columnconfigure(0, weight=1)
        self.show_page('home')
        self.after(200, self.poll_events)

    def t(self, key):
        return TRANSLATIONS[key][self.language]

    def set_language(self, value):
        self.language = value.lower()
        self.state_data['language'] = self.language
        save_state(self.state_data)
        for key, btn in self.nav.items():
            btn.configure(text=self.nav_icons[key] + '   ' + self.t(key))
        self.sidebar_footer.configure(text=self.t('planned') + '\nVersion 0.3')
        self.show_page(self.page or 'home')

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def heading(self, title, subtitle):
        ctk.CTkLabel(self.content, text=title, text_color=TEXT,
                     font=('Segoe UI', 28, 'bold')).pack(anchor='w', padx=26, pady=(24, 4))
        ctk.CTkLabel(self.content, text=subtitle, text_color=MUTED,
                     font=('Segoe UI', 13)).pack(anchor='w', padx=26, pady=(0, 22))

    def show_page(self, page):
        self.page = page
        self.clear_content()
        for key, btn in self.nav.items():
            btn.configure(fg_color=BLUE if key == page else 'transparent',
                          text_color='white' if key == page else NAVY)
        if page == 'home':
            self.home()
        elif page == 'import':
            self.import_page()
        elif page == 'analysis':
            self.analysis_page()
        else:
            self.info_page()

    def last_import_text(self):
        item = self.state_data.get('last_import')
        if not item:
            return self.t('never')
        return (self.t('last_success') if item.get('success') else self.t('last_failed')) + '\n' + item.get('timestamp', '')[:16].replace('T', ' ')

    def therapy_stats(self):
        if not DB.is_file():
            return None
        try:
            import duckdb
            with duckdb.connect(str(DB), read_only=True) as con:
                nights = con.execute(
                    'SELECT COUNT(*) FROM daily_summary WHERE usage_minutes >= 0').fetchone()[0]
                sessions = con.execute(
                    'SELECT COUNT(*) FROM mask_sessions').fetchone()[0]
                events = con.execute(
                    'SELECT COUNT(*) FROM events_timeline').fetchone()[0]
                latest = con.execute(
                    'SELECT MAX(therapy_date) FROM daily_summary WHERE usage_minutes >= 0').fetchone()[0]
            return (nights, sessions, events, str(latest) if latest else '—')
        except Exception:
            return None

    def summary_card(self):
        stats = self.therapy_stats()
        frame = ctk.CTkFrame(self.content, fg_color='white', border_width=1,
                             border_color='#DCE6F1', corner_radius=12)
        frame.pack(fill='x', padx=26, pady=(0, 22))
        ctk.CTkLabel(frame, text=self.t('summary'), text_color=TEXT,
                     font=('Segoe UI', 17, 'bold')).pack(anchor='w', padx=18, pady=(15, 8))
        if stats is None:
            ctk.CTkLabel(frame, text=self.t('no_summary'), text_color=MUTED,
                         font=('Segoe UI', 13)).pack(anchor='w', padx=18, pady=(0, 15))
            return
        row = ctk.CTkFrame(frame, fg_color='transparent')
        row.pack(fill='x', padx=18, pady=(0, 16))
        for index, (key, value) in enumerate(zip(('nights', 'sessions', 'events', 'latest_night'), stats)):
            cell = ctk.CTkFrame(row, fg_color='#F4F7FB', corner_radius=9)
            cell.grid(row=0, column=index, padx=5, sticky='nsew')
            row.grid_columnconfigure(index, weight=1)
            ctk.CTkLabel(cell, text=self.t(key), text_color=MUTED,
                         font=('Segoe UI', 12)).pack(anchor='w', padx=12, pady=(10, 2))
            ctk.CTkLabel(cell, text=str(value), text_color=TEXT,
                         font=('Segoe UI', 17, 'bold')).pack(anchor='w', padx=12, pady=(0, 10))

    def home(self):
        hero = ctk.CTkFrame(self.content, fg_color=NAVY, corner_radius=16)
        hero.pack(fill='x', padx=26, pady=(28, 22))
        ctk.CTkLabel(hero, text='Sleep & PAP Analytics', text_color='white',
                     font=('Segoe UI', 32, 'bold')).pack(anchor='w', padx=30, pady=(26, 6))
        ctk.CTkLabel(hero, text=self.t('hero'),
                     text_color='#DCE9F6', font=('Segoe UI', 14)).pack(anchor='w', padx=30, pady=(0, 30))

        cards = ctk.CTkFrame(self.content, fg_color='transparent')
        cards.pack(fill='x', padx=26)
        cards.grid_columnconfigure((0, 1), weight=1, uniform='cards')
        self.action_card(cards, 0, '#E7F6ED', self.t('import_title'),
                         self.t('import_desc'),
                         self.t('import_button'), GREEN, lambda: self.show_page('import'))
        self.action_card(cards, 1, '#E7F0FD', self.t('view_title'),
                         self.t('view_desc'),
                         self.t('view_button'), BLUE, self.open_dashboard)

        status = ctk.CTkFrame(self.content, fg_color='transparent')
        status.pack(fill='x', padx=26, pady=22)
        status.grid_columnconfigure((0, 1), weight=1, uniform='statuses')
        self.status_card(status, 0, self.t('database'), self.t('exists') if DB.is_file() else self.t('missing'),
                         DB.name if DB.is_file() else self.t('db_missing'))
        self.status_card(status, 1, self.t('sd_card'), self.t('sd_check'),
                         self.t('sd_search'))
        self.status_card(status, 2, self.t('last_import'), self.last_import_text(),
                         self.t('session'))
        self.summary_card()

    def action_card(self, parent, col, color, title, desc, button, accent, command):
        frame = ctk.CTkFrame(parent, fg_color=color, corner_radius=15)
        frame.grid(row=0, column=col, sticky='nsew',
                   padx=(0, 9) if col == 0 else (9, 0))
        ctk.CTkLabel(frame, text=title, text_color=TEXT, font=(
            'Segoe UI', 20, 'bold')).pack(anchor='w', padx=22, pady=(22, 9))
        ctk.CTkLabel(frame, text=desc, text_color='#42556B', font=('Segoe UI', 13),
                     wraplength=325, justify='left', height=65).pack(anchor='w', padx=22)
        ctk.CTkButton(frame, text=button, fg_color=accent, height=44,
                      command=command).pack(fill='x', padx=22, pady=(15, 22))

    def status_card(self, parent, col, title, value, detail):
        frame = ctk.CTkFrame(parent, fg_color='white', border_width=1,
                             border_color='#DCE6F1', corner_radius=12)
        frame.grid(row=0, column=col, sticky='nsew', padx=(
            0, 8) if col == 0 else (8, 0), pady=3)
        ctk.CTkLabel(frame, text=title, text_color=MUTED, font=(
            'Segoe UI', 12)).pack(anchor='w', padx=17, pady=(15, 5))
        ctk.CTkLabel(frame, text=value, text_color=TEXT, font=('Segoe UI', 14, 'bold'),
                     wraplength=225, justify='left').pack(anchor='w', padx=17)
        ctk.CTkLabel(frame, text=detail, text_color=MUTED, font=('Segoe UI', 11),
                     wraplength=225, justify='left').pack(anchor='w', padx=17, pady=(7, 16))

    def import_page(self):
        self.heading(self.t('import'), self.t('import_sub'))
        box = ctk.CTkFrame(self.content, fg_color='white', corner_radius=14)
        box.pack(fill='x', padx=26, pady=(0, 15))
        self.sd_label = ctk.CTkLabel(box, text=self.t('not_searched'), text_color=TEXT,
                                     font=('Segoe UI', 14))
        self.sd_label.pack(anchor='w', padx=20, pady=(20, 12))
        row = ctk.CTkFrame(box, fg_color='transparent')
        row.pack(fill='x', padx=20, pady=(0, 18))
        self.detect_btn = ctk.CTkButton(row, text=self.t(
            'detect'), command=self.detect_and_show, width=160)
        self.detect_btn.pack(side='left', padx=(0, 10))
        self.import_btn = ctk.CTkButton(row, text=self.t('start'), fg_color=GREEN,
                                        command=self.start_import, width=170)
        self.import_btn.pack(side='left')
        if self.running:
            self.detect_btn.configure(state='disabled')
            self.import_btn.configure(state='disabled')
        self.status_label = ctk.CTkLabel(self.content, text=self.t('working') if self.running else self.t('ready'),
                                         font=('Segoe UI', 14, 'bold'), text_color=TEXT)
        self.status_label.pack(anchor='w', padx=28, pady=(5, 4))
        self.progress = ctk.CTkProgressBar(self.content, mode='indeterminate')
        self.progress.pack(fill='x', padx=28, pady=(5, 14))
        if self.running:
            self.progress.start()
        else:
            self.progress.set(0)
        self.log = ctk.CTkTextbox(
            self.content, height=300, font=('Consolas', 12), wrap='word')
        self.log.pack(fill='both', expand=True, padx=26, pady=(0, 20))
        self.log.insert('end', '\n'.join(
            getattr(self, 'log_lines', ['Rakendus on valmis.'])) + '\n')
        self.log.configure(state='disabled')

    def analysis_page(self):
        self.heading(self.t('analysis'), self.t('view_sub'))
        frame = ctk.CTkFrame(self.content, fg_color='white', corner_radius=14)
        frame.pack(fill='x', padx=26)
        ctk.CTkLabel(frame, text=self.t('view_features'),
                     text_color=TEXT, font=('Segoe UI', 15), wraplength=680).pack(anchor='w', padx=24, pady=(24, 16))
        demo_label = 'Ava demoandmed' if self.language == 'et' else 'Open demo data'
        personal_label = 'Ava isiklikud andmed' if self.language == 'et' else 'Open personal data'
        ctk.CTkButton(frame, text=demo_label, height=48,
                      command=lambda: self.open_dashboard('demo')).pack(anchor='w', padx=24, pady=(0, 12))
        ctk.CTkButton(frame, text=personal_label, height=48,
                      fg_color=GREEN,
                      command=lambda: self.open_dashboard('personal')).pack(anchor='w', padx=24, pady=(0, 12))
        ctk.CTkButton(frame, text=self.t('stop_dashboard'), height=38,
                      fg_color='#6C7B8D', hover_color='#506176', command=self.stop_dashboard).pack(anchor='w', padx=24, pady=(0, 24))
        ctk.CTkLabel(self.content, text=self.t('lock_note'),
                     text_color=MUTED, font=('Segoe UI', 12)).pack(anchor='w', padx=28, pady=18)

    def info_page(self):
        self.heading(self.t('about_title'), self.t('about_sub'))
        for title, body in [
            ('ResMed APAP', 'SD-kaardi EDF-failid → kohalik arhiiv → DuckDB / Parquet → Streamlit.'),
            ('Samsung Health', self.t('samsung_desc')),
            (self.t('privacy'), self.t('privacy_desc')),
        ]:
            frame = ctk.CTkFrame(
                self.content, fg_color='white', corner_radius=12)
            frame.pack(fill='x', padx=26, pady=7)
            ctk.CTkLabel(frame, text=title, text_color=TEXT, font=(
                'Segoe UI', 17, 'bold')).pack(anchor='w', padx=20, pady=(16, 5))
            ctk.CTkLabel(frame, text=body, text_color=MUTED, font=('Segoe UI', 13),
                         wraplength=720, justify='left').pack(anchor='w', padx=20, pady=(0, 17))

    def add_log(self, line):
        if not hasattr(self, 'log_lines'):
            self.log_lines = []
        self.log_lines.append(line)
        self.log_lines = self.log_lines[-1500:]
        if self.page == 'import':
            self.log.configure(state='normal')
            self.log.insert('end', line + '\n')
            self.log.see('end')
            self.log.configure(state='disabled')

    def detect_and_show(self):
        drives = find_cards()
        self.sd_label.configure(text=(self.t('found') + ': ' + ', '.join(
            map(str, drives))) if drives else self.t('not_found'))
        return drives

    def choose_drive(self, drives):
        if not drives:
            messagebox.showwarning(
                'SD-kaarti ei leitud', 'Ühtegi DATALOG kausta ja STR.edf failiga ketast ei leitud.')
            return None
        if len(drives) == 1:
            return drives[0] if messagebox.askyesno('Kinnita import', f'Leitud SD-kaart: {drives[0]}\n\nKas alustada importi?') else None
        dialog = ctk.CTkInputDialog(title='Vali SD-kaart', text='Leitud kettad: ' +
                                    ', '.join(map(str, drives)) + '\nSisesta kettatäht:')
        value = dialog.get_input()
        if value:
            drive = Path(value.strip().rstrip(':\\/')[:1].upper() + ':\\')
            if drive in drives:
                return drive if messagebox.askyesno('Kinnita import', f'Kas alustada importi kettalt {drive}?') else None
        messagebox.showwarning('Vale valik', 'Sobivat kettatähte ei valitud.')
        return None

    def start_import(self):
        if self.running:
            return
        if not PYTHON.is_file() or not PIPELINE.is_file():
            messagebox.showerror(
                'Puuduv fail', 'Pythoni virtuaalkeskkonda või pipeline.py faili ei leitud.')
            return
        if (self.dashboard_process and self.dashboard_process.poll() is None) or port_open():
            messagebox.showwarning(
                'Dashboard töötab', 'Sulge Streamliti dashboard enne importi. Kui avasid selle siit, kasuta Andmete vaatamise lehel Peata nuppu.')
            return
        drive = self.choose_drive(find_cards())
        if drive is None:
            return
        self.running = True
        self.show_page('import')
        self.sd_label.configure(text=f'Valitud kaart: {drive}')
        self.status_label.configure(text=f'Andmete import käib: {drive}')
        self.add_log(
            f'\n=== Impordi algus {datetime.now():%Y-%m-%d %H:%M:%S}: {drive} ===')
        threading.Thread(target=self.run_pipeline,
                         args=(drive,), daemon=True).start()

    def run_pipeline(self, drive):
        try:
            self.import_process = subprocess.Popen(
                [str(PYTHON), '-u', str(PIPELINE), '--sd', str(drive)],
                cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding='utf-8', errors='replace', bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            for line in self.import_process.stdout:
                self.events.put(('log', line.rstrip('\r\n')))
            self.events.put(('finished', self.import_process.wait()))
        except Exception as exc:
            self.events.put(('failure', str(exc)))

    def dashboard_url(self):
        return URL + '?' + urlencode({'lang': self.language})

    def open_dashboard(self, mode='demo'):
        if self.running:
            messagebox.showinfo('Import', 'Oota impordi lõppemiseni.' if self.language == 'et'
                                else 'Wait for the import to finish.')
            return
        if mode == 'personal' and not DB.is_file():
            messagebox.showwarning(
                'Andmebaas puudub' if self.language == 'et' else 'Database missing',
                'Isiklikku andmebaasi ei leitud. Impordi esmalt enda APAP-andmed.'
                if self.language == 'et' else
                'Personal database not found. Import your own APAP data first.')
            return
        if port_open():
            if (self.dashboard_process and self.dashboard_process.poll() is None
                    and self.dashboard_mode == mode):
                webbrowser.open(self.dashboard_url())
            else:
                messagebox.showwarning(
                    'Dashboard töötab' if self.language == 'et' else 'Dashboard is running',
                    'Pordil 8501 töötab juba dashboard. Peata see enne režiimi vahetamist.'
                    if self.language == 'et' else
                    'A dashboard is already running on port 8501. Stop it before changing mode.')
            return
        if not PYTHON.is_file() or not DASHBOARD.is_file():
            messagebox.showerror(
                'Puuduv fail' if self.language == 'et' else 'Missing file',
                'Python või dashboard/app.py puudub.' if self.language == 'et'
                else 'Python or dashboard/app.py is missing.')
            return
        try:
            env = os.environ.copy()
            env['APAP_DATA_MODE'] = mode
            self.dashboard_process = subprocess.Popen(
                [str(PYTHON), '-m', 'streamlit', 'run', str(DASHBOARD),
                 '--server.address', '127.0.0.1', '--server.port', '8501',
                 '--server.headless', 'true'],
                cwd=str(ROOT), env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            self.dashboard_mode = mode
            self.add_log(f'Dashboard käivitub ({mode}): {URL}')
            self.after(600, lambda: self.wait_for_dashboard(0))
        except Exception as exc:
            messagebox.showerror('Dashboardi käivitamise viga', str(exc))

    def wait_for_dashboard(self, tries):
        if port_open():
            webbrowser.open(self.dashboard_url())
        elif tries >= 30 or (self.dashboard_process and self.dashboard_process.poll() is not None):
            messagebox.showerror(
                'Dashboardi viga', 'Streamlit ei käivitunud. Kontrolli Pythoni keskkonda.')
        else:
            self.after(500, lambda: self.wait_for_dashboard(tries + 1))

    def stop_dashboard(self):
        if self.dashboard_process and self.dashboard_process.poll() is None:
            self.dashboard_process.terminate()
            try:
                self.dashboard_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.dashboard_process.kill()
            self.add_log('Rakenduse käivitatud dashboard peatatud.')
            messagebox.showinfo(
                'Dashboard peatatud', 'Streamliti server peatati. Brauseri vahelehe võid sulgeda.')
        elif port_open():
            messagebox.showinfo(
                'Väline dashboard', 'Server töötab, kuid ei ole selle rakenduse käivitatud. Sulge see algses terminalis.')
        else:
            messagebox.showinfo('Dashboard', 'Dashboard ei tööta.')

    def poll_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == 'log':
                    self.add_log(payload)
                elif kind in ('finished', 'failure'):
                    self.running = False
                    success = kind == 'finished' and payload == 0
                    self.last_result = 'Edukalt lõpetatud' if success else 'Import ebaõnnestus'
                    self.state_data['last_import'] = {
                        'timestamp': datetime.now().isoformat(timespec='seconds'), 'success': success}
                    save_state(self.state_data)
                    self.add_log('=== ' + self.last_result + ' ===')
                    if self.page == 'import':
                        self.progress.stop()
                        self.progress.set(0)
                        self.import_btn.configure(state='normal')
                        self.detect_btn.configure(state='normal')
                        self.status_label.configure(text=self.last_result)
                    if self.last_result != 'Edukalt lõpetatud':
                        self.add_log('Viga: ' + str(payload))
                        messagebox.showerror(
                            'Impordi viga', 'Andmete uuendamine ebaõnnestus. Vaata logi laadimise vaates.')
        except queue.Empty:
            pass
        self.after(200, self.poll_events)

    def on_close(self):
        if self.running:
            messagebox.showwarning(
                'Import käib', 'Oota andmete impordi lõppemiseni, enne kui rakenduse sulged.')
            return
        if self.dashboard_process and self.dashboard_process.poll() is None:
            if messagebox.askyesno('Sulge rakendus', 'Kas peatada ka selle rakenduse käivitatud Streamliti server?'):
                self.dashboard_process.terminate()
        self.destroy()


if __name__ == '__main__':
    App().mainloop()
