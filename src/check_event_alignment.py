
from pathlib import Path
import pandas as pd
import pyedflib
import plotly.graph_objects as go


PROJECT_DIR = Path(__file__).resolve().parent.parent

BRP_FILE = (
    PROJECT_DIR
    / "data/raw/sd_initial/DATALOG/20261025"
    / "20261026_015824_BRP.edf"
)

OUTPUT_FILE = (
    PROJECT_DIR
    / "data/reports/event_alignment.html"
)

EVENT_TIME = pd.Timestamp("2026-10-26 03:34:53")
DURATION = pd.Timedelta(seconds=37)

WINDOW_START = EVENT_TIME - pd.Timedelta(minutes=2)
WINDOW_END = EVENT_TIME + pd.Timedelta(minutes=2)


def check_alignment():

    with pyedflib.EdfReader(str(BRP_FILE)) as edf:
        labels = edf.getSignalLabels()
        index = labels.index("Flow.40ms")

        start_time = pd.Timestamp(
            edf.getStartdatetime()
        )

        frequency = edf.getSampleFrequency(index)
        flow = edf.readSignal(index)

    # Valime ainult uuritava ajavahemiku
    first = max(
        0,
        int((WINDOW_START - start_time).total_seconds()
            * frequency)
    )

    last = min(
        len(flow),
        int((WINDOW_END - start_time).total_seconds()
            * frequency) + 1
    )

    if first >= last:
        raise ValueError("Valitud ajavahemikus andmeid pole.")

    timestamps = (
        start_time
        + pd.to_timedelta(
            pd.Series(range(first, last)) / frequency,
            unit="s"
        )
    )

    df = pd.DataFrame({
        "timestamp": timestamps,
        "flow": flow[first:last]
    })

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["flow"],
            mode="lines",
            name="Õhuvool",
            line=dict(color="#2878B5", width=1)
        )
    )

    # Variant A: ajatempel on algus
    fig.add_vrect(
        x0=EVENT_TIME,
        x1=EVENT_TIME + DURATION,
        fillcolor="red",
        opacity=0.15,
        line_width=0,
        annotation_text="A: algus",
        annotation_position="top left"
    )

    # Variant B: ajatempel on lõpp
    fig.add_vrect(
        x0=EVENT_TIME - DURATION,
        x1=EVENT_TIME,
        fillcolor="purple",
        opacity=0.15,
        line_width=0,
        annotation_text="B: lõpp",
        annotation_position="top left"
    )

    fig.add_vline(
        x=EVENT_TIME,
        line_color="black",
        line_dash="dash"
    )

    fig.update_layout(
        title="Sündmuse ajatemplite kontroll – 03:34:53",
        xaxis_title="Kellaaeg",
        yaxis_title="Õhuvool (L/s)",
        template="plotly_white",
        height=650
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fig.write_html(
        str(OUTPUT_FILE),
        include_plotlyjs=True
    )

    print(f"Sagedus: {frequency} Hz")
    print(f"Mõõtepunkte: {len(df):,}")
    print(f"Sündmuse ajatempel: {EVENT_TIME}")
    print(f"Sündmuse kestus: {DURATION}")
    print(f"Graafik: {OUTPUT_FILE}")


if __name__ == "__main__":
    check_alignment()
