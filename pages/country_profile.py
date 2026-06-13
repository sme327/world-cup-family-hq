import json
import os
import re
import unicodedata
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from services.teams import get_all_teams, get_team_by_name, get_flag
from services.passport import (
    get_stamp, log_discovery, get_country_metadata,
    get_discoveries, get_cheered_for, get_won_with,
    get_picks_per_country, get_points_per_country,
)
from services.matches import get_matches_by_team
from services.images import get_country_image_html, get_country_card_image
from services.roster import (
    get_team_roster, get_team_summary, get_featured_players,
    get_mls_players, get_roster_by_position, pos_icon,
)
from services.time_utils import fmt_date, fmt_match_time

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

_DETAILS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'country_details.json')
try:
    with open(_DETAILS_PATH) as _f:
        _COUNTRY_DETAILS: dict = json.load(_f)
except Exception:
    _COUNTRY_DETAILS = {}

def _details(country: str) -> dict:
    return _COUNTRY_DETAILS.get(country, {})

# ── Known card descriptions ───────────────────────────────────────────────────
_ANIMAL_INFO: dict[str, tuple[str, str]] = {
    "Jaguar":            ("The jaguar is the largest wild cat in the Americas and loves to swim.", "A jaguar's bite is stronger than a lion's — it can crack a turtle's shell!"),
    "Lion":              ("Lions live in family groups called prides. The females do most of the hunting!", "A lion's roar can be heard up to 5 miles away."),
    "Elephant":          ("Elephants are the largest land animals on Earth — and they never forget!", "An elephant uses its trunk as a hand, a nose, and even a snorkel when swimming."),
    "Tiger":             ("Tigers are the biggest wild cats and are expert swimmers.", "No two tigers have the same stripe pattern — like human fingerprints!"),
    "Giant Panda":       ("Giant pandas spend up to 14 hours a day eating bamboo!", "Pandas are born tiny — about the size of a stick of butter — but grow to 200+ lbs."),
    "Kangaroo":          ("Kangaroos can jump 25 feet in one leap and can't walk backwards.", "A baby kangaroo (joey) is about the size of a grape when it's born!"),
    "Polar Bear":        ("Polar bears have black skin under their white fur to absorb heat.", "Polar bears can swim over 60 miles without stopping."),
    "Giraffe":           ("Giraffes are the tallest animals on Earth — up to 18 feet tall!", "A giraffe's tongue is 18 inches long and dark blue to protect it from sunburn."),
    "Flamingo":          ("Flamingos get their pink color from the shrimp and algae they eat!", "Baby flamingos are born white — they turn pink as they eat more shrimp."),
    "Cheetah":           ("Cheetahs are the fastest land animals, reaching 70 mph in seconds.", "Cheetahs can go from 0 to 60 mph in just 3 seconds — faster than most sports cars!"),
    "Rhinoceros":        ("Rhinos have been on Earth for 50 million years, even before humans!", "A rhino's horn is made of the same material as your fingernails — keratin."),
    "Penguin":           ("Penguins are birds that can't fly, but they're amazing swimmers!", "Penguins propose to their mates by giving them a special pebble."),
    "Koala":             ("Koalas sleep up to 22 hours a day because eucalyptus leaves take lots of energy to digest.", "Koalas have fingerprints so similar to humans' that crime scene investigators can get confused!"),
    "Bald Eagle":        ("The bald eagle is the national bird of the USA and has incredible eyesight.", "Bald eagles can spot a fish in water from a mile away in the air!"),
    "Golden Eagle":      ("Golden eagles are among the fastest birds, diving at over 150 mph.", "Golden eagles mate for life and return to the same nest every year, adding to it each time."),
    "Wolf":              ("Wolves communicate with howls that can be heard up to 10 miles away.", "A wolf pack is really a family — the parents lead their children and grandchildren together."),
    "Brown Bear":        ("Brown bears can run 35 mph — faster than the fastest human sprinter.", "Bears can smell food from up to 20 miles away — the best nose of any land mammal."),
    "Dolphin":           ("Dolphins are so smart they can recognize themselves in a mirror!", "Dolphins sleep with one eye open, keeping half their brain awake to watch for danger."),
    "Snow Leopard":      ("Snow leopards can leap up to 50 feet in a single jump!", "Snow leopards can't roar — instead they make a special 'chuffing' noise."),
    "Monarch Butterfly": ("Monarch butterflies migrate 3,000 miles every year between Canada and Mexico.", "Monarchs navigate using the sun — and they can sense the Earth's magnetic field!"),
    "Axolotl":           ("Axolotls can regrow lost limbs, gills, and even parts of their brain!", "Axolotls never fully grow up — they keep their baby features their whole life."),
    "Komodo Dragon":     ("Komodo dragons are the world's largest lizards — up to 10 feet long!", "Their saliva is so powerful it acts like venom."),
    "Camel":             ("Camels store fat — not water — in their humps for energy on long desert journeys.", "A camel can drink 40 gallons of water in just 13 minutes!"),
    "Capybara":          ("Capybaras are the world's largest rodents — basically giant friendly guinea pigs!", "Capybaras are so chill that birds, monkeys, and even cats like to sit on them."),
}

