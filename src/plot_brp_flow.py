
from pathlib import Path

import duckdb
import pandas as pd
import pyedflib
import plotly.graph_objects as go


PROJECT_DIR = Path(__file__).resolve().parent.parent

BRP_FILE = (
    PROJECT_DIR
    / "data/raw/sd_initial/DATALOG/20261025"
    / "20261026_015824_BRP.edf"
)

DB_PATH = PROJECT_DIR / "data/analytics.duckdb"

OUTPUT_FILE = (
    PROJECT_DIR
    / "data/reports/brp_flow_detailed.html"
)

START_TIME = pd.Timestamp("2026-10-26 03:20:00")
END_TIME = pd.Timestamp("2026-10-26 03:55:00")

INITIAL_START = pd.Timestamp("2026-10-26 03:25:00")
INITIAL_END = pd.Timestamp("2026-10-26 03:36:00")


def load_flow():

    with pyedflib.EdfReader(str(BRP_FILE)) as edf:

        labels = edf.getSignalLabels()
        index = labels.index("Flow.40ms")

        frequency = edf.getSampleFrequency(index)
        file_start = pd.Timestamp(
            edf.getStartdatetime()
        )

        first = max(
            0,
            int(
                (START_TIME - file_start).total_seconds()
                * frequency
            )
        )

        last = min(
            edf.getNSamples()[index],
            int(
                (END_TIME - file_start).total_seconds()
                * frequency
            ) + 1
        )

        if first >= last:
            raise ValueError(
                "Valitud ajavahemikus BRP-andmeid ei leitud."
            )

        flow = edf.readSignal(
            index,
            start=first,
            n=last - first
        )

    timestamps = (
        file_start
        + pd.to_timedelta(
            pd.Series(range(first, last)) / frequency,
            unit="s"
        )
    )

    return pd.DataFrame({
        "timestamp": timestamps,
        "flow": flow
    })


def load_events():

    with duckdb.connect(str(DB_PATH), read_only=True) as con:

        return con.execute("""
            SELECT
                event_type,
                event_start,
                event_end,
                duration_seconds
            FROM events_timeline
            WHERE event_end >= ?
              AND event_start <= ?
            ORDER BY event_start
        """, [START_TIME, END_TIME]).df()


def create_plot():

    flow = load_flow()
    events = load_events()

    fig = go.Figure()

    fig.add_trace(
        go.Scattergl(
            x=flow["timestamp"],
            y=flow["flow"],
            mode="lines",
            name="Õhuvool",
            line=dict(
                color="#2878B5",
                width=1
            )
        )
    )

    event_colors = {
        "Obstructive Apnea": "rgba(217,83,79,0.20)",
        "Central Apnea": "rgba(142,99,184,0.20)",
        "Hypopnea": "rgba(123,135,148,0.20)",
    }

    for _, event in events.iterrows():

        color = event_colors.get(
            event["event_type"],
            "rgba(100,100,100,0.15)"
        )

        fig.add_vrect(
            x0=event["event_start"],
            x1=event["event_end"],
            fillcolor=color,
            line_width=0,
            annotation_text=(
                f"{event['event_type']} "
                f"({event['duration_seconds']:.0f}s)"
            ),
            annotation_position="top left"
        )

    fig.update_layout(
        title="CPAP õhuvool ja hingamissündmused",
        xaxis_title="Kellaaeg",
        yaxis_title="Õhuvool (L/s)",
        template="plotly_white",
        height=700,
        hovermode="x",
        xaxis=dict(
            range=[INITIAL_START, INITIAL_END],
            rangeslider=dict(visible=True),
            type="date"
        )
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fig.write_html(
        str(OUTPUT_FILE),
        include_plotlyjs=True
    )

    print(f"BRP mõõteridu: {len(flow):,}")
    print(f"Sündmusi: {len(events)}")
    print(f"Graafik: {OUTPUT_FILE}")


if __name__ == "__main__":
    create_plot()
