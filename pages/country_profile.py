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

# ── Animal / Food / Landmark info ─────────────────────────────────────────────
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
    "Fennec Fox":        ("The fennec fox has enormous ears to stay cool in the Sahara Desert.", "Their huge ears can hear insects moving underground — perfect for hunting at night!"),
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
    "Moussaka":    ("Moussaka is a Greek-style casserole with layers of eggplant, meat, and creamy sauce.", "Every Greek grandmother has their own secret moussaka recipe!"),
    "Mezze":       ("Mezze is a collection of small dishes shared by everyone at the table.", "In the Middle East, a big spread of mezze is a sign of hospitality and friendship."),
    "Hummus":      ("Hummus is a creamy dip made from chickpeas, tahini, lemon, and garlic.", "Lebanon once made the world's largest plate of hummus weighing over 23,000 pounds!"),
    "Falafel":     ("Falafel are crispy fried balls made from ground chickpeas or fava beans.", "Falafel has been eaten in the Middle East for over 1,000 years!"),
    "Barbecue":    ("Brazilian churrasco barbecue involves giant skewers of meat cooked over open flames.", "In southern Brazil, some restaurants keep bringing meat until you flip a card to say stop!"),
    "Stroopwafel": ("Stroopwafels are two thin waffles sandwiched together with caramel syrup.", "Dutch astronaut André Kuipers took stroopwafels to the International Space Station!"),
    "Stamppot":    ("Stamppot is a Dutch comfort food — mashed potatoes mixed with vegetables.", "Every Dutch family has their own special stamppot recipe passed down through generations."),
}

_LANDMARK_INFO: dict[str, tuple[str, str]] = {
    "Chichen Itza":        ("Chichen Itza is a spectacular Mayan pyramid — one of the New Seven Wonders of the World.", "Twice a year, the sun creates a shadow that looks exactly like a giant snake crawling down!"),
    "Eiffel Tower":        ("The Eiffel Tower was built as a temporary structure in 1889 but was never taken down.", "It grows about 6 inches taller in summer because the metal expands in heat!"),
    "Colosseum":           ("The Roman Colosseum could hold 80,000 spectators — more than most modern NFL stadiums!", "It had 80 entrances so it could be filled or emptied in just 15 minutes."),
    "Machu Picchu":        ("Machu Picchu was built by the Inca people high in the Andes mountains around 1450 AD.", "No one knows exactly why it was built — it might have been a royal vacation home!"),
    "Great Wall of China": ("The Great Wall of China stretches over 13,000 miles — you could walk it for years.", "It was built over 2,000 years and is still not entirely explored!"),
    "Taj Mahal":           ("The Taj Mahal was built by an emperor as a monument of love for his wife.", "It took 22 years and 20,000 workers to build — using no heavy machinery!"),
    "Pyramids of Giza":    ("The Great Pyramid of Giza is the oldest of the Seven Wonders of the Ancient World still standing!", "Its stones are so precisely cut that you can't fit a piece of paper between them."),
    "Stonehenge":          ("No one knows exactly why Stonehenge was built — it's still a mystery!", "The huge stones were transported over 150 miles — with no wheels or cranes!"),
    "Niagara Falls":       ("Niagara Falls moves about 1 million gallons of water per second — absolutely thundering!", "The sound can be heard from 100 miles away on a quiet day."),
    "Amazon Rainforest":   ("The Amazon is the world's largest rainforest and produces 20% of Earth's oxygen.", "The Amazon River freshens the Atlantic Ocean 100 miles out to sea."),
    "Ayers Rock":          ("Uluru changes color from red to orange to purple as the sun rises and sets.", "It is sacred to the Aboriginal Anangu people who have lived near it for 30,000 years."),
    "Sydney Opera House":  ("The Sydney Opera House's roof looks like a series of giant shells or sails.", "The building has 1 million tiles on the roof and took 14 years to build."),
    "Great Barrier Reef":  ("The Great Barrier Reef is so big it can be seen from space!", "Over 1,500 species of fish live there."),
    "Acropolis":           ("The Acropolis in Athens is over 2,500 years old!", "The Parthenon has no perfectly straight lines — the ancient Greeks curved everything slightly to make it look perfect from below."),
    "Sagrada Familia":     ("This amazing cathedral in Barcelona has been under construction for over 140 years!", "The architect Antoni Gaudí is buried inside the church he designed."),
}

_GOVT_TYPE: dict[str, str] = {
    "Algeria": "Republic", "Argentina": "Federal Republic",
    "Australia": "Constitutional Monarchy", "Austria": "Federal Republic",
    "Belgium": "Constitutional Monarchy", "Bosnia and Herzegovina": "Republic",
    "Brazil": "Federal Republic", "Canada": "Constitutional Monarchy",
    "Cape Verde": "Republic", "Colombia": "Republic", "Croatia": "Republic",
    "Curaçao": "Autonomous Territory", "Czechia": "Republic",
    "DR Congo": "Republic", "Ecuador": "Republic", "Egypt": "Republic",
    "England": "Constitutional Monarchy", "France": "Republic",
    "Germany": "Federal Republic", "Ghana": "Republic", "Haiti": "Republic",
    "Iran": "Islamic Republic", "Iraq": "Federal Republic",
    "Ivory Coast": "Republic", "Japan": "Constitutional Monarchy",
    "Jordan": "Kingdom", "Mexico": "Federal Republic", "Morocco": "Kingdom",
    "Netherlands": "Constitutional Monarchy", "New Zealand": "Constitutional Monarchy",
    "Norway": "Constitutional Monarchy", "Panama": "Republic",
    "Paraguay": "Republic", "Portugal": "Republic", "Qatar": "Emirate",
    "Saudi Arabia": "Kingdom", "Scotland": "Constitutional Monarchy",
    "Senegal": "Republic", "South Africa": "Republic",
    "South Korea": "Republic", "Spain": "Constitutional Monarchy",
    "Sweden": "Constitutional Monarchy", "Switzerland": "Federal Republic",
    "Tunisia": "Republic", "Türkiye": "Republic", "USA": "Federal Republic",
    "Uruguay": "Republic", "Uzbekistan": "Republic",
}

