"""
Shared map building utilities for the World Atlas page and home page mini-map.
"""
import pandas as pd
import plotly.graph_objects as go

# ── ISO alpha-2 → alpha-3 mapping for all 48 WC teams ────────────────────────
_ISO2_TO_ISO3: dict[str, str] = {
    "MX": "MEX", "ZA": "ZAF", "KR": "KOR", "CZ": "CZE", "CA": "CAN",
    "BA": "BIH", "QA": "QAT", "CH": "CHE", "BR": "BRA", "MA": "MAR",
    "HT": "HTI", "GB-SCT": "GBR", "US": "USA", "PY": "PRY", "AU": "AUS",
    "TR": "TUR", "DE": "DEU", "CW": "CUW", "CI": "CIV", "EC": "ECU",
    "NL": "NLD", "JP": "JPN", "SE": "SWE", "TN": "TUN", "BE": "BEL",
    "EG": "EGY", "IR": "IRN", "NZ": "NZL", "ES": "ESP", "CV": "CPV",
    "SA": "SAU", "UY": "URY", "FR": "FRA", "SN": "SEN", "NO": "NOR",
    "IQ": "IRQ", "AR": "ARG", "DZ": "DZA", "AT": "AUT", "JO": "JOR",
    "PT": "PRT", "CD": "COD", "UZ": "UZB", "CO": "COL", "GB": "GBR",
    "HR": "HRV", "GH": "GHA", "PA": "PAN",
}

# ── 16 official host venues ───────────────────────────────────────────────────
HOST_CITIES: list[dict] = [
    {"city": "East Rutherford", "label": "NY/NJ",    "stadium": "MetLife Stadium",        "lat": 40.8135,  "lon": -74.0745,  "host": "USA"},
    {"city": "Arlington",        "label": "Dallas",   "stadium": "AT&T Stadium",            "lat": 32.7481,  "lon": -97.0928,  "host": "USA"},
    {"city": "Los Angeles",      "label": "LA",       "stadium": "SoFi Stadium",            "lat": 33.9535,  "lon": -118.3392, "host": "USA"},
    {"city": "Santa Clara",      "label": "SF Bay",   "stadium": "Levi's Stadium",          "lat": 37.4030,  "lon": -121.9697, "host": "USA"},
    {"city": "Philadelphia",     "label": "Philly",   "stadium": "Lincoln Financial Field", "lat": 39.9006,  "lon": -75.1676,  "host": "USA"},
    {"city": "Miami Gardens",    "label": "Miami",    "stadium": "Hard Rock Stadium",       "lat": 25.9580,  "lon": -80.2389,  "host": "USA"},
    {"city": "Kansas City",      "label": "KC",       "stadium": "Arrowhead Stadium",       "lat": 39.0489,  "lon": -94.4839,  "host": "USA"},
    {"city": "Foxborough",       "label": "Boston",   "stadium": "Gillette Stadium",        "lat": 42.0910,  "lon": -71.2643,  "host": "USA"},
    {"city": "Atlanta",          "label": "Atlanta",  "stadium": "Mercedes-Benz Stadium",   "lat": 33.7553,  "lon": -84.4006,  "host": "USA"},
    {"city": "Seattle",          "label": "Seattle ⭐","stadium": "Lumen Field",            "lat": 47.5952,  "lon": -122.3316, "host": "USA"},
    {"city": "Houston",          "label": "Houston",  "stadium": "NRG Stadium",             "lat": 29.6847,  "lon": -95.4107,  "host": "USA"},
    {"city": "Vancouver",        "label": "Vancouver","stadium": "BC Place",                "lat": 49.2767,  "lon": -123.1117, "host": "Canada"},
    {"city": "Toronto",          "label": "Toronto",  "stadium": "BMO Field",               "lat": 43.6335,  "lon": -79.4181,  "host": "Canada"},
    {"city": "Mexico City",      "label": "CDMX",     "stadium": "Estadio Azteca",          "lat": 19.3030,  "lon": -99.1505,  "host": "Mexico"},
    {"city": "Guadalajara",      "label": "Guadalajara","stadium": "Estadio Akron",         "lat": 20.6818,  "lon": -103.4617, "host": "Mexico"},
    {"city": "Monterrey",        "label": "Monterrey","stadium": "Estadio BBVA",            "lat": 25.6695,  "lon": -100.2420, "host": "Mexico"},
]

_HOST_PIN_COLORS = {"USA": "#60A5FA", "Canada": "#F87171", "Mexico": "#34D399"}

