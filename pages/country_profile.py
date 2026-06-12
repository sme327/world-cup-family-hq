import json
import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from services.teams import get_all_teams, get_team_by_name, get_flag
from services.passport import get_stamp, log_discovery, get_country_metadata
from services.matches import get_matches_by_team
from services.images import get_country_image_html, get_country_card_image
from services.roster import (
    get_team_roster, get_team_summary, get_featured_players,
    get_mls_players, get_roster_by_position, pos_icon
)
from services.time_utils import fmt_date, fmt_match_time
import re
import unicodedata

# ── ISO-2 → ISO-3 for Plotly choropleth ──────────────────────────────────────
_ISO3 = {
    'MX':'MEX','ZA':'ZAF','KR':'KOR','CZ':'CZE','CA':'CAN','BA':'BIH',
    'QA':'QAT','CH':'CHE','BR':'BRA','MA':'MAR','HT':'HTI','GB':'GBR',
    'GB-SCT':'GBR','US':'USA','PY':'PRY','AU':'AUS','TR':'TUR','DE':'DEU',
    'CW':'CUW','CI':'CIV','EC':'ECU','NL':'NLD','JP':'JPN','SE':'SWE',
    'TN':'TUN','BE':'BEL','EG':'EGY','IR':'IRN','NZ':'NZL','ES':'ESP',
    'CV':'CPV','SA':'SAU','UY':'URY','FR':'FRA','SN':'SEN','NO':'NOR',
    'IQ':'IRQ','AR':'ARG','DZ':'DZA','AT':'AUT','JO':'JOR','PT':'PRT',
    'CD':'COD','UZ':'UZB','CO':'COL','HR':'HRV','GH':'GHA','PA':'PAN',
}

# ── Country details (soccer snapshot, neighbors, compare data) ────────────────
_DETAILS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'country_details.json')
try:
    with open(_DETAILS_PATH) as _f:
        _COUNTRY_DETAILS: dict = json.load(_f)
except Exception:
    _COUNTRY_DETAILS = {}


def _details(country: str) -> dict:
    return _COUNTRY_DETAILS.get(country, {})


# ── Known card descriptions (description, fun_fact) ──────────────────────────
_ANIMAL_INFO: dict[str, tuple[str, str]] = {
    "Jaguar":           ("The jaguar is the largest wild cat in the Americas and loves to swim.", "A jaguar's bite is stronger than a lion's — it can crack a turtle's shell!"),
    "Lion":             ("Lions live in family groups called prides. The females do most of the hunting!", "A lion's roar can be heard up to 5 miles away."),
    "Elephant":         ("Elephants are the largest land animals on Earth — and they never forget!", "An elephant uses its trunk as a hand, a nose, and even a snorkel when swimming."),
    "Tiger":            ("Tigers are the biggest wild cats and are expert swimmers.", "No two tigers have the same stripe pattern — like human fingerprints!"),
    "Giant Panda":      ("Giant pandas spend up to 14 hours a day eating bamboo!", "Pandas are born tiny — about the size of a stick of butter — but grow to 200+ lbs."),
    "Kangaroo":         ("Kangaroos can jump 25 feet in one leap and can't walk backwards.", "A baby kangaroo (joey) is about the size of a grape when it's born!"),
    "Polar Bear":       ("Polar bears have black skin under their white fur to absorb heat.", "Polar bears can swim over 60 miles without stopping."),
    "Giraffe":          ("Giraffes are the tallest animals on Earth — up to 18 feet tall!", "A giraffe's tongue is 18 inches long and dark blue to protect it from sunburn."),
    "Flamingo":         ("Flamingos get their pink color from the shrimp and algae they eat!", "Baby flamingos are born white — they turn pink as they eat more shrimp."),
    "Cheetah":          ("Cheetahs are the fastest land animals, reaching 70 mph in seconds.", "Cheetahs can go from 0 to 60 mph in just 3 seconds — faster than most sports cars!"),
    "Rhinoceros":       ("Rhinos have been on Earth for 50 million years, even before humans!", "A rhino's horn is made of the same material as your fingernails — keratin."),
    "Penguin":          ("Penguins are birds that can't fly, but they're amazing swimmers!", "Penguins propose to their mates by giving them a special pebble."),
    "Koala":            ("Koalas sleep up to 22 hours a day because eucalyptus leaves take lots of energy to digest.", "Koalas have fingerprints so similar to humans' that crime scene investigators can get confused!"),
    "Bald Eagle":       ("The bald eagle is the national bird of the USA and has incredible eyesight.", "Bald eagles can spot a fish in water from a mile away in the air!"),
    "Golden Eagle":     ("Golden eagles are among the fastest birds, diving at over 150 mph.", "Golden eagles mate for life and return to the same nest every year, adding to it each time."),
    "Wolf":             ("Wolves communicate with howls that can be heard up to 10 miles away.", "A wolf pack is really a family — the parents lead their children and grandchildren together."),
    "Brown Bear":       ("Brown bears can run 35 mph — faster than the fastest human sprinter.", "Bears can smell food from up to 20 miles away — the best nose of any land mammal."),
    "Dolphin":          ("Dolphins are so smart they can recognize themselves in a mirror!", "Dolphins sleep with one eye open, keeping half their brain awake to watch for danger."),
    "Snow Leopard":     ("Snow leopards can leap up to 50 feet in a single jump!", "Snow leopards can't roar — instead they make a special sound called a 'chuffing' noise."),
    "Monarch Butterfly":("Monarch butterflies migrate 3,000 miles every year between Canada and Mexico.", "Monarchs navigate using the sun — and they can even sense the Earth's magnetic field!"),
    "Axolotl":          ("Axolotls are amazing because they can regrow lost limbs, gills, and even parts of their brain!", "Axolotls never fully grow up — they keep their baby features their whole life."),
    "Komodo Dragon":    ("Komodo dragons are the world's largest lizards — up to 10 feet long!", "Their saliva is full of bacteria so powerful it acts like venom."),
    "Camel":            ("Camels store fat — not water — in their humps for energy on long desert journeys.", "A camel can drink 40 gallons of water in just 13 minutes!"),
    "Capybara":         ("Capybaras are the world's largest rodents — basically giant friendly guinea pigs!", "Capybaras are so chill that birds, monkeys, and even cats like to sit on them."),
}