# ── Landscape / terrain descriptions ─────────────────────────────────────────
# (emoji, headline, terrain_tags, description)
_LANDSCAPE: dict[str, tuple[str, str, list[str], str]] = {
    "Algeria":    ("🏜️", "Sahara Desert & Atlas Mountains", ["Sahara Desert", "Atlas Mountains", "Mediterranean Coast", "Saharan Oasis"], "Algeria is the largest country in Africa! The north has green mountains and a beautiful Mediterranean coastline, but nearly 90% of the country is covered by the vast Sahara Desert — the world's largest hot desert, where temperatures can swing from blazing hot days to freezing cold nights."),
    "Argentina":  ("🏔️", "Andes, Patagonia & Pampas", ["Andes Mountains", "Patagonian Glaciers", "Pampas Grasslands", "Iguazu Falls"], "Argentina stretches from tropical rainforests in the north all the way down to the frozen tip of South America. The mighty Andes Mountains form its entire western border, while the flat Pampas grasslands in the middle feed millions of cattle — and fuel one of the world's greatest barbecue traditions."),
    "Australia":  ("🔴", "Red Outback & Great Barrier Reef", ["Red Rock Outback", "Great Barrier Reef", "Tropical Rainforest", "Snowy Mountains"], "Australia is an entire continent shaped like a story — dry red desert in the middle, lush tropical rainforest in the north, snowy mountains in the south, and thousands of miles of coastline. The famous 'Red Centre' around Uluru looks like it's from another planet, painted in deep oranges and reds."),
    "Austria":    ("⛰️", "Alpine Peaks & Green Valleys", ["Austrian Alps", "Danube River", "Alpine Lakes", "Forests"], "Austria sits right in the heart of Europe, completely surrounded by mountains. The Austrian Alps cover most of the country, with dramatic peaks, crystal-clear mountain lakes, and picture-perfect meadows full of wildflowers. Vienna, the capital, sits in a gentle valley where the famous Danube River flows through."),
    "Belgium":    ("🌾", "Gentle Hills & North Sea Coast", ["Ardennes Forest", "North Sea Beaches", "Rolling Farmland", "River Valleys"], "Belgium is a small, densely packed country with a surprisingly varied landscape. The south has the dense Ardennes Forest full of ancient hills and rivers, while the north opens up into flat farmland that stretches to the sandy North Sea coast. It's one of the most densely populated countries in Europe."),
    "Bosnia and Herzegovina": ("🏔️", "Mountains, Rivers & Medieval Villages", ["Dinaric Alps", "Neretva River", "Old-Growth Forest", "Waterfalls"], "Bosnia and Herzegovina is one of Europe's most rugged and dramatic landscapes, with deep mountain ranges, crystal-clear rivers cutting through gorges, and dense old-growth forests that feel untouched by time. The country has so many waterfalls and rushing rivers that it's nicknamed 'the land of 7,000 waterfalls.'"),
    "Brazil":     ("🌿", "Amazon Rainforest, Wetlands & Beaches", ["Amazon Rainforest", "Pantanal Wetlands", "Iguazu Falls", "Ipanema Beach"], "Brazil contains the world's largest tropical rainforest — the Amazon — covering an area nearly the size of the continental USA. But Brazil isn't just jungle: it has the Pantanal (the world's largest wetland, bigger than France), spectacular waterfalls, endless Atlantic beaches, and vast savanna grasslands full of wildlife."),
    "Canada":     ("🍁", "Rocky Mountains, Arctic & Great Lakes", ["Rocky Mountains", "Arctic Tundra", "Great Lakes", "Prairie Wheat Fields"], "Canada is the second-largest country in the world, with landscapes so varied they're hard to imagine in one place. From the jagged Rocky Mountains and vast prairies to the frozen Arctic wilderness and Great Lakes that hold 20% of the world's fresh water — Canada is a giant of natural wonder."),
    "Cape Verde": ("🌊", "Volcanic Islands & Atlantic Ocean", ["Volcanic Peaks", "Black Sand Beaches", "Atlantic Cliffs", "Desert Interior"], "Cape Verde is a group of 10 volcanic islands rising dramatically from the Atlantic Ocean, about 400 miles off the coast of West Africa. Each island has its own personality — some are lush and green with waterfalls, others are barren moonscapes of black volcanic rock with towering peaks disappearing into clouds."),
    "Colombia":   ("🌺", "Andes, Amazon & Caribbean Coast", ["Andes Mountains", "Amazon Jungle", "Caribbean Coast", "Coffee Mountains"], "Colombia is one of the most biodiverse places on Earth — it has more species of birds than any other country! The three ranges of the Andes Mountains run through the middle, while the west opens to the Pacific Ocean, the north to the Caribbean, and the southeast plunges into the Amazon jungle."),
    "Croatia":    ("🌊", "Adriatic Coastline & 1,000 Islands", ["Adriatic Sea", "Dalmatian Islands", "Plitvice Lakes", "Dinaric Alps"], "Croatia has one of the most beautiful coastlines in Europe — the Adriatic Sea laps against medieval stone cities, and over 1,000 islands dot the turquoise water. Inland, the dramatic Plitvice Lakes National Park features a series of cascading bright-blue lakes connected by waterfalls, like something from a fantasy story."),
    "Curaçao":    ("🏝️", "Caribbean Island & Coral Reefs", ["Turquoise Lagoons", "Coral Reefs", "Limestone Cliffs", "Dutch Colonial Towns"], "Curaçao is a small tropical island in the southern Caribbean, just 37 miles long. Its waters are some of the clearest in the world, with vibrant coral reefs right at the shore. The colorful Dutch colonial buildings of the capital Willemstad are so unique they're a UNESCO World Heritage Site."),
    "Czechia":    ("🏰", "Bohemian Highlands & Medieval Castles", ["Bohemian Forest", "Elbe River", "Sandstone Rocks", "Rolling Farmland"], "Czechia (Czech Republic) is a landlocked country in the heart of Europe, surrounded by gentle forested mountains. The Bohemian sandstone rock formations in the north look like a fairy-tale landscape of towers and arches. The country has more castles per square mile than almost anywhere in the world."),
    "DR Congo":   ("🌿", "Congo Rainforest & Mighty Rivers", ["Congo River", "Tropical Rainforest", "Virunga Volcanoes", "Mountain Gorilla Habitat"], "The Democratic Republic of Congo contains the second-largest tropical rainforest on Earth, covering an area bigger than Alaska. The Congo River — the deepest river in the world — winds through the jungle. In the east, dramatic volcanic mountains are home to some of the last wild mountain gorillas on the planet."),
    "Ecuador":    ("🌋", "Andes, Amazon & Galápagos Islands", ["Galápagos Islands", "Andes Volcanoes", "Amazon Jungle", "Pacific Coast"], "Ecuador is a small country packed with geographical extremes. It sits right on the equator (Ecuador means 'equator' in Spanish!), has over 50 active volcanoes, contains part of the Amazon jungle, and owns the Galápagos Islands — the world's most famous wildlife laboratory, where Darwin developed his theory of evolution."),
    "Egypt":      ("🏜️", "Nile River & Sahara Desert", ["Sahara Desert", "Nile River Delta", "Red Sea Coast", "Sinai Mountains"], "Egypt is dominated by the endless Sahara Desert, but a thin green ribbon follows the Nile River — the longest river in the world — all the way from the south to the Mediterranean Sea. This narrow strip of fertile land along the Nile is where almost all of Egypt's 100 million people live, surrounded by golden desert on both sides."),
    "England":    ("🌿", "Green Hills, White Cliffs & Moors", ["White Cliffs of Dover", "Lake District Mountains", "Yorkshire Moors", "Thames River"], "England is famous for its patchwork of green hills and hedgerows, with gentle rolling farmland covering most of the country. The dramatic white chalk cliffs of Dover face France just 21 miles away. In the north, wild windswept moors and the rugged Lake District feel like something from a storybook."),
    "France":     ("🗻", "Alps, Mediterranean Coast & River Valleys", ["French Alps", "Mediterranean Riviera", "Loire Valley", "Normandy Coast"], "France has an extraordinary variety of landscapes — snow-capped Alpine peaks in the southeast, lavender fields in Provence, Atlantic cliffs in Brittany, golden Mediterranean beaches in the south, and the gentle Loire Valley with its fairy-tale châteaux. Mont Blanc is the highest mountain in Western Europe at 15,774 feet."),
    "Germany":    ("🌲", "Black Forest, Alps & Rhine River", ["Black Forest", "Bavarian Alps", "Rhine & Moselle Rivers", "North Sea Coast"], "Germany's landscape ranges from the Baltic Sea coast in the north to the Bavarian Alps in the south — a distance of 600 miles of remarkably varied terrain. The famous Black Forest in the southwest is a dense, ancient woodland that inspired many of the Brothers Grimm fairy tales. The Rhine River cuts a dramatic gorge past medieval castles."),
    "Ghana":      ("🌴", "Savanna, Forest & Gulf of Guinea Coast", ["Gulf of Guinea", "Tropical Rainforest", "Volta Lake", "Northern Savanna"], "Ghana sits on the Gulf of Guinea in West Africa, with a coastline of palm-fringed beaches and old European forts. Moving inland, the landscape shifts from tropical rainforest to open savanna. Lake Volta — one of the world's largest artificial lakes — was created when a massive dam was built in the 1960s, flooding a valley the size of Lebanon."),
    "Haiti":      ("⛰️", "Mountains, Valleys & Caribbean Coast", ["Massif du Nord Mountains", "Caribbean Beaches", "Artibonite River", "Tropical Forest"], "Haiti shares the island of Hispaniola with the Dominican Republic, and its name means 'Land of High Mountains' — fitting, because rugged mountain ranges cover most of the country. Haiti has beautiful tropical coastlines, but deforestation over centuries has left many of its hillsides bare and exposed to tropical storms."),
    "Iran":       ("🏔️", "Alborz Mountains, Desert & Persian Gulf", ["Alborz Mountains", "Dasht-e Kavir Desert", "Persian Gulf Coast", "Zagros Mountains"], "Iran is a country of dramatic contrasts — snow-capped mountains over 18,000 feet tall, vast salt deserts where almost nothing survives, lush forests on the Caspian Sea coast, and warm turquoise waters in the Persian Gulf. The ancient Silk Road passed through Iran's great cities for thousands of years."),
    "Iraq":       ("🌊", "Mesopotamia — Birthplace of Civilization", ["Tigris River", "Euphrates River", "Mesopotamian Marshes", "Zagros Mountains"], "Iraq sits between the Tigris and Euphrates Rivers — the famous 'Cradle of Civilization' where writing, cities, and agriculture were invented over 5,000 years ago. The southern marshes are a unique ecosystem of islands and reeds that have been home to the Marsh Arabs for millennia, though much was drained in the 20th century."),
    "Ivory Coast":("🌿", "Rainforest, Savanna & Atlantic Coast", ["Atlantic Coastline", "Tropical Rainforest", "Northern Savanna", "Bandama River"], "Ivory Coast (Côte d'Ivoire) has a long Atlantic coastline of sandy beaches and lagoons, a belt of tropical rainforest in the center — home to West African forest elephants — and drier savanna in the north. The country produces more cocoa beans than anywhere else in the world, meaning it's responsible for much of the world's chocolate!"),
    "Japan":      ("🗻", "Mountains, Volcanoes & Coastal Islands", ["Mount Fuji", "Volcanic Archipelago", "Cherry Blossom Forests", "Bamboo Groves"], "Japan is an archipelago of over 6,800 islands, with 73% of the land covered by mountains. The iconic Mount Fuji is a perfectly symmetrical active volcano and Japan's highest peak. Japan sits on the 'Ring of Fire,' meaning it has over 100 active volcanoes and experiences thousands of earthquakes every year — though most are too small to feel."),
    "Jordan":     ("🏜️", "Wadi Rum Desert & Petra Rock City", ["Wadi Rum Desert", "Petra Ancient City", "Dead Sea", "Aqaba Red Sea Coast"], "Jordan is a land of ancient stone and desert drama. The Wadi Rum desert looks like a red-rock landscape from Mars — it was used to film The Martian and parts of Star Wars. The ancient city of Petra was carved entirely into pink sandstone cliffs 2,000 years ago. The Dead Sea on Jordan's western border is the lowest point on Earth's surface at 1,400 feet below sea level."),
    "Mexico":     ("🏔️", "Sierra Madre, Yucatán & Two Coasts", ["Sierra Madre Mountains", "Yucatán Peninsula", "Pacific Coast", "Caribbean Coast"], "Mexico has an extraordinary range of landscapes — dramatic mountain ranges, the flat jungle-covered Yucatán Peninsula with its ancient Mayan ruins, smoking volcanoes including one that overlooked the Aztec capital, stunning Pacific beaches, and the turquoise Caribbean coast. Mexico City sits in a high mountain valley at 7,350 feet above sea level."),
    "Morocco":    ("🏜️", "Atlas Mountains, Sahara & Atlantic Coast", ["Atlas Mountains", "Sahara Desert Dunes", "Atlantic Coast", "Rif Mountains"], "Morocco has one of the most dramatic landscapes in Africa — the snow-capped Atlas Mountains rise from the center, and on one side you have Atlantic beaches and on the other, golden Sahara sand dunes that stretch into Algeria. The ancient medina cities like Marrakech and Fez are mazes of narrow alleyways, colorful markets, and ancient palaces."),
    "Netherlands":("🌷", "Flat Polders, Canals & North Sea", ["North Sea Coastline", "Tulip Polders", "Canal Networks", "Windmills"], "The Netherlands is famously flat — about a quarter of the country is actually below sea level, protected from the ocean by an ingenious system of dykes, dunes, and pumping stations. Without these engineering marvels, large parts of Amsterdam and Rotterdam would be underwater. The spring countryside explodes with tulip fields of brilliant red, yellow, and pink."),
    "New Zealand":("🏔️", "Fiords, Volcanoes & Green Islands", ["Southern Alps", "Milford Sound Fiords", "Tongariro Volcanoes", "Hobbiton Green Hills"], "New Zealand's two islands have wildly different personalities — the North Island has active volcanoes, geothermal hot springs with boiling mud pools, and lush subtropical forests. The South Island has dramatic glacier-carved fiords, the towering Southern Alps, and rolling green hills that look like the set of a fantasy film (which they literally were for Lord of the Rings!)."),
    "Norway":     ("🏔️", "Fjords, Midnight Sun & Arctic North", ["Norwegian Fjords", "Arctic Wilderness", "Lofoten Islands", "Midnight Sun"], "Norway is home to the world's most famous fjords — enormous glacier-carved valleys now filled with impossibly blue seawater, with cliffs rising thousands of feet on either side. Above the Arctic Circle, Norway experiences the 'midnight sun' in summer (when it never gets dark for months) and the Northern Lights in winter — a dancing curtain of green and purple light in the night sky."),
    "Panama":     ("🌿", "Rainforest, Canal & Two Oceans", ["Panama Canal", "Darién Jungle", "Pacific Coast", "Caribbean Coast"], "Panama is the narrow bridge connecting North and South America, and the famous Panama Canal cuts right through it — allowing ships to travel between the Pacific and Atlantic Oceans without sailing around South America. Despite its small size, Panama has extraordinary biodiversity, including over 900 species of birds — more than all of North America combined!"),
    "Paraguay":   ("🌊", "Chaco, Pantanal & Great Rivers", ["Gran Chaco", "Paraná River", "Itaipú Dam", "Subtropical Forest"], "Paraguay is a landlocked country in South America divided by the Paraguay River. The eastern half is green and subtropical, while the western Gran Chaco is one of the driest, most remote wildernesses in South America — a vast flatland of thorny scrub forest with almost no roads or people, but incredible wildlife."),
    "Portugal":   ("🌊", "Atlantic Coast, Wine Valleys & Cliffs", ["Algarve Sea Cliffs", "Douro Wine Valley", "Lisbon Hills", "Atlantic Islands"], "Portugal sits at the southwestern corner of Europe, facing the Atlantic Ocean that Portuguese explorers once crossed to map the entire world. The Algarve coast in the south has spectacular golden limestone cliffs and hidden coves. The Douro Valley is a UNESCO World Heritage Site of steep terraced vineyards producing world-famous wine."),
    "Qatar":      ("🏜️", "Arabian Desert & Persian Gulf", ["Arabian Desert", "Persian Gulf Coast", "Salt Flats", "Inland Sea"], "Qatar is a small peninsula jutting into the Persian Gulf, mostly flat desert with a rapidly changing coastline of mega-cities rising from the sand. Despite the harsh desert environment, Qatar has built extraordinary modern architecture and infrastructure. The Khor Al Adaid ('Inland Sea') in the south is a stunning natural lagoon surrounded by giant sand dunes."),
    "Saudi Arabia":("🏜️", "Arabian Desert, Asir Mountains & Red Sea", ["Rub' al Khali Desert", "Asir Mountains", "Red Sea Coast", "Ancient Nabataean Ruins"], "Saudi Arabia contains the Rub' al Khali — the 'Empty Quarter' — the world's largest continuous sand desert, covering an area bigger than France. But Saudi Arabia also has the dramatic Asir Mountains in the southwest with year-round cool weather, lush terraced farms, and a Red Sea coastline famous for exceptional diving on pristine coral reefs."),
    "Scotland":   ("🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Highlands, Lochs & Rugged Coastline", ["Scottish Highlands", "Loch Ness", "Isle of Skye", "Grampian Mountains"], "Scotland's landscape is wild, dramatic, and ancient. The Highlands in the north are one of Europe's few true wildernesses — vast treeless moorlands, towering peaks, and hundreds of lochs (lakes), including the famous Loch Ness. The Isle of Skye features bizarre rock formations that look sculpted by a giant's hand, with mist and rain adding to the moody atmosphere."),
    "Senegal":    ("🌊", "Savanna, Atlantic Coast & River Delta", ["Atlantic Coastline", "Casamance Forest", "Sahel Savanna", "Sine-Saloum Delta"], "Senegal is shaped like a curved arm reaching into the Atlantic Ocean, with an extraordinary coastline of beaches, mangrove forests, and bird-filled river deltas. Moving inland, the landscape transitions from forest to the Sahel savanna — a semi-arid zone where the Sahara slowly fades into green. The Sine-Saloum Delta is a labyrinth of waterways sheltering over 200 species of birds."),
    "South Africa":("🦁", "Savanna, Mountains, Desert & Two Oceans", ["Kruger National Park", "Drakensberg Mountains", "Cape Peninsula", "Kalahari Desert"], "South Africa is where two oceans meet — the warm Indian Ocean on the east and the cold Atlantic Ocean on the west. This creates dramatically different climates along its coastline. Inland, the Drakensberg Mountains tower over 11,000 feet, while the iconic Kruger National Park — larger than Wales — protects lions, elephants, rhinos, leopards, and buffalos on open savanna."),
    "South Korea":("🗻", "Mountains, Coastline & Rice Valleys", ["Taebaek Mountains", "Jeju Island Volcano", "West Sea Islands", "River Valleys"], "South Korea is a peninsula surrounded by sea on three sides, with 70% of its land covered by mountains and forests. The rocky Taebaek Mountains run down the spine of the country. Jeju Island — a volcanic island off the southern coast — has subtropical forests, lava tubes, and a dormant volcano. South Korea has extraordinary cherry blossom seasons each spring."),
    "Spain":      ("☀️", "Meseta Plateau, Pyrenees & Mediterranean", ["Spanish Meseta", "Pyrenees Mountains", "Mediterranean Coast", "Canary Islands"], "Spain is Europe's second-largest country by area, dominated by the high, dry Meseta plateau that covers most of the center. But the edges tell a different story — green, rainy Galicia in the northwest, the dramatic Pyrenees mountains separating Spain from France, white villages along the sunny Mediterranean coast, and volcanic Canary Islands off Africa."),
    "Sweden":     ("🌲", "Forest Lakes, Archipelago & Arctic North", ["Swedish Lapland", "Stockholm Archipelago", "Scandinavian Mountains", "24,000 Islands"], "Sweden is a long, narrow country stretching from mild southern farmland all the way to the Arctic Circle, where reindeer roam and the Northern Lights dance. The coastline is extraordinarily complex — Stockholm alone is spread across 14 islands, and Sweden has about 24,000 islands total. Over half the country is covered by deep forest."),
    "Switzerland":("🏔️", "Swiss Alps, Lakes & Mountain Meadows", ["Swiss Alps", "Alpine Lakes", "Rhine & Rhône Rivers", "Jura Mountains"], "Switzerland is the heart of the Alps — the most spectacular mountain range in Europe. The Swiss Alps have dramatic peaks, crystal-clear glacier lakes, and impossibly green mountain meadows. Although Switzerland is completely landlocked, its stunning Lake Geneva and Lake Constance are so large they can fool you into thinking you're at the sea."),
    "Tunisia":    ("🏜️", "Sahara, Mediterranean Coast & Salt Lakes", ["Sahara Desert", "Mediterranean Coast", "Chott el Jerid Salt Lake", "Atlas Mountains"], "Tunisia is where Europe meets Africa — the Mediterranean coast in the north has beautiful sandy beaches and ancient ruins, while the south plunges into the Sahara Desert with towering sand dunes. The giant Chott el Jerid salt lake turns pink and white when it dries out in summer, and Star Wars: Episode IV was filmed in the desert landscapes of southern Tunisia."),
    "Türkiye":    ("🏔️", "Anatolian Plateau, Cappadocia & Two Seas", ["Cappadocia Rock Cones", "Pamukkale Hot Springs", "Anatolian Plateau", "Bosphorus Strait"], "Turkey sits between Europe and Asia, literally bridged by Istanbul. The Anatolian plateau covers most of the country — a vast, high, semi-arid landmass. But the most surreal landscape is Cappadocia, where millions of years of volcanic eruptions created a forest of strange tall 'fairy chimney' rock formations. Hot air balloons float over them at sunrise every morning."),
    "USA":        ("🏔️", "Rocky Mountains, Grand Canyon & Great Plains", ["Rocky Mountains", "Grand Canyon", "Great Plains", "Florida Everglades"], "The USA has some of the most dramatic and varied landscapes on Earth — from the towering Rocky Mountains and the mile-deep Grand Canyon to the flat wheat-covered Great Plains, Alaskan glaciers, Hawaiian volcanoes, and Florida's subtropical Everglades swamps. The country spans from desert to rainforest, from tundra to tropical islands."),
    "Uruguay":    ("🌾", "Pampas Grasslands & Atlantic Coast", ["Pampas Grasslands", "Atlantic Beaches", "Río de la Plata", "Rolling Hills"], "Uruguay is the smallest country in South America, but what it lacks in size it makes up for in character. Most of the country is covered in rolling green pampas grasslands grazed by millions of cattle. Uruguay has a beautiful Atlantic coast with famous beach resorts, and the enormous Río de la Plata estuary (wider than the English Channel) forms the border with Argentina."),
    "Uzbekistan": ("🏜️", "Silk Road Desert & Ancient Blue-Tiled Cities", ["Kyzylkum Desert", "Pamir Mountains", "Aral Sea (shrinking)", "Fergana Valley"], "Uzbekistan sits in the middle of Central Asia, a desert country crossed for thousands of years by the ancient Silk Road trading route. The blue-tiled mosques and madrassas of Samarkand and Bukhara are among the most beautiful Islamic architecture in the world. The Aral Sea — once one of the world's largest lakes — has almost completely dried up due to Soviet-era irrigation projects, one of the world's greatest environmental disasters."),
}