# Colorscale configs per layer
_SCALES: dict[str, dict] = {
    "today": {
        "cs":   [[0.0, "#1A3050"], [0.49, "#1A3050"], [0.5, "#2D5A9E"], [1.0, "#F59E0B"]],
        "zmin": 1, "zmax": 2,
    },
    "passport": {
        "cs": [
            [0.00, "#1A2A3D"],
            [0.34, "#0F766E"],
            [0.67, "#2563EB"],
            [1.00, "#10B981"],
        ],
        "zmin": 1, "zmax": 4,
    },
    "favorites": {
        "cs": [[0.0, "#1A2A3D"], [0.15, "#78350F"], [1.0, "#F59E0B"]],
        "zmin": 0, "zmax": 5,
    },
    "all": {
        "cs":   [[0.0, "#2D5A9E"], [1.0, "#3B82F6"]],
        "zmin": 0, "zmax": 1,
    },
}


def get_iso3_maps(teams_df: pd.DataFrame) -> tuple[dict, dict]:
    """Return (iso3→team_name, team_name→iso3).
    When Scotland and England both map to GBR, England gets the polygon (more widely known)."""
    i2n, n2i = {}, {}
    for _, row in teams_df.iterrows():
        iso2 = str(row.get("country_code", ""))
        iso3 = _ISO2_TO_ISO3.get(iso2)
        if not iso3:
            continue
        name = row["name"]
        n2i[name] = iso3
        # England (iso2 "GB") gets priority over Scotland (iso2 "GB-SCT") for GBR polygon
        if iso3 not in i2n or iso2 == "GB":
            i2n[iso3] = name
    return i2n, n2i


def build_atlas_figure(
    *,
    layer: str,
    teams_df: pd.DataFrame,
    discoveries: set,
    cheered: set,
    won: set,
    family_favs: list,
    today_countries: set,
    height: int = 520,
    show_pins: bool = True,
) -> go.Figure:
    """Build a Plotly world atlas choropleth for the given exploration layer."""
    iso3_list, z_list, text_list, name_list = [], [], [], []
    seen: set[str] = set()

    for _, row in teams_df.iterrows():
        iso2 = str(row.get("country_code", ""))
        iso3 = _ISO2_TO_ISO3.get(iso2)
        if not iso3 or iso3 in seen:
            continue
        seen.add(iso3)

        name = str(row["name"])
        flag = str(row.get("flag_emoji", ""))

        if layer == "today":
            z = 2.0 if name in today_countries else 1.0
        elif layer == "passport":
            if name in won:
                z = 4.0
            elif name in cheered:
                z = 3.0
            elif name in discoveries:
                z = 2.0
            else:
                z = 1.0
        elif layer == "favorites":
            try:
                z = float(max(1, 5 - family_favs.index(name)))
            except ValueError:
                z = 0.0
        else:  # "all"
            z = 1.0

        iso3_list.append(iso3)
        z_list.append(z)
        text_list.append(f"{flag} {name}")
        name_list.append(name)

    sc = _SCALES.get(layer, _SCALES["all"])

    choropleth = go.Choropleth(
        locations=iso3_list,
        z=z_list,
        text=text_list,
        customdata=[[n] for n in name_list],
        locationmode="ISO-3",
        colorscale=sc["cs"],
        zmin=sc["zmin"],
        zmax=sc["zmax"],
        showscale=False,
        hovertemplate="%{text}<extra></extra>",
        marker=dict(line=dict(color="#0D1B2E", width=0.5)),
    )

    traces = [choropleth]

    if show_pins:
        pin_size = 7 if height < 380 else 10
        pins = go.Scattergeo(
            lat=[c["lat"] for c in HOST_CITIES],
            lon=[c["lon"] for c in HOST_CITIES],
            text=[f"🏟️ {c['stadium']}<br>📍 {c['city']}" for c in HOST_CITIES],
            customdata=[[c["city"], c["stadium"], c["host"]] for c in HOST_CITIES],
            mode="markers",
            marker=dict(
                size=pin_size,
                color=[_HOST_PIN_COLORS.get(c["host"], "#FFF") for c in HOST_CITIES],
                symbol="circle",
                line=dict(color="#0D1B2E", width=1.5),
                opacity=0.9,
            ),
            hovertemplate="%{text}<extra></extra>",
            showlegend=False,
        )
        traces.append(pins)

    fig = go.Figure(data=traces)
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#0F172A",
        dragmode=False,
        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="#1E3A5F",
            showland=True,
            landcolor="#1A2A3D",
            showocean=True,
            oceancolor="#0D1520",
            showcountries=True,
            countrycolor="#1E3A5F",
            bgcolor="#0F172A",
            projection_type="natural earth",
            showlakes=False,
            showrivers=False,
        ),
    )
    return fig