_FOOD_INFO: dict[str, tuple[str, str]] = {
    "Tacos":       ("Tacos are corn or flour tortillas filled with meat, beans, salsa, and toppings.", "There are hundreds of regional taco styles in Mexico — from al pastor to fish tacos!"),
    "Guacamole":   ("Guacamole is made from mashed avocados mixed with lime, onion, and cilantro.", "Avocados are native to Mexico — the Aztecs were making guacamole 500 years ago!"),
    "Tamales":     ("Tamales are corn dough stuffed with meat or cheese, wrapped in corn husks and steamed.", "Making tamales is a family tradition — families gather to make hundreds at holiday time."),
    "Sushi":       ("Sushi combines vinegared rice with fresh seafood, vegetables, or egg.", "The word 'sushi' actually refers to the special rice, not the fish!"),
    "Pizza":       ("Pizza started in Naples, Italy, but is now loved all over the world.", "The world's most expensive pizza takes 72 hours to make and costs thousands of dollars."),
    "Pasta":       ("Italy has over 350 different pasta shapes — each one designed to hold a different sauce!", "Italians eat about 60 pounds of pasta per person every year."),
    "Croissant":   ("Croissants are buttery, flaky pastries that take over two days to make properly.", "The croissant was actually invented in Austria, not France — it was called a Kipferl!"),
    "Baguette":    ("A French baguette must be at least 22 inches long by law!", "Over 30 million baguettes are baked in France every single day."),
    "Schnitzel":   ("Schnitzel is a thin breaded meat cutlet pounded flat and fried until crispy.", "The original Wiener Schnitzel must legally be made from veal in Austria."),
    "Braai":       ("Braai is the South African word for barbecue — it's a huge social tradition.", "In South Africa there's a National Braai Day every September 24th!"),
    "Biltong":     ("Biltong is dried, spiced meat — like beef jerky but even more flavorful.", "South African rugby and cricket fans always bring biltong to matches."),
    "Ramen":       ("Ramen is a Japanese noodle soup that can take up to 18 hours to prepare the broth.", "Japan has over 35,000 ramen restaurants — more than any other country!"),
    "Tempura":     ("Tempura is lightly battered and deep-fried seafood and vegetables — super crispy!", "Tempura was actually introduced to Japan by Portuguese missionaries in the 1500s."),
    "Kimchi":      ("Kimchi is fermented vegetables (usually cabbage) with spicy seasoning.", "The average South Korean eats about 40 pounds of kimchi every year!"),
    "Bibimbap":    ("Bibimbap means 'mixed rice' — it's rice topped with vegetables, egg, and sauce.", "There are said to be over 70 different toppings you can put on bibimbap!"),
    "Poutine":     ("Poutine is french fries topped with cheese curds and gravy — Canada's most famous dish.", "The squeaky sound of fresh cheese curds when you eat them means they're extra fresh!"),
    "Pampushky":   ("Pampushky are soft Ukrainian garlic bread rolls — fluffy and delicious!", "Ukrainians traditionally serve pampushky alongside borscht."),
    "Moussaka":    ("Moussaka is a Greek-style casserole with layers of eggplant, meat, and creamy sauce.", "Every Greek grandmother has their own secret moussaka recipe!"),
    "Mezze":       ("Mezze is a collection of small dishes shared by everyone at the table.", "In the Middle East, a big spread of mezze is a sign of hospitality and friendship."),
    "Hummus":      ("Hummus is a creamy dip made from chickpeas, tahini, lemon, and garlic.", "Lebanon once made the world's largest plate of hummus weighing over 23,000 pounds!"),
    "Falafel":     ("Falafel are crispy fried balls made from ground chickpeas or fava beans.", "Falafel has been eaten in the Middle East for over 1,000 years!"),
    "Barbecue":    ("Brazilian churrasco barbecue involves giant skewers of meat cooked over open flames.", "In southern Brazil, some restaurants keep bringing meat until you flip a card to say stop!"),
    "Stroopwafel": ("Stroopwafels are two thin waffles sandwiched together with caramel syrup.", "Dutch astronaut André Kuipers took stroopwafels to the International Space Station!"),
    "Stamppot":    ("Stamppot is a Dutch comfort food — mashed potatoes mixed with vegetables.", "Every Dutch family has their own special stamppot recipe passed down through generations."),
}

_LANDMARK_INFO: dict[str, tuple[str, str]] = {
    "Chichen Itza":       ("Chichen Itza is a spectacular Mayan pyramid — one of the New Seven Wonders of the World.", "Twice a year, the sun creates a shadow that looks exactly like a giant snake crawling down!"),
    "Eiffel Tower":       ("The Eiffel Tower was built as a temporary structure in 1889 but was never taken down.", "It grows about 6 inches taller in summer because the metal expands in heat!"),
    "Colosseum":          ("The Roman Colosseum could hold 80,000 spectators — more than most modern NFL stadiums!", "It had 80 entrances so it could be filled or emptied in just 15 minutes."),
    "Machu Picchu":       ("Machu Picchu was built by the Inca people high in the Andes mountains around 1450 AD.", "No one knows exactly why it was built — it might have been a royal vacation home!"),
    "Great Wall of China":("The Great Wall of China stretches over 13,000 miles — you could walk it for years.", "It was built over 2,000 years and is still not entirely explored!"),
    "Taj Mahal":          ("The Taj Mahal was built by an emperor as a monument of love for his wife.", "It took 22 years and 20,000 workers to build — using no heavy machinery!"),
    "Pyramids of Giza":   ("The Great Pyramid of Giza is the oldest of the Seven Wonders of the Ancient World still standing!", "Its stones are so precisely cut that you can't fit a piece of paper between them."),
    "Stonehenge":         ("No one knows exactly why Stonehenge was built — it's still a mystery!", "The huge stones were transported over 150 miles — with no wheels or cranes!"),
    "Niagara Falls":      ("Niagara Falls moves about 1 million gallons of water per second — absolutely thundering!", "The sound can be heard from 100 miles away on a quiet day."),
    "Amazon Rainforest":  ("The Amazon is the world's largest rainforest and produces 20% of Earth's oxygen.", "The Amazon River freshens the Atlantic Ocean 100 miles out to sea."),
    "Ayers Rock":         ("Uluru changes color from red to orange to purple as the sun rises and sets.", "It is sacred to the Aboriginal Anangu people who have lived near it for 30,000 years."),
    "Sydney Opera House": ("The Sydney Opera House's roof looks like a series of giant shells or sails.", "The building has 1 million tiles on the roof and took 14 years to build."),
    "Great Barrier Reef": ("The Great Barrier Reef is so big it can be seen from space!", "Over 1,500 species of fish live there."),
    "Acropolis":          ("The Acropolis in Athens is over 2,500 years old!", "The Parthenon has no perfectly straight lines — the ancient Greeks curved everything slightly to make it look perfect from below."),
    "Sagrada Familia":    ("This amazing cathedral in Barcelona has been under construction for over 140 years!", "The architect Antoni Gaudí is buried inside the church he designed."),
}