_FOOD_INFO: dict[str, tuple[str, str]] = {
    "Tacos":          ("Tacos are corn or flour tortillas filled with meat, beans, salsa, and toppings.", "There are hundreds of regional taco styles in Mexico — from al pastor to fish tacos!"),
    "Guacamole":      ("Guacamole is made from mashed avocados mixed with lime, onion, and cilantro.", "Avocados are native to Mexico — the Aztecs were making guacamole 500 years ago!"),
    "Tamales":        ("Tamales are corn dough stuffed with meat or cheese, wrapped in corn husks and steamed.", "Making tamales is a family tradition — families gather to make hundreds at holiday time."),
    "Sushi":          ("Sushi combines vinegared rice with fresh seafood, vegetables, or egg.", "The word 'sushi' actually refers to the special rice, not the fish!"),
    "Pizza":          ("Pizza started in Naples, Italy, but is now loved all over the world.", "The world's most expensive pizza takes 72 hours to make and costs thousands of dollars."),
    "Pasta":          ("Italy has over 350 different pasta shapes — each one designed to hold a different sauce!", "Italians eat about 60 pounds of pasta per person every year."),
    "Croissant":      ("Croissants are buttery, flaky pastries that take over two days to make properly.", "The croissant was actually invented in Austria, not France — it was called a Kipferl!"),
    "Baguette":       ("A French baguette must be at least 22 inches long by law!", "Over 30 million baguettes are baked in France every single day."),
    "Schnitzel":      ("Schnitzel is a thin breaded meat cutlet pounded flat and fried until crispy.", "The original Wiener Schnitzel must legally be made from veal in Austria."),
    "Braai":          ("Braai is the South African word for barbecue — it's a huge social tradition.", "In South Africa there's a National Braai Day every September 24th!"),
    "Biltong":        ("Biltong is dried, spiced meat — like beef jerky but even more flavorful.", "South African rugby and cricket fans always bring biltong to matches."),
    "Ramen":          ("Ramen is a Japanese noodle soup that can take up to 18 hours to prepare the broth.", "Japan has over 35,000 ramen restaurants — more than any other country!"),
    "Tempura":        ("Tempura is lightly battered and deep-fried seafood and vegetables — super crispy!", "Tempura was actually introduced to Japan by Portuguese missionaries in the 1500s."),
    "Kimchi":         ("Kimchi is fermented vegetables (usually cabbage) with spicy seasoning.", "The average South Korean eats about 40 pounds of kimchi every year!"),
    "Bibimbap":       ("Bibimbap means 'mixed rice' — it's rice topped with vegetables, egg, and sauce.", "There are said to be over 70 different toppings you can put on bibimbap!"),
    "Poutine":        ("Poutine is french fries topped with cheese curds and gravy — Canada's most famous dish.", "The squeaky sound of fresh cheese curds when you eat them means they're extra fresh!"),
    "Pampushky":      ("Pampushky are soft Ukrainian garlic bread rolls — fluffy and delicious!", "Ukrainians traditionally serve pampushky alongside borscht."),
    "Crocodile":      ("Crocodile meat is actually eaten in parts of Africa — it tastes like chicken!", "Crocodile is rich in protein and considered a delicacy in some African countries."),
    "Moussaka":       ("Moussaka is a Greek-style casserole with layers of eggplant, meat, and creamy sauce.", "Every Greek grandmother has their own secret moussaka recipe!"),
    "Mezze":          ("Mezze is a collection of small dishes shared by everyone at the table.", "In the Middle East, sharing a big spread of mezze dishes is a sign of hospitality and friendship."),
    "Hummus":         ("Hummus is a creamy dip made from chickpeas, tahini, lemon, and garlic.", "Lebanon once made the world's largest plate of hummus weighing over 23,000 pounds!"),
    "Falafel":        ("Falafel are crispy fried balls made from ground chickpeas or fava beans.", "Falafel has been eaten in the Middle East for over 1,000 years!"),
    "Barbecue":       ("Brazilian churrasco barbecue involves giant skewers of meat cooked over open flames.", "In southern Brazil, some restaurants keep bringing more meat to your table until you flip a card to say stop!"),
    "Açaí":           ("Açaí berries are a superfood from the Amazon rainforest — dark purple and delicious!", "In Brazil, açaí bowls are eaten for breakfast, lunch, and as a snack — they're that popular."),
    "Stroopwafel":    ("Stroopwafels are two thin waffles sandwiched together with caramel syrup.", "Dutch astronaut André Kuipers took stroopwafels to the International Space Station!"),
    "Stamppot":       ("Stamppot is a Dutch comfort food — mashed potatoes mixed with vegetables.", "Every Dutch family has their own special stamppot recipe that gets passed down through generations."),
}