# ── Soccer bridge paragraphs ──────────────────────────────────────────────────
_SOCCER_INTRO: dict[str, str] = {
    "Algeria":    "Soccer is the undisputed national passion of Algeria. Millions of fans follow the national team — the Desert Foxes — everywhere they go. Algeria has appeared at multiple World Cups and is famous for producing stunning upsets against bigger, more famous nations.",
    "Argentina":  "Argentina doesn't just love soccer — it lives and breathes it. From the moment children can walk, they're kicking a ball in the street. Argentina has produced two of the greatest players who ever lived: Diego Maradona and Lionel Messi. Winning the World Cup is the most important thing in Argentine culture.",
    "Australia":  "Soccer (called 'football' everywhere except here!) has grown enormously in Australia over the past 30 years. The Socceroos are now a respected World Cup regular, and many Australian players have starred in top European leagues. Tim Cahill's spectacular bicycle kick goal against the Netherlands in 2014 is one of the most famous World Cup goals ever.",
    "Belgium":    "Belgium punched well above its weight in soccer for over a decade — with a 'golden generation' of world-class players that made them the #1 ranked team in the world. Kevin De Bruyne, Eden Hazard, and Romelu Lukaku became global superstars. Belgium reached the 2018 World Cup semifinals, their best finish ever.",
    "Brazil":     "Brazil and soccer are inseparable — some say Brazil invented the beautiful game as the world knows it. With five World Cup titles, Brazil is the most successful nation in World Cup history. Players like Pelé, Ronaldo, Ronaldinho, and Neymar have made Brazil synonymous with flair, creativity, and pure joy on the ball.",
    "Canada":     "Canada has made extraordinary soccer progress in recent years. After qualifying for the 2022 World Cup for only the second time ever, they're now a legitimate force — led by the brilliant Alphonso Davies, who plays for Bayern Munich. Canadian fans are loud, passionate, and extremely proud of how far their team has come.",
    "Colombia":   "Colombia's love for soccer is explosive — literally. Crowds at matches are some of the loudest and most passionate in the world. The country produced one of the 1990s' most exciting teams, including goalkeeper René Higuita who famously saved a shot with his feet. James Rodríguez's stunning volley goal at the 2014 World Cup was voted Goal of the Tournament.",
    "Croatia":    "For such a tiny country (population: 4 million), Croatia has produced a remarkable number of world-class players. The 'Vatreni' (The Blazers) reached the 2018 World Cup Final and the 2022 semifinal — remarkable achievements for a nation smaller than Los Angeles. Luka Modrić was voted the best player in the world in 2018.",
    "Egypt":      "Soccer is Egypt's national obsession, and the Pharaohs are among Africa's most decorated teams. Cairo's derbies between Zamalek and Al Ahly are among the most intense club rivalries on Earth. Mohamed Salah, who plays for Liverpool, is one of the most famous athletes in all of Africa and the Arab world.",
    "England":    "England invented the modern game of soccer in the 19th century — they wrote the first official rules in 1863. But they've only ever won the World Cup once, in 1966 on home soil. England's players are among the most famous in the world, and the Premier League is watched by hundreds of millions of fans globally.",
    "France":     "France has one of the deepest pools of soccer talent in the world, producing stars across every generation. Les Bleus have won two World Cups (1998 and 2018) and have reached multiple finals. The 2022 World Cup Final — where Mbappé scored a hat-trick in a thrilling 3-3 draw before losing on penalties — may be the greatest match ever played.",
    "Germany":    "Germany is soccer royalty — four World Cup titles, eight finals, and a tradition of disciplined, efficient, technically brilliant football stretching back 70 years. The German national team has never gone a full tournament without scoring. Their 7–1 demolition of Brazil on Brazilian soil in 2014 left the world speechless.",
    "Japan":      "Soccer has exploded in Japan since 1993, when the J-League was founded. Millions of Japanese fans follow European leagues passionately, and Japanese players now star at clubs across Europe. Japan is famous for their technical precision, teamwork, and the incredible noise their fans make — and make when they clean up their section after every match.",
    "Mexico":     "In Mexico, soccer is not just a sport — it is culture, religion, and national identity all wrapped in one. El Tricolor have qualified for every World Cup since 1994 and always bring tens of thousands of screaming fans wherever they play. The Azteca Stadium in Mexico City has hosted two World Cup finals — more than any other stadium.",
    "Morocco":    "Morocco's 2022 World Cup run was one of the greatest stories in World Cup history — the first African nation ever to reach the semifinals. Their passionate fans — the 'Ultras Maroc' — created an atmosphere unlike anything ever seen. The Atlas Lions are now considered serious contenders, and a whole continent cheers for them.",
    "Netherlands":("The Netherlands has produced some of the greatest players and ideas in soccer history — Johan Cruyff invented 'Total Football,' a revolutionary style where every player can play every position. Dutch players like Cruyff, Van Basten, Gullit, Robben, and Van Dijk have changed how the game is played. Despite all this talent, the Netherlands has never won the World Cup."),
    "Portugal":   "Portugal's golden era of soccer began with Eusébio in the 1960s and has continued through Luis Figo and Cristiano Ronaldo. Ronaldo is one of the most famous athletes on Earth, having won five Ballon d'Or awards. Portugal won their first major title at Euro 2016 and have consistently challenged for World Cup glory.",
    "Saudi Arabia":"Soccer is the dominant sport in Saudi Arabia, where the Saudi Pro League has recently attracted global stars like Cristiano Ronaldo, Karim Benzema, and Neymar. The Green Falcons shocked the world at the 2022 World Cup by beating eventual champion Argentina 2–1 in one of the greatest upsets in World Cup history.",
    "South Korea":("South Korea co-hosted the 2002 World Cup and produced the biggest surprise in tournament history — becoming the first Asian team to ever reach the semifinals, knocking out Spain, Italy, and Portugal along the way. Korean soccer has grown dramatically, with players like Son Heung-min becoming global stars."),
    "Spain":      "Spain's 'golden generation' of the 2000s-2010s was considered the greatest national team ever assembled — winning Euro 2008, the 2010 World Cup, and Euro 2012 in a row. Their 'tiki-taka' style of short passing and possession mesmerized the world. Now a new generation of young stars is attempting to recapture that dominance.",
    "USA":        "Soccer is the fastest-growing major sport in the United States, and hosting the 2026 World Cup is expected to accelerate that dramatically. The US team qualified for every World Cup from 1990-2022 (except 2018). American fans who grew up watching MLS or playing youth soccer are now playing in top European leagues.",
    "Uruguay":    "For a country of just 3.5 million people, Uruguay's soccer history is extraordinary. They won the first ever World Cup in 1930, then beat Brazil on their home soil in 1950 in the biggest upset in World Cup history — an event still called 'el Maracanazo.' Uruguay has also won the Copa América more than any other nation.",
}

