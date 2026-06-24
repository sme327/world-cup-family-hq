"""
Retry downloading the 170 images that failed in the initial run.

Uses hand-curated alternative search queries tuned to what actually exists
on Wikimedia Commons. Reads missing_images.txt, looks up slugs in the
targets CSV, tries the curated queries, and saves to the correct paths.

Usage:
    python scripts/retry_missing_images.py
    python scripts/retry_missing_images.py --dry-run
    python scripts/retry_missing_images.py --limit 20
    python scripts/retry_missing_images.py --section foods
    python scripts/retry_missing_images.py --country czechia
"""

import argparse
import csv
import sys
import time
from pathlib import Path

# Reuse the shared download machinery from the original script
sys.path.insert(0, str(Path(__file__).parent))
from download_country_card_images import (
    try_download_one, BASE_DIR, IMG_BASE, TARGETS_CSV, SOURCES_CSV, MISSING_TXT,
    RATE_LIMIT_S, resize_and_save,
)

# ── Curated alternative queries ───────────────────────────────────────────────
# Key: "Country / section / Item Name" (must match missing_images.txt exactly)
# Value: list of search queries to try in order

_BETTER_QUERIES: dict[str, list[str]] = {

    # ── LANDMARKS ──────────────────────────────────────────────────────────────

    "Qatar / landmarks / Lusail Stadium": [
        "Lusail International Stadium Qatar",
        "Lusail Stadium exterior night",
        "Qatar 2022 World Cup stadium",
    ],
    "Brazil / landmarks / Christ the Redeemer": [
        "Christ the Redeemer statue Rio de Janeiro",
        "Cristo Redentor Rio statue",
        "Corcovado Rio de Janeiro",
    ],
    "Morocco / landmarks / Medina of Marrakech": [
        "Marrakech medina Djemaa el-Fna",
        "Marrakech old city souks Morocco",
        "Jemaa el-Fnaa square Marrakech",
    ],
    "Haiti / landmarks / Sans-Souci Palace": [
        "Sans-Souci Palace Haiti Milot ruins",
        "Citadelle Laferrière Haiti",
        "Haiti UNESCO heritage Milot",
    ],
    "Haiti / landmarks / Bassin-Bleu Waterfall": [
        "Bassin-Bleu waterfall Haiti turquoise",
        "Haiti waterfall Jacmel",
        "Haiti natural swimming pool waterfall",
    ],
    "Paraguay / landmarks / Pantanal Wetlands": [
        "Pantanal wetlands wildlife Paraguay",
        "Pantanal caiman sunset wetland",
        "Paraguay Gran Pantanal nature",
    ],
    "Curaçao / landmarks / Boca Tabla": [
        "Curaçao national park rocky coast waves",
        "Christoffelpark Curaçao coastline",
        "Curaçao rugged coastline natural pool",
    ],
    "Curaçao / landmarks / Klein Curaçao Island": [
        "Klein Curaçao island beach Caribbean",
        "Klein Curacao uninhabited island",
        "Curaçao small island turquoise water",
    ],
    "Ivory Coast / landmarks / Tai Forest": [
        "Taï National Park Ivory Coast forest",
        "Taï Forest Côte d'Ivoire chimpanzee",
        "West Africa tropical rainforest canopy",
    ],
    "Sweden / landmarks / IKEA birthplace (Älmhult)": [
        "Älmhult Sweden IKEA museum",
        "IKEA Museum Älmhult interior",
        "IKEA store Sweden",
    ],
    "Tunisia / landmarks / Sahara Desert": [
        "Sahara Desert Tunisia Douz dunes",
        "Tozeur Tunisia sand dunes Sahara",
        "Grand Erg Oriental Tunisia desert",
    ],
    "Spain / landmarks / La Tomatina festival": [
        "La Tomatina Buñol tomato festival Spain",
        "La Tomatina festival tomato fight Spain",
        "Buñol Spain festival tomatoes",
    ],
    "Saudi Arabia / landmarks / Al-Khobar Corniche": [
        "Al-Khobar Corniche waterfront Saudi Arabia",
        "Khobar seafront promenade Saudi",
        "Eastern Province Saudi Arabia waterfront",
    ],
    "Algeria / landmarks / Tassili n'Ajjer rock art": [
        "Tassili n'Ajjer prehistoric rock painting Algeria",
        "Tassili Najjer cave painting Sahara",
        "Algeria rock art ancient Sahara",
    ],
    "Portugal / landmarks / Jerónimos Monastery": [
        "Jerónimos Monastery Lisbon Belém",
        "Mosteiro dos Jerónimos Portugal",
        "Belém Tower Lisbon Portugal",
    ],
    "DR Congo / landmarks / Congo River": [
        "Congo River aerial Democratic Republic",
        "Congo River Kinshasa boat",
        "Congo River Africa wide",
    ],
    "Uzbekistan / landmarks / Silk Road markets": [
        "Chorsu Bazaar Tashkent Uzbekistan market",
        "Samarkand bazaar Silk Road market",
        "Uzbekistan traditional market spices",
    ],
    "Colombia / landmarks / Cocora Valley": [
        "Cocora Valley wax palm trees Colombia Quindío",
        "Valle del Cocora Colombia palms fog",
        "Quindío Colombia wax palm landscape",
    ],

    # ── ANIMALS ───────────────────────────────────────────────────────────────

    "Morocco / animals / Barbary Lion (extinct but symbol)": [
        "Barbary lion taxidermy museum specimen",
        "Atlas lion Panthera leo leo historical",
        "North African lion historic photograph",
    ],
    "Morocco / animals / Barbary Macaque": [
        "Barbary macaque Morocco ape",
        "Barbary ape Gibraltar Macaca sylvanus",
        "Barbary macaque Atlas Mountains Morocco",
    ],
    "Scotland / animals / Puffin": [
        "Atlantic puffin seabird Scotland cliffs",
        "puffin Fratercula arctica bird",
        "puffin colony British Isles",
    ],
    "Scotland / animals / Golden Eagle": [
        "golden eagle soaring raptor Scotland",
        "Aquila chrysaetos golden eagle flight",
        "golden eagle Highland Scotland",
    ],
    "USA / animals / Florida Manatee": [
        "West Indian manatee Florida underwater",
        "manatee Trichechus manatus seacow",
        "Florida manatee springs Crystal River",
    ],
    "USA / animals / Gray Wolf": [
        "gray wolf Canis lupus portrait",
        "grey wolf American wild",
        "Yellowstone wolf pack",
    ],
    "Türkiye / animals / Flamingo": [
        "flamingo flock Lake Tuz Turkey",
        "greater flamingo Phoenicopterus Turkey",
        "flamingo İzmir Turkey wetland",
    ],
    "Curaçao / animals / Sea Turtle": [
        "green sea turtle Caribbean reef",
        "Chelonia mydas sea turtle underwater",
        "sea turtle swimming tropical ocean",
    ],
    "Iran / animals / Asiatic Cheetah (critically endangered!)": [
        "Asiatic cheetah Acinonyx jubatus venaticus Iran",
        "Iranian cheetah rare endangered",
        "cheetah rare portrait closeup",
    ],
    "DR Congo / animals / Okapi (unicorn-like animal!)": [
        "okapi Okapia johnstoni Congo forest",
        "okapi zoo animal stripes",
        "okapi rare Congo giraffe relative",
    ],

    # ── FOODS ─────────────────────────────────────────────────────────────────

    "Czechia / foods / Trdelník (chimney cake)": [
        "trdelník chimney cake Prague street food",
        "spit cake chimney pastry sugar",
        "trdelnik coiled pastry Czech",
    ],
    "Bosnia and Herzegovina / foods / Bosanski Lonac (meat stew)": [
        "bosanski lonac Bosnian meat vegetable stew",
        "Bosnian traditional stew pot",
        "Balkan meat stew clay pot",
    ],
    "Qatar / foods / Machboos (spiced rice & meat)": [
        "machboos spiced rice meat Qatar",
        "kabsa Saudi Arabian rice dish chicken",
        "Middle Eastern spiced rice platter",
    ],
    "Qatar / foods / Harees": [
        "harees wheat porridge lamb dish",
        "Arab harees porridge Ramadan",
        "harees traditional Gulf food",
    ],
    "Qatar / foods / Luqaimat (sweet dumplings)": [
        "luqaimat sweet fried dumplings honey",
        "luqaimat Arabic dessert golden balls",
        "Middle Eastern sweet dumpling honey sesame",
    ],
    "Qatar / foods / Kabsa": [
        "kabsa Saudi rice spiced chicken platter",
        "kabsa Arabian rice dish lamb",
        "Saudi kabsa national dish",
    ],
    "Switzerland / foods / Fondue": [
        "cheese fondue pot Switzerland melted",
        "Swiss cheese fondue bread dipping",
        "fondue caquelon pot bubbling",
    ],
    "Switzerland / foods / Raclette": [
        "raclette melted cheese Switzerland",
        "raclette cheese plate potatoes Switzerland",
        "raclette Swiss alpine cheese dish",
    ],
    "Switzerland / foods / Swiss chocolate": [
        "Swiss milk chocolate bar Lindt",
        "Toblerone Swiss mountain chocolate",
        "Swiss chocolate Läderach praline",
    ],
    "Switzerland / foods / Rösti (potato cake)": [
        "rösti Swiss potato cake golden",
        "rosti fried potato pancake Switzerland",
        "Rösti traditional Swiss breakfast",
    ],
    "Haiti / foods / Akasan (corn porridge)": [
        "cornmeal porridge corn gruel breakfast",
        "Haitian corn drink porridge sweet",
        "corn starch drink porridge Caribbean",
    ],
    "Haiti / foods / Pikliz (spicy slaw)": [
        "pikliz Haitian spicy pickled coleslaw",
        "pikliz Haiti vinegar cabbage hot peppers",
        "Haitian condiment pickled slaw",
    ],
    "Haiti / foods / Joumou (pumpkin soup)": [
        "joumou Haitian pumpkin squash soup",
        "Haitian independence pumpkin soup",
        "joumou soup Haïti butternut",
    ],
    "Scotland / foods / Haggis": [
        "haggis traditional Scottish meal plated",
        "haggis neeps tatties Scotland",
        "Scottish haggis pudding served",
    ],
    "Scotland / foods / Fish and Chips": [
        "fish and chips British newspaper UK",
        "fish chips plate England takeaway",
        "fried fish battered chips British",
    ],
    "Scotland / foods / Shortbread": [
        "shortbread Scottish butter cookies biscuits",
        "Walker's shortbread tin Scotland",
        "Scottish shortbread fingers biscuits",
    ],
    "Scotland / foods / Cranachan (raspberry cream)": [
        "cranachan Scottish dessert raspberry cream oats",
        "cranachan glass layers whisky cream",
        "Scottish cranachan traditional pudding",
    ],
    "Paraguay / foods / Sopa Paraguaya (corn bread)": [
        "sopa paraguaya cornbread Paraguay",
        "Paraguayan corn bread dense cake",
        "Paraguay traditional cornbread slice",
    ],
    "Paraguay / foods / Bori-Bori (chicken soup)": [
        "vorí vorí Paraguayan chicken corn dumpling soup",
        "bori bori Paraguay soup dumplings",
        "Paraguayan traditional soup chicken balls",
    ],
    "Australia / foods / Meat Pie": [
        "Australian meat pie pastry",
        "meat pie Australia beef pastry individual",
        "Australian bakery meat pie",
    ],
    "Australia / foods / Tim Tams (chocolate biscuits)": [
        "Tim Tam chocolate biscuit Arnott's Australia",
        "Tim Tam biscuit pack chocolate",
        "Australian chocolate biscuit Tim Tam",
    ],
    "Australia / foods / Pavlova": [
        "pavlova meringue dessert cream strawberry",
        "pavlova Australian dessert kiwi cream",
        "pavlova white meringue topped fruit",
    ],
    "Australia / foods / Vegemite on toast": [
        "Vegemite toast Australian breakfast",
        "Vegemite jar spread toast brown",
        "Australian Vegemite bread",
    ],
    "Australia / foods / Lamingtons": [
        "lamington sponge cake coconut chocolate Australia",
        "lamingtons Australian cake coconut",
        "lamington dessert square coconut",
    ],
    "Türkiye / foods / Kebab": [
        "doner kebab Turkish spit meat rotating",
        "Turkish kebab plate Adana",
        "Iskender kebab Turkey plate",
    ],
    "Türkiye / foods / Baklava": [
        "baklava Turkish pastry honey nuts pistachio",
        "baklava sweet Turkish dessert layers",
        "baklava tray Gaziantep pistachio",
    ],
    "Türkiye / foods / Turkish Delight": [
        "Turkish delight lokum sweet cubes sugar",
        "lokum Turkish sweet rosewater pistachio",
        "Turkish delight rose flavored cubes",
    ],
    "Curaçao / foods / Stobá (goat stew)": [
        "Caribbean goat stew braised",
        "stoba Curaçao goat meat stew",
        "Caribbean slow braised goat meat",
    ],
    "Curaçao / foods / Keshi Yená (stuffed cheese)": [
        "keshi yena stuffed Edam cheese Curaçao",
        "Keshi Yena Antillean stuffed cheese",
        "Curaçao traditional cheese dish",
    ],
    "Curaçao / foods / Bolo Preto (black cake)": [
        "Caribbean black cake rum fruit dark",
        "black cake rum soaked Christmas Caribbean",
        "Antillean dark fruit cake",
    ],
    "Ivory Coast / foods / Attiéké (cassava couscous)": [
        "attiéké cassava couscous West Africa",
        "attieke fermented cassava granules Ivory Coast",
        "Ivorian cassava dish attiéké plate",
    ],
    "Ivory Coast / foods / Aloco (fried plantain)": [
        "aloco fried plantain West Africa",
        "fried ripe plantain aloco Ivory Coast",
        "West African fried plantain banana",
    ],
    "Ivory Coast / foods / Fufu": [
        "fufu cassava dough West Africa",
        "fufu ball soup pounded cassava",
        "African fufu traditional starchy food",
    ],
    "Ivory Coast / foods / Kedjenou (chicken stew)": [
        "kedjenou Ivorian chicken stew pot",
        "Ivory Coast traditional chicken stew slow",
        "kedjenou Côte d'Ivoire clay pot",
    ],
    "Ecuador / foods / Ceviche": [
        "ceviche shrimp lime Ecuador seafood",
        "Ecuadorian ceviche shrimp bowl",
        "ceviche marinated seafood citrus",
    ],
    "Ecuador / foods / Llapingachos (potato cakes)": [
        "llapingachos potato patties Ecuador cheese",
        "Ecuadorian potato cakes fried stuffed",
        "llapingachos Andean potato pancake",
    ],
    "Ecuador / foods / Fanesca (spring soup)": [
        "fanesca Ecuadorian Easter soup grains",
        "Ecuadorian fanesca cod vegetables soup",
        "fanesca traditional soup Ecuador Holy Week",
    ],
    "Ecuador / foods / Cuy (guinea pig)": [
        "cuy roasted guinea pig Peru Ecuador Andean",
        "cuy asado traditional Andean food",
        "roasted guinea pig Andean delicacy",
    ],
    "Sweden / foods / ABBA-themed candy": [
        "Swedish pick and mix candy store",
        "Swedish godis pick mix candy assorted",
        "Scandinavian candy sweets colorful",
    ],
    "Tunisia / foods / Lablabi (chickpea soup)": [
        "lablabi Tunisian chickpea soup harissa",
        "Tunisian chickpea stew lablabi bowl",
        "North African chickpea bread soup",
    ],
    "New Zealand / foods / Hangi (earth oven feast)": [
        "hangi Maori earth oven New Zealand",
        "hangi traditional Maori cooking underground",
        "New Zealand Maori earth oven food",
    ],
    "Cape Verde / foods / Cachupa (bean & corn stew)": [
        "cachupa Cape Verde bean corn stew",
        "Cape Verde national dish cachupa",
        "cachupa rich stew beans sausage",
    ],
    "Cape Verde / foods / Pastéis de bacalhau (fish cakes)": [
        "pasteis de bacalhau cod fish cakes fried",
        "codfish cakes Portuguese Cape Verde",
        "bacalhau fritters fried cod",
    ],
    "Cape Verde / foods / Catchupa rica": [
        "cachupa rica Cape Verde special stew",
        "Cape Verde cachupa rich festive version",
        "Cape Verde stew corn beans sausage eggs",
    ],
    "Cape Verde / foods / Grogue (sugarcane spirit)": [
        "grogue Cape Verde sugarcane spirit bottle",
        "Cape Verde sugarcane rum grogue",
        "cachaça sugarcane spirit rum bottle",
    ],
    "Saudi Arabia / foods / Mutabbaq (stuffed pancake)": [
        "mutabbaq stuffed pancake Saudi street food",
        "mutabaq filled pancake Middle East",
        "Saudi Arabia stuffed pancake fried",
    ],
    "Norway / foods / Rakfisk (fermented fish)": [
        "rakfisk fermented trout Norway traditional",
        "Norwegian rakfisk fish preserved",
        "rakfisk Norway sliced fermented trout",
    ],
    "Norway / foods / Kjøttkaker (meat cakes)": [
        "kjøttkaker Norwegian meatballs brown sauce",
        "Norwegian meat cakes kjøttkaker dinner",
        "Scandinavian meatballs gravy potato",
    ],
    "Iraq / foods / Masgûf (grilled carp)": [
        "masgouf Iraqi grilled carp Tigris",
        "masgouf Baghdad fish grill traditional",
        "Iraqi masgouf carp split grilled riverside",
    ],
    "Iraq / foods / Kubba (rice dumpling)": [
        "kibbeh kubba stuffed dumpling Iraq",
        "kubba Iraqi stuffed rice ball",
        "Iraqi kubba haleb fried dumpling",
    ],
    "Iraq / foods / Dolma (stuffed vegetables)": [
        "dolma stuffed grape vine leaves rice",
        "Iraqi dolma stuffed vegetables rice",
        "Middle Eastern dolma stuffed vine leaves",
    ],
    "Iraq / foods / Iraqi biryani": [
        "Iraqi biryani rice spiced dried fruit",
        "Iraq biryani rice lamb saffron",
        "Middle Eastern biryani rice dish",
    ],
    "Algeria / foods / Chakhchoukha (ripped bread stew)": [
        "chakhchoukha Algeria torn flatbread stew",
        "Algerian chakhchoukha marqa bread",
        "shakshouka bread stew North Africa",
    ],
    "Jordan / foods / Mansaf (lamb & yogurt sauce)": [
        "mansaf Jordanian lamb yogurt sauce rice",
        "mansaf traditional Jordanian feast",
        "Jordan mansaf national dish platter",
    ],
    "DR Congo / foods / Fufu & Moambe (palm nut sauce)": [
        "moambe palm nut sauce chicken Congo",
        "moambe African palm nut stew",
        "Congo moambe sauce traditional",
    ],
    "DR Congo / foods / Pondu (cassava leaf stew)": [
        "pondu cassava leaf stew Congo",
        "saka saka cassava leaves Congo food",
        "Congolese cassava leaf peanut stew",
    ],
    "DR Congo / foods / Makayabu (salted fish)": [
        "makayabu salted dried fish Congo",
        "stockfish saltfish Congo market",
        "dried salted fish African market",
    ],
    "DR Congo / foods / Liboke (banana leaf-wrapped fish)": [
        "liboke banana leaf wrapped fish Congo",
        "Congolese fish banana leaf steamed",
        "African fish cooked banana leaf parcel",
    ],
    "Uzbekistan / foods / Plov (rice pilaf)": [
        "plov Uzbek rice pilaf kazan",
        "Uzbekistan plov national dish rice",
        "Central Asian plov rice carrots lamb",
    ],
    "Uzbekistan / foods / Shashlik (grilled meat)": [
        "shashlik grilled meat skewer Central Asia",
        "Uzbek shashlik barbecue lamb",
        "skewered meat Uzbekistan grill",
    ],
    "Uzbekistan / foods / Samsa (pastry)": [
        "samsa baked pastry Uzbekistan triangular",
        "Uzbek samsa lamb pastry oven",
        "Central Asian samsa baked meat pastry",
    ],
    "Uzbekistan / foods / Lagman (noodle soup)": [
        "lagman pulled noodles soup Uzbekistan",
        "Uzbek lagman noodle broth vegetables",
        "Central Asian lagman hand-pulled noodles",
    ],
    "Uzbekistan / foods / Chuchvara (dumplings)": [
        "chuchvara Uzbek dumplings soup",
        "Uzbek chuchvara boiled dumplings broth",
        "Central Asian chuchvara dumpling",
    ],
    "Colombia / foods / Bandeja Paisa (rice & beans feast)": [
        "bandeja paisa Colombian platter rice beans",
        "bandeja paisa Antioquia Colombia full plate",
        "Colombian bandeja paisa traditional",
    ],
    "Colombia / foods / Arepas": [
        "arepas Colombian corn flatbread grilled",
        "arepa Colombia street food corn",
        "Colombian arepa stuffed cheese",
    ],
    "Colombia / foods / Sancocho (hearty stew)": [
        "sancocho Colombian chicken soup stew",
        "Sancocho Colombiano hearty stew yuca",
        "Colombian sancocho pot soup traditional",
    ],
    "Colombia / foods / Empanadas": [
        "empanadas fried Colombian pastry",
        "Colombian empanadas corn fried stuffed",
        "Latin American empanadas fried golden",
    ],
    "Colombia / foods / Ajiaco soup": [
        "ajiaco Colombian soup potato chicken",
        "Bogotá ajiaco soup traditional",
        "Colombian ajiaco cream potato soup",
    ],
    "England / foods / Fish and Chips": [
        "fish and chips newspaper England takeaway",
        "fish chips British traditional meal pub",
        "battered cod chips England",
    ],
    "England / foods / Sunday Roast": [
        "Sunday roast beef Yorkshire pudding England",
        "traditional Sunday roast dinner British",
        "roast dinner plate England beef",
    ],
    "Croatia / foods / Peka (slow-cooked meat)": [
        "peka Croatian bell cover slow roast lamb",
        "peka Croatia meat vegetables bell oven",
        "Croatian peka traditional dish",
    ],
    "Croatia / foods / Fritule (doughnuts)": [
        "fritule Croatian Christmas doughnuts",
        "fritule small Croatian fritters sugar",
        "Croatian fritule fried dough balls",
    ],
    "Ghana / foods / Jollof Rice (West Africa's greatest debate!)": [
        "jollof rice tomato stew Ghana",
        "Ghanaian jollof rice party",
        "West African jollof rice pot",
    ],

    # ── CHEER REASONS ─────────────────────────────────────────────────────────

    "Czechia / cheer_reasons / Václav Havel's homeland": [
        "Prague Charles Bridge Czech Republic historic",
        "Prague Castle Hradčany",
        "Prague Czech Republic old town square",
    ],
    "Canada / cheer_reasons / Alphonso Davies is a superstar": [
        "Alphonso Davies Bayern Munich footballer",
        "Alphonso Davies football dribbling",
        "Alphonso Davies Canada soccer",
    ],
    "Bosnia and Herzegovina / cheer_reasons / Ćevapi (best grilled meat ever!)": [
        "ćevapi Bosnian grilled sausage meat",
        "cevapi Balkan grilled sausage bread",
        "Bosnia ćevapi somun flatbread",
    ],
    "Bosnia and Herzegovina / cheer_reasons / History of resilience": [
        "Stari Most bridge Mostar Bosnia rebuilt",
        "Mostar bridge Bosnia Herzegovina",
        "Stari Most stone bridge Mostar river",
    ],
    "Qatar / cheer_reasons / Hosted the 2022 World Cup": [
        "Qatar 2022 FIFA World Cup opening ceremony",
        "Qatar World Cup 2022 stadium night",
        "FIFA World Cup 2022 Qatar",
    ],
    "Qatar / cheer_reasons / Pearl diving history": [
        "pearl diving Qatar traditional dhow",
        "Qatar pearl diver historical",
        "Persian Gulf pearl diving Arabia",
    ],
    "Switzerland / cheer_reasons / World's most famous knife": [
        "Swiss Army knife Victorinox red",
        "Swiss Army knife tools open blades",
        "Victorinox Swiss knife official",
    ],
    "Brazil / cheer_reasons / Rodney Dourado is amazing": [
        "Brazil national football team Seleção",
        "Vinicius Junior Brazil footballer",
        "Brazil football team yellow jersey",
    ],
    "Haiti / cheer_reasons / Amazing music (Kompa)": [
        "Haiti Carnival music celebration Port au Prince",
        "Haitian Carnival street celebration",
        "Haiti music festival street celebration",
    ],
    "Australia / cheer_reasons / Matildas are superstars": [
        "Sam Kerr Australia Matildas women football",
        "Matildas Australia women football team",
        "Australia women national football team",
    ],
    "Curaçao / cheer_reasons / Smallest country in World Cup history": [
        "Willemstad Curaçao colorful Dutch colonial houses",
        "Willemstad Punda Curaçao harbor colorful",
        "Curaçao Handelskade waterfront colorful",
    ],
    "Ivory Coast / cheer_reasons / Didier Drogba's homeland": [
        "Didier Drogba Chelsea footballer",
        "Didier Drogba Ivory Coast legend",
        "Drogba Ivory Coast football",
    ],
    "Netherlands / cheer_reasons / 3x World Cup finalists": [
        "Netherlands Holland orange football fans",
        "Dutch orange football crowd",
        "Netherlands football national team orange",
    ],
    "Sweden / cheer_reasons / Zlatan Ibrahimović legend": [
        "Zlatan Ibrahimovic Swedish footballer",
        "Zlatan Ibrahimović goal celebration",
        "Zlatan Ibrahimovic Sweden national team",
    ],
    "Tunisia / cheer_reasons / First African team to win a WC match": [
        "Tunisia football team celebrating",
        "Tunisia Eagles of Carthage football",
        "Tunisia national football team",
    ],
    "Belgium / cheer_reasons / Kevin De Bruyne is a genius": [
        "Kevin De Bruyne Manchester City Belgium",
        "Kevin De Bruyne football midfielder",
        "Kevin De Bruyne Belgium national team",
    ],
    "Belgium / cheer_reasons / 3 languages in one country": [
        "Brussels Belgium Grand Place architecture",
        "Brussels Grand Place square historic",
        "Brussels Atomium Belgian landmark",
    ],
    "Egypt / cheer_reasons / Pyramids of Giza": [
        "Great Pyramid Giza Egypt sphinx",
        "Pyramids Giza desert camel Egypt",
        "Giza Pyramid complex aerial",
    ],
    "Egypt / cheer_reasons / Nile River": [
        "Nile River felucca sailboat Egypt",
        "Nile River Egypt Aswan cruise",
        "Nile Egypt aerial river",
    ],
    "Egypt / cheer_reasons / Mohamed Salah (world's best?)": [
        "Mohamed Salah Liverpool footballer",
        "Mohamed Salah Egypt national team",
        "Salah Egypt Premier League",
    ],
    "Iran / cheer_reasons / Critically endangered Asiatic cheetah": [
        "Asiatic cheetah Iran rare endangered",
        "Iranian cheetah Acinonyx jubatus",
        "cheetah rare Iran wildlife",
    ],
    "Iran / cheer_reasons / Mehdi Taremi is dangerous": [
        "Mehdi Taremi Iran footballer striker",
        "Mehdi Taremi Inter Milan footballer",
        "Iran football national team",
    ],
    "Spain / cheer_reasons / Iberian Lynx (endangered beauty)": [
        "Iberian lynx Lynx pardinus Spain",
        "Iberian lynx Spain rare cat",
        "Lynx pardinus Spain nature reserve",
    ],
    "Cape Verde / cheer_reasons / Smallest team in Group H": [
        "Cape Verde islands beach landscape",
        "Sal Cape Verde beach tropical",
        "Cape Verde football team blue sharks",
    ],
    "Saudi Arabia / cheer_reasons / Saudi Pro League stars": [
        "King Fahd Stadium Riyadh Saudi Arabia football",
        "Saudi Pro League stadium crowd",
        "Mrsool Park stadium Riyadh Saudi",
    ],
    "Uruguay / cheer_reasons / Won the FIRST EVER World Cup": [
        "Estadio Centenario Uruguay Montevideo",
        "Uruguay 1930 World Cup historic Montevideo",
        "Centenario stadium Uruguay first World Cup",
    ],
    "Uruguay / cheer_reasons / Best BBQ in the world": [
        "asado Uruguay barbecue grilling meat",
        "Uruguayan asado beef grill fire",
        "South American asado beef grill",
    ],
    "Uruguay / cheer_reasons / Only 3.5 million people but 2x champions": [
        "Montevideo Uruguay skyline rambla",
        "Montevideo Uruguay port city",
        "Uruguay cityscape Montevideo",
    ],
    "Uruguay / cheer_reasons / Luis Suárez is a legend": [
        "Luis Suárez Uruguay footballer",
        "Luis Suarez footballer legendary",
        "Luis Suárez Uruguay national team",
    ],
    "France / cheer_reasons / Kylian Mbappé is the fastest player alive": [
        "Kylian Mbappé France football",
        "Kylian Mbappe Paris Saint-Germain footballer",
        "Mbappe France national team sprint",
    ],
    "France / cheer_reasons / Croissants": [
        "French croissant golden flaky pastry",
        "croissant Paris bakery boulangerie",
        "French croissant butter pastry morning",
    ],
    "France / cheer_reasons / French fashion": [
        "Paris fashion week haute couture catwalk",
        "Paris haute couture fashion show",
        "Paris fashion luxury design",
    ],
    "Senegal / cheer_reasons / Africa Cup of Nations champs": [
        "Senegal Africa Cup of Nations 2021 champions",
        "AFCON Senegal winners trophy",
        "Senegal Sadio Mane AFCON celebration",
    ],
    "Senegal / cheer_reasons / Sadio Mané is a superstar": [
        "Sadio Mane Senegal footballer",
        "Sadio Mané Bayern Munich Senegal",
        "Sadio Mane African football star",
    ],
    "Senegal / cheer_reasons / African wildlife": [
        "Niokolo-Koba National Park Senegal wildlife",
        "Senegal wildlife nature chimpanzee",
        "West Africa wildlife savanna Senegal",
    ],
    "Senegal / cheer_reasons / Colorful boubou clothing": [
        "Senegalese boubou colorful traditional dress",
        "boubou West African colorful fabric clothing",
        "Senegal traditional boubou robe colorful",
    ],
    "Iraq / cheer_reasons / Where writing was invented": [
        "Sumerian cuneiform tablet Mesopotamia ancient",
        "cuneiform tablet clay ancient writing Mesopotamia",
        "Babylon ancient Mesopotamia Iraq ruins",
    ],
    "Iraq / cheer_reasons / Tigris River fish feast": [
        "Tigris River Baghdad Iraq",
        "Tigris River Iraq waterfront",
        "Baghdad Tigris river boats Iraq",
    ],
    "Argentina / cheer_reasons / 3x World Cup champions": [
        "Argentina 2022 World Cup champions celebration",
        "Argentina World Cup trophy Lionel Messi",
        "Argentina Selección football champions",
    ],
    "Argentina / cheer_reasons / Best BBQ in the world": [
        "Argentine asado barbecue grill beef",
        "Argentina asado fire grilled meat",
        "South American asado Argentina beef",
    ],
    "Argentina / cheer_reasons / Tango dancing": [
        "tango dancing Buenos Aires Argentina",
        "tango couple dance Buenos Aires",
        "Argentine tango performance La Boca",
    ],
    "Argentina / cheer_reasons / Patagonia wilderness": [
        "Patagonia Argentina mountains lake landscape",
        "Patagonia Torres del Paine Argentina Chile",
        "Patagonia Argentina Perito Moreno glacier",
    ],
    "Algeria / cheer_reasons / World's largest desert": [
        "Sahara Desert Algeria sand dunes ergs",
        "Grand Erg Occidental Algeria desert",
        "Sahara dunes Algeria golden",
    ],
    "Algeria / cheer_reasons / Riyad Mahrez is lightning fast": [
        "Riyad Mahrez Manchester City Algeria footballer",
        "Riyad Mahrez Algeria winger",
        "Mahrez Algeria football player",
    ],
    "Austria / cheer_reasons / Mozart's homeland": [
        "Salzburg Mozart birthplace Austria",
        "Mozart statue Salzburg Austria",
        "Salzburg Austria historic old town",
    ],
    "Austria / cheer_reasons / Best chocolate cake (Sachertorte)": [
        "Sachertorte Vienna chocolate cake Hotel Sacher",
        "Sachertorte Austrian chocolate torte slice",
        "Sacher cake Vienna apricot chocolate",
    ],
    "Austria / cheer_reasons / David Alaba is amazing": [
        "David Alaba Real Madrid Austria footballer",
        "David Alaba Austria national team",
        "Alaba Austrian footballer",
    ],
    "Jordan / cheer_reasons / Petra": [
        "Petra ancient city Jordan Treasury Al-Khazneh",
        "Petra Jordan rose red city",
        "Al-Khazneh Petra Jordan Nabatean",
    ],
    "Jordan / cheer_reasons / Dead Sea (saltiest lake!)": [
        "Dead Sea Jordan floating person salt lake",
        "Dead Sea Israel Jordan salt lowest point",
        "floating Dead Sea salt water unique",
    ],
    "Portugal / cheer_reasons / Cristiano Ronaldo (GOAT debate!)": [
        "Cristiano Ronaldo Portugal football",
        "Cristiano Ronaldo national team celebration",
        "Ronaldo Portugal footballer",
    ],
    "DR Congo / cheer_reasons / Incredible biodiversity": [
        "Congo rainforest biodiversity gorilla DRC",
        "Democratic Republic Congo tropical forest",
        "Congo basin biodiversity tropical wildlife",
    ],
    "Uzbekistan / cheer_reasons / Samarkand (most beautiful city you've never heard of!)": [
        "Registan Samarkand Uzbekistan blue tiles",
        "Samarkand Uzbekistan Silk Road city",
        "Registan square Samarkand Timurid",
    ],
    "Uzbekistan / cheer_reasons / Plov (world's best rice dish?)": [
        "plov Uzbek rice pilaf kazan outdoor",
        "Uzbekistan plov celebration cooking",
        "Uzbek plov rice carrots lamb",
    ],
    "Colombia / cheer_reasons / James Rodríguez golden boot 2014": [
        "James Rodriguez Colombia 2014 World Cup",
        "James Rodríguez Colombia footballer",
        "James Rodriguez footballer goal",
    ],
    "Colombia / cheer_reasons / Cartagena beauty": [
        "Cartagena de Indias Colombia colonial walled city",
        "Cartagena Colombia colorful buildings",
        "Old City Cartagena Colombia Caribbean",
    ],
    "Colombia / cheer_reasons / Amazon biodiversity": [
        "Amazon rainforest Colombia biodiversity",
        "Colombian Amazon Leticia wildlife",
        "Amazon jungle Colombia river",
    ],
    "Colombia / cheer_reasons / Lucho Díaz is electrifying": [
        "Luis Diaz Liverpool Colombia footballer",
        "Luis Díaz Colombia footballer",
        "Lucho Diaz Colombia football winger",
    ],
    "England / cheer_reasons / Invented football": [
        "Victorian football England historic photograph",
        "Wembley Stadium England football",
        "England football history 1800s FA Cup",
    ],
    "England / cheer_reasons / Harry Kane is a goal machine": [
        "Harry Kane England national team footballer",
        "Harry Kane Bayern Munich England striker",
        "Harry Kane goal England",
    ],
    "England / cheer_reasons / Premier League (world's best league)": [
        "Premier League Wembley Stadium crowd",
        "English Premier League football stadium",
        "Premier League match Old Trafford crowd",
    ],
    "England / cheer_reasons / 1966 World Cup winners": [
        "England 1966 World Cup winners trophy Wembley",
        "Bobby Moore 1966 World Cup",
        "England 1966 World Cup celebration",
    ],
    "Croatia / cheer_reasons / Luka Modrić is ageless": [
        "Luka Modrić Real Madrid Croatia midfielder",
        "Luka Modric Croatia national team",
        "Modrić Croatia footballer",
    ],
    "Croatia / cheer_reasons / Under 4 million people reached the final!": [
        "Croatia 2018 World Cup runners up celebration",
        "Croatia national football team celebration",
        "Croatia World Cup 2018 checkerboard fans",
    ],
    "Ghana / cheer_reasons / Jollof Rice": [
        "jollof rice Ghana tomato stew party",
        "Ghanaian jollof rice traditional",
        "West African jollof rice celebration",
    ],
    "Ghana / cheer_reasons / Reached quarterfinals in 2010": [
        "Ghana 2010 World Cup South Africa celebration",
        "Black Stars Ghana 2010 quarterfinal",
        "Ghana football World Cup South Africa",
    ],
    "Ghana / cheer_reasons / Kente cloth": [
        "kente cloth Ghana traditional weaving colorful",
        "Kente weaving Ghana strip cloth",
        "Ghanaian kente fabric colorful",
    ],
    "Ghana / cheer_reasons / Black Stars nickname": [
        "Ghana Black Stars football jersey national",
        "Ghana national team football Black Stars",
        "Ghana football team black star badge",
    ],
    "Ghana / cheer_reasons / André Ayew family dynasty": [
        "Andre Ayew Ghana footballer",
        "Ayew family Ghana football",
        "Ghana Ayew Black Stars",
    ],
    "Panama / cheer_reasons / Kuna Yala indigenous culture": [
        "Kuna Guna Yala Panama indigenous mola craft",
        "Kuna people Panama San Blas islands",
        "Guna Yala indigenous Panama mola textile",
    ],
}