_GOVT_TYPE: dict[str, str] = {
    "Algeria":                "Republic",
    "Argentina":              "Federal Republic",
    "Australia":              "Constitutional Monarchy",
    "Austria":                "Federal Republic",
    "Belgium":                "Constitutional Monarchy",
    "Bosnia and Herzegovina": "Republic",
    "Brazil":                 "Federal Republic",
    "Canada":                 "Constitutional Monarchy",
    "Cape Verde":             "Republic",
    "Colombia":               "Republic",
    "Croatia":                "Republic",
    "Curaçao":                "Autonomous Territory",
    "Czechia":                "Republic",
    "DR Congo":               "Republic",
    "Ecuador":                "Republic",
    "Egypt":                  "Republic",
    "England":                "Constitutional Monarchy",
    "France":                 "Republic",
    "Germany":                "Federal Republic",
    "Ghana":                  "Republic",
    "Haiti":                  "Republic",
    "Iran":                   "Islamic Republic",
    "Iraq":                   "Federal Republic",
    "Ivory Coast":            "Republic",
    "Japan":                  "Constitutional Monarchy",
    "Jordan":                 "Kingdom",
    "Mexico":                 "Federal Republic",
    "Morocco":                "Kingdom",
    "Netherlands":            "Constitutional Monarchy",
    "New Zealand":            "Constitutional Monarchy",
    "Norway":                 "Constitutional Monarchy",
    "Panama":                 "Republic",
    "Paraguay":               "Republic",
    "Portugal":               "Republic",
    "Qatar":                  "Emirate",
    "Saudi Arabia":           "Kingdom",
    "Scotland":               "Constitutional Monarchy",
    "Senegal":                "Republic",
    "South Africa":           "Republic",
    "South Korea":            "Republic",
    "Spain":                  "Constitutional Monarchy",
    "Sweden":                 "Constitutional Monarchy",
    "Switzerland":            "Federal Republic",
    "Tunisia":                "Republic",
    "Türkiye":                "Republic",
    "USA":                    "Federal Republic",
    "Uruguay":                "Republic",
    "Uzbekistan":             "Republic",
}


def _card_info(item_type: str, label: str, country: str) -> tuple[str, str]:
    clean = _strip_emoji(label).strip()
    if item_type == "animal":
        for key, val in _ANIMAL_INFO.items():
            if key.lower() in clean.lower() or clean.lower() in key.lower():
                return val
        return (f"The {clean} is one of the most amazing animals found in {country}.",
                f"{country} has incredible wildlife found nowhere else in the world!")
    if item_type == "food":
        for key, val in _FOOD_INFO.items():
            if key.lower() in clean.lower() or clean.lower() in key.lower():
                return val
        return (f"{clean} is a delicious dish from {country} loved by people around the world.",
                f"Food in {country} is famous for its amazing flavors and traditions!")
    if item_type == "landmark":
        for key, val in _LANDMARK_INFO.items():
            if key.lower() in clean.lower() or clean.lower() in key.lower():
                return val
        return (f"{clean} is one of the most famous places to visit in {country}.",
                f"Millions of people travel to {country} every year to see incredible places like this!")
    return (f"This is one of the coolest things that makes {country} special!",
            f"Learning about {country} is like going on a mini adventure from your couch.")


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

_EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002702-\U000027B0\U0000FE00-\U0000FE0F☀-⛿⭐⭕▪-◾☔♈-♓]+",
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

def _cheer_blurb(label: str, country: str) -> str:
    lo = label.lower()
    if any(w in lo for w in ["food", "taco", "sushi", "pizza", "cuisine", "eat"]):
        return f"The food in {country} is absolutely delicious — kids who try it always want more!"
    if any(w in lo for w in ["pyramid", "temple", "castle", "ancient", "ruins", "wonder"]):
        return f"Imagine standing next to something built thousands of years ago! {country} has real ancient wonders."
    if any(w in lo for w in ["cat", "jaguar", "lion", "tiger", "leopard", "puma"]):
        return f"Big cats are the most powerful hunters on Earth — and {country} has amazing ones!"
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
    if any(w in lo for w in ["game", "nintendo", "anime", "manga", "pokemon"]):
        return f"Some of your favorite games and cartoons come from {country}. It's the coolest!"
    if any(w in lo for w in ["animal", "wildlife", "safari", "nature", "jungle"]):
        return f"The wildlife in {country} is like stepping into a nature documentary!"
    if any(w in lo for w in ["underdog", "surprise", "qualify", "first time", "debut"]):
        return f"{country} worked so hard to get here — everyone loves a great underdog story!"
    return f"This is one of the coolest things that makes {country} truly special!"