# ── Per-country World Cup story moments ───────────────────────────────────────
# (year, headline, story)
_WC_COUNTRY_STORY: dict[str, list[tuple[str, str, str]]] = {
    "Algeria": [
        ("1982", "The Miracle of Gijón",          "Algeria beat eventual third-place West Germany 2–1 in one of the biggest upsets in World Cup history. But they were still eliminated after Germany and Austria played a suspicious 1–0 result that sent both teams through."),
        ("2014", "Best Finish Ever — Round of 16","Algeria beat South Korea and Russia to escape the group stage, then gave defending champion Germany a massive scare before losing 2–1 after extra time. Their best-ever World Cup run."),
        ("2026", "Back on the World Stage",        "Algeria returns to the World Cup aiming to build on their 2014 heroics. With a passionate fan base and a new generation of talented players, Les Fennecs are hungry to make history."),
    ],
    "Argentina": [
        ("1978", "First World Cup Title",          "Argentina won their first World Cup on home soil, in front of 77,000 screaming fans in Buenos Aires. The ticker tape celebrations were unlike anything the world had seen."),
        ("1986", "Maradona's World Cup",           "Diego Maradona single-handedly carried Argentina to glory. In the quarterfinal against England, he scored both the 'Hand of God' goal and the 'Goal of the Century' in the same match — two of the most famous goals ever."),
        ("2022", "Messi Finally Has His Cup",      "After four World Cups of heartbreak, Lionel Messi lifted the trophy in Qatar in possibly the greatest final ever played — a 3–3 draw with France decided on penalties. A billion people watched. An entire continent celebrated."),
    ],
    "Brazil": [
        ("1970", "The Greatest Team Ever",         "Brazil's 1970 team — with Pelé, Jairzinho, Tostão, and Rivelino — is still considered the greatest team to ever play the game. Jairzinho scored in every single match. They didn't just win; they created art."),
        ("2014", "The Mineirazo",                  "Hosting the World Cup, Brazil was demolished 7–1 by Germany in the semifinal in front of 60,000 fans. Brazilian fans wept in the stands. It's called 'the worst day in Brazilian soccer history.'"),
        ("2026", "Hunting a Record 6th Title",     "Brazil arrives in 2026 with a new generation of stars and an enormous hunger to reclaim the World Cup after years of heartbreak. No country has ever won six — Brazil wants to change that."),
    ],
    "Croatia": [
        ("1998", "Third Place on Debut",           "In their very first World Cup as an independent country, Croatia finished third place. Davor Šuker won the Golden Boot as the tournament's top scorer. An astonishing debut on the world stage."),
        ("2018", "World Cup Final",                "Croatia defeated England in the semifinal and became the second-smallest country (by population) to reach a World Cup Final. They lost to France, but the whole nation of 4 million celebrated their incredible run."),
        ("2022", "Semifinal Again",                "Croatia did it again in Qatar — defeating Brazil and Argentina favorite Japan on their way to another top-four finish. Luka Modrić, at 37, played some of the best soccer of his career."),
    ],
    "England": [
        ("1966", "England's Only World Cup",       "England hosted the tournament and won 4–2 against West Germany in the final at Wembley Stadium. Geoff Hurst scored a hat-trick — still the only hat-trick in a World Cup Final. England has been chasing that glory ever since."),
        ("1990", "Gazza's Tears",                  "England reached the semifinals, where midfielder Paul Gascoigne received a yellow card that would have banned him from the final. Realizing this, he burst into tears on the pitch — one of the most iconic images in World Cup history."),
        ("2021+", "Still Waiting",                 "After 60+ years, England still hasn't won a second World Cup. They came close at Euro 2020 (lost the final on penalties to Italy). Every tournament brings enormous hope — and the same heartbreaking ending... so far."),
    ],
    "France": [
        ("1998", "First World Cup — at Home",      "France won their first World Cup on home soil with Zidane scoring two headers in the final. One million people celebrated on the Champs-Élysées. Zinédine Zidane became a national legend overnight."),
        ("2018", "Second World Cup",               "A young, dynamic French team won in Russia with a 4–2 final victory over Croatia. 19-year-old Mbappé became the first teenager to score in a World Cup Final since Pelé in 1958."),
        ("2022", "The Greatest Final",             "France lost the 2022 final to Argentina on penalties after a breathtaking 3–3 draw. Mbappé scored a hat-trick, becoming the first player to ever do so in a final. Many call it the greatest World Cup match ever played."),
    ],
    "Germany": [
        ("1954", "The Miracle of Bern",            "West Germany came back from being 2–0 down against Hungary — the unbeaten favorites — to win 3–2 in the final. The Germans called it 'das Wunder von Bern.' A war-ravaged nation found joy again."),
        ("2014", "The 7–1",                        "Germany demolished Brazil 7–1 in the semifinal on Brazilian soil — five goals in 18 minutes. Then they beat Argentina 1–0 in extra time in the final. Mario Götze scored the winning goal 113 minutes in."),
        ("2022", "Shock Exit",                     "Germany was eliminated in the group stage — their second such exit in a row (after 2018). The most disappointing chapter in German soccer history sent shockwaves through world football."),
    ],
    "Japan": [
        ("2002", "Semifinal Dream",                "Co-hosting with South Korea, Japan reached the Round of 16 for the first time ever. Their win over Russia and draw with Belgium thrilled millions. The whole country went soccer-mad overnight."),
        ("2010+", "Consistent Qualifiers",         "Japan has qualified for every World Cup since 1998. In 2022, they pulled off two incredible upsets — beating Germany and Spain — before losing to Croatia on penalties. Japan has become a genuine World Cup threat."),
        ("2022", "Beating Germany & Spain",        "In Qatar, Japan beat Group E favorites Germany 2–1 coming from behind, then repeated the feat against Spain 2–1. Both wins came from extraordinary late comebacks. Japan was one of the stories of the tournament."),
    ],
    "Mexico": [
        ("1970", "Host Country, Great Run",        "Hosting the World Cup at the iconic Azteca stadium, Mexico reached the quarterfinals. The 1970 tournament — with Pelé's Brazil winning beautifully — is still considered the greatest World Cup ever, and Mexico was right in the middle of it."),
        ("1986", "Second Home World Cup",          "Mexico hosted again (after Colombia dropped out) and reached the quarterfinals, where they lost to West Germany on penalties. Hugo Sánchez was the biggest star, and Mexican fans created some of the most passionate atmospheres in World Cup history."),
        ("1994+", "The Round of 16 Wall",          "Mexico has reached the Round of 16 (top 16) in every World Cup since 1994 — but has never gotten past that round. Mexicans call it 'el quinto partido' (the fifth game) that they can never seem to win."),
    ],
    "Morocco": [
        ("1986", "Africa's First Group Win",       "Morocco became the first African team ever to top their World Cup group — winning Group F ahead of England, Poland, and Portugal. They were knocked out in the Round of 16 by West Germany, but made all of Africa proud."),
        ("2022", "Semifinal — History Made",       "Morocco became the first African and Arab team to ever reach a World Cup semifinal. Along the way they eliminated Spain and Portugal. Their passionate fans celebrated across the Arab world. They lost to France but changed history."),
        ("2026", "Can They Go Further?",           "Morocco returns to the World Cup on a wave of momentum and confidence. After their 2022 heroics, the world will be watching — can the Atlas Lions become the first African team to reach the final?"),
    ],
    "South Korea": [
        ("2002", "The Miracle of Seoul",           "Co-hosting with Japan, South Korea produced the biggest surprise in World Cup history — reaching the semifinals. They beat Spain, Italy, and Portugal (all previous champions or runners-up) along the way. The nation exploded with joy; millions celebrated in the streets of Seoul."),
        ("2010+", "Consistent Performers",         "South Korea qualified for their 10th consecutive World Cup in 2022, reaching the Round of 16 by defeating Portugal. Son Heung-min is now one of the most famous soccer players in Asia, starring for Tottenham Hotspur."),
    ],
    "Spain": [
        ("2010", "First World Cup Title",          "Spain's tiki-taka generation won their first and only World Cup in South Africa — beating Netherlands 1–0 in extra time through Andrés Iniesta's goal. After winning Euros in 2008 and winning the Cup in 2010, then winning Euros again in 2012, they were the undisputed greatest team in the world."),
        ("2014", "Shock Defense",                  "Defending champions Spain was stunned — losing 5–1 to the Netherlands in their opening game and exiting in the group stage. The golden generation's era ended with a crash."),
        ("2022", "New Generation Arrives",         "Spain's brilliant young team dazzled in Qatar before losing to Morocco on penalties. Players like Pedri, Gavi, and Yamal are now considered among the best in the world — Spain's next golden era may be beginning."),
    ],
    "Uruguay": [
        ("1930", "First Ever World Cup Champions", "Uruguay won the very first World Cup on home soil, beating Argentina 4–2 in the final in Montevideo in front of 93,000 fans. The whole country celebrated for days."),
        ("1950", "The Maracanazo",                 "Uruguay shocked Brazil 2–1 in the final in Brazil's own stadium in front of 200,000 fans — widely considered the greatest upset in sports history. Brazil fans stood in silence. Uruguay went wild. The scar in Brazil has never fully healed."),
        ("2010", "Semifinal Run",                  "Uruguay reached the semifinals in South Africa with striker Luis Suárez, infamously saving a goal with his hand on the line against Ghana in the quarterfinal. A controversial moment that ended Ghana's dream but kept Uruguay's alive."),
    ],
    "USA": [
        ("1950", "Beating England",                "The USA's greatest ever World Cup result — a 1–0 shock victory over England, which had invented the game. The English press refused to believe it at first, thinking it was a typo. It remains one of the biggest upsets in World Cup history."),
        ("1994", "America's First World Cup",      "The USA hosted the 1994 World Cup and surprised everyone by averaging 69,000 fans per game — the highest ever. The US team reached the Round of 16. This tournament transformed American soccer and led to the creation of MLS."),
        ("2026", "Hosting Again — and Ready",      "The USA co-hosts the 2026 World Cup and comes in as a legitimate threat to go deep in the tournament. With a young, talented squad including players who star in top European leagues, American soccer has never been stronger."),
    ],
}