def main():
    parser = argparse.ArgumentParser(description="Retry 170 missing images with better queries")
    parser.add_argument("--dry-run",  action="store_true", help="Show queries without downloading")
    parser.add_argument("--limit",    type=int, default=0, help="Stop after N successful downloads")
    parser.add_argument("--section",  help="Restrict to one section")
    parser.add_argument("--country",  help="Restrict to one country name (partial match, case-insensitive)")
    args = parser.parse_args()

    if not MISSING_TXT.exists():
        print("No missing_images.txt found — nothing to retry!")
        return

    # Load current missing items
    with open(MISSING_TXT, encoding="utf-8") as f:
        missing_keys = [ln.strip() for ln in f if ln.strip()]

    print(f"Found {len(missing_keys)} missing items")

    # Build slug lookup from targets CSV
    slug_lookup: dict[str, dict] = {}
    if TARGETS_CSV.exists():
        with open(TARGETS_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = f"{row['country']} / {row['section']} / {row['item_name']}"
                if key not in slug_lookup:
                    slug_lookup[key] = row

    # Load existing sources
    existing_sources: dict[str, dict] = {}
    if SOURCES_CSV.exists():
        with open(SOURCES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing_sources[row.get("image_path", "")] = row

    # Apply filters
    queue = missing_keys
    if args.section:
        queue = [k for k in queue if f"/ {args.section} /" in k]
    if args.country:
        queue = [k for k in queue if args.country.lower() in k.lower()]

    print(f"Queue after filters: {len(queue)}")
    if args.dry_run:
        print("(DRY RUN)\n")

    downloaded = failed = skipped = 0
    still_missing: list[str] = []
    source_updates: dict[str, dict] = {}

    SOURCE_FIELDS = [
        "image_path", "country", "country_slug", "section", "item_name", "item_slug",
        "search_query", "image_url", "source_page", "author", "license", "description", "status",
    ]

    for key in queue:
        row = slug_lookup.get(key)
        if not row:
            print(f"  SKIP (not in targets CSV): {key}")
            skipped += 1
            continue

        out_path = BASE_DIR / row["image_path"]

        if out_path.exists():
            print(f"  ↷ already exists: {key}")
            skipped += 1
            continue

        queries = _BETTER_QUERIES.get(key)
        if not queries:
            print(f"  SKIP (no curated query): {key}")
            still_missing.append(key)
            continue

        print(f"\n  {key}")

        if args.dry_run:
            for q in queries:
                print(f"    would try: '{q}'")
            continue

        meta = try_download_one(queries, out_path, row["section"])

        if not meta:
            # Brief pause before moving on — helps avoid burst rate-limiting
            time.sleep(12)

        if meta:
            downloaded += 1
            source_updates[row["image_path"]] = {
                "image_path":   row["image_path"],
                "country":      row["country"],
                "country_slug": row["country_slug"],
                "section":      row["section"],
                "item_name":    row["item_name"],
                "item_slug":    row["item_slug"],
                "search_query": queries[0],
                "image_url":    meta.get("url", ""),
                "source_page":  meta.get("source_page", ""),
                "author":       meta.get("author", ""),
                "license":      meta.get("license", ""),
                "description":  meta.get("description", ""),
                "status":       "downloaded",
            }
            time.sleep(RATE_LIMIT_S)
        else:
            failed += 1
            still_missing.append(key)

        if args.limit and downloaded >= args.limit:
            print(f"\n--limit {args.limit} reached, stopping.")
            # Items not yet processed remain missing
            idx = queue.index(key)
            still_missing.extend(queue[idx + 1:])
            break

    if not args.dry_run:
        # Merge source updates back into sources CSV
        merged = dict(existing_sources)
        for k, v in source_updates.items():
            merged[k] = v
        with open(SOURCES_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SOURCE_FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(merged.values())

        # Update targets CSV status
        all_rows: list[dict] = []
        if TARGETS_CSV.exists():
            with open(TARGETS_CSV, encoding="utf-8") as f:
                all_rows = list(csv.DictReader(f))
        for r in all_rows:
            if (BASE_DIR / r["image_path"]).exists():
                r["status"] = "downloaded"
        if all_rows:
            with open(TARGETS_CSV, "w", newline="", encoding="utf-8") as f:
                w2 = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
                w2.writeheader()
                w2.writerows(all_rows)

        # Update missing_images.txt
        if still_missing:
            with open(MISSING_TXT, "w", encoding="utf-8") as f:
                f.write("\n".join(still_missing) + "\n")
        else:
            if MISSING_TXT.exists():
                MISSING_TXT.unlink()
            print("\n✅ All missing images resolved!")

    print("\n" + "=" * 52)
    print("RETRY SUMMARY")
    print("=" * 52)
    print(f"  Downloaded      : {downloaded}")
    print(f"  Still missing   : {len(still_missing)}")
    print(f"  Skipped         : {skipped}")
    if still_missing:
        print(f"\n  Still missing ({len(still_missing)}):")
        for m in still_missing[:20]:
            print(f"    - {m}")
        if len(still_missing) > 20:
            print(f"    ... and {len(still_missing) - 20} more")


if __name__ == "__main__":
    main()