_LANDMARK_INFO: dict[str, tuple[str, str]] = {
    "Chichen Itza":          ("Chichen Itza is a spectacular Mayan pyramid in Mexico — one of the New Seven Wonders of the World.", "Twice a year, the sun creates a shadow on Chichen Itza that looks exactly like a giant snake crawling down!"),
    "Eiffel Tower":          ("The Eiffel Tower was built as a temporary structure in 1889 but was never taken down.", "The Eiffel Tower grows about 6 inches taller in summer because the metal expands in heat!"),
    "Colosseum":             ("The Roman Colosseum could hold 80,000 spectators — more than most modern NFL stadiums!", "The Colosseum had 80 entrances so it could be completely filled or emptied in just 15 minutes."),
    "Machu Picchu":          ("Machu Picchu was built by the Inca people high in the Andes mountains around 1450 AD.", "No one is sure exactly why Machu Picchu was built — it might have been a royal vacation home!"),
    "Great Wall of China":   ("The Great Wall of China stretches over 13,000 miles — you could walk it for years.", "Millions of workers built the wall over 2,000 years — and it's still not entirely explored!"),
    "Taj Mahal":             ("The Taj Mahal was built by an emperor as a monument of love for his wife.", "The Taj Mahal took 22 years and 20,000 workers to build — using no heavy machinery!"),
    "Pyramids of Giza":      ("The Great Pyramid of Giza is the oldest of the Seven Wonders of the Ancient World — and the only one still standing!", "The pyramid's stones are so precisely cut that you can't fit a piece of paper between them."),
    "Stonehenge":            ("No one knows exactly why Stonehenge was built — it's still a mystery!", "The huge stones at Stonehenge were transported over 150 miles — with no wheels or cranes!"),
    "Colosseum":             ("The Roman Colosseum once hosted battles with lions, elephants, and thousands of gladiators.", "Workers could flood the Colosseum floor to stage mock sea battles!"),
    "Niagara Falls":         ("Niagara Falls moves about 1 million gallons of water per second — absolutely thundering!", "The sound of Niagara Falls can be heard from 100 miles away on a quiet day."),
    "Amazon Rainforest":     ("The Amazon is the world's largest rainforest and produces 20% of Earth's oxygen.", "The Amazon River flows so much water that it freshens the Atlantic Ocean 100 miles out to sea."),
    "Ayers Rock":            ("Uluru (Ayers Rock) in Australia changes color from red to orange to purple as the sun rises and sets.", "Uluru is sacred to the Aboriginal Anangu people who have lived near it for 30,000 years."),
    "Sydney Opera House":    ("The Sydney Opera House's roof looks like a series of giant shells or sails.", "The building has 1 million tiles on the roof and took 14 years to build."),
    "Great Barrier Reef":    ("The Great Barrier Reef is the world's largest coral reef — so big it can be seen from space!", "Over 1,500 species of fish live in the Great Barrier Reef."),
    "Acropolis":             ("The Acropolis in Athens is over 2,500 years old — built before cars, power tools, or calculators!", "The Parthenon on the Acropolis has no perfectly straight lines — the ancient Greeks curved everything slightly to make it look perfect from below."),
    "Sagrada Familia":       ("This amazing cathedral in Barcelona has been under construction for over 140 years — it's still not finished!", "The architect Antoni Gaudí is buried inside the church he designed."),
}


def _card_info(item_type: str, label: str, country: str) -> tuple[str, str]:
    """Return (description, fun_fact) for a card item."""
    clean = _strip_emoji(label).strip()

    if item_type == "animal":
        for key, val in _ANIMAL_INFO.items():
            if key.lower() in clean.lower() or clean.lower() in key.lower():
                return val
        return (
            f"The {clean} is one of the most amazing animals found in {country}.",
            f"{country} has incredible wildlife found nowhere else in the world!"
        )
    if item_type == "food":
        for key, val in _FOOD_INFO.items():
            if key.lower() in clean.lower() or clean.lower() in key.lower():
                return val
        return (
            f"{clean} is a delicious dish from {country} loved by people around the world.",
            f"Food in {country} is famous for its amazing flavors and traditions!"
        )
    if item_type == "landmark":
        for key, val in _LANDMARK_INFO.items():
            if key.lower() in clean.lower() or clean.lower() in key.lower():
                return val
        return (
            f"{clean} is one of the most famous places to visit in {country}.",
            f"Millions of people travel to {country} every year to see incredible places like this!"
        )
    # cheer reason
    return (
        f"This is one of the coolest things that makes {country} special!",
        f"Learning about {country} is like going on a mini adventure from your couch."
    )


