from pathlib import Path
import os

import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from src import brp_reader


PROJECT_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# SEADISTUSED
# =========================================================

DATA_MODE = os.getenv("APAP_DATA_MODE", "demo").strip().lower()

if DATA_MODE == "demo":
    DB_PATH = PROJECT_DIR / "demo" / "data" / "apap_demo.duckdb"
elif DATA_MODE == "personal":
    DB_PATH = (
        PROJECT_DIR
        / "data"
        / "pipeline_test"
        / "analytics_fresh.duckdb"
    )
else:
    raise ValueError(
        "APAP_DATA_MODE must be 'demo' or 'personal' "
        f"(received: {DATA_MODE!r})."
    )

# Keep the existing BRP reader on the same data source as the dashboard.
# No change to src/brp_reader.py is required for this version.
brp_reader.DB_PATH = DB_PATH

st.set_page_config(
    page_title="CPAP Analytics",
    page_icon="🌙",
    layout="wide",
)

# Presentation-only styling. No source data, filters or calculation rules change.
st.markdown(
    """
    <style>
    .block-container {padding-top: .55rem; padding-bottom: 2rem;}
    .apap-hero {
        position: relative; isolation: isolate; overflow: hidden;
        min-height: 132px; padding: 20px 22px;
        background: linear-gradient(100deg,#fff 0%,#fff 41%,#eff7ff 60%,#9bcafa 100%);
        border: 1px solid #e3ecf7; border-radius: 8px 8px 0 0;
    }
    .apap-hero h1 {
        position: relative; z-index: 1; margin: 0 0 9px; padding: 0;
        color: #0c1c42; font-size: 2rem; font-weight: 750; line-height: 1.15;
    }
    .apap-hero p {position: relative; z-index: 1; color: #5b7194; margin: 0;}
    .apap-art {position: absolute; width: 57%; height: 100%; right: 0; top: 0; pointer-events: none;}
    .apap-kpi {
        min-width: 0; height: 105px; position: relative;
        border: 1px solid #dce7f5; border-radius: 9px;
        background: linear-gradient(145deg,#fff 0%,#f7faff 100%);
        padding: 15px 15px 10px;
    }
    .apap-kpi-label {color: #4a5c7b; padding-right: 40px; font-size: .92rem; line-height: 1.25;}
    .apap-kpi-value {margin-top: 8px; font-size: 1.6rem; line-height: 1.18; font-weight: 700; color:#101d42; white-space: nowrap;}
    .apap-kpi-icon {position: absolute; right: 12px; top: 11px; width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center;}
    .apap-kpi-icon svg {width: 23px; height: 23px; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; fill:none;}
    .apap-kpi-icon.blue {background:#e3f1ff;color:#1380dc;}
    .apap-kpi-icon.red {background:#ffe9ea;color:#ed515c;}
    .apap-kpi-icon.green {background:#dff7e9;color:#159b64;}
    div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {color:#ed515c; border-bottom-color:#ed515c;}
    div[data-testid="stDateInput"] {max-width:100%;}
    div[data-testid="stPlotlyChart"] {background:#fff;}
    @media (max-width: 800px) {
       .apap-hero {min-height:110px;padding:15px;}
       .apap-hero h1 {font-size:1.45rem;}
       .apap-art {opacity:.55;width:50%;}
       .apap-kpi-value {font-size:1.25rem;}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# KASUTAJALIIDESE KEEL / INTERFACE LANGUAGE
# =========================================================

EN_TRANSLATIONS = {
    "CPAP ravi analüüs": "APAP therapy analysis",
    "ResMed AirSense 10 – raviandmete ülevaade": "ResMed AirSense 10 – therapy data overview",
    "Andmebaasi ei leitud: ": "Database not found: ",
    "Andmete laadimine ebaõnnestus: ": "Failed to load data: ",
    "Andmebaasis puuduvad raviandmed.": "No therapy data found in the database.",
    "Raviööde ülevaade": "Therapy nights overview",
    "Sessiooni detailanalüüs": "Session details",
    "Hingamise detailanalüüs": "Breathing details",
    "Raviperiood": "Therapy period",
    "Vali kuupäevad": "Select dates",
    "Vali perioodi algus- ja lõppkuupäev.": "Select both start and end dates.",
    "Valitud perioodil raviandmed puuduvad.": "No therapy data in the selected period.",
    "Põhinäitajad": "Key metrics",
    "Keskmine kasutusaeg": "Average usage time",
    "Kogu perioodi AHI": "Overall AHI",
    "Keskmine rõhk P95": "Average pressure P95",
    "Keskmine leke P95": "Average leak P95",
    "Ravi tulemused": "Therapy results",
    "AHI raviööde lõikes": "AHI by therapy night",
    "Rõhk P95 raviööde lõikes": "Pressure P95 by therapy night",
    "Raviöö": "Therapy night",
    "AHI (sündmust/h)": "AHI (events/h)",
    "Rõhk (cmH₂O)": "Pressure (cmH₂O)",
    "Vaata raviööde algandmeid": "View therapy night source data",
    "Maskisessiooni analüüs": "Mask session analysis",
    "Vali sessioon": "Select session",
    "Kestus": "Duration",
    "Keskmine rõhk": "Average pressure",
    "Leke P95": "Leak P95",
    "Selle sessiooni kohta puuduvad detailsed PLD mõõtmisandmed.": "No detailed PLD measurements for this session.",
    "Ajaperioodi valik": "Time range selection",
    "Kogu sessioon": "Entire session",
    "30 minutit": "30 minutes",
    "10 minutit": "10 minutes",
    "5 minutit": "5 minutes",
    "Kuvatava ajavahemiku pikkus": "Displayed time range length",
    "Ajaperioodi algus": "Time range start",
    "Sessiooni ajatelg": "Session timeline",
    "Maskileke (L/min)": "Mask leak (L/min)",
    "Hingamissagedus (hingetõmmet/min)": "Respiratory rate (breaths/min)",
    "Hingamissündmused": "Respiratory events",
    "Rõhk": "Pressure",
    "Leke": "Leak",
    "Hingamissagedus": "Respiratory rate",
    "Obstruktiivne": "Obstructive",
    "Tsentraalne": "Central",
    "Hüpopnoe": "Hypopnea",
    "Algus: ": "Start: ",
    "Lõpp: ": "End: ",
    "Kestus: ": "Duration: ",
    "Kellaaeg": "Time of day",
    "Vaata hingamissündmuste andmeid": "View respiratory event data",
    "Valitud ajavahemikus hingamissündmusi ei ole.": "No respiratory events in the selected time range.",
    "Õhuvool hingamissündmuse ajal": "Airflow during respiratory event",
    "Vali maskisessioon": "Select mask session",
    "Selle sessiooni kohta puuduvad ajavahemiku määramiseks PLD-andmed.": "PLD data for determining the session time range is unavailable.",
    "Selles sessioonis hingamissündmusi ei leitud.": "No respiratory events found in this session.",
    "Obstruktiivne apnoe": "Obstructive apnea",
    "Tsentraalne apnoe": "Central apnea",
    "Vali hingamissündmus": "Select respiratory event",
    "Ajavahemik enne ja pärast sündmust": "Time before and after event",
    "Õhuvooluandmete laadimine...": "Loading airflow data...",
    "Valitud ajavahemiku kohta BRP õhuvooluandmeid ei leitud.": "No BRP airflow data found for the selected time range.",
    "Õhuvool": "Airflow",
    "Õhuvool (L/s)": "Airflow (L/s)",
    "Sündmuse tüüp": "Event type",
    "Sündmuse kestus": "Event duration",
    "Õhuvoolu mõõtmisi": "Airflow samples",
    "Rõhu ja lekke P95 näitajad on raviööde P95 väärtuste aritmeetilised keskmised, mitte kogu perioodi P95.": "Pressure and leak P95 figures are arithmetic averages of nightly P95 values, not P95 for the entire period.",
    "Kuvatav ajavahemik": "Displayed time range",
    "Valitud ajavahemikus": "Selected time range",
    "Kogu sessioonis": "Entire session",
    "sündmust": "events",
    "sekundit": "seconds",
    "Värviline ala tähistab seadme tuvastatud hingamissündmust. Õhuvoolukõver võimaldab uurida hingamist enne sündmust, selle ajal ja pärast seda.": "The colored area marks a respiratory event detected by the device. The airflow curve shows breathing before, during and after the event.",
    "Andmed on informatiivsed ega asenda arsti hinnangut ravitulemustele.": "These data are for information only and do not replace a clinician’s assessment of therapy results.",
    "Algus": "Start",
    "Lõpp": "End",
    "Andmekvaliteet": "Data quality",
    "Andmete terviklikkuse ülevaade": "Data completeness overview",
    "Täielikud STR-päevad": "Complete STR days",
    "Puudulikud STR-päevad": "Incomplete STR days",
    "PLD mõõtmisteta sessioonid": "Sessions without PLD measurements",
    "Vigased BRP-failid": "Invalid BRP files",
    "STR-päevakokkuvõtted": "STR daily summaries",
    "PLD sessioonide kontroll": "PLD session checks",
    "BRP failide kontroll": "BRP file checks",
    "Kuupäev": "Date",
    "Kasutusaeg (min)": "Usage (min)",
    "AHI": "AHI",
    "Rõhk P95": "Pressure P95",
    "Leke P95": "Leak P95",
    "Staatus": "Status",
    "Täielik": "Complete",
    "Puudulik": "Incomplete",
    "Sessioon": "Session",
    "Mõõtmisi": "Measurements",
    "Mõõtmised olemas": "Measurements available",
    "Mõõtmised puuduvad": "Measurements missing",
    "Fail": "File",
    "Suurus (B)": "Size (B)",
    "Veateade": "Error message",
    "Kõik BRP-failid": "All BRP files",
    "Näita ainult probleemseid BRP-faile": "Show only problematic BRP files",
    "STR täielikkus põhineb neljal väljal: kasutusaeg, AHI, rõhk P95 ja leke P95. PLD ning BRP puudumine ei tähenda automaatselt puudulikku raviööd.": "STR completeness uses four fields: usage, AHI, pressure P95 and leak P95. Missing PLD or BRP does not automatically mean an incomplete therapy night.",
    "BRP staatus näitab EDF-faili tehnilist loetavust, mitte kogu raviöö täielikkust.": "BRP status reflects technical EDF file readability, not completeness of the entire therapy night.",
    "Andmekvaliteedi andmete laadimine ebaõnnestus": "Failed to load data quality information",
    "Andmebaasi ei leitud": "Database not found",
    "Andmete laadimine ebaõnnestus": "Failed to load data"
}


def t(estonian):
    if st.session_state.get("ui_language", "et") == "en":
        return EN_TRANSLATIONS.get(estonian, estonian)
    return estonian


# The launcher opens /?lang=et or /?lang=en. A direct browser visit
# defaults to Estonian. Manual changes update the URL as well, so a rerun
# does not unexpectedly restore the launcher language.
query_lang = st.query_params.get("lang", "")
if query_lang not in ("et", "en"):
    query_lang = "et"

if ("ui_language" not in st.session_state
        or st.session_state.get("last_query_language") != query_lang):
    st.session_state.ui_language = query_lang
    st.session_state.language_picker = query_lang.upper()
    st.session_state.last_query_language = query_lang


def change_language():
    language = st.session_state.language_picker.lower()
    st.session_state.ui_language = language
    st.session_state.last_query_language = language
    st.query_params["lang"] = language


# Keep the language selector above the header, at the upper left.
# It remains a native Streamlit widget with the existing language callback.
language_col, _ = st.columns([1.25, 8])
with language_col:
    st.segmented_control(
        "Language / Keel",
        options=["ET", "EN"],
        key="language_picker",
        label_visibility="collapsed",
        on_change=change_language,
    )

from html import escape

# Inline vector illustration scales with the real dashboard width.
HERO_ART = """
<svg class="apap-art" viewBox="0 0 660 160" preserveAspectRatio="xMidYMid slice"
     xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M0 154 Q150 145 260 78 T660 110 V160 H0Z" fill="#bddfff" opacity=".58"/>
  <path d="M0 154 Q170 126 300 114 T660 118" fill="none" stroke="white" stroke-width="2" opacity=".9"/>
  <path d="M0 160 Q170 137 310 130 T660 142" fill="none" stroke="white" stroke-width="1.5" opacity=".75"/>
  <path d="M462 23a26 26 0 1 0 28 40 29 29 0 0 1-28-40z" fill="white" opacity=".93"/>
  <g fill="none" stroke="white" stroke-width="11" stroke-linecap="round" stroke-linejoin="round">
    <path d="M525 72 V124 M525 112 H622 V124 M535 95 H602 Q620 95 620 112"/>
  </g>
  <circle cx="548" cy="88" r="11" fill="white"/>
  <g fill="white" font-family="Arial, sans-serif" font-weight="bold" text-anchor="middle">
    <text x="584" y="69" font-size="22">z</text><text x="609" y="44" font-size="29">z</text><text x="633" y="17" font-size="35">z</text>
  </g>
</svg>
"""
st.markdown(
    '<div class="apap-hero">'
    f'<h1>{escape(t("CPAP ravi analüüs"))}</h1>'
    f'<p>{escape(t("ResMed AirSense 10 – raviandmete ülevaade"))}</p>'
    + HERO_ART + '</div>',
    unsafe_allow_html=True,
)

if DATA_MODE == "demo":
    if st.session_state.get("ui_language", "et") == "en":
        st.info(
            "DEMO MODE — All data are synthetic and not clinically "
            "validated. Detailed comparison with real APAP recordings "
            "is not appropriate. Airflow recordings are available for "
            "selected events only."
        )
    else:
        st.info(
            "NÄIDISREŽIIM — Kõik andmed on sünteetilised ega ole "
            "kliiniliselt valideeritud. Detailne võrdlus tegelike APAP "
            "mõõtmistega ei ole asjakohane. Õhuvoolu salvestised "
            "on olemas ainult valitud sündmuste kohta."
        )


# =========================================================
# ANDMETE LAADIMINE
# =========================================================

@st.cache_data
def load_overview(db_path, modified_time):
    with duckdb.connect(db_path, read_only=True) as con:
        daily = con.execute("""
            SELECT
                therapy_date,
                usage_minutes,
                ahi,
                pressure_p95,
                leak_p95_l_min
            FROM daily_summary
            ORDER BY therapy_date
        """).df()

        sessions = con.execute("""
            SELECT
                therapy_date,
                duration_minutes,
                total_events
            FROM session_analysis
        """).df()

        session_summary = con.execute("""
            SELECT *
            FROM pld_session_summary
            ORDER BY therapy_date, session_number
        """).df()

    return daily, sessions, session_summary


@st.cache_data
def load_session_measurements(
    db_path,
    modified_time,
    session_id,
):
    with duckdb.connect(db_path, read_only=True) as con:
        return con.execute("""
            SELECT
                timestamp,
                pressure,
                leak_l_min,
                resp_rate
            FROM pld_session_measurements
            WHERE session_id = ?
            ORDER BY timestamp
        """, [session_id]).df()


@st.cache_data
def load_session_events(
    db_path,
    modified_time,
    start_time,
    end_time,
):
    with duckdb.connect(db_path, read_only=True) as con:
        return con.execute("""
            SELECT
                event_start,
                event_end,
                event_type,
                duration_seconds
            FROM events_timeline
            WHERE event_end >= ?
              AND event_start <= ?
            ORDER BY event_start
        """, [start_time, end_time]).df()


@st.cache_data
def load_quality_data(db_path, modified_time):
    """Loeb kvaliteedivaate jaoks ainult vajalikud tabelid."""
    with duckdb.connect(db_path, read_only=True) as con:
        quality_daily = con.execute("""
            SELECT therapy_date, usage_minutes, ahi,
                   pressure_p95, leak_p95_l_min
            FROM daily_summary
            ORDER BY therapy_date
        """).df()
        quality_pld = con.execute("""
            SELECT s.session_id, s.therapy_date, s.duration_minutes,
                   p.measurement_count
            FROM mask_sessions s
            LEFT JOIN pld_session_summary p
                ON s.session_id = p.session_id
            ORDER BY s.therapy_date, s.start_time
        """).df()
        quality_brp = con.execute("""
            SELECT file_name, file_size, status, error_message
            FROM brp_file_index
            ORDER BY file_name
        """).df()
    return quality_daily, quality_pld, quality_brp


# =========================================================
# ABIFUNKTSIOONID
# =========================================================

def format_minutes(value):
    if pd.isna(value):
        return "N/A"
    hours, minutes = divmod(round(value), 60)
    return f"{hours} h {minutes:02d} min"


def format_number(value, decimals=2, unit=""):
    if pd.isna(value):
        return "N/A"

    result = f"{value:.{decimals}f}"

    if unit:
        result += f" {unit}"

    return result


# =========================================================
# ANDMEBAASI KONTROLL
# =========================================================

if not DB_PATH.is_file():
    st.error(f"{t('Andmebaasi ei leitud')}: {DB_PATH}")
    st.stop()

db_mtime = DB_PATH.stat().st_mtime_ns

try:
    daily, sessions, session_summary = load_overview(
        str(DB_PATH),
        db_mtime,
    )
except Exception as exc:
    st.error(f"{t('Andmete laadimine ebaõnnestus')}: {exc}")
    st.stop()

if daily.empty or session_summary.empty:
    st.warning(t("Andmebaasis puuduvad raviandmed."))
    st.stop()

daily["therapy_date"] = pd.to_datetime(
    daily["therapy_date"]
).dt.date

sessions["therapy_date"] = pd.to_datetime(
    sessions["therapy_date"]
).dt.date

session_summary["therapy_date"] = pd.to_datetime(
    session_summary["therapy_date"]
).dt.date


# =========================================================
# VAHELEHED
# =========================================================

tab_overview, tab_session, tab_breathing, tab_quality = st.tabs([
    t("Raviööde ülevaade"),
    t("Sessiooni detailanalüüs"),
    t("Hingamise detailanalüüs"),
    t("Andmekvaliteet"),
])


# =========================================================
# VAHELEHT 1 – RAVIÖÖDE ÜLEVAADE
# =========================================================

with tab_overview:

    st.subheader(t("Raviperiood"))

    min_date = daily["therapy_date"].min()
    max_date = daily["therapy_date"].max()

    date_range = st.date_input(
        t("Vali kuupäevad"),
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="overview_dates",
    )

    if len(date_range) != 2:
        st.info(t("Vali perioodi algus- ja lõppkuupäev."))

    else:
        start_date, end_date = date_range

        filtered = daily[
            (daily["therapy_date"] >= start_date)
            & (daily["therapy_date"] <= end_date)
        ].copy()

        filtered_sessions = sessions[
            (sessions["therapy_date"] >= start_date)
            & (sessions["therapy_date"] <= end_date)
        ]

        if filtered.empty:
            st.info(t("Valitud perioodil raviandmed puuduvad."))

        else:
            # ---------------------------------------------
            # KPI-d
            # ---------------------------------------------

            average_minutes = filtered["usage_minutes"].mean()

            total_events = filtered_sessions[
                "total_events"
            ].sum()

            total_session_minutes = filtered_sessions[
                "duration_minutes"
            ].sum()

            overall_ahi = (
                total_events * 60 / total_session_minutes
                if total_session_minutes > 0
                else float("nan")
            )

            st.subheader(t("Põhinäitajad"))

            def kpi_card(label, value, color, svg_body):
                return (
                    '<div class="apap-kpi">'
                    f'<div class="apap-kpi-label">{escape(str(label))}</div>'
                    f'<div class="apap-kpi-value">{escape(str(value))}</div>'
                    f'<div class="apap-kpi-icon {color}">'
                    '<svg viewBox="0 0 24 24" stroke="currentColor">'
                    f'{svg_body}</svg></div></div>'
                )

            icons = [
                '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 3"/>',
                '<path d="M2 12h5l3-7 4 14 3-7h5"/>',
                '<path d="M3 17a9 9 0 1 1 18 0"/><path d="M12 17l5-7"/>',
                '<path d="M2 8h12q5 0 5-3 0-3-3-3"/><path d="M2 13h17q4 0 4 3t-4 3"/><path d="M2 18h9"/>'
            ]
            metrics = [
                (t("Keskmine kasutusaeg"), format_minutes(average_minutes), "blue", icons[0]),
                (t("Kogu perioodi AHI"), format_number(overall_ahi), "red", icons[1]),
                (t("Keskmine rõhk P95"), format_number(filtered["pressure_p95"].mean(), unit="cmH₂O"), "blue", icons[2]),
                (t("Keskmine leke P95"), format_number(filtered["leak_p95_l_min"].mean(), decimals=1, unit="L/min"), "green", icons[3]),
            ]
            cols = st.columns(4, gap="small")
            for col, (label, value, color, icon) in zip(cols, metrics):
                with col:
                    st.markdown(kpi_card(label, value, color, icon), unsafe_allow_html=True)

            st.caption(
                t("Rõhu ja lekke P95 näitajad on raviööde P95 väärtuste "
                  "aritmeetilised keskmised, mitte kogu perioodi P95.")
            )

            # ---------------------------------------------
            # Ülevaategraafikud
            # ---------------------------------------------

            st.subheader(t("Ravi tulemused"))

            filtered["date_label"] = filtered[
                "therapy_date"
            ].apply(lambda d: d.strftime("%d.%m.%Y"))

            left, right = st.columns(2, gap="small")

            with left:
                fig_ahi = px.line(
                    filtered,
                    x="date_label",
                    y="ahi",
                    markers=True,
                    title=t("AHI raviööde lõikes"),
                    labels={
                        "date_label": t("Raviöö"),
                        "ahi": t("AHI (sündmust/h)"),
                    },
                )

                fig_ahi.update_yaxes(
                    rangemode="tozero"
                )

                with st.container(border=True):
                    st.plotly_chart(
                        fig_ahi,
                        width="stretch",
                    )

            with right:
                fig_pressure = px.line(
                    filtered,
                    x="date_label",
                    y="pressure_p95",
                    markers=True,
                    title=t("Rõhk P95 raviööde lõikes"),
                    labels={
                        "date_label": t("Raviöö"),
                        "pressure_p95": t("Rõhk (cmH₂O)"),
                    },
                )

                fig_pressure.update_yaxes(
                    rangemode="tozero"
                )

                with st.container(border=True):
                    st.plotly_chart(
                        fig_pressure,
                        width="stretch",
                    )

            # ---------------------------------------------
            # Algandmete tabel
            # ---------------------------------------------

            with st.expander(
                t("Vaata raviööde algandmeid")
            ):
                st.dataframe(
                    filtered.drop(
                        columns="date_label"
                    ),
                    width="stretch",
                    hide_index=True,
                )


# =========================================================
# VAHELEHT 2 – SESSIOONI DETAILANALÜÜS
# =========================================================

with tab_session:

    st.subheader(t("Maskisessiooni analüüs"))

    session_ids = session_summary[
        "session_id"
    ].tolist()

    selected_session = st.selectbox(
        t("Vali sessioon"),
        options=session_ids,
        index=len(session_ids) - 1,
        key="selected_session",
    )

    selected = session_summary[
        session_summary["session_id"]
        == selected_session
    ].iloc[0]

    # -----------------------------------------------------
    # Sessiooni KPI-d
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        t("Kestus"),
        format_minutes(
            selected["duration_minutes"]
        ),
    )

    c2.metric(
        "AHI",
        format_number(
            selected["calculated_ahi"]
        ),
    )

    c3.metric(
        t("Keskmine rõhk"),
        format_number(
            selected["avg_pressure"],
            unit="cmH₂O",
        ),
    )

    c4.metric(
        t("Leke P95"),
        format_number(
            selected["leak_p95"],
            decimals=1,
            unit="L/min",
        ),
    )

    # -----------------------------------------------------
    # Mõõtmisandmete laadimine
    # -----------------------------------------------------

    measurements = load_session_measurements(
        str(DB_PATH),
        db_mtime,
        selected_session,
    )

    if measurements.empty:
        st.info(
            t("Selle sessiooni kohta puuduvad detailsed PLD mõõtmisandmed.")
        )

    else:
        measurements["timestamp"] = pd.to_datetime(
            measurements["timestamp"]
        )

        start_time = measurements[
            "timestamp"
        ].min()

        end_time = measurements[
            "timestamp"
        ].max()

        events = load_session_events(
            str(DB_PATH),
            db_mtime,
            start_time,
            end_time,
        )

        if not events.empty:
            events["event_start"] = pd.to_datetime(
                events["event_start"]
            )

            events["event_end"] = pd.to_datetime(
                events["event_end"]
            )

        # -------------------------------------------------
        # Ajaperioodi valik
        # -------------------------------------------------

        st.subheader(t("Ajaperioodi valik"))

        period_options = {
            t("Kogu sessioon"): None,
            t("30 minutit"): 30,
            t("10 minutit"): 10,
            t("5 minutit"): 5,
        }

        selected_period = st.selectbox(
            t("Kuvatava ajavahemiku pikkus"),
            options=list(period_options.keys()),
            key="selected_period",
        )

        period_minutes = period_options[
            selected_period
        ]

        if period_minutes is None:
            view_start = start_time
            view_end = end_time

        else:
            period_delta = pd.Timedelta(
                minutes=period_minutes
            )

            latest_start = max(
                start_time,
                end_time - period_delta,
            )

            if latest_start <= start_time:
                view_start = start_time

            else:
                view_start = st.slider(
                    t("Ajaperioodi algus"),
                    min_value=start_time.to_pydatetime(),
                    max_value=latest_start.to_pydatetime(),
                    value=start_time.to_pydatetime(),
                    step=pd.Timedelta(
                        minutes=1
                    ).to_pytimedelta(),
                    format="DD.MM.YYYY HH:mm:ss",
                    key=(
                        f"time_slider_"
                        f"{selected_session}_"
                        f"{period_minutes}"
                    ),
                )

                view_start = pd.Timestamp(
                    view_start
                )

            view_end = min(
                view_start + period_delta,
                end_time,
            )

        st.caption(
            f"{t('Kuvatav ajavahemik')}: "
            f"{view_start:%d.%m.%Y %H:%M:%S} – "
            f"{view_end:%d.%m.%Y %H:%M:%S}"
        )

        # -------------------------------------------------
        # Valitud perioodi andmed
        # -------------------------------------------------

        visible_measurements = measurements[
            (
                measurements["timestamp"]
                >= view_start
            )
            & (
                measurements["timestamp"]
                <= view_end
            )
        ].copy()

        visible_events = events[
            (
                events["event_end"]
                >= view_start
            )
            & (
                events["event_start"]
                <= view_end
            )
        ].copy()

        # -------------------------------------------------
        # Ühise ajateljega graafik
        # -------------------------------------------------

        st.subheader(t("Sessiooni ajatelg"))

        fig = make_subplots(
            rows=4,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=(
                t("Rõhk (cmH₂O)"),
                t("Maskileke (L/min)"),
                t("Hingamissagedus (hingetõmmet/min)"),
                t("Hingamissündmused"),
            ),
            row_heights=[
                0.30,
                0.25,
                0.25,
                0.20,
            ],
        )

        # -------------------------------------------------
        # Mõõtegraafikud
        # -------------------------------------------------

        signals = [
            (
                "pressure",
                t("Rõhk"),
                1,
                "#2563EB",
            ),
            (
                "leak_l_min",
                t("Leke"),
                2,
                "#06B6D4",
            ),
            (
                "resp_rate",
                t("Hingamissagedus"),
                3,
                "#16A34A",
            ),
        ]

        for (
            column,
            label,
            row_number,
            color,
        ) in signals:

            fig.add_trace(
                go.Scatter(
                    x=visible_measurements[
                        "timestamp"
                    ],
                    y=visible_measurements[
                        column
                    ],
                    mode="lines",
                    name=label,
                    line=dict(
                        color=color,
                        width=1.3,
                    ),
                ),
                row=row_number,
                col=1,
            )

        # -------------------------------------------------
        # Hingamissündmused
        # -------------------------------------------------

        event_styles = {
            "Obstructive Apnea": {
                "position": 3,
                "label": t("Obstruktiivne"),
                "color": "#DC2626",
            },
            "Central Apnea": {
                "position": 2,
                "label": t("Tsentraalne"),
                "color": "#F59E0B",
            },
            "Hypopnea": {
                "position": 1,
                "label": t("Hüpopnoe"),
                "color": "#8B5CF6",
            },
        }

        for event_type, style in event_styles.items():

            subset = visible_events[
                visible_events["event_type"]
                == event_type
            ]

            for _, event in subset.iterrows():

                event_start = max(
                    event["event_start"],
                    view_start,
                )

                event_end = min(
                    event["event_end"],
                    view_end,
                )

                is_point = (
                    event_start == event_end
                )

                x_values = (
                    [event_end]
                    if is_point
                    else [
                        event_start,
                        event_end,
                    ]
                )

                y_values = [
                    style["position"]
                ] * len(x_values)

                event_details = [
                    [
                        event["event_start"].strftime(
                            "%H:%M:%S"
                        ),
                        event["event_end"].strftime(
                            "%H:%M:%S"
                        ),
                        event["duration_seconds"],
                    ]
                ] * len(x_values)

                fig.add_trace(
                    go.Scatter(
                        x=x_values,
                        y=y_values,
                        mode=(
                            "markers"
                            if is_point
                            else "lines+markers"
                        ),
                        name=style["label"],
                        legendgroup=event_type,
                        showlegend=False,
                        line=dict(
                            color=style["color"],
                            width=5,
                        ),
                        marker=dict(
                            color=style["color"],
                            size=8,
                        ),
                        customdata=event_details,
                        hovertemplate=(
                            f"{style['label']}"
                            f"<br>{t('Algus')}: %{{customdata[0]}}"
                            f"<br>{t('Lõpp')}: %{{customdata[1]}}"
                            f"<br>{t('Kestus')}: %{{customdata[2]:.0f}} s"
                            "<extra></extra>"
                        ),
                    ),
                    row=4,
                    col=1,
                )

        # -------------------------------------------------
        # Telgede seadistused
        # -------------------------------------------------

        fig.update_yaxes(
            tickvals=[1, 2, 3],
            ticktext=[
                t("Hüpopnoe"),
                t("Tsentraalne"),
                t("Obstruktiivne"),
            ],
            range=[0.5, 3.5],
            row=4,
            col=1,
        )

        fig.update_xaxes(
            range=[
                view_start,
                view_end,
            ],
        )

        fig.update_xaxes(
            title_text=t("Kellaaeg"),
            row=4,
            col=1,
        )

        fig.update_layout(
            height=900,
            hovermode="x unified",
            margin=dict(
                l=40,
                r=20,
                t=80,
                b=40,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="left",
                x=0,
            ),
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

        st.caption(
            f"{t('Valitud ajavahemikus')}: {len(visible_events)} "
            f"{t('sündmust')}. {t('Kogu sessioonis')}: "
            f"{len(events)} {t('sündmust')}."
        )

        # -------------------------------------------------
        # Sündmuste tabel
        # -------------------------------------------------

        with st.expander(
            t("Vaata hingamissündmuste andmeid")
        ):
            if visible_events.empty:
                st.info(
                    t("Valitud ajavahemikus hingamissündmusi ei ole.")
                )

            else:
                st.dataframe(
                    visible_events[
                        [
                            "event_start",
                            "event_end",
                            "event_type",
                            "duration_seconds",
                        ]
                    ],
                    width="stretch",
                    hide_index=True,
                )


# =========================================================
# VAHELEHT 3 – HINGAMISE DETAILANALÜÜS
# =========================================================

with tab_breathing:

    st.subheader(t("Õhuvool hingamissündmuse ajal"))

    brp_session = st.selectbox(
        t("Vali maskisessioon"),
        options=session_ids,
        index=len(session_ids) - 1,
        key="brp_session",
    )

    # Sessiooni ajavahemik võetakse PLD mõõtmistest.
    brp_measurements = load_session_measurements(
        str(DB_PATH),
        db_mtime,
        brp_session,
    )

    if brp_measurements.empty:
        st.info(
            t("Selle sessiooni kohta puuduvad ajavahemiku määramiseks PLD-andmed.")
        )

    else:
        brp_start = pd.to_datetime(
            brp_measurements["timestamp"]
        ).min()

        brp_end = pd.to_datetime(
            brp_measurements["timestamp"]
        ).max()

        brp_events = load_session_events(
            str(DB_PATH),
            db_mtime,
            brp_start,
            brp_end,
        )

        if brp_events.empty:
            st.info(
                t("Selles sessioonis hingamissündmusi ei leitud.")
            )

        else:
            brp_events["event_start"] = pd.to_datetime(
                brp_events["event_start"]
            )
            brp_events["event_end"] = pd.to_datetime(
                brp_events["event_end"]
            )

            event_names = {
                "Obstructive Apnea": t("Obstruktiivne apnoe"),
                "Central Apnea": t("Tsentraalne apnoe"),
                "Hypopnea": t("Hüpopnoe"),
            }

            event_options = []

            for event_index, event in brp_events.iterrows():
                label = (
                    f"{event['event_start']:%H:%M:%S} – "
                    f"{event_names.get(event['event_type'], event['event_type'])} "
                    f"({event['duration_seconds']:.0f} s)"
                )

                event_options.append(
                    (event_index, label)
                )

            selected_event_index = st.selectbox(
                t("Vali hingamissündmus"),
                options=range(len(event_options)),
                format_func=lambda i: event_options[i][1],
                key="brp_event",
            )

            selected_event = brp_events.loc[
                event_options[selected_event_index][0]
            ]

            context_seconds = st.select_slider(
                t("Ajavahemik enne ja pärast sündmust"),
                options=[15, 30, 60, 120],
                value=30,
                format_func=lambda x: f"{x} {t('sekundit')}",
                key="brp_context",
            )

            view_start = (
                selected_event["event_start"]
                - pd.Timedelta(seconds=context_seconds)
            )

            view_end = (
                selected_event["event_end"]
                + pd.Timedelta(seconds=context_seconds)
            )

            @st.cache_data(show_spinner=False)
            def load_cached_brp(start, end, database_path, database_mtime):
                return brp_reader.load_brp_flow(start, end)

            with st.spinner(t("Õhuvooluandmete laadimine...")):
                flow = load_cached_brp(
                    view_start,
                    view_end,
                    str(DB_PATH),
                    db_mtime,
                )

            if flow.empty:
                st.warning(
                    t("Valitud ajavahemiku kohta BRP õhuvooluandmeid ei leitud.")
                )

            else:
                fig_flow = go.Figure()

                fig_flow.add_trace(
                    go.Scattergl(
                        x=flow["timestamp"],
                        y=flow["flow"],
                        mode="lines",
                        name=t("Õhuvool"),
                        line=dict(
                            color="#2563EB",
                            width=1.3,
                        ),
                    )
                )

                event_colors = {
                    "Obstructive Apnea": "rgba(220,38,38,0.20)",
                    "Central Apnea": "rgba(245,158,11,0.20)",
                    "Hypopnea": "rgba(139,92,246,0.20)",
                }

                event_color = event_colors.get(
                    selected_event["event_type"],
                    "rgba(100,100,100,0.20)",
                )

                event_start = selected_event["event_start"]
                event_end = selected_event["event_end"]

                # Nullkestusega sündmuse puhul näitame
                # vertikaalset joont.
                if event_end <= event_start:
                    fig_flow.add_vline(
                        x=event_start,
                        line_color="#DC2626",
                        line_dash="dash",
                        line_width=2,
                    )

                else:
                    fig_flow.add_vrect(
                        x0=event_start,
                        x1=event_end,
                        fillcolor=event_color,
                        line_width=0,
                    )

                fig_flow.update_layout(
                    title=(
                        f"{event_names.get(selected_event['event_type'], selected_event['event_type'])}"
                        f" – {event_start:%H:%M:%S}"
                    ),
                    xaxis_title=t("Kellaaeg"),
                    yaxis_title=t("Õhuvool (L/s)"),
                    template="plotly_white",
                    height=600,
                    hovermode="x",
                    xaxis=dict(
                        range=[view_start, view_end],
                    ),
                    margin=dict(
                        l=40,
                        r=20,
                        t=70,
                        b=40,
                    ),
                )

                st.plotly_chart(
                    fig_flow,
                    width="stretch",
                )

                c1, c2, c3 = st.columns(3)

                c1.metric(
                    t("Sündmuse tüüp"),
                    event_names.get(
                        selected_event["event_type"],
                        selected_event["event_type"],
                    ),
                )

                c2.metric(
                    t("Sündmuse kestus"),
                    f"{selected_event['duration_seconds']:.0f} s",
                )

                c3.metric(
                    t("Õhuvoolu mõõtmisi"),
                    f"{len(flow):,}",
                )

                st.caption(
                    t("Värviline ala tähistab seadme tuvastatud "
                      "hingamissündmust. Õhuvoolukõver võimaldab "
                      "uurida hingamist enne sündmust, selle ajal "
                      "ja pärast seda.")
                )


# =========================================================
# VAHELEHT 4 – ANDMEKVALITEET / DATA QUALITY
# =========================================================

with tab_quality:
    st.subheader(t("Andmete terviklikkuse ülevaade"))
    st.caption(t(
        "STR täielikkus põhineb neljal väljal: kasutusaeg, AHI, rõhk P95 ja leke P95. "
        "PLD ning BRP puudumine ei tähenda automaatselt puudulikku raviööd."
    ))

    try:
        quality_daily, quality_pld, quality_brp = load_quality_data(
            str(DB_PATH), db_mtime
        )
    except (duckdb.Error, OSError) as exc:
        st.error(f"{t('Andmekvaliteedi andmete laadimine ebaõnnestus')}: {exc}")
    else:
        required = ["usage_minutes", "ahi", "pressure_p95", "leak_p95_l_min"]
        for column in required:
            quality_daily[column] = pd.to_numeric(
                quality_daily[column], errors="coerce"
            )
        incomplete = (
            quality_daily[required].isna().any(axis=1)
            | quality_daily[required].lt(0).any(axis=1)
        )
        quality_daily["status_label"] = incomplete.map(
            {True: t("Puudulik"), False: t("Täielik")}
        )

        quality_pld["measurement_count"] = pd.to_numeric(
            quality_pld["measurement_count"], errors="coerce"
        )
        missing_pld = (
            quality_pld["measurement_count"].isna()
            | quality_pld["measurement_count"].le(0)
        )
        quality_pld["status_label"] = missing_pld.map(
            {True: t("Mõõtmised puuduvad"), False: t("Mõõtmised olemas")}
        )
        invalid_brp = quality_brp["status"].isna() | quality_brp["status"].ne("ok")

        k1, k2, k3, k4 = st.columns(4)
        k1.metric(t("Täielikud STR-päevad"), int((~incomplete).sum()))
        k2.metric(t("Puudulikud STR-päevad"), int(incomplete.sum()))
        k3.metric(t("PLD mõõtmisteta sessioonid"), int(missing_pld.sum()))
        k4.metric(t("Vigased BRP-failid"), int(invalid_brp.sum()))

        st.subheader(t("STR-päevakokkuvõtted"))
        daily_display = quality_daily.rename(columns={
            "therapy_date": t("Kuupäev"),
            "usage_minutes": t("Kasutusaeg (min)"),
            "ahi": t("AHI"),
            "pressure_p95": t("Rõhk P95"),
            "leak_p95_l_min": t("Leke P95"),
            "status_label": t("Staatus"),
        })
        st.dataframe(daily_display, width="stretch", hide_index=True)

        st.subheader(t("PLD sessioonide kontroll"))
        pld_display = quality_pld[[
            "session_id", "therapy_date", "duration_minutes",
            "measurement_count", "status_label"
        ]].rename(columns={
            "session_id": t("Sessioon"),
            "therapy_date": t("Kuupäev"),
            "duration_minutes": t("Kestus"),
            "measurement_count": t("Mõõtmisi"),
            "status_label": t("Staatus"),
        })
        st.dataframe(pld_display, width="stretch", hide_index=True)

        st.subheader(t("BRP failide kontroll"))
        st.caption(t(
            "BRP staatus näitab EDF-faili tehnilist loetavust, "
            "mitte kogu raviöö täielikkust."
        ))
        show_only_invalid = st.checkbox(
            t("Näita ainult probleemseid BRP-faile"), value=True,
            key="quality_invalid_brp_only"
        )
        brp_display = quality_brp.loc[
            invalid_brp if show_only_invalid else slice(None),
            ["file_name", "file_size", "status", "error_message"]
        ].rename(columns={
            "file_name": t("Fail"),
            "file_size": t("Suurus (B)"),
            "status": t("Staatus"),
            "error_message": t("Veateade"),
        })
        st.dataframe(brp_display, width="stretch", hide_index=True)


# =========================================================
# LÕPUMÄRKUS
# =========================================================

st.caption(
    t("Andmed on informatiivsed ega asenda "
      "arsti hinnangut ravitulemustele.")
)