@st.cache_data(ttl=86400)
def _country_map(iso3: str):
    fig = go.Figure(go.Choropleth(
        locations=[iso3], z=[1], locationmode='ISO-3',
        colorscale=[[0, '#2563EB'], [1, '#2563EB']],
        showscale=False,
        marker_line_color='white', marker_line_width=0.8,
    ))
    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, coastlinecolor='#94A3B8',
                 showland=True, landcolor='#E2E8F0', showocean=True, oceancolor='#DBEAFE',
                 projection_type='natural earth'),
        margin=dict(l=0, r=0, t=0, b=0), height=320,
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def _stat_card(icon: str, label: str, value: str) -> str:
    return (
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
        "padding:.8rem;text-align:center;color:white;border:1px solid rgba(148,163,184,.15)'>"
        f"<div style='font-size:1.5rem'>{icon}</div>"
        f"<div style='font-size:.72rem;color:#94A3B8;margin:.12rem 0;font-weight:700;"
        f"text-transform:uppercase;letter-spacing:.04em'>{label}</div>"
        f"<div style='font-size:.9rem;font-weight:800;color:#F1F5F9;line-height:1.2'>{value}</div>"
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


# ── Formation SVG ─────────────────────────────────────────────────────────────
def _formation_svg(roster_df: pd.DataFrame, captain_name: str = "") -> str:
    """SVG soccer formation view — 4-3-3, attack at top (TV broadcast style)."""
    if roster_df is None or roster_df.empty:
        return ""

    W, H = 420, 560
    ROW_Y = {"fwd": 105, "mid": 225, "def": 360, "gk": 465}

    gks  = roster_df[roster_df["position"] == "Goalkeeper"].sort_values("shirt_number").to_dict("records")
    defs = roster_df[roster_df["position"] == "Defender"].sort_values("shirt_number").to_dict("records")
    mids = roster_df[roster_df["position"] == "Midfielder"].sort_values("shirt_number").to_dict("records")
    fwds = roster_df[roster_df["position"] == "Forward"].sort_values("shirt_number").to_dict("records")

    cap_num = None
    if captain_name:
        cap_last = captain_name.split()[-1].lower() if captain_name.split() else ""
        for row in roster_df.to_dict("records"):
            if cap_last and cap_last in str(row["player_name"]).lower():
                cap_num = int(row["shirt_number"])
                break

    def _cap_first(group, n):
        if not group:
            return []
        if cap_num is not None:
            cap_in = [r for r in group if int(r["shirt_number"]) == cap_num]
            rest   = [r for r in group if int(r["shirt_number"]) != cap_num]
            return (cap_in + rest)[:n]
        return group[:n]

    gk_xi  = _cap_first(gks, 1)
    def_xi = _cap_first(defs, 4)
    mid_xi = _cap_first(mids, 3)
    fwd_xi = _cap_first(fwds, 3)

    used  = {int(r["shirt_number"]) for r in gk_xi + def_xi + mid_xi + fwd_xi}
    spare = [r for r in sorted(roster_df.to_dict("records"), key=lambda r: int(r["shirt_number"]))
             if int(r["shirt_number"]) not in used]

    def _fill(grp, n):
        while len(grp) < n and spare:
            grp.append(spare.pop(0))
        return grp

    gk_xi  = _fill(gk_xi, 1)
    def_xi = _fill(def_xi, 4)
    mid_xi = _fill(mid_xi, 3)
    fwd_xi = _fill(fwd_xi, 3)

    def _xs(n):
        if n == 0: return []
        if n == 1: return [W // 2]
        m = 48
        return [round(m + i * (W - 2 * m) / (n - 1)) for i in range(n)]

    def _last(name):
        parts = str(name).split()
        ln = parts[-1] if parts else str(name)
        return (ln[:9] + ".") if len(ln) > 9 else ln

    p = []
    lc, lw = "rgba(255,255,255,0.38)", "1.5"

    p.append(
        "<defs><linearGradient id='fg2' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0%' stop-color='#155e1a'/>"
        "<stop offset='100%' stop-color='#1a7a20'/>"
        "</linearGradient></defs>"
    )
    p.append(f"<rect width='{W}' height='{H}' fill='url(#fg2)' rx='12'/>")
    p.append(f"<rect x='14' y='10' width='{W-28}' height='{H-20}' fill='none' stroke='{lc}' stroke-width='{lw}'/>")
    p.append(f"<line x1='14' y1='{H//2}' x2='{W-14}' y2='{H//2}' stroke='{lc}' stroke-width='{lw}'/>")
    p.append(f"<circle cx='{W//2}' cy='{H//2}' r='52' fill='none' stroke='{lc}' stroke-width='{lw}'/>")
    p.append(f"<circle cx='{W//2}' cy='{H//2}' r='4' fill='{lc}'/>")
    pbw, pbh = 190, 90
    pbx = (W - pbw) // 2
    p.append(f"<rect x='{pbx}' y='10' width='{pbw}' height='{pbh}' fill='none' stroke='{lc}' stroke-width='{lw}'/>")
    p.append(f"<rect x='{pbx}' y='{H-10-pbh}' width='{pbw}' height='{pbh}' fill='none' stroke='{lc}' stroke-width='{lw}'/>")

    form = f"{len(def_xi)}-{len(mid_xi)}-{len(fwd_xi)}"
    p.append(
        f"<text x='{W//2}' y='32' text-anchor='middle' font-size='11' font-weight='700' "
        f"fill='rgba(255,255,255,0.42)' font-family='system-ui,sans-serif' letter-spacing='1'>"
        f"FORMATION {form}</text>"
    )

    # Jersey silhouette: smooth armpits + round neckhole cutout via evenodd
    JERSEY = (
        "M -15,-15 "
        "L -22,-8 Q -20,-6 -17,-5 "           # left sleeve, smooth armpit curve
        "L -17,17 L 17,17 "                    # body bottom
        "L 17,-5 Q 20,-6 22,-8 "              # right side, smooth armpit curve
        "L 15,-15 C 8,-21 -8,-21 -15,-15 Z "  # right shoulder + collar arch
        "M -5,-17 A 5,3 0 0 1 5,-17 A 5,3 0 0 1 -5,-17 Z"  # neckhole (evenodd)
    )

    def _draw_row(players, y, _tag_unused):
        xs = _xs(len(players))
        for i, pl in enumerate(players):
            px = xs[i]
            snum = str(int(pl["shirt_number"]))
            lname = _last(pl["player_name"])
            is_cap = cap_num is not None and int(pl["shirt_number"]) == cap_num
            stroke = "#FCD34D" if is_cap else "rgba(255,255,255,0.55)"
            sw = "2.5" if is_cap else "1.5"
            p.append(f"<g transform='translate({px},{y})'>")
            p.append(
                f"<path d='{JERSEY}' fill='#1D4ED8' stroke='{stroke}' stroke-width='{sw}' "
                f"stroke-linejoin='round' fill-rule='evenodd' opacity='0.93'/>"
            )
            # Visible collar ring
            p.append("<ellipse cx='0' cy='-17' rx='5' ry='3' fill='none' stroke='rgba(255,255,255,0.35)' stroke-width='1'/>")
            p.append(f"<text y='5' text-anchor='middle' font-size='12' font-weight='900' fill='white' font-family='system-ui,sans-serif'>{snum}</text>")
            if is_cap:
                p.append("<circle cx='15' cy='-14' r='8' fill='#FCD34D'/>")
                p.append("<text x='15' y='-10' text-anchor='middle' font-size='8.5' font-weight='900' fill='#1E293B' font-family='system-ui,sans-serif'>C</text>")
            p.append("</g>")
            p.append(f"<text x='{px}' y='{y+28}' text-anchor='middle' font-size='9.5' font-weight='700' fill='rgba(255,255,255,0.83)' font-family='system-ui,sans-serif'>{lname}</text>")

    _draw_row(fwd_xi, ROW_Y["fwd"], "FWD")
    _draw_row(mid_xi, ROW_Y["mid"], "MID")
    _draw_row(def_xi, ROW_Y["def"], "DEF")
    _draw_row(gk_xi,  ROW_Y["gk"],  "GK")

    svg = f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:440px;display:block;margin:0 auto;border-radius:12px">{"".join(p)}</svg>'
    return (
        "<div style='background:#0F172A;border-radius:14px;padding:.6rem;"
        "border:1px solid rgba(148,163,184,.1)'>"
        + svg +
        "<div style='font-size:.63rem;color:#475569;text-align:center;margin-top:.3rem'>"
        "Best-guess lineup based on squad position counts &nbsp;·&nbsp; Gold C = captain &nbsp;·&nbsp; Not confirmed by team"
        "</div></div>"
    )


# ── Passport widget ───────────────────────────────────────────────────────────
def _passport_widget_html(
    country: str,
    stamp: dict,
    disc_df: pd.DataFrame,
    cheered: list,
    won: list,
    picks_per: dict,
    points_per: dict,
) -> str:
    if not disc_df.empty and "country_name" in disc_df.columns:
        row = disc_df[disc_df["country_name"] == country]
        is_disc = not row.empty
        visit_count = int(row["visit_count"].iloc[0]) if is_disc else 0
    else:
        is_disc, visit_count = False, 0

    is_cheered = country in cheered
    is_won     = country in won
    pick_count = picks_per.get(country, 0)
    pts        = points_per.get(country, 0.0)
    total_disc = len(disc_df) if not disc_df.empty else 0

    if is_won:
        badge_emoji, badge_label, badge_color = "🏆", "WON WITH", "#FCD34D"
        pts_str = str(int(pts)) if pts == int(pts) else f"{pts:.1f}"
        detail  = f"Earned {pts_str} pts · {pick_count} pick{'s' if pick_count != 1 else ''}"
    elif is_cheered:
        badge_emoji, badge_label, badge_color = "⚽", "CHEERING FOR", "#4ADE80"
        detail = f"{pick_count} pick{'s' if pick_count != 1 else ''} placed"
    elif is_disc and visit_count == 1:
        badge_emoji, badge_label, badge_color = "✨", "JUST DISCOVERED", "#A78BFA"
        detail = "First visit — passport stamp earned!"
    elif is_disc:
        badge_emoji, badge_label, badge_color = "🌱", "DISCOVERED", "#60A5FA"
        detail = f"Visited {visit_count} time{'s' if visit_count != 1 else ''}"
    else:
        badge_emoji, badge_label, badge_color = "✨", "JUST DISCOVERED", "#A78BFA"
        detail = "First visit — passport stamp earned!"

    return (
        f"<div style='background:linear-gradient(135deg,#0F172A,#1E293B);border-radius:14px;"
        f"padding:.6rem 1rem;border:1px solid rgba(148,163,184,.1);"
        f"display:flex;align-items:center;gap:.85rem;margin-bottom:.9rem'>"
        f"<div style='font-size:2.4rem;line-height:1;flex-shrink:0'>{stamp.get('stamp_emoji','🌍')}</div>"
        f"<div style='flex:1;min-width:0'>"
        f"<div style='display:flex;align-items:center;gap:.45rem;flex-wrap:wrap;margin-bottom:.15rem'>"
        f"<span style='font-size:.68rem;font-weight:800;color:{badge_color};"
        f"border:1px solid {badge_color}55;border-radius:20px;padding:.1rem .5rem;"
        f"background:{badge_color}18;letter-spacing:.06em'>{badge_emoji} {badge_label}</span>"
        f"<span style='font-size:.71rem;color:#64748B'>{detail}</span>"
        f"</div>"
        f"<div style='font-size:.68rem;color:#475569'>"
        f"Your passport: {total_disc}/48 countries explored</div>"
        f"</div>"
        f"</div>"
    )


# ── Position group cards HTML ─────────────────────────────────────────────────
def _position_group_html(players: list, icon: str, pos_label: str) -> str:
    if not players:
        return ""
    cards = ""
    for pl in players:
        snum = str(int(pl.get("shirt_number", 0)))
        name = str(pl.get("player_name", ""))
        club = str(pl.get("club_short", pl.get("club", "")))
        age_v = pl.get("age", 0)
        try:
            age = int(float(age_v)) if age_v else 0
        except (ValueError, TypeError):
            age = 0
        age_str = f" · Age {age}" if age else ""
        cards += (
            f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
            f"border-radius:9px;padding:.42rem .55rem;"
            f"border:1px solid rgba(148,163,184,.1)'>"
            f"<div style='font-size:.88rem;font-weight:900;color:#FCD34D;line-height:1'>#{snum}</div>"
            f"<div style='font-size:.76rem;font-weight:800;color:#F1F5F9;line-height:1.25;margin:.04rem 0;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{name}</div>"
            f"<div style='font-size:.64rem;color:#64748B;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>"
            f"{club}{age_str}</div>"
            "</div>"
        )
    return (
        f"<div style='margin:.5rem 0 .9rem'>"
        f"<div style='font-size:.74rem;font-weight:800;color:#64748B;text-transform:uppercase;"
        f"letter-spacing:.06em;margin-bottom:.32rem'>{icon} {pos_label}s ({len(players)})</div>"
        f"<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:.28rem'>"
        f"{cards}</div></div>"
    )


def _player_role_blurb(role: str, name: str, age: int) -> str:
    r = role.lower()
    first = name.split()[0] if name else name
    if "captain" in r:
        return "Team leader — wears the armband and speaks for the squad"
    if "young" in r:
        return f"At {age}, one of the youngest in the squad — a rising star"
    if "old" in r or "veteran" in r or "experi" in r:
        return f"At {age}, a seasoned veteran — composure under pressure"
    if "mls" in r or "us " in r:
        return "Plays American soccer — you might catch them on TV this season!"
    return "A key starter and one to watch when they play"


# ── Sidebar ───────────────────────────────────────────────────────────────────
teams_df = get_all_teams()
_nav_country = st.session_state.pop("_nav_country", None)

with st.sidebar:
    st.markdown("### 🌍 Explore Countries")
    all_countries = sorted(teams_df["name"].tolist())
    default_idx   = all_countries.index(_nav_country) if _nav_country and _nav_country in all_countries else 0
    selected_country = st.selectbox("Country", all_countries, index=default_idx)

active_user_id = st.session_state.get("active_user_id", 1)

# ── Log discovery (idempotent) ────────────────────────────────────────────────
log_discovery(active_user_id, selected_country)

# ── Load all data ─────────────────────────────────────────────────────────────
team    = get_team_by_name(selected_country)
stamp   = get_stamp(selected_country)
flag    = get_flag(selected_country)
cslug   = _country_slug(selected_country)
details = _details(selected_country)

if team is None:
    st.error(f"Country data not found: {selected_country}")
    st.stop()

iso2 = _safe(team.get("country_code"), "")
iso3 = _ISO3.get(iso2, "")
fun  = _safe(team.get("fun_fact"), "")

# Passport data for current user
disc_df    = get_discoveries(active_user_id)
cheered    = get_cheered_for(active_user_id)
won        = get_won_with(active_user_id)
picks_per  = get_picks_per_country(active_user_id)
points_per = get_points_per_country(active_user_id)

# Roster data
roster       = get_team_roster(selected_country)
summary      = get_team_summary(selected_country)
captain_name = _safe(team.get("captain"), "")
by_pos       = get_roster_by_position(selected_country)
featured     = get_featured_players(selected_country, captain_name)
mls_players  = get_mls_players(selected_country)

# ── Section 1: Hero Image ─────────────────────────────────────────────────────
hero_html = get_country_image_html(selected_country, height="250px")
has_hero  = hero_html is not None
if has_hero:
    st.markdown(hero_html, unsafe_allow_html=True)

# ── Section 2: Country Banner ─────────────────────────────────────────────────
flag_size     = "4rem" if has_hero else "6.5rem"       # ~60% larger than original
header_pad    = "0.65rem 1.2rem 0.8rem" if has_hero else "1.4rem"
border_radius = "0 0 16px 16px" if has_hero else "16px"

st.markdown(
    f"<div style='background:linear-gradient(135deg,#1E3A5F,#2563EB);"
    f"padding:{header_pad};border-radius:{border_radius};text-align:center;color:white;margin-bottom:.6rem'>"
    f"<div style='font-size:{flag_size};line-height:1;margin-bottom:.1rem'>{flag}</div>"
    f"<div style='font-size:1.9rem;font-weight:900;line-height:1.1'>{selected_country}</div>"
    f"<div style='font-size:1.1rem;color:#FCD34D;margin:.2rem 0'>"
    f"{stamp['stamp_emoji']} {stamp['stamp_label']}</div>"
    f"<div style='color:#CBD5E1;font-size:.88rem'>"
    f"{stamp['continent']} · Group {_safe(team.get('group_letter'))} · FIFA #{_safe(team.get('fifa_ranking'))}"
    f"</div></div>",
    unsafe_allow_html=True
)

if not has_hero:
    st.markdown(
        "<div style='background:linear-gradient(135deg,#1E293B,#0F172A);border-radius:12px;"
        "height:80px;display:flex;align-items:center;justify-content:center;"
        "color:rgba(255,255,255,.3);font-size:.85rem;margin-bottom:.8rem;"
        "border:1px dashed rgba(148,163,184,.3)'>"
        "<div style='text-align:center'><div style='font-size:1.8rem'>📷</div>"
        "<div>Country photo coming soon</div></div></div>",
        unsafe_allow_html=True
    )

# ── Section 3: Passport Widget ────────────────────────────────────────────────
st.markdown(
    _passport_widget_html(selected_country, stamp, disc_df, cheered, won, picks_per, points_per),
    unsafe_allow_html=True
)

# ── Section 4: Meet This Country in 60 Seconds ────────────────────────────────
animals   = _parse_pipe(team.get("animals"))
foods     = _parse_pipe(team.get("foods"))
landmarks = _parse_pipe(team.get("landmarks"))
reasons   = _parse_pipe(team.get("cheer_reasons"))
flag_fact = stamp.get("flag_fact", "")

tiles: list[dict] = []
if fun:
    tiles.append({"emoji": "💡", "label": "Did You Know?", "text": fun[:110]})
if animals:
    al, ae = _split_label_emoji(animals[0], "🐾")
    ad, _  = _card_info("animal", al, selected_country)
    tiles.append({"emoji": ae, "label": al, "text": ad[:110]})
if foods:
    fl2, fe = _split_label_emoji(foods[0], "🍴")
    fd, _   = _card_info("food", fl2, selected_country)
    tiles.append({"emoji": fe, "label": fl2, "text": fd[:110]})
if landmarks:
    ll = _strip_emoji(landmarks[0]).strip()
    ld, _  = _card_info("landmark", ll, selected_country)
    tiles.append({"emoji": "🏛️", "label": ll[:22], "text": ld[:110]})
if reasons:
    rl, re2 = _split_label_emoji(reasons[0], "⭐")
    tiles.append({"emoji": re2, "label": rl, "text": _cheer_blurb(rl, selected_country)[:110]})
elif flag_fact:
    tiles.append({"emoji": "🚩", "label": "Flag Story", "text": flag_fact[:110]})

if tiles:
    st.markdown("### ⚡ Meet This Country in 60 Seconds")
    n = min(len(tiles), 5)
    t_cols = st.columns(n)
    for col, tile in zip(t_cols, tiles[:n]):
        with col:
            st.markdown(
                "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
                "padding:.75rem .6rem;text-align:center;border:1px solid rgba(148,163,184,.1);min-height:130px'>"
                f"<div style='font-size:1.9rem;line-height:1;margin-bottom:.3rem'>{tile['emoji']}</div>"
                f"<div style='font-size:.78rem;font-weight:800;color:#F1F5F9;margin-bottom:.25rem;line-height:1.2'>{tile['label']}</div>"
                f"<div style='font-size:.69rem;color:#94A3B8;line-height:1.4'>{tile['text']}</div>"
                "</div>",
                unsafe_allow_html=True
            )

# ── Section 5: Country Facts ──────────────────────────────────────────────────
st.markdown("### 🌍 Country Facts")
row1 = st.columns(3)
row2 = st.columns(3)
facts = [
    ("🏙️", "Capital",       _safe(team.get("capital"))),
    ("👥", "Population",    _safe(team.get("population"))),
    ("🗣️", "Languages",     _safe(team.get("languages"))),
    ("💰", "Currency",      _safe(team.get("currency"))),
    ("🌍", "Continent",     stamp["continent"]),
    ("🏛️", "Government",   _GOVT_TYPE.get(selected_country, "—")),
]
for col, (icon, label, val) in zip(list(row1) + list(row2), facts):
    col.markdown(_stat_card(icon, label, val), unsafe_allow_html=True)

# Flag fact callout
if flag_fact:
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#1E293B,#0F172A);border-radius:12px;"
        f"padding:.65rem 1rem;margin:.6rem 0;border-left:3px solid #FCD34D'>"
        f"<div style='font-size:.85rem;color:#CBD5E1'><b>🚩 Flag Story:</b> {flag_fact}</div></div>",
        unsafe_allow_html=True
    )
elif fun:
    st.markdown(
        f"<div style='background:linear-gradient(135deg,#FEF3C7,#FDE68A);border-radius:12px;"
        f"padding:.65rem 1rem;margin:.6rem 0;border-left:4px solid #FCD34D'>"
        f"<div style='font-size:.88rem;color:#78350F'><b>💡 Did you know?</b> {fun}</div></div>",
        unsafe_allow_html=True
    )

# ── Section 6: Where Is This Country? ────────────────────────────────────────
st.markdown("### 🗺️ Where Is This Country?")
if iso3:
    try:
        st.plotly_chart(_country_map(iso3), use_container_width=True, config={"staticPlot": True})
    except Exception:
        st.info(f"📍 {selected_country} is located in {stamp['continent']}.")
else:
    st.info(f"📍 {selected_country} is located in {stamp['continent']}.")

neighbors = details.get("neighbors", [])
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
        f"<div style='font-size:.76rem;color:#64748B;font-weight:700;margin-bottom:.3rem'>🌎 Neighboring Countries</div>"
        f"<div>{neighbor_pills}</div></div>",
        unsafe_allow_html=True
    )