# ── Helpers ───────────────────────────────────────────────────────────────────
def _parse_pipe(val) -> list[str]:
    if not val or pd.isna(val):
        return []
    return [s.strip() for s in str(val).split('|') if s.strip()]


def _safe(val, default="—"):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    return val


def _parse_pop_m(pop_str: str) -> float | None:
    s = str(pop_str).lower().replace(',', '')
    try:
        if 'billion' in s:
            return float(s.split('billion')[0].split()[-1]) * 1000
        if 'million' in s:
            return float(s.split('million')[0].split()[-1])
        if 'thousand' in s:
            return float(s.split('thousand')[0].split()[-1]) / 1000
    except Exception:
        pass
    return None


# ── Slug helpers ───────────────────────────────────────────────────────────────
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002702-\U000027B0\U0000FE00-\U0000FE0F☀-⛿⭐⭕▪-◾☔♈-♓]+",
    flags=re.UNICODE,
)


def _strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text).strip()


def _country_slug(name: str) -> str:
    s = name.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("'", "").replace("'", "")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")


def _item_slug(raw: str) -> str:
    s = _strip_emoji(raw).lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", "_", s.strip())
    return s.strip("_")


def _split_label_emoji(raw: str, fallback_emoji: str) -> tuple[str, str]:
    parts = raw.rsplit(" ", 1)
    if len(parts) == 2 and not parts[-1].isascii():
        return parts[0].strip(), parts[1].strip()
    return raw.strip(), fallback_emoji


@st.cache_data(ttl=86400)
def _country_map(iso3: str):
    fig = go.Figure(go.Choropleth(
        locations=[iso3], z=[1], locationmode='ISO-3',
        colorscale=[[0, '#2563EB'], [1, '#2563EB']],
        showscale=False,
        marker_line_color='white', marker_line_width=0.8,
    ))
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True, coastlinecolor='#94A3B8',
            showland=True,       landcolor='#E2E8F0',
            showocean=True,      oceancolor='#DBEAFE',
            projection_type='natural earth',
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=340,
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def _stat_card(icon: str, label: str, value: str) -> str:
    return (
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
        "padding:.8rem;text-align:center;color:white;border:1px solid rgba(148,163,184,.15)'>"
        f"<div style='font-size:1.5rem'>{icon}</div>"
        f"<div style='font-size:.75rem;color:#94A3B8;margin:.15rem 0;font-weight:600;"
        f"text-transform:uppercase;letter-spacing:.04em'>{label}</div>"
        f"<div style='font-size:.92rem;font-weight:800;color:#F1F5F9;line-height:1.2'>{value}</div>"
        "</div>"
    )


def _explore_card(emoji: str, label: str, img: tuple | None = None) -> str:
    if img:
        b64, mime = img
        return (
            "<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;"
            "overflow:hidden;text-align:center'>"
            f"<img src='data:image/{mime};base64,{b64}' alt='{label}' "
            "style='width:100%;height:120px;object-fit:cover;display:block'>"
            "<div style='padding:.4rem .5rem .5rem'>"
            f"<div style='font-size:.82rem;font-weight:700;color:#0F172A;line-height:1.2'>{label}</div>"
            "</div></div>"
        )
    return (
        "<div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;"
        "padding:.7rem .5rem;text-align:center'>"
        f"<div style='font-size:2.2rem;line-height:1.1;margin-bottom:.3rem'>{emoji}</div>"
        f"<div style='font-size:.82rem;font-weight:700;color:#0F172A;line-height:1.2'>{label}</div>"
        "</div>"
    )


def _cheer_card(emoji: str, label: str, blurb: str, img: tuple | None = None) -> str:
    if img:
        b64, mime = img
        return (
            "<div style='background:white;border:1.5px solid #E2E8F0;border-radius:14px;"
            "overflow:hidden;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)'>"
            f"<img src='data:image/{mime};base64,{b64}' alt='{label}' "
            "style='width:100%;height:100px;object-fit:cover;display:block'>"
            "<div style='padding:.5rem .6rem .6rem'>"
            f"<div style='font-size:.88rem;font-weight:800;color:#0F172A;margin-bottom:.15rem'>{label}</div>"
            f"<div style='font-size:.75rem;color:#64748B;line-height:1.35'>{blurb}</div>"
            "</div></div>"
        )
    return (
        "<div style='background:white;border:1.5px solid #E2E8F0;border-radius:14px;"
        "padding:.9rem .6rem;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,.06)'>"
        f"<div style='font-size:2.5rem;margin-bottom:.3rem'>{emoji}</div>"
        f"<div style='font-size:.88rem;font-weight:800;color:#0F172A;margin-bottom:.2rem'>{label}</div>"
        f"<div style='font-size:.75rem;color:#64748B;line-height:1.35'>{blurb}</div>"
        "</div>"
    )