# ── Teaser facts for neighbor cards ──────────────────────────────────────────
_COUNTRY_TEASER: dict[str, str] = {
    "Algeria":              "Home to the Sahara Desert — the world's largest hot desert.",
    "Argentina":            "Five-time World Cup champions — the most successful team in South America.",
    "Australia":            "Home of kangaroos, koalas, and the world's largest coral reef.",
    "Austria":              "Birthplace of Mozart and the croissant. The Alps cover most of the country.",
    "Belgium":              "The world's chocolate capital — producing over 220,000 tons per year.",
    "Bosnia and Herzegovina":"A land of 7,000 waterfalls and one of Europe's most dramatic landscapes.",
    "Brazil":               "The Amazon rainforest — the lungs of the Earth — covers much of this country.",
    "Canada":               "The second-largest country in the world, with more lakes than anywhere on Earth.",
    "Cape Verde":           "Ten volcanic islands rising dramatically from the Atlantic Ocean.",
    "Colombia":             "Has more bird species than any other country in the world.",
    "Croatia":              "Over 1,000 stunning Adriatic islands and the ancient walled city of Dubrovnik.",
    "Curaçao":              "A colorful Caribbean island known for the world's best-hidden diving spots.",
    "Czechia":              "More castles per square mile than almost anywhere else in the world.",
    "DR Congo":             "Home to the Congo rainforest — Earth's second-largest tropical jungle.",
    "Ecuador":              "The Galápagos Islands — Darwin's laboratory for the theory of evolution.",
    "Egypt":                "The Great Pyramids of Giza — the last surviving Wonder of the Ancient World.",
    "England":              "Invented modern soccer in 1863. Still waiting for a second World Cup title.",
    "France":               "The most visited country in the world — over 90 million tourists per year.",
    "Germany":              "Four-time World Cup champions and home of the world-famous Oktoberfest.",
    "Ghana":                "The first sub-Saharan African country to achieve independence (1957).",
    "Haiti":                "The first Black republic in the world, winning independence in 1804.",
    "Iran":                 "One of the world's oldest continuous civilizations — over 7,000 years of history.",
    "Iraq":                 "Mesopotamia — the birthplace of writing, cities, and agriculture.",
    "Ivory Coast":          "Produces more cocoa beans than anywhere else — responsible for much of the world's chocolate!",
    "Japan":                "Home of sushi, Nintendo, anime, and Mount Fuji — an iconic volcano.",
    "Jordan":               "The ancient city of Petra, carved entirely from pink rock cliffs 2,000 years ago.",
    "Mexico":               "Ancient Mayan and Aztec civilizations left pyramids that still stand today.",
    "Morocco":              "Reached the World Cup semifinals in 2022 — first African team in history.",
    "Netherlands":          "A quarter of the country is below sea level, protected by an incredible system of dykes.",
    "New Zealand":          "Where Lord of the Rings was filmed — a land of volcanoes and stunning fjords.",
    "Norway":               "Home of the Northern Lights and fjords that stretch miles into the mountains.",
    "Panama":               "The Panama Canal connects the Pacific and Atlantic Oceans — a feat of engineering.",
    "Paraguay":             "The Gran Chaco — one of South America's wildest and least-explored wildernesses.",
    "Portugal":             "Portuguese explorers once mapped the entire world — from Brazil to Japan.",
    "Qatar":                "Hosted the 2022 World Cup — the first in the Middle East and in winter.",
    "Saudi Arabia":         "Beat Argentina 2–1 in one of the greatest upsets in World Cup history (2022).",
    "Scotland":             "The Highlands and Loch Ness — wild, ancient, and shrouded in mystery.",
    "Senegal":              "One of West Africa's most vibrant cultures, famous for wrestling, music, and hospitality.",
    "South Africa":         "Home of the Big Five — lions, elephants, rhinos, leopards, and buffalos.",
    "South Korea":          "Reached the World Cup semifinals in 2002 — the first Asian team ever to do so.",
    "Spain":                "The Sagrada Família — a cathedral under construction for over 140 years.",
    "Sweden":               "The Aurora Borealis (Northern Lights) dances in the Swedish winter sky.",
    "Switzerland":          "The Swiss Alps — the most spectacular mountain scenery in Europe.",
    "Tunisia":              "Star Wars' Tatooine was filmed in Tunisia's desert landscapes.",
    "Türkiye":              "Cappadocia's surreal 'fairy chimney' rock towers — hot air balloons float over them daily.",
    "USA":                  "The Grand Canyon — a mile-deep gorge carved over 6 million years.",
    "Uruguay":              "Won the first-ever World Cup in 1930 — the smallest country to ever win it.",
    "Uzbekistan":           "The ancient Silk Road cities of Samarkand and Bukhara are living museums.",
}

# ── Compact WC history data (for embedded tabs) ───────────────────────────────
_WC_ALL_CHAMPIONS = [
    (1930,"🇺🇾","Uruguay"),(1934,"🇮🇹","Italy"),(1938,"🇮🇹","Italy"),
    (1950,"🇺🇾","Uruguay"),(1954,"🇩🇪","Germany"),(1958,"🇧🇷","Brazil"),
    (1962,"🇧🇷","Brazil"),(1966,"🏴󠁧󠁢󠁥󠁮󠁧󠁿","England"),(1970,"🇧🇷","Brazil"),
    (1974,"🇩🇪","Germany"),(1978,"🇦🇷","Argentina"),(1982,"🇮🇹","Italy"),
    (1986,"🇦🇷","Argentina"),(1990,"🇩🇪","Germany"),(1994,"🇧🇷","Brazil"),
    (1998,"🇫🇷","France"),(2002,"🇧🇷","Brazil"),(2006,"🇮🇹","Italy"),
    (2010,"🇪🇸","Spain"),(2014,"🇩🇪","Germany"),(2018,"🇫🇷","France"),
    (2022,"🇦🇷","Argentina"),
]

_WC_LEGENDS_COMPACT = [
    ("🌟","Pelé",          "🇧🇷","Brazil",    "Won 3 World Cups. Many consider him the greatest player ever. He scored 77 goals for Brazil and was just 17 when he won his first title."),
    ("🤌","Maradona",      "🇦🇷","Argentina", "Led Argentina to glory in 1986. Famous for the 'Goal of the Century' — dribbling past 5 defenders to score in the World Cup quarterfinal."),
    ("🐐","Lionel Messi",  "🇦🇷","Argentina", "Won the 2022 World Cup at age 35 after a 16-year wait. Many say he's the greatest player who ever lived."),
    ("🕺","Zidane",        "🇫🇷","France",    "Scored two headers in the 1998 World Cup Final. Was voted the best player of the 1990s and 2000s."),
    ("👽","Ronaldo (R9)",  "🇧🇷","Brazil",    "The original Ronaldo — 'The Phenomenon.' Scored 15 World Cup goals and won the trophy twice (1994 and 2002)."),
    ("⚡","Mbappé",        "🇫🇷","France",    "Won the World Cup at age 19. Scored a hat-trick in the 2022 final. The fastest player in international soccer."),
]

