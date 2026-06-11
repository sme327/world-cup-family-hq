import os
import base64
import pandas as pd
import streamlit as st

_SVC_DIR  = os.path.dirname(__file__)
_APP_ROOT = os.path.join(_SVC_DIR, '..')
_DATA_DIR = os.path.join(_APP_ROOT, 'data')

# App team name → manifest country name (where they differ)
_COUNTRY_NAME_MAP: dict[str, str] = {
    'Iran':       'IR Iran',
    'South Korea':'Korea Republic',
    'Ivory Coast':"Côte d'Ivoire",
    'Cape Verde': 'Cabo Verde',
    'DR Congo':   'Congo DR',
}

# App city name (from matches.csv) → manifest city_slug
_CITY_SLUG_MAP: dict[str, str] = {
    'East Rutherford': 'new-york',
    'Arlington':       'dallas',
    'Los Angeles':     'los-angeles',
    'Santa Clara':     'san-francisco',
    'Philadelphia':    'philadelphia',
    'Miami Gardens':   'miami',
    'Kansas City':     'kansas-city',
    'Foxborough':      'boston',
    'Atlanta':         'atlanta',
    'Seattle':         'seattle',
    'Houston':         'houston',
    'Vancouver':       'vancouver',
    'Toronto':         'toronto',
    'Mexico City':     'mexico-city',
    'Guadalajara':     'guadalajara',
    'Monterrey':       'monterrey',
}


@st.cache_data
def _load_country_manifest() -> dict[str, str]:
    path = os.path.join(_DATA_DIR, 'country_image_manifest.csv')
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    return dict(zip(df['country'], df['image_path']))


@st.cache_data
def _load_city_manifest() -> pd.DataFrame:
    path = os.path.join(_DATA_DIR, 'city_image_manifest.csv')
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def _read_b64(abs_path: str) -> tuple[str, str] | None:
    """Returns (base64_data, mime_type) or None on any failure."""
    if not os.path.exists(abs_path):
        return None
    try:
        with open(abs_path, 'rb') as f:
            data = base64.b64encode(f.read()).decode()
        ext  = abs_path.rsplit('.', 1)[-1].lower()
        mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'webp': 'webp'}.get(ext, 'jpeg')
        return data, mime
    except Exception:
        return None


def get_country_image_html(
    country: str,
    height: str = '320px',
    border_radius: str = '16px 16px 0 0',
) -> str | None:
    """Return an <img> HTML string for a country, or None if no image found."""
    manifest = _load_country_manifest()
    canonical = _COUNTRY_NAME_MAP.get(country, country)
    rel = manifest.get(canonical)
    if not rel:
        return None
    result = _read_b64(os.path.join(_APP_ROOT, rel))
    if not result:
        return None
    b64, mime = result
    style = f'width:100%;height:{height};object-fit:cover;display:block;border-radius:{border_radius}'
    return f"<img src='data:image/{mime};base64,{b64}' alt='{country}' style='{style}'>"


def get_city_image_html(
    city: str,
    image_type: str = 'landmark',
    height: str = '260px',
    border_radius: str = '16px 16px 0 0',
) -> str | None:
    """Return an <img> HTML string for a host city, or None if no image found.

    image_type: 'landmark' (default) or 'stadium'
    """
    slug = _CITY_SLUG_MAP.get(city, city.lower().replace(' ', '-'))
    df   = _load_city_manifest()
    if df.empty:
        return None
    row = df[df['city_slug'] == slug]
    if row.empty:
        return None
    col = 'landmark_image' if image_type == 'landmark' else 'stadium_image'
    rel = str(row.iloc[0].get(col, '')).strip()
    if not rel:
        return None
    result = _read_b64(os.path.join(_APP_ROOT, rel))
    if not result:
        return None
    b64, mime = result
    style = f'width:100%;height:{height};object-fit:cover;display:block;border-radius:{border_radius}'
    return f"<img src='data:image/{mime};base64,{b64}' alt='{city}' style='{style}'>"