def _cheer_blurb(label: str, country: str) -> str:
    """Generate a kid-friendly cheer reason blurb."""
    lo = label.lower()
    if any(w in lo for w in ["food", "taco", "sushi", "pizza", "cuisine", "eat"]):
        return f"The food in {country} is absolutely delicious — kids who try it always want more!"
    if any(w in lo for w in ["pyramid", "temple", "castle", "ancient", "ruins", "wonder"]):
        return f"Imagine standing next to something built thousands of years ago! {country} has real ancient wonders."
    if any(w in lo for w in ["cat", "jaguar", "lion", "tiger", "leopard", "puma"]):
        return f"Big cats are the most powerful hunters on Earth — and {country} has some amazing ones!"
    if any(w in lo for w in ["bird", "eagle", "flamingo", "parrot", "toucan"]):
        return f"The birds of {country} are stunning — some have colors brighter than a rainbow!"
    if any(w in lo for w in ["soccer", "football", "futbol", "sport", "team"]):
        return f"Soccer is religion in {country} — the passion and energy at their matches is unreal!"
    if any(w in lo for w in ["music", "dance", "samba", "flamenco", "tango"]):
        return f"The music and dance of {country} is so energetic you can't help but want to move!"
    if any(w in lo for w in ["beach", "ocean", "island", "sea", "surf"]):
        return f"The beaches of {country} are world-famous — crystal blue water and amazing waves!"
    if any(w in lo for w in ["mountain", "volcano", "hiking", "alps", "andes"]):
        return f"The mountains of {country} are jaw-dropping — some are so tall they have snow year-round!"
    if any(w in lo for w in ["host", "world cup", "stadium", "fifa"]):
        return f"{country} is hosting World Cup 2026! The stadiums and fan energy will be incredible."
    if any(w in lo for w in ["game", "nintendo", "anime", "manga", "pokemon"]):
        return f"Some of your favorite games and cartoons come from {country}. It's the coolest!"
    if any(w in lo for w in ["space", "nasa", "astronaut", "science", "tech"]):
        return f"{country} is a world leader in science and exploration — they're always pushing boundaries!"
    if any(w in lo for w in ["animal", "wildlife", "safari", "nature", "jungle"]):
        return f"The wildlife in {country} is like stepping into a nature documentary — incredible creatures everywhere!"
    if any(w in lo for w in ["underdog", "surprise", "qualify", "first time", "debut"]):
        return f"{country} worked so hard to get here — everyone loves a great underdog story!"
    return f"This is one of the coolest things that makes {country} truly special!"


# ── Sidebar ───────────────────────────────────────────────────────────────────
teams_df = get_all_teams()

_nav_country = st.session_state.pop("_nav_country", None)

with st.sidebar:
    st.markdown("### 🌍 Explore Countries")
    all_countries = sorted(teams_df['name'].tolist())
    default_idx   = all_countries.index(_nav_country) if _nav_country and _nav_country in all_countries else 0
    selected_country = st.selectbox("Country", all_countries, index=default_idx)

active_user_id = st.session_state.get("active_user_id", 1)

# ── Silent discovery logging ──────────────────────────────────────────────────
log_discovery(active_user_id, selected_country)

# ── Load data ─────────────────────────────────────────────────────────────────
team    = get_team_by_name(selected_country)
stamp   = get_stamp(selected_country)
flag    = get_flag(selected_country)
cslug   = _country_slug(selected_country)
details = _details(selected_country)

if team is None:
    st.error(f"Country data not found: {selected_country}")
    st.stop()

iso2 = _safe(team.get('country_code'), '')
iso3 = _ISO3.get(iso2, '')
fun  = _safe(team.get('fun_fact'), '')

# ── 1. Hero Image (reduced height ~250px) ─────────────────────────────────────
hero_html = get_country_image_html(selected_country, height='250px')
has_hero  = hero_html is not None

if has_hero:
    st.markdown(hero_html, unsafe_allow_html=True)

# ── Country identity banner ───────────────────────────────────────────────────
flag_size    = "2.5rem" if has_hero else "4rem"
header_pad   = "1rem 1.5rem 1.2rem" if has_hero else "2rem"
border_radius = "0 0 16px 16px" if has_hero else "16px"

st.markdown(
    f"<div style='background:linear-gradient(135deg,#1E3A5F,#2563EB);"
    f"padding:{header_pad};border-radius:{border_radius};text-align:center;color:white;margin-bottom:1.2rem'>"
    f"<div style='font-size:{flag_size};margin-bottom:.2rem'>{flag}</div>"
    f"<div style='font-size:2rem;font-weight:900'>{selected_country}</div>"
    f"<div style='font-size:1.1rem;color:#FCD34D;margin:.2rem 0'>{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
    f"<div style='color:#CBD5E1;font-size:.88rem'>"
    f"{stamp['continent']} · Group {_safe(team.get('group_letter'))} · FIFA #{_safe(team.get('fifa_ranking'))}"
    f"</div></div>",
    unsafe_allow_html=True
)

if not has_hero:
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1E293B,#0F172A);border-radius:12px;"
        "height:100px;display:flex;align-items:center;justify-content:center;"
        "color:rgba(255,255,255,.3);font-size:.85rem;margin-bottom:1rem;"
        "border:1px dashed rgba(148,163,184,.3)'>"
        "<div style='text-align:center'><div style='font-size:1.8rem'>📷</div>"
        "<div>Country photo coming soon</div></div></div>",
        unsafe_allow_html=True
    )

