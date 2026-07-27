"""France Top 50: audience sensitivity and release-format dashboard.

Run with: streamlit run app.py
"""

from __future__ import annotations

from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="France Top 50 | Atlantic", page_icon="🎵", layout="wide"
)

REQUIRED_COLUMNS = {
    "date", "position", "song", "artist", "popularity", "duration_ms",
    "album_type", "total_tracks", "is_explicit", "album_cover_url",
}
DEFAULT_DATA_PATH = Path(r"C:\Users\SherlinPreethi\Downloads\Atlantic_France.csv")


@st.cache_data(show_spinner=False)
def load_data(source: object) -> pd.DataFrame:
    """Load, normalize and validate the playlist extract."""
    df = pd.read_csv(source)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    for column in ["position", "popularity", "duration_ms", "total_tracks"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["album_type"] = (
        df["album_type"].astype(str).str.strip().str.title().replace({"Ep": "EP"})
    )
    df["is_explicit"] = (
        df["is_explicit"].astype(str).str.strip().str.upper()
        .map({"TRUE": True, "FALSE": False, "1": True, "0": False, "YES": True, "NO": False})
    )
    df["duration_min"] = df["duration_ms"] / 60_000
    df["content_label"] = np.where(df["is_explicit"], "Explicit", "Clean")
    df["duration_bucket"] = pd.cut(
        df["duration_min"], bins=[0, 2.5, 3.5, np.inf], labels=["Short (<2.5 min)", "Medium (2.5–3.5 min)", "Long (>3.5 min)"], include_lowest=True
    )
    invalid_duration_count = int(df["duration_min"].le(0).sum())
    cleaned = df.dropna(subset=["date", "position", "popularity", "duration_min"])
    cleaned = cleaned[cleaned["duration_min"] > 0].copy()
    cleaned.attrs["excluded_invalid_duration"] = invalid_duration_count
    return cleaned


def pct(value: float) -> str:
    return f"{value:.1%}"


def build_validation(df: pd.DataFrame) -> pd.DataFrame:
    entries = df.groupby("date").size().rename("entries")
    return pd.DataFrame({
        "Playlist days": [entries.size],
        "Total records": [len(df)],
        "Days with exactly 50 entries": [(entries == 50).sum()],
        "Incomplete days": [(entries != 50).sum()],
        "Missing explicit flags": [df["is_explicit"].isna().sum()],
        "Invalid durations excluded": [df.attrs.get("excluded_invalid_duration", 0)],
    })


st.title("France Top 50: Content & Format Intelligence")
st.caption("Atlantic Recording Corporation | Audience sensitivity, compliance, and format acceptance analysis")

with st.sidebar:
    st.header("Data & filters")
    uploaded = st.file_uploader("Upload France Top 50 CSV", type="csv")
    if uploaded is None and DEFAULT_DATA_PATH.exists():
        source = DEFAULT_DATA_PATH
        st.success("Using the supplied Atlantic_France.csv")
    elif uploaded is not None:
        source = uploaded
    else:
        source = None
        st.info("Upload the provided Atlantic_France.csv to begin.")

if source is None:
    st.stop()

try:
    raw = load_data(source)
except Exception as exc:
    st.error(f"The file could not be prepared: {exc}")
    st.stop()

with st.sidebar:
    min_date, max_date = raw["date"].min().date(), raw["date"].max().date()
    date_range = st.date_input("Snapshot date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if not isinstance(date_range, tuple) or len(date_range) != 2:
        st.warning("Select a start and end date.")
        st.stop()
    rank_limit = st.select_slider("Rank tier", options=[10, 25, 50], value=50, format_func=lambda x: f"Top {x}")
    explicit_filter = st.radio("Content", ["All", "Explicit only", "Clean only"], horizontal=True)
    format_filter = st.multiselect("Release format", sorted(raw["album_type"].dropna().unique()), default=sorted(raw["album_type"].dropna().unique()))

filtered = raw.loc[
    raw["date"].between(pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))
    & raw["position"].le(rank_limit)
    & raw["album_type"].isin(format_filter)
].copy()
if explicit_filter == "Explicit only":
    filtered = filtered[filtered["is_explicit"]]
elif explicit_filter == "Clean only":
    filtered = filtered[~filtered["is_explicit"]]

if filtered.empty:
    st.warning("No records match these filters. Adjust the filters and try again.")
    st.stop()

# KPI calculations use the current selection, so every metric remains auditable.
explicit_share = filtered["is_explicit"].mean()
clean_ratio = (1 - explicit_share) / explicit_share if explicit_share else np.inf
single_share = (filtered["album_type"] == "Single").mean()
avg_duration = filtered["duration_min"].mean()
album_rows = filtered[filtered["album_type"] == "Album"].dropna(subset=["total_tracks"])
album_size_impact = album_rows[["total_tracks", "popularity"]].corr().iloc[0, 1] if len(album_rows) > 1 else np.nan
# 100 means the selected content is concentrated at rank 1; 0 is rank 50.
acceptance_score = (1 - (filtered["position"].mean() - 1) / 49) * 100

st.subheader("Content compliance summary")
metrics = st.columns(6)
metrics[0].metric("Explicit content share", pct(explicit_share))
metrics[1].metric("Clean dominance ratio", "—" if np.isinf(clean_ratio) else f"{clean_ratio:.2f}×")
metrics[2].metric("Single vs album ratio", f"{single_share / (1-single_share):.2f}×" if single_share < 1 else "Singles only")
metrics[3].metric("Average duration", f"{avg_duration:.2f} min")
metrics[4].metric("Album size impact", "—" if pd.isna(album_size_impact) else f"r = {album_size_impact:.2f}")
metrics[5].metric("Content acceptance score", f"{acceptance_score:.0f}/100")
st.caption("Acceptance score is rank-aligned: 100 = average rank #1, 0 = average rank #50. Album size impact is the album-track correlation between total tracks and popularity.")

left, right = st.columns(2)
with left:
    st.subheader("Explicit versus clean content")
    content_share = filtered["content_label"].value_counts(normalize=True).rename_axis("Content").reset_index(name="Share")
    st.altair_chart(
        alt.Chart(content_share).mark_bar().encode(
            x=alt.X("Share:Q", axis=alt.Axis(format="%")), y=alt.Y("Content:N", sort="-x"), color=alt.Color("Content:N", scale=alt.Scale(domain=["Clean", "Explicit"], range=["#2a9d8f", "#e76f51"])), tooltip=["Content", alt.Tooltip("Share:Q", format=".1%")]
        ).properties(height=220), use_container_width=True
    )
with right:
    st.subheader("Release format representation")
    format_share = filtered["album_type"].value_counts(normalize=True).rename_axis("Format").reset_index(name="Share")
    st.altair_chart(
        alt.Chart(format_share).mark_arc(innerRadius=55).encode(theta=alt.Theta("Share:Q"), color="Format:N", tooltip=["Format", alt.Tooltip("Share:Q", format=".1%")]).properties(height=220), use_container_width=True
    )

st.subheader("Rank-tier content attribute comparison")
# These tiers are cumulative so the Top 25 and Top 50 match playlist-pitching usage.
tier_rows = []
for tier in (10, 25, 50):
    subset = filtered[filtered["position"] <= tier]
    if not subset.empty:
        tier_rows.append({
            "rank_tier": f"Top {tier}", "Records": len(subset),
            "Explicit_share": subset["is_explicit"].mean(),
            "Single_share": (subset["album_type"] == "Single").mean(),
            "Average_popularity": subset["popularity"].mean(),
            "Average_duration_min": subset["duration_min"].mean(),
            "Average_rank": subset["position"].mean(),
        })
tier_summary = pd.DataFrame(tier_rows)
tier_melted = tier_summary.melt(id_vars="rank_tier", value_vars=["Explicit_share", "Single_share"], var_name="Attribute", value_name="Share")
st.altair_chart(
    alt.Chart(tier_melted).mark_bar().encode(
        x=alt.X("rank_tier:N", title="Rank tier"), y=alt.Y("Share:Q", axis=alt.Axis(format="%")), color="Attribute:N", xOffset="Attribute:N", tooltip=["rank_tier", "Attribute", alt.Tooltip("Share:Q", format=".1%")]
    ).properties(height=280), use_container_width=True
)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Song duration preference")
    histogram = alt.Chart(filtered).mark_bar().encode(
        x=alt.X("duration_min:Q", bin=alt.Bin(maxbins=18), title="Song duration (minutes)"), y=alt.Y("count():Q", title="Playlist appearances"), tooltip=[alt.Tooltip("count():Q", title="Appearances")]
    ).properties(height=260)
    st.altair_chart(histogram, use_container_width=True)
    duration_summary = filtered.groupby("duration_bucket", observed=False).agg(Appearances=("song", "size"), Average_popularity=("popularity", "mean"), Average_rank=("position", "mean")).reset_index()
    st.dataframe(duration_summary, use_container_width=True, hide_index=True)
with c2:
    st.subheader("Album structure impact")
    if album_rows.empty:
        st.info("No album tracks are included in the current selection.")
    else:
        scatter = alt.Chart(album_rows).mark_circle(size=55, opacity=0.55).encode(
            x=alt.X("total_tracks:Q", title="Album size (tracks)"), y=alt.Y("popularity:Q", title="Popularity score"), color=alt.Color("position:Q", title="Playlist rank", scale=alt.Scale(reverse=True)), tooltip=["song", "artist", "total_tracks", "popularity", "position"]
        ).properties(height=260)
        st.altair_chart(scatter, use_container_width=True)
        st.caption("A negative correlation suggests potential dilution; a positive correlation suggests larger albums concentrate stronger-performing tracks.")

st.subheader("Popularity and rank alignment")
comparison = filtered.groupby(["content_label", "album_type"], dropna=False).agg(
    Appearances=("song", "size"), Average_popularity=("popularity", "mean"), Average_rank=("position", "mean"), Average_duration_min=("duration_min", "mean")
).reset_index().sort_values("Average_rank")
st.dataframe(comparison, use_container_width=True, hide_index=True)

with st.expander("Data quality and validation", expanded=False):
    st.dataframe(build_validation(raw), use_container_width=True, hide_index=True)
    invalid_positions = raw.loc[~raw["position"].between(1, 50), "position"].notna().sum()
    st.write(f"Out-of-range playlist positions: **{invalid_positions:,}**. Album types were standardized and duration was converted from milliseconds to minutes.")

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button("Download filtered data", csv, "france_top_50_filtered.csv", "text/csv")