else:
    st.markdown(
        "<div style='font-size:.82rem;color:#64748B;margin-top:.3rem'>"
        "🌊 Island nation — surrounded by ocean on all sides</div>",
        unsafe_allow_html=True
    )

# ── Section 7: Compare To Seattle ────────────────────────────────────────────
st.markdown("### 🏡 Compare To Seattle")

dist_miles  = details.get("distance_miles", 0)
tz_offset   = details.get("timezone_offset", 0)
pop_m       = _parse_pop_m(team.get("population", ""))
seattle_pop = 4.0

compare_cards = []
if dist_miles and dist_miles > 50:
    compare_cards.append(("✈️", "Distance from Seattle",
                          f"{dist_miles:,} miles",
                          f"That's about {dist_miles // 500} long road trips away!"))
elif dist_miles and dist_miles <= 50:
    compare_cards.append(("🏠", "Distance from Seattle", "Right next door!", "You could almost drive there in a day."))

if tz_offset == 0:
    tz_label, tz_note = "Same time!", "When it's 3 PM here, it's 3 PM there too."
elif tz_offset > 0:
    hour = 9 + int(tz_offset)
    ampm = "AM" if hour < 12 else "PM"
    tz_label = f"+{tz_offset}h ahead"
    tz_note  = f"When it's 9 AM in Seattle, it's {hour}{ampm} there."
