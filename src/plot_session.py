
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "data" / "analytics.duckdb"
OUTPUT_DIR = PROJECT_DIR / "data" / "reports"

SESSION_ID = "2026-10-25_2"


def plot_session():

    with duckdb.connect(str(DB_PATH), read_only=True) as con:

        measurements = con.execute("""
            SELECT
                timestamp,
                pressure,
                leak_l_min,
                resp_rate
            FROM pld_session_measurements
            WHERE session_id = ?
            ORDER BY timestamp
        """, [SESSION_ID]).df()

        events = con.execute("""
            SELECT
                e.event_time,
                e.event_type
            FROM events e
            JOIN mask_sessions s
                ON e.event_time >= s.start_time
               AND e.event_time < s.end_time
            WHERE s.session_id = ?
            ORDER BY e.event_time
        """, [SESSION_ID]).df()

    if measurements.empty:
        print("Sessiooni mõõtmisandmeid ei leitud.")
        return

    measurements["timestamp"] = pd.to_datetime(
        measurements["timestamp"]
    )

    events["event_time"] = pd.to_datetime(
        events["event_time"]
    )

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        subplot_titles=[
            "Rõhk (cmH₂O)",
            "Maskileke (L/min)",
            "Hingamissagedus (hingetõmmet/min)",
        ],
    )

    fig.add_trace(
        go.Scatter(
            x=measurements["timestamp"],
            y=measurements["pressure"],
            mode="lines",
            name="Rõhk",
            line=dict(color="#2878B5"),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=measurements["timestamp"],
            y=measurements["leak_l_min"],
            mode="lines",
            name="Leke",
            line=dict(color="#E59A35"),
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=measurements["timestamp"],
            y=measurements["resp_rate"],
            mode="lines",
            name="Hingamissagedus",
            line=dict(color="#31966B"),
        ),
        row=3,
        col=1,
    )

    event_colors = {
        "Obstructive Apnea": "#D9534F",
        "Central Apnea": "#8E63B8",
        "Hypopnea": "#7B8794",
    }

    for event_type, group in events.groupby("event_type"):

        color = event_colors.get(
            event_type,
            "#666666",
        )

        for i, event_time in enumerate(group["event_time"]):

            fig.add_vline(
                x=event_time,
                line_width=1,
                line_dash="dot",
                line_color=color,
                row="all",
                col=1,
            )

        # Lisame legendi jaoks eraldi jälje
        fig.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="lines",
                line=dict(
                    color=color,
                    dash="dot",
                ),
                name=event_type,
            ),
            row=1,
            col=1,
        )

    fig.update_layout(
        title=(
            f"CPAP sessiooni analüüs – {SESSION_ID}"
        ),
        height=900,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.08,
        ),
    )

    fig.update_xaxes(
        title_text="Kellaaeg",
        row=3,
        col=1,
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR / f"session_{SESSION_ID}.html"
    )

    fig.write_html(
        str(output_file),
        include_plotlyjs=True,
    )

    print(f"Sessioon: {SESSION_ID}")
    print(f"Mõõteridu: {len(measurements):,}")
    print(f"Hingamissündmusi: {len(events)}")
    print(f"Graafik salvestatud: {output_file}")


if __name__ == "__main__":
    plot_session()