_WC_MOMENTS_COMPACT = [
    ("1950","😱","The Maracanazo",         "200,000 Brazilian fans expected their team to win. Uruguay scored late to win 2–1. Brazil fans stood in silence. Still called the greatest upset in World Cup history."),
    ("1986","🤌","The Goal of the Century","Maradona dribbled from midfield past five defenders and the goalkeeper in 11 seconds. Voted the greatest goal in World Cup history — in the same match as the Hand of God."),
    ("1994","💔","Baggio's Penalty",       "Italy's greatest player stepped up for the final penalty in the shootout. He blazed it over the bar. Brazil won. Baggio stood alone with his head bowed."),
    ("2014","🇩🇪","The 7–1",              "Germany scored five goals in 18 minutes against Brazil in Brazil. Brazilian fans wept. The host nation was humiliated at home. Germany went on to win the trophy."),
    ("2022","🐐","Messi's Moment",         "Argentina and France played possibly the greatest final ever — 3–3 after extra time. Mbappé scored a hat-trick. Messi scored twice. Argentina won on penalties. The whole world exhaled."),
]


# ── Core helpers ──────────────────────────────────────────────────────────────
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

def _parse_pipe(val) -> list[str]:
    if not val or pd.isna(val): return []
    return [s.strip() for s in str(val).split('|') if s.strip()]

def _safe(val, default="—"):
    if val is None or (isinstance(val, float) and pd.isna(val)): return default
    return val

def _parse_pop_m(pop_str: str) -> float | None:
    s = str(pop_str).lower().replace(',', '')
    try:
        if 'billion' in s: return float(s.split('billion')[0].split()[-1]) * 1000
        if 'million' in s: return float(s.split('million')[0].split()[-1])
        if 'thousand' in s: return float(s.split('thousand')[0].split()[-1]) / 1000
    except Exception: pass
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
    if any(w in lo for w in ["food","taco","sushi","pizza","cuisine","eat"]):
        return f"The food in {country} is absolutely delicious — kids who try it always want more!"
    if any(w in lo for w in ["pyramid","temple","castle","ancient","ruins","wonder"]):
        return f"Imagine standing next to something built thousands of years ago! {country} has real ancient wonders."
    if any(w in lo for w in ["cat","jaguar","lion","tiger","leopard","puma"]):
        return f"Big cats are the most powerful hunters on Earth — and {country} has amazing ones!"
    if any(w in lo for w in ["bird","eagle","flamingo","parrot","toucan"]):
        return f"The birds of {country} are stunning — some have colors brighter than a rainbow!"
    if any(w in lo for w in ["soccer","football","futbol","sport","team"]):
        return f"Soccer is religion in {country} — the passion and energy at their matches is unreal!"
    if any(w in lo for w in ["music","dance","samba","flamenco","tango"]):
        return f"The music and dance of {country} is so energetic you can't help but want to move!"
    if any(w in lo for w in ["beach","ocean","island","sea","surf"]):
        return f"The beaches of {country} are world-famous — crystal blue water and amazing waves!"
    if any(w in lo for w in ["mountain","volcano","hiking","alps","andes"]):
        return f"The mountains of {country} are jaw-dropping — some are so tall they have snow year-round!"
    if any(w in lo for w in ["game","nintendo","anime","manga","pokemon"]):
        return f"Some of your favorite games and cartoons come from {country}. It's the coolest!"
    if any(w in lo for w in ["animal","wildlife","safari","nature","jungle"]):
        return f"The wildlife in {country} is like stepping into a nature documentary!"
    if any(w in lo for w in ["underdog","surprise","qualify","first time","debut"]):
        return f"{country} worked so hard to get here — everyone loves a great underdog story!"
    return f"This is one of the coolest things that makes {country} truly special!"


@st.cache_data(ttl=86400)
def _country_map(iso3: str):
    fig = go.Figure(go.Choropleth(
        locations=[iso3], z=[1], locationmode='ISO-3',
        colorscale=[[0,'#2563EB'],[1,'#2563EB']],
        showscale=False, marker_line_color='white', marker_line_width=0.8,
    ))
    fig.update_layout(
        geo=dict(showframe=False, showcoastlines=True, coastlinecolor='#94A3B8',
                 showland=True, landcolor='#E2E8F0', showocean=True, oceancolor='#DBEAFE',
                 projection_type='natural earth'),
        margin=dict(l=0,r=0,t=0,b=0), height=320,
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def _country_zoom_map(iso3: str):
    """Zoomed-in map of the country with rivers, lakes, and country borders."""
    fig = go.Figure(go.Choropleth(
        locations=[iso3], z=[1], locationmode='ISO-3',
        colorscale=[[0,'#3B82F6'],[1,'#60A5FA']],
        showscale=False,
        marker_line_color='white', marker_line_width=1.5,
    ))
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,  coastlinecolor='#475569',
            showland=True,        landcolor='#D1FAE5',
            showocean=True,       oceancolor='#BFDBFE',
            showcountries=True,   countrycolor='rgba(148,163,184,.5)',
            showlakes=True,       lakecolor='#93C5FD',
            showrivers=True,      rivercolor='#93C5FD',
            fitbounds='locations',
            resolution=50,
        ),
        margin=dict(l=0,r=0,t=0,b=0), height=320,
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
    if roster_df is None or roster_df.empty: return ""
    W, H = 420, 560
    ROW_Y = {"fwd": 105, "mid": 225, "def": 360, "gk": 465}

    gks  = roster_df[roster_df["position"]=="Goalkeeper"].sort_values("shirt_number").to_dict("records")
    defs = roster_df[roster_df["position"]=="Defender"].sort_values("shirt_number").to_dict("records")
    mids = roster_df[roster_df["position"]=="Midfielder"].sort_values("shirt_number").to_dict("records")
    fwds = roster_df[roster_df["position"]=="Forward"].sort_values("shirt_number").to_dict("records")

    cap_num = None
    if captain_name:
        cap_last = captain_name.split()[-1].lower() if captain_name.split() else ""
        for row in roster_df.to_dict("records"):
            if cap_last and cap_last in str(row["player_name"]).lower():
                cap_num = int(row["shirt_number"]); break

    def _cap_first(group, n):
        if not group: return []
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
        while len(grp) < n and spare: grp.append(spare.pop(0))
        return grp

    gk_xi  = _fill(gk_xi, 1)
    def_xi = _fill(def_xi, 4)
    mid_xi = _fill(mid_xi, 3)
    fwd_xi = _fill(fwd_xi, 3)

    def _xs(n):
        if n == 0: return []
        if n == 1: return [W // 2]
        m = 48
        return [round(m + i * (W - 2*m) / (n-1)) for i in range(n)]

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

    JERSEY = (
        "M -15,-15 L -22,-8 Q -20,-6 -17,-5 L -17,17 L 17,17 L 17,-5 Q 20,-6 22,-8 "
        "L 15,-15 C 8,-21 -8,-21 -15,-15 Z M -5,-17 A 5,3 0 0 1 5,-17 A 5,3 0 0 1 -5,-17 Z"
    )

    def _draw_row(players, y, _):
        xs = _xs(len(players))
        for i, pl in enumerate(players):
            px    = xs[i]
            snum  = str(int(pl["shirt_number"]))
            lname = _last(pl["player_name"])
            is_cap = cap_num is not None and int(pl["shirt_number"]) == cap_num
            stroke = "#FCD34D" if is_cap else "rgba(255,255,255,0.55)"
            sw = "2.5" if is_cap else "1.5"
            p.append(f"<g transform='translate({px},{y})'>")
            p.append(f"<path d='{JERSEY}' fill='#1D4ED8' stroke='{stroke}' stroke-width='{sw}' stroke-linejoin='round' fill-rule='evenodd' opacity='0.93'/>")
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
def _passport_widget_html(country, stamp, disc_df, cheered, won, picks_per, points_per) -> str:
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
        f"</div></div>"
    )


# ── Position group cards ──────────────────────────────────────────────────────
def _position_group_html(players: list, icon: str, pos_label: str) -> str:
    if not players: return ""
    cards = ""
    for pl in players:
        snum  = str(int(pl.get("shirt_number", 0)))
        name  = str(pl.get("player_name", ""))
        club  = str(pl.get("club_short", pl.get("club", "")))
        age_v = pl.get("age", 0)
        try:    age = int(float(age_v)) if age_v else 0
        except: age = 0
        age_str = f" · Age {age}" if age else ""
        cards += (
            f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
            f"border-radius:9px;padding:.42rem .55rem;"
            f"border:1px solid rgba(148,163,184,.1)'>"
            f"<div style='font-size:.88rem;font-weight:900;color:#FCD34D;line-height:1'>#{snum}</div>"
            f"<div style='font-size:.76rem;font-weight:800;color:#F1F5F9;line-height:1.25;margin:.04rem 0;"
            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>{name}</div>"
            f"<div style='font-size:.64rem;color:#64748B;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>"
            f"{club}{age_str}</div></div>"
        )
    return (
        f"<div style='margin:.5rem 0 .9rem'>"
        f"<div style='font-size:.74rem;font-weight:800;color:#64748B;text-transform:uppercase;"
        f"letter-spacing:.06em;margin-bottom:.32rem'>{icon} {pos_label}s ({len(players)})</div>"
        f"<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:.28rem'>"
        f"{cards}</div></div>"
    )


def _story_role(raw_role: str, position: str) -> tuple[str, str]:
    r = raw_role.lower()
    if "captain" in r:                    return "⭐", "Team Captain"
    if "young" in r:                      return "🌱", "Rising Star"
    if "mls" in r or "u.s." in r:         return "🇺🇸", "MLS & US"
    if "old" in r or "veteran" in r:      return "🎖️", "Veteran"
    pos = position.lower()
    if "forward" in pos:                  return "🎯", "Goal Scorer"
    if "midfielder" in pos:               return "🎩", "Playmaker"
    if "defender" in pos:                 return "🧱", "Defender"
    if "goalkeeper" in pos:               return "🥅", "Goalkeeper"
    return "⚡", "Key Player"

def _player_story(role_label: str, name: str, age: int, club: str) -> str:
    first = name.split()[0] if name else name
    if role_label == "Team Captain":
        return f"Wears the armband and leads on the field — every player looks to {first} when things get tough."
    if role_label == "Rising Star":
        return f"At just {age}, {first} is already playing at the highest level. Could be the breakout star of this tournament!"
    if role_label == "MLS & US":
        return f"Plays in America — you might have seen them on TV! Brings a special connection to the host country."
    if role_label == "Goal Scorer":
        return f"Put {first} in front of goal and something exciting is about to happen. The team's most dangerous attacker."
    if role_label == "Playmaker":
        return f"{first} is the conductor — decides the tempo, finds the passes, unlocks defenses."
    if role_label == "Defender":
        return f"{first} is the wall opponents have to break through — strong, smart, and nearly impossible to beat."
    if role_label == "Goalkeeper":
        return f"The last line of defense — {first} can save a match with a single leap."
    if role_label == "Veteran":
        return f"At {age}, {first} has seen it all. Experience is everything in knockout football."
    return f"{first} is one of the key players to watch whenever they take the field."


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR & DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════
teams_df = get_all_teams()
_nav_country = st.session_state.pop("_nav_country", None)