else:
    tz_label = f"{tz_offset}h behind"
    tz_note  = f"When it's 9 AM in Seattle, it's {9 + int(tz_offset)} AM there."
compare_cards.append(("🕐", "Time Zone", tz_label, tz_note))

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

lang = _safe(team.get("languages"), "")
if lang and lang != "—":
    if "English" in lang:
        compare_cards.append(("🗣️", "Language", lang, "They speak English too — just like Seattle!"))
    else:
        first_lang = lang.split(",")[0].strip()
        compare_cards.append(("🗣️", "Language", first_lang, f"People say hello in {first_lang} — how cool is that!"))

n_cmp = min(len(compare_cards), 4)
if n_cmp > 0:
    cmp_cols = st.columns(n_cmp)
    for col, (icon, label, val, note) in zip(cmp_cols, compare_cards[:n_cmp]):
        col.markdown(
            "<div style='background:linear-gradient(160deg,#0F172A,#1E293B);"
            "border:1px solid rgba(148,163,184,.15);border-radius:12px;"
            "padding:.75rem;text-align:center'>"
            f"<div style='font-size:1.4rem'>{icon}</div>"
            f"<div style='font-size:.72rem;color:#94A3B8;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:.04em;margin:.1rem 0'>{label}</div>"
            f"<div style='font-size:.95rem;font-weight:900;color:#F1F5F9;line-height:1.2'>{val}</div>"
            f"<div style='font-size:.7rem;color:#64748B;margin-top:.2rem;line-height:1.3'>{note}</div>"
            "</div>",
            unsafe_allow_html=True
        )