# ── 2. Country Facts Grid ─────────────────────────────────────────────────────
st.markdown("### 🌍 Country Facts")
row1 = st.columns(3)
row2 = st.columns(3)
facts = [
    ("🏙️", "Capital",       _safe(team.get('capital'))),
    ("👥", "Population",    _safe(team.get('population'))),
    ("🗣️", "Languages",     _safe(team.get('languages'))),
    ("💰", "Currency",      _safe(team.get('currency'))),
    ("🌍", "Continent",     stamp['continent']),
    ("⚽", "Confederation", _safe(team.get('confederation'))),
]
for col, (icon, label, val) in zip(list(row1) + list(row2), facts):
    col.markdown(_stat_card(icon, label, val), unsafe_allow_html=True)

if fun:
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#FEF3C7,#FDE68A);border-radius:12px;"
        f"padding:.75rem 1rem;margin:.7rem 0;border-left:4px solid #FCD34D'>"
        f"<div style='font-size:.88rem;color:#78350F'><b>💡 Did you know?</b> {fun}</div></div>",
        unsafe_allow_html=True
    )

# ── 3. Soccer Snapshot ────────────────────────────────────────────────────────
nickname      = details.get('nickname', '—')
famous_player = details.get('famous_player', _safe(team.get('captain'), '—'))
home_stadium  = details.get('home_stadium', '—')
best_finish   = _safe(team.get('best_finish'), '—')

st.markdown("### ⚽ Soccer Snapshot")
ss_cols = st.columns(4)
soccer_facts = [
    ("🎽", "Nickname",       nickname),
    ("🏆", "Best WC Finish", best_finish),
    ("⭐", "Famous Player",  famous_player),
    ("🏟️", "Home Stadium",   home_stadium),
]
for col, (icon, label, val) in zip(ss_cols, soccer_facts):
    col.markdown(_stat_card(icon, label, val), unsafe_allow_html=True)

# ── 4. Where Is This Country? Map (larger) ────────────────────────────────────
st.markdown("### 🗺️ Where Is This Country?")
if iso3:
    try:
        fig = _country_map(iso3)
        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})
    except Exception:
        st.info(f"📍 {selected_country} is located in {stamp['continent']}.")
else:
    st.info(f"📍 {selected_country} is located in {stamp['continent']}.")

# Neighbor pills
neighbors = details.get('neighbors', [])
if neighbors:
    neighbor_pills = "".join(
        f"<span style='background:rgba(37,99,235,.18);color:#93C5FD;"
        f"border:1px solid rgba(37,99,235,.35);border-radius:20px;"
        f"padding:.2rem .65rem;font-size:.8rem;margin:.15rem;display:inline-block'>"
        f"{get_flag(n)} {n}</span>"
        for n in neighbors
    )
    st.markdown(
        f"<div style='margin-top:.3rem'>"
        f"<div style='font-size:.78rem;color:#64748B;font-weight:700;margin-bottom:.3rem'>🌎 Neighboring Countries</div>"
        f"<div>{neighbor_pills}</div></div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<div style='font-size:.82rem;color:#64748B;margin-top:.3rem'>"
        "🌊 Island nation — surrounded by ocean on all sides</div>",
        unsafe_allow_html=True
    )

# ── 5. Compare To Seattle ─────────────────────────────────────────────────────
st.markdown("### 🏡 Compare To Seattle")

dist_miles   = details.get('distance_miles', 0)
tz_offset    = details.get('timezone_offset', 0)
pop_m        = _parse_pop_m(team.get('population', ''))
seattle_pop  = 4.0  # Seattle metro, millions

compare_cards = []

# Distance
if dist_miles and dist_miles > 50:
    compare_cards.append(("✈️", "Distance from Seattle",
                          f"{dist_miles:,} miles",
                          f"That's about {dist_miles // 500} long road trips away!"))
elif dist_miles <= 50:
    compare_cards.append(("🏠", "Distance from Seattle", "Right next door!", "You could almost drive there in a day."))

# Time zone
if tz_offset == 0:
    tz_label = "Same time!"
    tz_note  = "When it's 3 PM here, it's 3 PM there too."
elif tz_offset > 0:
    tz_label = f"+{tz_offset}h ahead"
    tz_note  = f"When it's 9 AM in Seattle, it's {9 + int(tz_offset)}{'AM' if 9+int(tz_offset)<12 else 'PM'} there."
else:
    tz_label = f"{tz_offset}h behind"
    tz_note  = f"When it's 9 AM in Seattle, it's {9 + int(tz_offset)} AM there."
compare_cards.append(("🕐", "Time Zone", tz_label, tz_note))

# Population
if pop_m:
    sea_ratio = pop_m / seattle_pop
    if pop_m >= 1000:
        pop_display = f"{pop_m/1000:.1f} billion"
    elif pop_m >= 1:
        pop_display = f"{pop_m:.0f} million"
    else:
        pop_display = f"{pop_m*1000:.0f} thousand"

    if sea_ratio >= 10:
        pop_note = f"That's {int(sea_ratio)}× more people than the Seattle metro area!"
    elif sea_ratio >= 2:
        pop_note = f"About {sea_ratio:.1f}× as many people as the Seattle area."
    elif sea_ratio >= 0.5:
        pop_note = "A similar number of people to the Seattle area."
    else:
        pop_note = "Smaller population than the Seattle metro area!"
    compare_cards.append(("👥", "Population", pop_display, pop_note))