with st.sidebar:
    st.markdown("### 🌍 Explore Countries")
    all_countries = sorted(teams_df["name"].tolist())
    default_idx   = all_countries.index(_nav_country) if _nav_country and _nav_country in all_countries else 0
    selected_country = st.selectbox("Country", all_countries, index=default_idx)

active_user_id = st.session_state.get("active_user_id", 1)
log_discovery(active_user_id, selected_country)

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

disc_df    = get_discoveries(active_user_id)
cheered    = get_cheered_for(active_user_id)
won        = get_won_with(active_user_id)
picks_per  = get_picks_per_country(active_user_id)
points_per = get_points_per_country(active_user_id)

roster       = get_team_roster(selected_country)
summary      = get_team_summary(selected_country)
captain_name = _safe(team.get("captain"), "")
by_pos       = get_roster_by_position(selected_country)
featured     = get_featured_players(selected_country, captain_name)
mls_players  = get_mls_players(selected_country)

animals   = _parse_pipe(team.get("animals"))
foods     = _parse_pipe(team.get("foods"))
landmarks = _parse_pipe(team.get("landmarks"))
reasons   = _parse_pipe(team.get("cheer_reasons"))
flag_fact = stamp.get("flag_fact", "")
neighbors = details.get("neighbors", [])

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 & 2: HERO BANNER
# ══════════════════════════════════════════════════════════════════════════════
hero_html = get_country_image_html(selected_country, height="250px")
has_hero  = hero_html is not None
if has_hero:
    st.markdown(hero_html, unsafe_allow_html=True)

flag_size     = "4rem" if has_hero else "6.5rem"
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

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: PASSPORT STAMP WIDGET
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    _passport_widget_html(selected_country, stamp, disc_df, cheered, won, picks_per, points_per),
    unsafe_allow_html=True
)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: MEET THIS COUNTRY IN 60 SECONDS
# ══════════════════════════════════════════════════════════════════════════════
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
    ld, _ = _card_info("landmark", ll, selected_country)
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

# Continent + distance + timezone inline (shown right below 60 Seconds)
dist_miles = details.get("distance_miles", 0)
tz_offset  = details.get("timezone_offset", 0)
_loc_parts = [f"🌍 **{stamp['continent']}**"]
if dist_miles and dist_miles > 50:
    _loc_parts.append(f"✈️ **{dist_miles:,} miles** from Seattle")
elif dist_miles and dist_miles <= 50:
    _loc_parts.append("🏠 **Right next door** to Seattle")
if tz_offset == 0:
    _loc_parts.append("🕐 **Same time zone** as Seattle")
elif tz_offset > 0:
    _loc_parts.append(f"🕐 **+{tz_offset}h ahead** of Seattle")
else:
    _loc_parts.append(f"🕐 **{tz_offset}h behind** Seattle")
st.markdown("  ·  ".join(_loc_parts))

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5: WHERE IS THIS COUNTRY?
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🗺️ Where Is This Country?")

if iso3:
    try:
        st.plotly_chart(_country_map(iso3), use_container_width=True, config={"staticPlot": True})
    except Exception:
        st.info(f"📍 {selected_country} is located in {stamp['continent']}.")
else:
    st.info(f"📍 {selected_country} is located in {stamp['continent']}.")