# ── Section 8: Animals & Nature ───────────────────────────────────────────────
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

# ── Section 9: Famous Foods ───────────────────────────────────────────────────
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

# ── Section 10: Famous Landmarks ─────────────────────────────────────────────
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

# ── Section 11: Why Kids Might Cheer ─────────────────────────────────────────
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

# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("## ⚽ Soccer Team")

nickname = details.get("nickname", "")
if nickname and nickname not in ("—", ""):
    st.markdown(
        f"<div style='color:#94A3B8;font-size:.88rem;margin:-.4rem 0 .8rem'>"
        f"Also known as: <b style='color:#FCD34D'>{nickname}</b></div>",
        unsafe_allow_html=True
    )
famous_player = details.get("famous_player", _safe(team.get("captain"), "—"))
home_stadium  = details.get("home_stadium", "—")

# ── Team Snapshot ─────────────────────────────────────────────────────────────
st.markdown("#### 📊 Team Snapshot")
_avg_age = f"{float(summary.get('average_age', 0)):.1f}" if summary else "—"
ss_cols = st.columns(4)
for col, (icon, label, val) in zip(ss_cols, [
    ("🏅", "FIFA Ranking",   f"#{_safe(team.get('fifa_ranking'))}"),
    ("🔢", "WC Appearances", _safe(team.get("wc_appearances"), "—")),
    ("🏆", "Best WC Finish", _safe(team.get("best_finish"))),
    ("🌐", "Confederation",  _safe(team.get("confederation"))),
]):
    col.markdown(_stat_card(icon, label, val), unsafe_allow_html=True)