# Language
lang = _safe(team.get('languages'), '')
if lang and lang != '—':
    if 'English' in lang:
        compare_cards.append(("🗣️", "Language", lang, "They speak English there too — just like Seattle!"))
    else:
        first_lang = lang.split(',')[0].strip()
        compare_cards.append(("🗣️", "Language", first_lang, f"People there say hello in {first_lang} — how cool is that!"))

# Show up to 4 compare cards
n_compare = min(len(compare_cards), 4)
if n_compare > 0:
    cmp_cols = st.columns(n_compare)
    for col, (icon, label, val, note) in zip(cmp_cols, compare_cards[:n_compare]):
        col.markdown(
            "<div style='background:linear-gradient(160deg,#0F172A,#1E293B);"
            "border:1px solid rgba(148,163,184,.15);border-radius:12px;"
            "padding:.75rem;text-align:center'>"
            f"<div style='font-size:1.4rem'>{icon}</div>"
            f"<div style='font-size:.72rem;color:#94A3B8;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:.04em;margin:.12rem 0'>{label}</div>"
            f"<div style='font-size:.95rem;font-weight:900;color:#F1F5F9;line-height:1.2'>{val}</div>"
            f"<div style='font-size:.7rem;color:#64748B;margin-top:.2rem;line-height:1.3'>{note}</div>"
            "</div>",
            unsafe_allow_html=True
        )

# ── 6. Animals & Nature ───────────────────────────────────────────────────────
animals = _parse_pipe(team.get('animals'))
if animals:
    st.markdown("### 🐾 Animals & Nature")
    a_cols = st.columns(min(len(animals), 4))
    for col, a in zip(a_cols, animals[:4]):
        label, emoji = _split_label_emoji(a, "🐾")
        islug = _item_slug(a)
        img   = get_country_card_image(cslug, islug)
        desc, fact = _card_info("animal", label, selected_country)
        with col:
            st.markdown(_explore_card(emoji, label, img), unsafe_allow_html=True)
            with st.popover(f"✨ {label}", use_container_width=True):
                st.markdown(f"### {emoji} {label}")
                st.markdown(desc)
                st.info(f"🎯 **Fun Fact:** {fact}")

# ── 7. Famous Foods ───────────────────────────────────────────────────────────
foods = _parse_pipe(team.get('foods'))
if foods:
    st.markdown("### 🍽️ Famous Foods")
    f_cols = st.columns(min(len(foods), 4))
    for col, food in zip(f_cols, foods[:4]):
        label, emoji = _split_label_emoji(food, "🍴")
        islug = _item_slug(food)
        img   = get_country_card_image(cslug, islug)
        desc, fact = _card_info("food", label, selected_country)
        with col:
            st.markdown(_explore_card(emoji, label, img), unsafe_allow_html=True)
            with st.popover(f"✨ {label}", use_container_width=True):
                st.markdown(f"### {emoji} {label}")
                st.markdown(desc)
                st.info(f"🎯 **Fun Fact:** {fact}")

# ── 8. Famous Landmarks ───────────────────────────────────────────────────────
landmarks = _parse_pipe(team.get('landmarks'))
if landmarks:
    st.markdown("### 🏛️ Famous Landmarks")
    l_cols = st.columns(min(len(landmarks), 4))
    for col, lm in zip(l_cols, landmarks[:4]):
        islug = _item_slug(lm)
        img   = get_country_card_image(cslug, islug)
        desc, fact = _card_info("landmark", lm, selected_country)
        with col:
            st.markdown(_explore_card("📍", lm, img), unsafe_allow_html=True)
            with st.popover(f"✨ {_strip_emoji(lm).strip()}", use_container_width=True):
                st.markdown(f"### 📍 {lm}")
                st.markdown(desc)
                st.info(f"🎯 **Fun Fact:** {fact}")

# ── 9. Why Kids Might Cheer ───────────────────────────────────────────────────
reasons = _parse_pipe(team.get('cheer_reasons'))
if reasons:
    st.markdown("### 🎉 Why Kids Might Cheer For This Country")
    r_cols = st.columns(min(len(reasons), 4))
    for col, reason in zip(r_cols, reasons[:4]):
        label, emoji = _split_label_emoji(reason, "⭐")
        blurb = _cheer_blurb(label, selected_country)
        islug = _item_slug(reason)
        img   = get_country_card_image(cslug, islug)
        desc, fact = _card_info("cheer", label, selected_country)
        with col:
            st.markdown(_cheer_card(emoji, label, blurb, img), unsafe_allow_html=True)
            with st.popover(f"✨ {label}", use_container_width=True):
                st.markdown(f"### {emoji} {label}")
                st.markdown(blurb)
                st.info(f"🎯 **Fun Fact:** {fact}")

# ── 10. Soccer Team Overview ──────────────────────────────────────────────────
st.divider()
st.markdown("## ⚽ Soccer Team")