if neighbors:
    neighbor_pills = "".join(
        f"<span style='background:rgba(37,99,235,.18);color:#93C5FD;"
        f"border:1px solid rgba(37,99,235,.35);border-radius:20px;"
        f"padding:.2rem .65rem;font-size:.8rem;margin:.15rem;display:inline-block'>"
        f"{get_flag(n)} {n}</span>"
        for n in neighbors
    )
    st.markdown(
        f"<div style='margin-top:.4rem'>"
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

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6: WHY KIDS MIGHT CHEER FOR THIS COUNTRY
# ══════════════════════════════════════════════════════════════════════════════
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
# SECTION 7: WHAT DOES THIS PLACE ACTUALLY LOOK LIKE?
# ══════════════════════════════════════════════════════════════════════════════
_land = _LANDSCAPE.get(selected_country)
_land_emoji    = _land[0] if _land else "🌍"
_land_headline = _land[1] if _land else f"The Landscapes of {selected_country}"
_land_tags     = _land[2] if _land else []
_land_desc     = _land[3] if _land else fun if fun else f"{selected_country} is a country in {stamp['continent']} with remarkable natural landscapes."

st.markdown("### 🌄 What Does This Place Actually Look Like?")
_tag_pills = "".join(
    f"<span style='background:rgba(34,197,94,.12);color:#4ADE80;border:1px solid rgba(34,197,94,.3);"
    f"border-radius:14px;padding:.18rem .6rem;font-size:.76rem;font-weight:700;margin:.12rem;display:inline-block'>{t}</span>"
    for t in _land_tags
)
st.markdown(
    f"<div style='background:linear-gradient(135deg,rgba(15,23,42,.95),rgba(30,41,59,.9));"
    f"border:1px solid rgba(148,163,184,.15);border-radius:16px;padding:1.1rem 1.3rem;margin:.2rem 0 .8rem'>"
    f"<div style='display:flex;align-items:center;gap:.9rem;margin-bottom:.6rem'>"
    f"<span style='font-size:2.8rem;line-height:1'>{_land_emoji}</span>"
    f"<div>"
    f"<div style='font-size:1.15rem;font-weight:900;color:#F1F5F9'>{_land_headline}</div>"
    f"<div style='margin-top:.25rem'>{_tag_pills}</div>"
    f"</div></div>"
    f"<div style='font-size:.94rem;color:#CBD5E1;line-height:1.65'>{_land_desc}</div>"
    f"</div>",
    unsafe_allow_html=True
)
if iso3:
    try:
        st.plotly_chart(_country_zoom_map(iso3), use_container_width=True, config={"staticPlot": True})
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8: COUNTRY FACTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🌍 Country Facts")
row1 = st.columns(3)
row2 = st.columns(3)
facts = [
    ("🏙️", "Capital",    _safe(team.get("capital"))),
    ("👥", "Population", _safe(team.get("population"))),
    ("🗣️", "Languages",  _safe(team.get("languages"))),
    ("💰", "Currency",   _safe(team.get("currency"))),
    ("🌍", "Continent",  stamp["continent"]),
    ("🏛️", "Government", _GOVT_TYPE.get(selected_country, "—")),
]
for col, (icon, label, val) in zip(list(row1) + list(row2), facts):
    col.markdown(_stat_card(icon, label, val), unsafe_allow_html=True)

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

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9: ANIMALS & NATURE
# ══════════════════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10: FAMOUS FOODS
# ══════════════════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11: FAMOUS LANDMARKS
# ══════════════════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12: COMPARE TO SEATTLE
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🏡 Compare To Seattle")
pop_m       = _parse_pop_m(team.get("population", ""))
seattle_pop = 4.0

compare_cards = []
if dist_miles and dist_miles > 50:
    compare_cards.append(("✈️", "Distance", f"{dist_miles:,} miles",
                           f"About {dist_miles // 500} long road trips away!"))
elif dist_miles and dist_miles <= 50:
    compare_cards.append(("🏠", "Distance", "Right next door!", "You could almost drive there."))

if tz_offset == 0:
    tz_label, tz_note = "Same time!", "When it's 3 PM here, it's 3 PM there too."
elif tz_offset > 0:
    hour = 9 + int(tz_offset)
    ampm = "AM" if hour < 12 else "PM"
    tz_label = f"+{tz_offset}h ahead"
    tz_note  = f"When it's 9 AM in Seattle, it's {hour}{ampm} there."
else:
    tz_label = f"{tz_offset}h behind"
    tz_note  = f"When it's 9 AM here, it's {9 + int(tz_offset)} AM there."
compare_cards.append(("🕐", "Time Zone", tz_label, tz_note))

if pop_m:
    sea_ratio = pop_m / seattle_pop
    if pop_m >= 1000:     pop_display = f"{pop_m/1000:.1f} billion"
    elif pop_m >= 1:      pop_display = f"{pop_m:.0f} million"
    else:                 pop_display = f"{pop_m*1000:.0f} thousand"
    if sea_ratio >= 10:   pop_note = f"{int(sea_ratio)}× more people than the Seattle metro area!"
    elif sea_ratio >= 2:  pop_note = f"About {sea_ratio:.1f}× as many people as the Seattle area."
    elif sea_ratio >= 0.5: pop_note = "Similar number of people to the Seattle area."
    else:                 pop_note = "Smaller population than the Seattle metro area!"
    compare_cards.append(("👥", "Population", pop_display, pop_note))

lang = _safe(team.get("languages"), "")
if lang and lang != "—":
    if "English" in lang:
        compare_cards.append(("🗣️", "Language", lang, "They speak English too — just like Seattle!"))
    else:
        first_lang = lang.split(",")[0].strip()
        compare_cards.append(("🗣️", "Language", first_lang, f"People say hello in {first_lang}!"))

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


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13: SOCCER IN [COUNTRY]
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown(f"## ⚽ Soccer in {selected_country}")

nickname = details.get("nickname", "")
if nickname and nickname not in ("—", ""):
    st.markdown(
        f"<div style='color:#94A3B8;font-size:.88rem;margin:-.4rem 0 .8rem'>"
        f"Also known as: <b style='color:#FCD34D'>{nickname}</b></div>",
        unsafe_allow_html=True
    )

_intro_text = _SOCCER_INTRO.get(selected_country)
if not _intro_text:
    _appearances = _safe(team.get("wc_appearances"), "several")
    _best        = _safe(team.get("best_finish"), "the group stage")
    _confed      = _safe(team.get("confederation"), "")
    _nick_part   = f"known as {nickname}, " if nickname and nickname not in ("—","") else ""
    _intro_text  = (
        f"Soccer is the heart of {selected_country}'s sporting culture. "
        f"The national team — {_nick_part}competing in {_confed} — has appeared at the World Cup {_appearances} times. "
        f"Their best finish has been {_best}. "
        f"In 2026 they bring a passionate squad ready to make their mark on the world stage."
    )

st.markdown(
    f"<div style='background:linear-gradient(135deg,rgba(29,78,216,.12),rgba(29,78,216,.05));"
    f"border:1px solid rgba(29,78,216,.25);border-radius:14px;"
    f"padding:.9rem 1.1rem;margin:.2rem 0 1rem;font-size:.97rem;color:#CBD5E1;line-height:1.7'>"
    f"{_intro_text}</div>",
    unsafe_allow_html=True
)

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14: SOCCER TEAM
# ══════════════════════════════════════════════════════════════════════════════
famous_player = details.get("famous_player", _safe(team.get("captain"), "—"))
home_stadium  = details.get("home_stadium", "—")

st.markdown("### 📊 Team Snapshot")
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

# Group Stage Matches — pills in a row, above the formation
matches = get_matches_by_team(selected_country)
if not matches.empty:
    st.markdown("### 📅 Group Stage Matches")
    _m_cols = st.columns(len(matches))
    for col, (_, m) in zip(_m_cols, matches.iterrows()):
        opp      = m["away_team"] if m["home_team"] == selected_country else m["home_team"]
        opp_flag = get_flag(opp)
        mid      = int(m["id"])
        _mdate   = fmt_date(m["match_date"]) if hasattr(m, 'match_date') else str(m.get("match_date",""))
        _mkick   = str(m.get("kickoff_time_et",""))[:5]
        if m["status"] == "completed":
            hs, as_ = int(m["home_score"]), int(m["away_score"])
            _is_home = m["home_team"] == selected_country
            _my_score  = hs if _is_home else as_
            _opp_score = as_ if _is_home else hs
            if _my_score > _opp_score:
                _pill_bg, _score_color, _result_label = "#052e16", "#4ADE80", "W"
            elif _my_score == _opp_score:
                _pill_bg, _score_color, _result_label = "#1c1917", "#FCD34D", "D"
            else:
                _pill_bg, _score_color, _result_label = "#450a0a", "#F87171", "L"
            _score_html = (
                f"<div style='font-size:1.3rem;font-weight:900;color:{_score_color};line-height:1'>"
                f"{_my_score}–{_opp_score}</div>"
                f"<div style='font-size:.65rem;font-weight:800;color:{_score_color}'>{_result_label}</div>"
            )
            _time_html = f"<div style='font-size:.65rem;color:#64748B;margin-top:.1rem'>Final</div>"
        else:
            _pill_bg    = "#0f172a"
            _score_html = f"<div style='font-size:.78rem;font-weight:800;color:#FCD34D'>{_mkick} ET</div>"
            _time_html  = f"<div style='font-size:.65rem;color:#64748B;margin-top:.1rem'>{_mdate}</div>"
        with col:
            st.markdown(
                f"<div style='background:{_pill_bg};border:1px solid rgba(148,163,184,.15);"
                f"border-radius:14px;padding:.75rem .5rem;text-align:center'>"
                f"<div style='font-size:1.6rem;line-height:1;margin-bottom:.15rem'>{opp_flag}</div>"
                f"<div style='font-size:.72rem;font-weight:800;color:#F1F5F9;line-height:1.2;margin-bottom:.25rem'>"
                f"vs {opp}</div>"
                f"{_score_html}{_time_html}"
                f"</div>",
                unsafe_allow_html=True
            )
            if st.button("🏟️ Matchup", key=f"match_link_{mid}", use_container_width=True):
                st.session_state["_nav_match_id"] = mid
                st.switch_page("pages/matchup.py")

# Formation
if not roster.empty:
    st.markdown("### 🟩 Predicted Starting XI")
    _, _fc, _ = st.columns([1, 2, 1])
    with _fc:
        st.markdown(_formation_svg(roster, captain_name), unsafe_allow_html=True)

# Players To Know (story-driven)
if featured:
    st.markdown("### ⭐ Players To Know")
    n_feat = min(len(featured), 5)
    p_cols = st.columns(n_feat)
    for col, pl in zip(p_cols, featured[:n_feat]):
        role_emoji, role_label = _story_role(pl["role"], pl.get("position",""))
        blurb = _player_story(role_label, pl["name"], pl.get("age", 0), pl.get("club_short",""))
        with col:
            st.markdown(
                "<div style='background:linear-gradient(160deg,#1E293B,#0F172A);border-radius:12px;"
                "padding:.85rem .7rem;text-align:center;color:white;border:1px solid rgba(148,163,184,.15)'>"
                f"<div style='font-size:1.4rem;line-height:1'>{role_emoji}</div>"
                f"<div style='font-size:.62rem;color:#94A3B8;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:.04em;margin:.1rem 0'>{role_label}</div>"
                f"<div style='font-size:1.8rem;font-weight:900;color:#FCD34D;line-height:1.2'>#{pl['shirt_number']}</div>"
                f"<div style='font-size:.86rem;font-weight:800;line-height:1.25;margin:.1rem 0'>{pl['name']}</div>"
                f"<div style='font-size:.73rem;color:#94A3B8'>{pl['position']}</div>"
                f"<div style='font-size:.69rem;color:#64748B;margin:.1rem 0'>{pl['club_short']} · Age {pl['age']}</div>"
                f"<div style='font-size:.66rem;color:#475569;margin-top:.3rem;line-height:1.35;"
                f"border-top:1px solid rgba(148,163,184,.1);padding-top:.25rem'>{blurb}</div>"
                "</div>",
                unsafe_allow_html=True
            )

# MLS & US Connections
if not mls_players.empty:
    st.markdown("### 🏟️ MLS & US Connections")
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

# Full Squad
if not roster.empty:
    st.markdown("#### 📋 Full Squad")
    for _pos in ["Goalkeeper", "Defender", "Midfielder", "Forward"]:
        _pos_df = by_pos.get(_pos)
        if _pos_df is None or _pos_df.empty: continue
        _icon    = pos_icon(_pos)
        _players = _pos_df.to_dict("records")
        st.markdown(_position_group_html(_players, _icon, _pos), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 15: THIS COUNTRY'S WORLD CUP STORY
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown(f"## 🏆 {selected_country} at the World Cup")

_country_moments = _WC_COUNTRY_STORY.get(selected_country, [])
if _country_moments:
    st.caption(f"{selected_country}'s journey through the World Cup — the key moments.")
    for yr, headline, story in _country_moments:
        st.markdown(
            f"<div style='border-left:3px solid #2563EB;padding:.6rem .9rem;margin:.5rem 0;"
            f"background:rgba(37,99,235,.08);border-radius:0 10px 10px 0'>"
            f"<div style='display:flex;align-items:center;gap:.6rem;margin-bottom:.2rem'>"
            f"<span style='background:#2563EB;color:white;border-radius:6px;"
            f"padding:.08rem .45rem;font-size:.76rem;font-weight:800'>{yr}</span>"
            f"<span style='font-weight:800;color:#F1F5F9;font-size:.95rem'>{headline}</span>"
            f"</div>"
            f"<div style='font-size:.88rem;color:#CBD5E1;line-height:1.55'>{story}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
else:
    _apps = _safe(team.get("wc_appearances"), "")
    _best = _safe(team.get("best_finish"), "")
    if _apps and _apps != "—":
        st.markdown(
            f"<div style='background:rgba(30,41,59,.8);border:1px solid rgba(255,255,255,.1);"
            f"border-radius:12px;padding:1rem 1.1rem;margin:.3rem 0'>"
            f"<div style='font-size:2rem;margin-bottom:.4rem'>{flag}</div>"
            f"<div style='font-weight:800;font-size:1rem;color:#F1F5F9;margin-bottom:.3rem'>"
            f"{selected_country} at the World Cup</div>"
            f"<div style='font-size:.9rem;color:#CBD5E1;line-height:1.6'>"
            f"{selected_country} has appeared at the World Cup <b>{_apps}</b> time{'s' if _apps not in ('1','one') else ''}."
            f" Their best finish has been <b>{_best}</b>."
            f" In 2026, they arrive ready to write new chapters in their World Cup story."
            f"</div></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.3);"
            f"border-radius:12px;padding:1rem 1.1rem;margin:.3rem 0'>"
            f"<div style='font-size:2rem;margin-bottom:.4rem'>✨</div>"
            f"<div style='font-weight:800;font-size:1rem;color:#FCD34D;margin-bottom:.3rem'>"
            f"Making History in 2026</div>"
            f"<div style='font-size:.9rem;color:#CBD5E1;line-height:1.6'>"
            f"{selected_country} is competing at the World Cup in 2026. "
            f"Every great World Cup story had to start somewhere — this could be the beginning of something special."
            f"</div></div>",
            unsafe_allow_html=True
        )

if st.button("📖 See full World Cup History", key="btn_wch_moments"):
    st.switch_page("pages/world_cup_history.py")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 16: EXPLORE NEARBY COUNTRIES
# ══════════════════════════════════════════════════════════════════════════════
_wc_set = set(all_countries)
_disc_names = set(disc_df["country_name"].tolist()) if not disc_df.empty and "country_name" in disc_df.columns else set()

# Show neighbors that are in this year's World Cup first, then others
_nb_wc    = [n for n in neighbors if n in _wc_set]
_nb_other = [n for n in neighbors if n not in _wc_set]
_nb_show  = (_nb_wc + _nb_other)[:6]

if _nb_show:
    st.divider()
    st.markdown("### 🧭 Explore Nearby Countries")
    st.caption("One country always leads to another — tap any neighbor to keep exploring.")

    nb_cols = st.columns(min(len(_nb_show), 3))
    for col, nb in zip(nb_cols * 2, _nb_show):
        nb_flag   = get_flag(nb)
        nb_teaser = _COUNTRY_TEASER.get(nb, f"An interesting neighbor of {selected_country}.")
        in_wc     = nb in _wc_set

        if nb in won:
            nb_state_badge = "🏆 Won With"
            nb_state_color = "#FCD34D"
        elif nb in cheered:
            nb_state_badge = "⚽ Cheering"
            nb_state_color = "#4ADE80"
        elif nb in _disc_names:
            nb_state_badge = "🌱 Discovered"
            nb_state_color = "#60A5FA"
        else:
            nb_state_badge = "🔍 Not Yet Visited"
            nb_state_color = "#475569"

        wc_pill = (
            f"<span style='background:rgba(29,78,216,.2);color:#93C5FD;"
            f"border:1px solid rgba(29,78,216,.3);border-radius:8px;"
            f"padding:.06rem .35rem;font-size:.67rem;font-weight:700'>2026 WC</span> "
        ) if in_wc else ""

        with col:
            st.markdown(
                f"<div style='background:linear-gradient(160deg,#1E293B,#0F172A);"
                f"border:1px solid rgba(148,163,184,.15);border-radius:14px;"
                f"padding:.8rem .9rem;margin:.3rem 0'>"
                f"<div style='display:flex;align-items:center;gap:.6rem;margin-bottom:.35rem'>"
                f"<span style='font-size:2rem;line-height:1'>{nb_flag}</span>"
                f"<div>"
                f"<div style='font-weight:900;font-size:.96rem;color:#F1F5F9'>{nb}</div>"
                f"<div style='font-size:.68rem;color:{nb_state_color};margin-top:.06rem'>{wc_pill}{nb_state_badge}</div>"
                f"</div></div>"
                f"<div style='font-size:.8rem;color:#94A3B8;line-height:1.45;margin-bottom:.5rem'>{nb_teaser}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            if in_wc and st.button(f"Explore {nb} →", key=f"nb_{nb}", use_container_width=True):
                st.session_state["_nav_country"] = nb
                st.rerun()
