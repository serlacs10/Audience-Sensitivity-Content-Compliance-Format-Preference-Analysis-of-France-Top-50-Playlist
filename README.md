# Audience-Sensitivity-Content-Compliance-Format-Preference-Analysis-of-France-Top-50-Playlist
Analyzed France Top 50 playlist data to evaluate explicit content, album formats, song duration, and popularity trends. Built a Streamlit dashboard with interactive filters, KPIs, and visual insights for data-driven decisions.
France Top 50 Content & Format Dashboard

An interactive Streamlit dashboard for Atlantic Recording Corporation's France Top 50 playlist analysis.

## Run it

1. Install the packages: `pip install -r requirements.txt`
2. Start the dashboard: `streamlit run app.py`
3. Upload `Atlantic_France.csv` if the default file location is not available.

## Included analysis

- Data validation: playlist-day completeness, positions, and explicit-content flag coverage
- Explicit vs. clean representation and rank-tier comparison
- Single vs. album format distribution and popularity/rank comparison
- Album size vs. popularity relationship (dilution/concentration signal)
- Song-duration distribution, duration buckets, and rank/popularity alignment
- Content compliance KPI panel, filters, and a filtered-data export

### KPI definitions
- **Explicit Content Share:** proportion of selected playlist appearances marked explicit.
- **Clean Content Dominance Ratio:** clean appearances divided by explicit appearances.
- **Single vs Album Track Ratio:** selected single appearances divided by selected album appearances.
- **Average Song Duration:** mean duration in minutes across selected appearances.
- **Album Size Impact:** Pearson correlation between album track count and popularity for album tracks.
- **Content Acceptance Score:** rank-aligned score, where 100 is an average rank of #1 and 0 is #50.
