import streamlit as st
import plotly.graph_objects as go
from services.matches import get_all_matches
from services.teams import get_flag
from services.time_utils import fmt_date, fmt_match_time
from services.images import get_city_image_html

# ── City coordinates (lat, lon) ───────────────────────────────────────────────
_CITY_COORDS: dict[str, tuple[float, float]] = {
    "Seattle":         (47.61, -122.33),
    "East Rutherford": (40.81,  -74.07),
    "Arlington":       (32.74,  -97.11),
    "Los Angeles":     (34.05, -118.24),
    "Santa Clara":     (37.35, -121.96),
    "Philadelphia":    (39.95,  -75.17),
    "Miami Gardens":   (25.94,  -80.25),
    "Kansas City":     (39.10,  -94.58),
    "Foxborough":      (42.09,  -71.26),
    "Atlanta":         (33.75,  -84.39),
    "Houston":         (29.76,  -95.37),
    "Mexico City":     (19.43,  -99.13),
    "Guadalajara":     (20.66, -103.35),
    "Monterrey":       (25.69, -100.32),
    "Vancouver":       (49.28, -123.12),
    "Toronto":         (43.65,  -79.38),
}


@st.cache_data
def _city_map(city_name: str):
    coords = _CITY_COORDS.get(city_name)
    if not coords:
        return None
    lat, lon = coords
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(
        lat=[lat], lon=[lon],
        mode='markers+text',
        marker=dict(size=14, color='#EF4444', symbol='circle',
                    line=dict(color='white', width=2)),
        text=[city_name],
        textposition='top center',
        textfont=dict(size=11, color='#1E293B'),
        showlegend=False,
    ))
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,  coastlinecolor='#94A3B8',
            showland=True,        landcolor='#E2E8F0',
            showocean=True,       oceancolor='#DBEAFE',
            showlakes=True,       lakecolor='#DBEAFE',
            showcountries=True,   countrycolor='#CBD5E1',
            showsubunits=True,    subunitcolor='#E2E8F0',
            projection_type='natural earth',
            # Fixed viewport covering all 16 host cities
            lataxis_range=[13, 57],
            lonaxis_range=[-136, -62],
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=260,
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig

# ── City data ─────────────────────────────────────────────────────────────────
CITY_DATA = {
    "Seattle": {
        "country": "USA", "stadium": "Lumen Field", "flag": "🇺🇸",
        "population": "750K city · 4M metro", "home_city": True,
        "hero_emoji": "🌊🏔️🌲",
        "hero_image_path": "assets/city_hero/seattle.jpg",
        "wc_history": "Seattle has never previously hosted a World Cup. 2026 will be its first — and Lumen Field is ready.",
        "fun_facts": [
            "Seattle is the birthplace of Starbucks, Amazon, Microsoft, and Boeing — four of the world's most iconic companies.",
            "The Space Needle was built for the 1962 World's Fair and still defines the skyline at 605 feet tall.",
            "Seattle gets more sunny days per year than Miami — despite its rainy reputation!",
        ],
        "why_kids_cards": [
            {"emoji": "🏠", "title": "Your Home City", "blurb": "Lumen Field is YOUR World Cup venue — cheer for your city on the biggest stage!"},
            {"emoji": "🐋", "title": "Orca Whales", "blurb": "Puget Sound is home to some of the world's most famous orca whale pods."},
            {"emoji": "🐟", "title": "Flying Fish", "blurb": "At Pike Place Market, fishmongers throw huge salmon through the air — and the crowds go wild."},
            {"emoji": "🚀", "title": "Space Needle", "blurb": "Ride to the top for a 360° view of Seattle, the mountains, and Elliott Bay."},
            {"emoji": "⚽", "title": "Sounders Soccer", "blurb": "Lumen Field hosts Seattle Sounders FC — one of America's most passionate soccer crowds."},
        ],
        "landmarks": [("🏪", "Pike Place Market"), ("🗼", "Space Needle"), ("🏔️", "Mount Rainier"), ("🎨", "Chihuly Garden")],
        "foods": [("🦀", "Dungeness Crab"), ("🐟", "Pike Place Salmon"), ("🌭", "Seattle Dog"), ("🍵", "Teriyaki")],
        "wildlife": [("🐋", "Orca Whales"), ("🦅", "Bald Eagles"), ("🐻", "Black Bears"), ("🐟", "Salmon Runs")],
    },
    "East Rutherford": {
        "country": "USA", "stadium": "MetLife Stadium", "flag": "🇺🇸",
        "population": "52K city · 9M metro (NYC)", "home_city": False,
        "hero_emoji": "🗽🌆🏟️",
        "hero_image_path": "assets/city_hero/east_rutherford.jpg",
        "wc_history": "MetLife Stadium hosted the 1994 World Cup. It will host the 2026 Final on July 19 — one of the greatest venues in sports history.",
        "fun_facts": [
            "The World Cup FINAL will be played here on July 19, 2026!",
            "New York City has 8.3 million people — the largest in the USA.",
            "Times Square gets 50 million visitors every year.",
        ],
        "why_kids_cards": [
            {"emoji": "🏆", "title": "World Cup Final", "blurb": "The biggest game in world soccer will be played right here on July 19!"},
            {"emoji": "🗽", "title": "Statue of Liberty", "blurb": "A gift from France in 1886, Lady Liberty has welcomed millions to America."},
            {"emoji": "🍕", "title": "NYC Pizza", "blurb": "New Yorkers say their pizza is the best in the world — try a slice and decide."},
            {"emoji": "🎭", "title": "Broadway", "blurb": "The most famous theater street on Earth lights up New York every night."},
        ],
        "landmarks": [("🗽", "Statue of Liberty"), ("🌳", "Central Park"), ("🏢", "Empire State Bldg"), ("🌉", "Brooklyn Bridge")],
        "foods": [("🍕", "New York Pizza"), ("🥯", "Bagels with Lox"), ("🌭", "NYC Street Dogs"), ("🍰", "Cheesecake")],
        "wildlife": [("🦅", "Peregrine Falcons"), ("🦭", "Harbor Seals"), ("🦆", "Central Park Ducks"), ("🐟", "Hudson River Fish")],
    },
    "Arlington": {
        "country": "USA", "stadium": "AT&T Stadium", "flag": "🇺🇸",
        "population": "400K city · 7M DFW metro", "home_city": False,
        "hero_emoji": "🤠🔥🏈",
        "hero_image_path": "assets/city_hero/arlington.jpg",
        "wc_history": "AT&T Stadium hosted matches in the 1994 World Cup at the Cotton Bowl in Dallas. 2026 brings the World Cup back to the Metroplex.",
        "fun_facts": [
            "AT&T Stadium has the world's largest HD video screen — and the roof can open!",
            "Texas is the second-largest US state with its own iconic lone star flag.",
            "Texas barbecue is a slow-smoked art form — brisket is king.",
        ],
        "why_kids_cards": [
            {"emoji": "🏈", "title": "Cowboys Stadium", "blurb": "AT&T Stadium is the most high-tech NFL stadium ever built — with a screen the size of a city block."},
            {"emoji": "🔥", "title": "Texas BBQ", "blurb": "Texas slow-smoked brisket is legendary — some say it's the best food in America."},
            {"emoji": "🦔", "title": "Armadillos", "blurb": "These armored little animals are everywhere in Texas and only live in the Americas."},
            {"emoji": "🎢", "title": "Six Flags", "blurb": "Six Flags Over Texas theme park is just minutes away from the stadium."},
        ],
        "landmarks": [("🏟️", "AT&T Stadium"), ("🏛️", "Sixth Floor Museum"), ("🐂", "Fort Worth Stockyards"), ("🔬", "Perot Museum")],
        "foods": [("🥩", "BBQ Brisket"), ("🌮", "Breakfast Tacos"), ("🍦", "Blue Bell Ice Cream"), ("🍗", "Chicken Fried Steak")],
        "wildlife": [("🐦", "Roadrunners"), ("🦔", "Armadillos"), ("🦌", "White-tailed Deer"), ("🦎", "Horned Lizards")],
    },
    "Los Angeles": {
        "country": "USA", "stadium": "SoFi Stadium", "flag": "🇺🇸",
        "population": "4M city · 13M metro", "home_city": False,
        "hero_emoji": "🎬☀️🏄",
        "hero_image_path": "assets/city_hero/los_angeles.jpg",
        "wc_history": "LA hosted the 1994 World Cup including the Final. SoFi Stadium — one of the most expensive ever built at $5.5B — brings the World Cup back.",
        "fun_facts": [
            "SoFi Stadium cost $5.5 billion to build — one of the most expensive stadiums ever.",
            "Hollywood produces more movies than anywhere else in the world.",
            "LA has the largest population of any city on the US West Coast.",
        ],
        "why_kids_cards": [
            {"emoji": "🎬", "title": "Hollywood", "blurb": "The movies and shows you love are made right here in LA — you might see a star!"},
            {"emoji": "🛹", "title": "Venice Beach", "blurb": "The world's most famous boardwalk has skateboarders, street performers, and ocean views."},
            {"emoji": "🎢", "title": "Universal Studios", "blurb": "Theme park rides based on your favorite movies — including Harry Potter and Jurassic Park."},
            {"emoji": "🏄", "title": "Surfing", "blurb": "LA's beaches are famous for their surf culture — the waves are always calling."},
        ],
        "landmarks": [("🎬", "Hollywood Sign"), ("🔭", "Griffith Observatory"), ("🎡", "Santa Monica Pier"), ("🏛️", "Getty Center")],
        "foods": [("🍔", "In-N-Out Burger"), ("🥩", "Korean BBQ"), ("🌮", "Birria Tacos"), ("🫙", "Açaí Bowls")],
        "wildlife": [("🦭", "California Sea Lions"), ("🦋", "Monarch Butterflies"), ("🦅", "Ospreys"), ("🐬", "Dolphins")],
    },
    "Santa Clara": {
        "country": "USA", "stadium": "Levi's Stadium", "flag": "🇺🇸",
        "population": "130K city · 7M Bay Area", "home_city": False,
        "hero_emoji": "🌉💻🌊",
        "hero_image_path": "assets/city_hero/santa_clara.jpg",
        "wc_history": "The Bay Area hosted 1994 World Cup matches at Stanford Stadium. Levi's Stadium in Silicon Valley brings the World Cup back to California.",
        "fun_facts": [
            "Silicon Valley is home to Apple, Google, Meta, and thousands of tech companies!",
            "The Golden Gate Bridge is one of the most photographed structures on Earth.",
            "San Francisco was built on 43 hills.",
        ],
        "why_kids_cards": [
            {"emoji": "💻", "title": "Silicon Valley", "blurb": "The companies that made your phone, apps, and games all started within miles of this stadium."},
            {"emoji": "🌉", "title": "Golden Gate Bridge", "blurb": "One of the world's most iconic bridges connects San Francisco to Marin County."},
            {"emoji": "🦦", "title": "Sea Otters", "blurb": "Monterey Bay is home to adorable sea otters that float on their backs holding hands."},
            {"emoji": "⛓️", "title": "Alcatraz Island", "blurb": "A famous prison island in the San Francisco Bay — now a bird sanctuary and tourist site."},
        ],
        "landmarks": [("🌉", "Golden Gate Bridge"), ("⛓️", "Alcatraz Island"), ("🐟", "Fisherman's Wharf"), ("🏚️", "Winchester Mystery House")],
        "foods": [("🍞", "Sourdough Bread"), ("🦀", "Crab Cioppino"), ("🌯", "Mission Burrito"), ("🍫", "Ghirardelli Chocolate")],
        "wildlife": [("🦦", "Sea Otters"), ("🐋", "Gray Whales"), ("🦅", "Golden Eagles"), ("🦁", "Mountain Lions")],
    },
    "Philadelphia": {
        "country": "USA", "stadium": "Lincoln Financial Field", "flag": "🇺🇸",
        "population": "1.5M city", "home_city": False,
        "hero_emoji": "🔔🦅🥩",
        "hero_image_path": "assets/city_hero/philadelphia.jpg",
        "wc_history": "Philadelphia hosted 1994 World Cup matches. The city that gave birth to American democracy hosts the World Cup again in 2026.",
        "fun_facts": [
            "The Declaration of Independence was signed here in 1776!",
            "The Liberty Bell's famous crack — nobody knows exactly when it happened.",
            "Philadelphia Zoo is the oldest zoo in the United States.",
        ],
        "why_kids_cards": [
            {"emoji": "🇺🇸", "title": "Birthplace of America", "blurb": "The Declaration of Independence was signed here — America was born in Philadelphia!"},
            {"emoji": "🔔", "title": "Liberty Bell", "blurb": "One of America's most iconic symbols — with a mysterious crack that happened centuries ago."},
            {"emoji": "🥊", "title": "Rocky Balboa", "blurb": "Run up the famous museum steps where Rocky trained — the whole city cheers you on."},
            {"emoji": "🦁", "title": "Philly Zoo", "blurb": "America's first zoo — full of animals from around the world."},
        ],
        "landmarks": [("🔔", "Liberty Bell"), ("🏛️", "Independence Hall"), ("🥊", "Rocky Steps"), ("🦁", "Philadelphia Zoo")],
        "foods": [("🥩", "Philly Cheesesteak"), ("🥨", "Soft Pretzels"), ("🧊", "Water Ice"), ("🥓", "Scrapple")],
        "wildlife": [("🦊", "Red Foxes"), ("🦅", "Bald Eagles"), ("🦉", "Great Horned Owls"), ("🦌", "White-tailed Deer")],
    },
    "Miami Gardens": {
        "country": "USA", "stadium": "Hard Rock Stadium", "flag": "🇺🇸",
        "population": "115K city · 6M Miami metro", "home_city": False,
        "hero_emoji": "🌴🐊🌊",
        "hero_image_path": "assets/city_hero/miami.jpg",
        "wc_history": "Miami hosted 1994 World Cup matches. Hard Rock Stadium brings the World Cup back to South Florida.",
        "fun_facts": [
            "Lionel Messi plays for Inter Miami — the most famous soccer player in the world is right here!",
            "Miami is the only continental US city founded by a woman — Julia Tuttle.",
            "The Everglades — a unique subtropical wilderness — is just one hour away.",
        ],
        "why_kids_cards": [
            {"emoji": "⭐", "title": "Lionel Messi", "blurb": "The world's greatest soccer player plays for Inter Miami — just down the road from Hard Rock Stadium!"},
            {"emoji": "🐊", "title": "Everglades Alligators", "blurb": "Real wild alligators live just an hour away in the world's only subtropical wilderness."},
            {"emoji": "🏖️", "title": "South Beach", "blurb": "The most famous beach in the USA, with Art Deco buildings painted in pastel colors."},
            {"emoji": "🥧", "title": "Key Lime Pie", "blurb": "Florida's official pie — tart, sweet, and served everywhere in South Florida."},
        ],
        "landmarks": [("🌿", "Everglades National Park"), ("🏛️", "Art Deco District"), ("🎨", "Wynwood Walls"), ("🏛️", "Vizcaya Museum")],
        "foods": [("🥪", "Cuban Sandwich"), ("🥧", "Key Lime Pie"), ("🍲", "Ceviche"), ("☕", "Cafecito")],
        "wildlife": [("🐊", "American Alligators"), ("🐄", "Manatees"), ("🐆", "Florida Panthers"), ("🦩", "Roseate Spoonbills")],
    },
    "Kansas City": {
        "country": "USA", "stadium": "Arrowhead Stadium", "flag": "🇺🇸",
        "population": "500K city · 2M metro", "home_city": False,
        "hero_emoji": "🔥🍖⛲",
        "hero_image_path": "assets/city_hero/kansas_city.jpg",
        "wc_history": "Kansas City hosted 1994 World Cup matches at Arrowhead. The loudest stadium in the world returns to World Cup action.",
        "fun_facts": [
            "Arrowhead Stadium holds the Guinness World Record for loudest outdoor stadium crowd noise!",
            "Kansas City spans two states — Missouri AND Kansas.",
            "Kansas City has more fountains than any city in the world except Rome!",
        ],
        "why_kids_cards": [
            {"emoji": "📢", "title": "World's Loudest Stadium", "blurb": "Arrowhead holds the Guinness record for loudest crowd noise ever recorded outdoors!"},
            {"emoji": "🔥", "title": "Kansas City BBQ", "blurb": "KC slow-smoked BBQ is a religion here — burnt ends, ribs, and brisket done perfectly."},
            {"emoji": "⛲", "title": "City of Fountains", "blurb": "Kansas City has more fountains than anywhere except Rome — they're everywhere!"},
            {"emoji": "🏈", "title": "Chiefs Kingdom", "blurb": "Home of the Super Bowl champion Kansas City Chiefs — one of football's greatest teams."},
        ],
        "landmarks": [("🏛️", "WWI Museum"), ("🛍️", "Country Club Plaza"), ("🎨", "Nelson-Atkins Museum"), ("🚂", "Union Station")],
        "foods": [("🔥", "KC BBQ"), ("🥩", "Arthur Bryant's Ribs"), ("🌭", "Burnt Ends"), ("🧁", "Runza")],
        "wildlife": [("🦌", "White-tailed Deer"), ("🦃", "Wild Turkey"), ("🦋", "Monarch Butterflies"), ("🐦", "Greater Prairie-Chicken")],
    },
    "Foxborough": {
        "country": "USA", "stadium": "Gillette Stadium", "flag": "🇺🇸",
        "population": "18K city · 4.9M Boston metro", "home_city": False,
        "hero_emoji": "⚓🦞🏛️",
        "hero_image_path": "assets/city_hero/foxborough.jpg",
        "wc_history": "The Boston area hosted 1994 World Cup matches at Foxboro Stadium. Gillette Stadium carries on that legacy in 2026.",
        "fun_facts": [
            "Gillette Stadium is just 30 minutes from Boston, one of America's oldest cities.",
            "The Boston Tea Party of 1773 helped spark the American Revolution.",
            "Harvard and MIT — two of the world's top universities — are in nearby Cambridge.",
        ],
        "why_kids_cards": [
            {"emoji": "🏛️", "title": "American Revolution", "blurb": "Boston is where America's fight for independence began — history is everywhere here."},
            {"emoji": "🐋", "title": "Whale Watching", "blurb": "Humpback whales feed off the Boston coast — whale watching boats go out daily."},
            {"emoji": "🦞", "title": "Lobster Rolls", "blurb": "Fresh New England lobster stuffed into a buttered roll — one of the best foods in America."},
            {"emoji": "🤖", "title": "MIT Robots", "blurb": "The world's most advanced robots are built just minutes away at MIT in Cambridge."},
        ],
        "landmarks": [("🛤️", "Freedom Trail"), ("🏛️", "Paul Revere's House"), ("🎓", "Harvard University"), ("⛪", "Old North Church")],
        "foods": [("🍲", "Clam Chowder"), ("🦞", "Lobster Roll"), ("🍰", "Boston Cream Pie"), ("🍮", "Cannoli")],
        "wildlife": [("🐋", "Humpback Whales"), ("🦭", "Harbor Seals"), ("🐦", "Atlantic Puffins"), ("🦅", "Ospreys")],
    },
    "Atlanta": {
        "country": "USA", "stadium": "Mercedes-Benz Stadium", "flag": "🇺🇸",
        "population": "500K city · 6M metro", "home_city": False,
        "hero_emoji": "🍑🦈🥤",
        "hero_image_path": "assets/city_hero/atlanta.jpg",
        "wc_history": "Atlanta hosted the 1996 Olympics and has a rich sporting history. 2026 will be its first World Cup.",
        "fun_facts": [
            "Atlanta is the birthplace of Coca-Cola and Martin Luther King Jr.!",
            "The Georgia Aquarium is the largest in the Western Hemisphere.",
            "Hartsfield-Jackson Atlanta Airport is the busiest in the entire world.",
        ],
        "why_kids_cards": [
            {"emoji": "🦈", "title": "Biggest Aquarium", "blurb": "The Georgia Aquarium is the largest in the Western Hemisphere — whale sharks swim inside!"},
            {"emoji": "🥤", "title": "Coca-Cola Birthplace", "blurb": "The world's most famous drink was invented in Atlanta — tour the World of Coca-Cola museum."},
            {"emoji": "🍑", "title": "Georgia Peaches", "blurb": "Georgia peaches are legendary — the sweetest fruit in the American South."},
            {"emoji": "⚽", "title": "Atlanta United", "blurb": "Mercedes-Benz Stadium is home to Atlanta United FC — one of MLS's biggest clubs."},
        ],
        "landmarks": [("🏛️", "MLK Historic Site"), ("🥤", "World of Coca-Cola"), ("🦈", "Georgia Aquarium"), ("🏅", "Centennial Olympic Park")],
        "foods": [("🍑", "Peach Cobbler"), ("🍗", "Fried Chicken"), ("🥜", "Boiled Peanuts"), ("🧇", "Waffle House")],
        "wildlife": [("🦌", "White-tailed Deer"), ("🦃", "Wild Turkeys"), ("🐻", "Black Bears"), ("🐊", "Alligators")],
    },
    "Houston": {
        "country": "USA", "stadium": "NRG Stadium", "flag": "🇺🇸",
        "population": "2.3M city · 7M metro", "home_city": False,
        "hero_emoji": "🚀🌮🦐",
        "hero_image_path": "assets/city_hero/houston.jpg",
        "wc_history": "Houston hosted 1994 World Cup matches at the Astrodome. NRG Stadium brings the World Cup back to Space City.",
        "fun_facts": [
            "NASA's Mission Control for all human spaceflight is right here in Houston!",
            "Houston is one of the most diverse cities in the USA.",
            "Houston has an underground tunnel system connecting downtown buildings!",
        ],
        "why_kids_cards": [
            {"emoji": "🚀", "title": "NASA Space Center", "blurb": "Mission Control — where astronauts are guided to space — is right here in Houston."},
            {"emoji": "🌮", "title": "Tex-Mex Food", "blurb": "Houston's Tex-Mex cuisine is some of the best in the world — tacos, enchiladas, and more."},
            {"emoji": "🕳️", "title": "Underground Tunnels", "blurb": "Houston has 7 miles of underground tunnels connecting downtown buildings — hidden city!"},
            {"emoji": "⚽", "title": "Houston Dynamo", "blurb": "NRG Stadium is home to the Houston Dynamo — Panama's MLS star plays right here!"},
        ],
        "landmarks": [("🚀", "NASA Space Center"), ("🦕", "Natural Science Museum"), ("🐘", "Houston Zoo"), ("⚔️", "San Jacinto Monument")],
        "foods": [("🌮", "Tex-Mex"), ("🦐", "Gulf Shrimp"), ("🍩", "Kolaches"), ("🍜", "Vietnamese Pho")],
        "wildlife": [("🐦", "Whooping Cranes"), ("🦩", "Roseate Spoonbills"), ("🐊", "Alligators"), ("🦅", "Bald Eagles")],
    },
    "Mexico City": {
        "country": "Mexico", "stadium": "Estadio Azteca", "flag": "🇲🇽",
        "population": "9M city · 22M metro", "home_city": False,
        "hero_emoji": "🏛️🦅🌮",
        "hero_image_path": "assets/city_hero/mexico_city.jpg",
        "wc_history": "Estadio Azteca hosted the 1970 and 1986 World Cup Finals — the only stadium in history to do so. 2026 is its third World Cup.",
        "fun_facts": [
            "The Azteca has hosted TWO World Cup finals — 1970 and 1986. No other stadium matches this.",
            "Mexico City sits at 2,240 meters altitude — players literally get more tired here!",
            "Mexico City is built on a dried lake bed — it sinks slightly every year!",
        ],
        "why_kids_cards": [
            {"emoji": "🏆", "title": "Two World Cup Finals", "blurb": "The Azteca is the only stadium to host TWO World Cup finals — this is sacred soccer ground."},
            {"emoji": "🏛️", "title": "Ancient Pyramids", "blurb": "The Teotihuacan Pyramids — older than the Aztecs — are just 30 miles from the stadium."},
            {"emoji": "🦎", "title": "The Axolotl", "blurb": "Mexico's famous walking fish — a salamander that never fully grows up — lives in local lakes."},
            {"emoji": "🌮", "title": "Street Food Heaven", "blurb": "Mexico City has the best tacos, tamales, and churros you'll ever taste — from street carts!"},
        ],
        "landmarks": [("🏟️", "Estadio Azteca"), ("🏛️", "Teotihuacan Pyramids"), ("🏰", "Chapultepec Castle"), ("⛪", "Zócalo Plaza")],
        "foods": [("🌮", "Tacos al Pastor"), ("🫔", "Tamales"), ("🍩", "Churros"), ("🌶️", "Chiles en Nogada")],
        "wildlife": [("🦎", "Axolotl"), ("🦋", "Monarch Butterflies"), ("🐺", "Mexican Wolf"), ("🦅", "Golden Eagle")],
    },
    "Guadalajara": {
        "country": "Mexico", "stadium": "Estadio Akron", "flag": "🇲🇽",
        "population": "1.5M city · 5M metro", "home_city": False,
        "hero_emoji": "🎺🥃💎",
        "hero_image_path": "assets/city_hero/guadalajara.jpg",
        "wc_history": "Guadalajara hosted the 1970 World Cup group stage at Estadio Jalisco. Estadio Akron — home of Club Chivas — hosts 2026.",
        "fun_facts": [
            "Mariachi music was born in Guadalajara — it's the most famous Mexican musical tradition.",
            "Tequila is made just 35 miles away in a town literally called Tequila!",
            "Guadalajara has a famous opal gemstone market.",
        ],
        "why_kids_cards": [
            {"emoji": "🎺", "title": "Birthplace of Mariachi", "blurb": "The most famous Mexican music style — mariachi — was born right here in Guadalajara."},
            {"emoji": "🥃", "title": "Tequila Country", "blurb": "The town of Tequila is just 35 miles away — that's where the famous drink is made!"},
            {"emoji": "⚽", "title": "Club Chivas", "blurb": "Estadio Akron is home to Club Chivas — one of Mexico's most beloved soccer clubs."},
            {"emoji": "🎨", "title": "Crafts Market", "blurb": "Tlaquepaque is a village of artists and craft makers — perfect for exploring."},
        ],
        "landmarks": [("⛪", "Guadalajara Cathedral"), ("🎨", "Tlaquepaque Arts"), ("🌵", "Tequila Town"), ("🏔️", "Barranca de Oblatos")],
        "foods": [("🥪", "Torta Ahogada"), ("🍲", "Birria Stew"), ("🌽", "Tejuino"), ("🍮", "Jericalla Custard")],
        "wildlife": [("🦋", "Monarch Butterflies"), ("🦌", "White-tailed Deer"), ("🦝", "Coatis"), ("🐦", "Guadalajara Birds")],
    },
    "Monterrey": {
        "country": "Mexico", "stadium": "Estadio BBVA", "flag": "🇲🇽",
        "population": "1.1M city · 5M metro", "home_city": False,
        "hero_emoji": "🏔️🐐🦅",
        "hero_image_path": "assets/city_hero/monterrey.jpg",
        "wc_history": "Monterrey hosted the 1970 and 1986 World Cups. Estadio BBVA — one of Latin America's most beautiful stadiums — hosts 2026.",
        "fun_facts": [
            "Monterrey is surrounded by the Sierra Madre Oriental mountains — perfect for hiking!",
            "Estadio BBVA is considered one of the most beautiful stadiums in Latin America.",
            "Monterrey is just 140 miles from the Texas border.",
        ],
        "why_kids_cards": [
            {"emoji": "🏔️", "title": "Mountain City", "blurb": "The Sierra Madre mountains surround Monterrey — you can see peaks from inside the stadium!"},
            {"emoji": "🗿", "title": "Underground Caves", "blurb": "The García Caves nearby are among the largest caves in the world — full of stalactites."},
            {"emoji": "🐐", "title": "Cabrito BBQ", "blurb": "Monterrey is famous for slow-roasted goat — a regional delicacy you won't find elsewhere."},
            {"emoji": "🏟️", "title": "Beautiful Stadium", "blurb": "Estadio BBVA is called one of the most beautiful stadiums in all of Latin America."},
        ],
        "landmarks": [("🏟️", "Estadio BBVA"), ("🏭", "Parque Fundidora"), ("🏔️", "Cerro de la Silla"), ("🗿", "García Caves")],
        "foods": [("🐐", "Cabrito (Roast Goat)"), ("🥩", "Machacado"), ("🍞", "Pan de Pulque"), ("🍬", "Glorias Candy")],
        "wildlife": [("🐻", "Black Bears"), ("🦅", "Mexican Golden Eagle"), ("🐆", "Jaguarundi"), ("🐟", "Catfish")],
    },
    "Vancouver": {
        "country": "Canada", "stadium": "BC Place", "flag": "🇨🇦",
        "population": "675K city · 2.5M metro", "home_city": False,
        "hero_emoji": "🏔️🐋🍁",
        "hero_image_path": "assets/city_hero/vancouver.jpg",
        "wc_history": "Vancouver has hosted the Olympics (2010 Winter Games). 2026 will be the city's first FIFA World Cup.",
        "fun_facts": [
            "Vancouver consistently ranks as one of the most beautiful and livable cities in the world!",
            "You can ski in the morning and kayak in the ocean in the afternoon — on the same day!",
            "Vancouver Whitecaps FC play at BC Place in MLS!",
        ],
        "why_kids_cards": [
            {"emoji": "🏔️", "title": "Mountains & Ocean", "blurb": "Vancouver has both ocean beaches AND ski mountains — sometimes visible at the same time."},
            {"emoji": "🐋", "title": "Orca Whales", "blurb": "Orca whale pods swim through Vancouver's nearby waters — whale watching is incredible here."},
            {"emoji": "😱", "title": "Suspension Bridge", "blurb": "The Capilano Suspension Bridge sways 70 meters above a river gorge — totally thrilling!"},
            {"emoji": "🚲", "title": "Stanley Park Seawall", "blurb": "Bike or walk the 9km seawall around Stanley Park with ocean and mountain views the whole way."},
        ],
        "landmarks": [("🌲", "Stanley Park"), ("😱", "Capilano Bridge"), ("🏪", "Granville Island"), ("⛷️", "Grouse Mountain")],
        "foods": [("🐟", "Fresh Salmon"), ("🍱", "Japanese Sushi"), ("🥟", "Dim Sum"), ("☕", "Tim Hortons"), ("🍫", "Nanaimo Bars")],
        "wildlife": [("🐋", "Orca Whales"), ("🐻", "Grizzly Bears"), ("🦅", "Bald Eagles"), ("🦦", "Sea Otters")],
    },
    "Toronto": {
        "country": "Canada", "stadium": "BMO Field", "flag": "🇨🇦",
        "population": "2.7M city · 6M metro", "home_city": False,
        "hero_emoji": "🗼💦🏒",
        "hero_image_path": "assets/city_hero/toronto.jpg",
        "wc_history": "Toronto has never previously hosted a World Cup. 2026 will be its historic first — at BMO Field, home of Toronto FC.",
        "fun_facts": [
            "Toronto is one of the most multicultural cities on Earth — over 200 languages are spoken!",
            "The CN Tower was the world's tallest freestanding structure for 34 years.",
            "Niagara Falls is just 80 miles away — one of the world's great natural wonders.",
        ],
        "why_kids_cards": [
            {"emoji": "😱", "title": "CN Tower Glass Floor", "blurb": "The CN Tower has a glass floor where you can look straight down 342 meters — terrifying!"},
            {"emoji": "💦", "title": "Niagara Falls", "blurb": "One of the world's great natural wonders is just 80 miles from Toronto — a must-visit."},
            {"emoji": "🏒", "title": "Hockey Hall of Fame", "blurb": "Canada's most beloved sport has its greatest museum right in downtown Toronto."},
            {"emoji": "🍟", "title": "Poutine!", "blurb": "Fries + gravy + cheese curds = Canada's most famous dish. Try it and you'll understand."},
        ],
        "landmarks": [("🗼", "CN Tower"), ("🏛️", "Royal Ontario Museum"), ("💦", "Niagara Falls Nearby"), ("🏒", "Hockey Hall of Fame")],
        "foods": [("🍟", "Poutine"), ("🥓", "Peameal Bacon"), ("🧈", "Butter Tarts"), ("🥘", "Jamaican Patties")],
        "wildlife": [("🦅", "Peregrine Falcons"), ("🦋", "Monarch Butterflies"), ("🐢", "Snapping Turtles"), ("🐺", "Coyotes")],
    },
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _stat_card(icon, label, value):
    return (
        "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
        "padding:.75rem .6rem;text-align:center;color:white;border:1px solid rgba(148,163,184,.15)'>"
        f"<div style='font-size:1.4rem'>{icon}</div>"
        f"<div style='font-size:.7rem;color:#94A3B8;font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin:.1rem 0'>{label}</div>"
        f"<div style='font-size:.85rem;font-weight:800;color:#F1F5F9;line-height:1.25'>{value}</div>"
        "</div>"
    )


def _img_placeholder_card(emoji, label):
    """Visual card with emoji-as-image placeholder, ready for real imagery."""
    return (
        "<div style='background:white;border:1px solid #E2E8F0;border-radius:12px;overflow:hidden'>"
        f"<div style='background:linear-gradient(135deg,#1E293B,#334155);height:80px;"
        f"display:flex;align-items:center;justify-content:center;font-size:2.5rem'>{emoji}</div>"
        f"<div style='padding:.4rem .5rem;font-size:.82rem;font-weight:700;color:#0F172A'>{label}</div>"
        "</div>"
    )


def _why_kids_card(emoji, title, blurb):
    return (
        "<div style='background:white;border:1.5px solid #E2E8F0;border-radius:14px;padding:.9rem .8rem;"
        "box-shadow:0 1px 4px rgba(0,0,0,.06)'>"
        f"<div style='font-size:2.5rem;margin-bottom:.3rem'>{emoji}</div>"
        f"<div style='font-size:.9rem;font-weight:800;color:#0F172A;margin-bottom:.2rem'>{title}</div>"
        f"<div style='font-size:.78rem;color:#64748B;line-height:1.4'>{blurb}</div>"
        "</div>"
    )


# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## 🏙️ Host City Explorer")
st.caption("2026 FIFA World Cup — 16 Host Cities across USA, Canada & Mexico")

# ── Sidebar ───────────────────────────────────────────────────────────────────
all_matches = get_all_matches()
cities      = sorted(all_matches['city'].unique().tolist())

_nav_city = st.session_state.pop("_nav_city", None)

with st.sidebar:
    st.markdown("### 🏙️ Select a City")
    default_city_idx = (
        cities.index(_nav_city) if _nav_city and _nav_city in cities
        else cities.index("Seattle") if "Seattle" in cities
        else 0
    )
    selected_city = st.selectbox("City", cities, index=default_city_idx)

city         = CITY_DATA.get(selected_city)
city_matches = all_matches[all_matches['city'] == selected_city].sort_values(['match_date', 'kickoff_time_et'])
host_country = city_matches['host_country'].iloc[0] if not city_matches.empty else "—"
stadium      = city_matches['venue'].iloc[0] if not city_matches.empty else "—"
match_count  = len(city_matches)
is_home      = city and city.get('home_city', False)
city_flag    = city['flag'] if city else "📍"

# ── 1. Hero Images — landmark + stadium side by side ─────────────────────────
hero_emoji = city.get('hero_emoji', '🌍') if city else '🌍'
home_label = " 🏠 YOUR HOME CITY!" if is_home else ""

landmark_img = get_city_image_html(selected_city, image_type='landmark', height='220px',
                                   border_radius='16px 0 0 0')
stadium_img  = get_city_image_html(selected_city, image_type='stadium',  height='220px',
                                   border_radius='0 16px 0 0')

if landmark_img and stadium_img:
    st.markdown(
        f"<div style='display:flex;gap:3px;border-radius:16px 16px 0 0;overflow:hidden'>"
        f"<div style='flex:1.1;position:relative'>{landmark_img}"
        f"<div style='position:absolute;bottom:0;left:0;right:0;"
        f"background:linear-gradient(transparent,rgba(0,0,0,.55));padding:.3rem .5rem'>"
        f"<span style='font-size:.68rem;color:rgba(255,255,255,.8);font-weight:700'>📍 City</span>"
        f"</div></div>"
        f"<div style='flex:.9;position:relative'>{stadium_img}"
        f"<div style='position:absolute;bottom:0;left:0;right:0;"
        f"background:linear-gradient(transparent,rgba(0,0,0,.55));padding:.3rem .5rem'>"
        f"<span style='font-size:.68rem;color:rgba(255,255,255,.8);font-weight:700'>🏟️ Stadium</span>"
        f"</div></div>"
        f"</div>",
        unsafe_allow_html=True
    )
elif landmark_img:
    st.markdown(landmark_img.replace("border-radius:'16px 0 0 0'", "border-radius:16px 16px 0 0"),
                unsafe_allow_html=True)
elif stadium_img:
    st.markdown(stadium_img.replace("border-radius:'0 16px 0 0'", "border-radius:16px 16px 0 0"),
                unsafe_allow_html=True)
else:
    st.markdown(
        f"<div style='background:linear-gradient(160deg,#0F172A,#1E293B);border-radius:16px 16px 0 0;"
        f"height:220px;display:flex;flex-direction:column;align-items:center;justify-content:center;"
        f"border:1px solid rgba(148,163,184,.1)'>"
        f"<div style='font-size:4rem;letter-spacing:.5rem'>{hero_emoji}</div>"
        f"</div>",
        unsafe_allow_html=True
    )

# Identity banner beneath hero
banner_bg = "linear-gradient(135deg,#1E3A5F,#7C3AED)" if is_home else "linear-gradient(135deg,#1E3A5F,#2563EB)"
st.markdown(
    f"<div style='background:{banner_bg};padding:.9rem 1.5rem 1.1rem;"
    f"border-radius:0 0 16px 16px;text-align:center;color:white;margin-bottom:1rem'>"
    f"<div style='font-size:2rem;font-weight:900'>{city_flag} {selected_city}{home_label}</div>"
    f"<div style='color:#CBD5E1;font-size:.88rem;margin-top:.2rem'>"
    f"🏟️ {stadium} · {match_count} World Cup matches · {host_country}"
    f"</div></div>",
    unsafe_allow_html=True
)

# ── 2. Quick Facts ────────────────────────────────────────────────────────────
if city:
    st.markdown("### 📊 Quick Facts")
    first_match_date = fmt_date(city_matches['match_date'].min()) if not city_matches.empty else "—"
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    fc1.markdown(_stat_card("🏙️", "Population",    city.get('population', '—')), unsafe_allow_html=True)
    fc2.markdown(_stat_card("🌎", "Country",       host_country), unsafe_allow_html=True)
    fc3.markdown(_stat_card("🏟️", "Stadium",       stadium), unsafe_allow_html=True)
    fc4.markdown(_stat_card("⚽", "Matches",       str(match_count)), unsafe_allow_html=True)
    fc5.markdown(_stat_card("📅", "First Match",   first_match_date), unsafe_allow_html=True)

# ── 3. Where Is This City? ────────────────────────────────────────────────────
st.markdown("### 🗺️ Where Is This City?")
_map_fig = _city_map(selected_city)
if _map_fig:
    st.plotly_chart(_map_fig, use_container_width=True, config={'staticPlot': True})
else:
    st.markdown(
    "<div style='background:linear-gradient(135deg,#1E293B,#0F172A);border-radius:12px;"
    "height:100px;display:flex;align-items:center;justify-content:center;"
    "color:rgba(255,255,255,.35);font-size:.85rem;border:1px dashed rgba(148,163,184,.25)'>"
    "<div style='text-align:center'><div style='font-size:1.5rem'>🗺️</div>"
    "<div>Map coming soon</div></div>"
    "</div>",
    unsafe_allow_html=True
)

if city:
    # ── 4. Why Kids Might Love It ─────────────────────────────────────────────
    why_cards = city.get('why_kids_cards', [])
    if why_cards:
        st.markdown("### ⭐ Why Kids Might Love It")
        wk_cols = st.columns(min(len(why_cards), 4))
        for col, wk in zip(wk_cols, why_cards[:4]):
            col.markdown(_why_kids_card(wk['emoji'], wk['title'], wk['blurb']), unsafe_allow_html=True)

    # ── 5. Famous Landmarks ───────────────────────────────────────────────────
    landmarks = city.get('landmarks', [])
    if landmarks:
        st.markdown("### 🏛️ Famous Landmarks")
        lm_cols = st.columns(min(len(landmarks), 4))
        for col, (emoji, label) in zip(lm_cols, landmarks[:4]):
            col.markdown(_img_placeholder_card(emoji, label), unsafe_allow_html=True)

    # ── 6. Famous Foods ───────────────────────────────────────────────────────
    foods = city.get('foods', [])
    if foods:
        st.markdown("### 🍽️ Famous Foods")
        fd_cols = st.columns(min(len(foods), 4))
        for col, (emoji, label) in zip(fd_cols, foods[:4]):
            col.markdown(_img_placeholder_card(emoji, label), unsafe_allow_html=True)

    # ── 7. Wildlife & Nature ──────────────────────────────────────────────────
    wildlife = city.get('wildlife', [])
    if wildlife:
        st.markdown("### 🐾 Wildlife & Nature")
        wl_cols = st.columns(min(len(wildlife), 4))
        for col, (emoji, label) in zip(wl_cols, wildlife[:4]):
            col.markdown(_img_placeholder_card(emoji, label), unsafe_allow_html=True)

st.divider()

# ── 8. Teams You'll See Here ──────────────────────────────────────────────────
if not city_matches.empty:
    all_teams = sorted(set(city_matches['home_team'].tolist() + city_matches['away_team'].tolist()))
    if all_teams:
        st.markdown("### ⚽ Teams You'll See Here")
        team_cols = st.columns(min(len(all_teams), 6))
        for col, team in zip(team_cols, all_teams):
            flag_emoji = get_flag(team)
            col.markdown(
                f"<div style='text-align:center;padding:.3rem'>"
                f"<div style='font-size:2.5rem'>{flag_emoji}</div>"
                f"<div style='font-size:.72rem;font-weight:600;color:#475569;margin-top:.2rem'>{team}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

# ── 9. Matches Hosted Here ────────────────────────────────────────────────────
st.markdown("### 📅 Matches Hosted Here")
if city_matches.empty:
    st.info("No matches found for this city.")
else:
    for _, m in city_matches.iterrows():
        mid  = int(m['id'])
        hf   = get_flag(m['home_team'])
        af   = get_flag(m['away_team'])
        time_str = fmt_match_time(m['match_date'], m['kickoff_time_et'])

        score_str = ""
        result_str = ""
        if m['status'] == 'completed':
            hs, as_ = int(m['home_score']), int(m['away_score'])
            score_str = f"**{hs}–{as_}**"
            if hs > as_:   result_str = f"🏆 {m['home_team']} wins"
            elif as_ > hs: result_str = f"🏆 {m['away_team']} wins"
            else:          result_str = "🤝 Draw"

        info_col, btn_col = st.columns([5, 2])
        with info_col:
            st.markdown(
                f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
                f"padding:.7rem 1rem;color:white;border:1px solid rgba(148,163,184,.12)'>"
                f"<div style='font-size:1.5rem'>{hf} {af}</div>"
                f"<div style='font-size:.92rem;font-weight:800;margin:.15rem 0'>{m['home_team']} vs {m['away_team']}</div>"
                f"<div style='font-size:.78rem;color:#94A3B8'>📅 {time_str}</div>"
                f"{'<div style=\"color:#FCD34D;font-size:.82rem;font-weight:700\">'+score_str+' — '+result_str+'</div>' if score_str else ''}"
                f"</div>",
                unsafe_allow_html=True
            )
        with btn_col:
            if st.button("🏟️ Game Day", key=f"city_match_{mid}", use_container_width=True):
                st.session_state["_nav_match_id"] = mid
                st.switch_page("pages/matchup.py")

# ── 10. World Cup History ─────────────────────────────────────────────────────
if city:
    wc_history = city.get('wc_history', '')
    if wc_history:
        st.divider()
        st.markdown("### 🏆 World Cup History")
        st.markdown(
            f"<div style='background:linear-gradient(135deg,#FEF3C7,#FDE68A);border-radius:12px;"
            f"padding:.75rem 1rem;border-left:4px solid #FCD34D'>"
            f"<div style='font-size:.88rem;color:#78350F'><b>⚽ {selected_city}</b><br>{wc_history}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
else:
    st.info(f"Detailed city guide for {selected_city} coming soon!")