soc1, soc2, soc3 = st.columns(3)
soc1.metric("FIFA Ranking", f"#{_safe(team.get('fifa_ranking'))}")
soc1.markdown(f"**Coach:** {_safe(team.get('coach'))}")
soc1.markdown(f"**Captain:** {_safe(team.get('captain'))}")
soc2.metric("World Cup Appearances", _safe(team.get('wc_appearances'), "—"))
soc2.markdown(f"**Best Finish:** {_safe(team.get('best_finish'))}")

# ── 11. Group Stage Matches ───────────────────────────────────────────────────
matches = get_matches_by_team(selected_country)
if not matches.empty:
    st.markdown("#### ⚽ Group Stage Matches")
    for _, m in matches.iterrows():
        opp      = m['away_team'] if m['home_team'] == selected_country else m['home_team']
        opp_flag = get_flag(opp)
        mid      = int(m['id'])
        time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])

        if m['status'] == 'completed':
            hs, as_ = int(m['home_score']), int(m['away_score'])
            score   = f"**{hs}–{as_}**"
            label   = f"{flag} {selected_country} vs {opp_flag} {opp} · {score}"
        else:
            label   = f"{flag} {selected_country} vs {opp_flag} **{opp}** · {time_str}"

        col_info, col_btn = st.columns([5, 2])
        col_info.markdown(label)
        if col_btn.button("🏟️ Matchup", key=f"match_link_{mid}"):
            st.session_state["_nav_match_id"] = mid
            st.switch_page("pages/matchup.py")

# ── 12. Meet the Team ─────────────────────────────────────────────────────────
st.divider()
st.markdown("## 👥 Meet the Team")

summary      = get_team_summary(selected_country)
roster       = get_team_roster(selected_country)
captain_name = _safe(team.get('captain'), '')

if summary:
    st.markdown("#### Squad Snapshot")
    sn_cols = st.columns(5)
    for col, (icon, label, key) in zip(sn_cols, [
        ("🧤", "GK",       "goalkeepers"),
        ("🛡️", "DEF",      "defenders"),
        ("⚙️", "MID",      "midfielders"),
        ("⚽", "FWD",      "forwards"),
        ("📅", "Avg Age",  "average_age"),
    ]):
        val     = summary.get(key, 0)
        display = f"{float(val):.1f}" if key == "average_age" else str(int(val))
        col.markdown(
            f"<div style='text-align:center'><div style='font-size:1.6rem'>{icon}</div>"
            f"<div style='font-weight:900;font-size:1.2rem'>{display}</div>"
            f"<div style='font-size:.75rem;color:#64748B'>{label}</div></div>",
            unsafe_allow_html=True
        )

featured = get_featured_players(selected_country, captain_name)
if featured:
    st.markdown("#### ⭐ Players to Know")
    p_cols = st.columns(min(len(featured), 5))
    for col, p in zip(p_cols, featured):
        with col:
            st.markdown(
                "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
                "padding:.9rem .7rem;text-align:center;color:white;border:1px solid rgba(148,163,184,.15)'>"
                f"<div style='font-size:.65rem;color:#94A3B8;font-weight:700;text-transform:uppercase'>{p['role']}</div>"
                f"<div style='font-size:1.8rem;font-weight:900;color:#FCD34D'>#{p['shirt_number']}</div>"
                f"<div style='font-size:.88rem;font-weight:800;line-height:1.2;margin:.1rem 0'>{p['name']}</div>"
                f"<div style='font-size:.75rem;color:#94A3B8'>{p['position']}</div>"
                f"<div style='font-size:.72rem;color:#64748B;margin-top:.15rem'>{p['club_short']}</div>"
                f"<div style='font-size:.7rem;color:#475569'>Age {p['age']}</div>"
                "</div>",
                unsafe_allow_html=True
            )

mls_players = get_mls_players(selected_country)
if not mls_players.empty:
    st.markdown("#### 🏟️ MLS & US Connections")
    mls_cols = st.columns(min(len(mls_players), 3))
    for col, (_, p) in zip(mls_cols, mls_players.iterrows()):
        col.markdown(
            "<div style='background:linear-gradient(135deg,#064E3B,#065F46);border-radius:10px;"
            "padding:.65rem .9rem;color:white'>"
            f"<div style='font-size:.95rem;font-weight:800'>#{int(p['shirt_number'])} {p['player_name']}</div>"
            f"<div style='font-size:.78rem;color:#6EE7B7'>{p['position']}</div>"
            f"<div style='font-size:.75rem;color:#A7F3D0'>🏟️ {p['club_short']} · Age {int(p['age'])}</div>"
            "</div>",
            unsafe_allow_html=True
        )

if not roster.empty:
    st.markdown("#### 📋 Full Squad")
    by_pos = get_roster_by_position(selected_country)
    for pos in ['Goalkeeper', 'Defender', 'Midfielder', 'Forward']:
        pos_df = by_pos.get(pos)
        if pos_df is None or pos_df.empty:
            continue
        icon  = pos_icon(pos)
        count = len(pos_df)
        with st.expander(f"{icon} {pos}s ({count})", expanded=False):
            for _, p in pos_df.iterrows():
                st.markdown(
                    f"**#{int(p['shirt_number'])}** &nbsp; {p['player_name']} "
                    f"<span style='color:#64748B;font-size:.88rem'>· {p['club_short']} · Age {int(p['age'])}</span>",
                    unsafe_allow_html=True
                )