ss2_cols = st.columns(4)
for col, (icon, label, val) in zip(ss2_cols, [
    ("🏟️", "Home Stadium", home_stadium),
    ("👔", "Coach",         _safe(team.get("coach"))),
    ("🎽", "Captain",       captain_name),
    ("📅", "Avg Age",       _avg_age),
]):
    col.markdown(_stat_card(icon, label, val), unsafe_allow_html=True)

# ── Formation View ────────────────────────────────────────────────────────────
if not roster.empty:
    st.markdown("#### 🟩 Predicted Starting XI")
    _, _fc, _ = st.columns([1, 2, 1])
    with _fc:
        st.markdown(_formation_svg(roster, captain_name), unsafe_allow_html=True)

# ── Players To Know ───────────────────────────────────────────────────────────
if featured:
    st.markdown("#### ⭐ Players To Know")
    n_feat = min(len(featured), 5)
    p_cols = st.columns(n_feat)
    for col, pl in zip(p_cols, featured[:n_feat]):
        blurb = _player_role_blurb(pl["role"], pl["name"], pl.get("age", 0))
        with col:
            st.markdown(
                "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
                "padding:.85rem .7rem;text-align:center;color:white;border:1px solid rgba(148,163,184,.15)'>"
                f"<div style='font-size:.62rem;color:#94A3B8;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:.04em'>{pl['role']}</div>"
                f"<div style='font-size:1.8rem;font-weight:900;color:#FCD34D;line-height:1.2'>#{pl['shirt_number']}</div>"
                f"<div style='font-size:.86rem;font-weight:800;line-height:1.25;margin:.1rem 0'>{pl['name']}</div>"
                f"<div style='font-size:.73rem;color:#94A3B8'>{pl['position']}</div>"
                f"<div style='font-size:.69rem;color:#64748B;margin:.1rem 0'>{pl['club_short']} · Age {pl['age']}</div>"
                f"<div style='font-size:.66rem;color:#475569;margin-top:.3rem;line-height:1.35;"
                f"border-top:1px solid rgba(148,163,184,.1);padding-top:.25rem'>{blurb}</div>"
                "</div>",
                unsafe_allow_html=True
            )

# ── MLS & US Connections ──────────────────────────────────────────────────────
if not mls_players.empty:
    st.markdown("#### 🏟️ MLS & US Connections")
    mls_cols = st.columns(min(len(mls_players), 3))
    for col, (_, mp) in zip(mls_cols, mls_players.iterrows()):
        col.markdown(
            "<div style='background:linear-gradient(135deg,#064E3B,#065F46);border-radius:10px;"
            "padding:.65rem .9rem;color:white'>"
            f"<div style='font-size:.95rem;font-weight:800'>#{int(mp['shirt_number'])} {mp['player_name']}</div>"
            f"<div style='font-size:.78rem;color:#6EE7B7'>{mp['position']}</div>"
            f"<div style='font-size:.75rem;color:#A7F3D0'>🏟️ {mp['club_short']} · Age {int(mp['age'])}</div>"
            "</div>",
            unsafe_allow_html=True
        )

# ── Group Stage Matches ───────────────────────────────────────────────────────
matches = get_matches_by_team(selected_country)
if not matches.empty:
    st.markdown("#### 📅 Group Stage Matches")
    for _, m in matches.iterrows():
        opp      = m["away_team"] if m["home_team"] == selected_country else m["home_team"]
        opp_flag = get_flag(opp)
        mid      = int(m["id"])
        time_str = fmt_match_time(m["match_date"], m["kickoff_time_et"])

        if m["status"] == "completed":
            hs, as_ = int(m["home_score"]), int(m["away_score"])
            score   = f"**{hs}–{as_}**"
            label   = f"{flag} {selected_country} vs {opp_flag} {opp} · {score}"
        else:
            label = f"{flag} {selected_country} vs {opp_flag} **{opp}** · {time_str}"

        col_info, col_btn = st.columns([5, 2])
        col_info.markdown(label)
        if col_btn.button("🏟️ Matchup", key=f"match_link_{mid}"):
            st.session_state["_nav_match_id"] = mid
            st.switch_page("pages/matchup.py")

# ── Full Squad (position group cards) ────────────────────────────────────────
if not roster.empty:
    st.markdown("#### 📋 Full Squad")
    for _pos in ["Goalkeeper", "Defender", "Midfielder", "Forward"]:
        _pos_df = by_pos.get(_pos)
        if _pos_df is None or _pos_df.empty:
            continue
        _icon = pos_icon(_pos)
        _players = _pos_df.to_dict("records")
        st.markdown(_position_group_html(_players, _icon, _pos), unsafe_allow_html=True)
