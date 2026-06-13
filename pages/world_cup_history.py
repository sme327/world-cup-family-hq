import streamlit as st

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;padding:1.2rem 0 .4rem'>"
    "<div style='font-size:3.5rem;line-height:1'>🏆</div>"
    "<h1 style='font-size:2.4rem;font-weight:900;margin:.3rem 0 .1rem'>World Cup History</h1>"
    "<div style='color:#94A3B8;font-size:1.05rem'>92 years of the world's greatest tournament</div>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Did You Know? — one per tab (index-driven) ────────────────────────────────
_DID_YOU_KNOW = [
    ("🇧🇷", "Brazil is the only country to have played in EVERY single World Cup — all 22 of them!"),
    ("👟", "Pelé was only 17 years old when he won his first World Cup in 1958. He's still the youngest ever World Cup winner!"),
    ("⚽", "The 1958 World Cup had a surprise ending — the host nation Sweden lost the final 5–2 to Brazil."),
    ("🌍", "The 2026 World Cup is the first ever hosted by THREE countries at the same time: USA, Canada, and Mexico!"),
    ("📈", "The very first World Cup in 1930 had just 13 teams. Now 48 teams compete — nearly 4 times as many!"),
]

_tab_labels = ["🏆 Champions", "⭐ Legends", "📖 Great Moments", "🌍 Hosts", "📈 Evolution"]
_tabs = st.tabs(_tab_labels)

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — CHAMPIONS
# ─────────────────────────────────────────────────────────────────────────────
with _tabs[0]:
    emoji, fact = _DID_YOU_KNOW[0]
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(251,191,36,.13),rgba(251,191,36,.05));"
        f"border:1px solid rgba(251,191,36,.35);border-radius:14px;"
        f"padding:.75rem 1.1rem;margin:.4rem 0 1.2rem;display:flex;align-items:flex-start;gap:.8rem'>"
        f"<span style='font-size:2rem;line-height:1.2'>{emoji}</span>"
        f"<div><div style='font-size:.68rem;font-weight:800;color:#F59E0B;letter-spacing:.07em;"
        f"text-transform:uppercase;margin-bottom:.2rem'>Did You Know?</div>"
        f"<div style='font-size:.97rem;color:#F1F5F9;font-weight:500'>{fact}</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### 🏆 Who Has Won the Most?")

    _champions = [
        ("🇧🇷", "Brazil",     5, [1958, 1962, 1970, 1994, 2002], "#009C3B"),
        ("🇩🇪", "Germany",    4, [1954, 1974, 1990, 2014],       "#000000"),
        ("🇮🇹", "Italy",      4, [1934, 1938, 1982, 2006],       "#0066CC"),
        ("🇦🇷", "Argentina",  3, [1978, 1986, 2022],             "#74ACDF"),
        ("🇫🇷", "France",     2, [1998, 2018],                   "#002395"),
        ("🇺🇾", "Uruguay",    2, [1930, 1950],                   "#5EB6E4"),
        ("🏴󠁧󠁢󠁥󠁮󠁧󠁿", "England",    1, [1966],                        "#CF142B"),
        ("🇪🇸", "Spain",      1, [2010],                         "#AA151B"),
    ]

    for flag, country, wins, years, color in _champions:
        trophies = "🏆" * wins
        year_pills = " ".join(
            f"<span style='background:rgba(255,255,255,.1);border-radius:8px;"
            f"padding:.12rem .45rem;font-size:.78rem;font-weight:700'>{y}</span>"
            for y in years
        )
        st.markdown(
            f"<div style='background:linear-gradient(90deg,{color}22,transparent);"
            f"border:1px solid {color}44;border-radius:14px;"
            f"padding:.75rem 1.1rem;margin:.4rem 0;"
            f"display:flex;align-items:center;gap:1rem;flex-wrap:wrap'>"
            f"<span style='font-size:2.6rem;line-height:1'>{flag}</span>"
            f"<div style='flex:1;min-width:180px'>"
            f"<div style='font-weight:900;font-size:1.25rem;color:#F1F5F9'>{country}"
            f"  <span style='font-size:.95rem;color:#FCD34D;font-weight:700'>{wins}× Champion</span></div>"
            f"<div style='margin-top:.25rem;display:flex;flex-wrap:wrap;gap:.25rem'>{year_pills}</div>"
            f"</div>"
            f"<div style='font-size:1.5rem;letter-spacing:.1rem'>{trophies}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("### 📅 Every World Cup Champion")

    _all_winners = [
        (1930, "🇺🇾", "Uruguay"),
        (1934, "🇮🇹", "Italy"),
        (1938, "🇮🇹", "Italy"),
        (1950, "🇺🇾", "Uruguay"),
        (1954, "🇩🇪", "Germany"),
        (1958, "🇧🇷", "Brazil"),
        (1962, "🇧🇷", "Brazil"),
        (1966, "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "England"),
        (1970, "🇧🇷", "Brazil"),
        (1974, "🇩🇪", "Germany"),
        (1978, "🇦🇷", "Argentina"),
        (1982, "🇮🇹", "Italy"),
        (1986, "🇦🇷", "Argentina"),
        (1990, "🇩🇪", "Germany"),
        (1994, "🇧🇷", "Brazil"),
        (1998, "🇫🇷", "France"),
        (2002, "🇧🇷", "Brazil"),
        (2006, "🇮🇹", "Italy"),
        (2010, "🇪🇸", "Spain"),
        (2014, "🇩🇪", "Germany"),
        (2018, "🇫🇷", "France"),
        (2022, "🇦🇷", "Argentina"),
    ]

    # Grid of champion cards — 4 per row
    for row_start in range(0, len(_all_winners), 4):
        row = _all_winners[row_start:row_start + 4]
        cols = st.columns(len(row))
        for col, (yr, flag, name) in zip(cols, row):
            with col:
                st.markdown(
                    f"<div style='background:rgba(30,41,59,.8);border:1px solid rgba(255,255,255,.1);"
                    f"border-radius:12px;padding:.7rem;text-align:center;margin:.2rem 0'>"
                    f"<div style='font-size:.72rem;font-weight:700;color:#94A3B8;margin-bottom:.1rem'>{yr}</div>"
                    f"<div style='font-size:2rem;line-height:1.2'>{flag}</div>"
                    f"<div style='font-size:.82rem;font-weight:800;margin-top:.2rem;color:#F1F5F9'>{name}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — LEGENDS
# ─────────────────────────────────────────────────────────────────────────────
with _tabs[1]:
    emoji, fact = _DID_YOU_KNOW[1]
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(251,191,36,.13),rgba(251,191,36,.05));"
        f"border:1px solid rgba(251,191,36,.35);border-radius:14px;"
        f"padding:.75rem 1.1rem;margin:.4rem 0 1.2rem;display:flex;align-items:flex-start;gap:.8rem'>"
        f"<span style='font-size:2rem;line-height:1.2'>{emoji}</span>"
        f"<div><div style='font-size:.68rem;font-weight:800;color:#F59E0B;letter-spacing:.07em;"
        f"text-transform:uppercase;margin-bottom:.2rem'>Did You Know?</div>"
        f"<div style='font-size:.97rem;color:#F1F5F9;font-weight:500'>{fact}</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### ⭐ The Greatest World Cup Players Ever")
    st.caption("These players made the whole world stop and watch.")

    _legends = [
        {
            "emoji":   "🌟",
            "name":    "Pelé",
            "flag":    "🇧🇷",
            "country": "Brazil",
            "years":   "1958 – 1970",
            "cups":    "🏆🏆🏆",
            "wow":     "3-time World Cup champion",
            "story":   "The greatest of all time. Pelé won THREE World Cups and scored 77 goals for Brazil. He was so good that countries declared a ceasefire during a war just to watch him play!",
            "color":   "#009C3B",
        },
        {
            "emoji":   "🤌",
            "name":    "Diego Maradona",
            "flag":    "🇦🇷",
            "country": "Argentina",
            "years":   "1982 – 1994",
            "cups":    "🏆",
            "wow":     "Scored the 'Goal of the Century'",
            "story":   "In 1986 he dribbled past 5 defenders and a goalkeeper for what was voted the greatest goal ever. In the same match, he also scored the infamous 'Hand of God' goal. Pure magic.",
            "color":   "#74ACDF",
        },
        {
            "emoji":   "🐐",
            "name":    "Lionel Messi",
            "flag":    "🇦🇷",
            "country": "Argentina",
            "years":   "2006 – 2022",
            "cups":    "🏆",
            "wow":     "Finally won it all in 2022 at age 35",
            "story":   "Many say Messi is the best player ever. After four heartbreaking World Cups, he finally lifted the trophy in Qatar 2022 — one of sport's greatest stories ever told.",
            "color":   "#74ACDF",
        },
        {
            "emoji":   "🕺",
            "name":    "Zinédine Zidane",
            "flag":    "🇫🇷",
            "country": "France",
            "years":   "1998 – 2006",
            "cups":    "🏆",
            "wow":     "Scored twice in the 1998 final with his head",
            "story":   "France's greatest ever player. Zidane was elegant, powerful, and unstoppable. He scored two headers in the 1998 World Cup final on home soil in front of 80,000 fans.",
            "color":   "#002395",
        },
        {
            "emoji":   "👽",
            "name":    "Ronaldo (R9)",
            "flag":    "🇧🇷",
            "country": "Brazil",
            "years":   "1994 – 2006",
            "cups":    "🏆🏆",
            "wow":     "Scored 15 World Cup goals in 3 tournaments",
            "story":   "The original Ronaldo — nicknamed 'The Phenomenon.' Unstoppable speed, deadly finishing. He bounced back from a mysterious illness before the 2002 final to score twice and win the Cup.",
            "color":   "#009C3B",
        },
        {
            "emoji":   "🦅",
            "name":    "Franz Beckenbauer",
            "flag":    "🇩🇪",
            "country": "Germany",
            "years":   "1966 – 1974",
            "cups":    "🏆",
            "wow":     "Won as player AND later as coach",
            "story":   "Called 'Der Kaiser' (The Emperor). He's one of only two people in history to win the World Cup as both a player and a coach. A defender who played like an artist.",
            "color":   "#000000",
        },
        {
            "emoji":   "🌀",
            "name":    "Johan Cruyff",
            "flag":    "🇳🇱",
            "country": "Netherlands",
            "years":   "1974",
            "cups":    "🥈",
            "wow":     "Invented the 'Cruyff Turn' move",
            "story":   "Cruyff invented a way of playing called 'Total Football' where everyone on the team could play any position. His 1974 Netherlands team is still talked about as one of the greatest teams ever — even though they lost the final.",
            "color":   "#FF4E00",
        },
        {
            "emoji":   "👑",
            "name":    "Marta",
            "flag":    "🇧🇷",
            "country": "Brazil",
            "years":   "2003 – 2019",
            "cups":    "🥈🥈",
            "wow":     "All-time top scorer in Women's World Cup history",
            "story":   "The greatest women's player of all time. Marta scored 17 goals across 5 World Cups — more than any player ever in a World Cup. She's won FIFA Player of the Year 6 times.",
            "color":   "#009C3B",
        },
        {
            "emoji":   "⚡",
            "name":    "Kylian Mbappé",
            "flag":    "🇫🇷",
            "country": "France",
            "years":   "2018 – present",
            "cups":    "🏆",
            "wow":     "Won the World Cup at age 19!",
            "story":   "France's superstar of today. Mbappé is incredibly fast — clocked at 36 km/h (22 mph). He won the World Cup at just 19 years old and scored 8 goals at the 2022 World Cup, including a hat-trick in the final.",
            "color":   "#002395",
        },
    ]

    for leg in _legends:
        bg = leg["color"]
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{bg}22,{bg}08);"
            f"border:1px solid {bg}44;border-radius:18px;"
            f"padding:1rem 1.25rem;margin:.6rem 0;"
            f"display:flex;align-items:flex-start;gap:1.1rem'>"
            # Left: big emoji + flag
            f"<div style='text-align:center;min-width:60px'>"
            f"<div style='font-size:2.8rem;line-height:1'>{leg['emoji']}</div>"
            f"<div style='font-size:1.6rem;margin-top:.15rem'>{leg['flag']}</div>"
            f"</div>"
            # Right: info
            f"<div style='flex:1'>"
            f"<div style='display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap'>"
            f"<span style='font-size:1.3rem;font-weight:900;color:#F1F5F9'>{leg['name']}</span>"
            f"<span style='font-size:.82rem;color:#94A3B8'>{leg['country']} · {leg['years']}</span>"
            f"<span style='font-size:1.1rem'>{leg['cups']}</span>"
            f"</div>"
            f"<div style='font-size:.8rem;font-weight:700;color:#FCD34D;margin:.2rem 0 .35rem'>✨ {leg['wow']}</div>"
            f"<div style='font-size:.91rem;color:#CBD5E1;line-height:1.55'>{leg['story']}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — GREAT MOMENTS
# ─────────────────────────────────────────────────────────────────────────────
with _tabs[2]:
    emoji, fact = _DID_YOU_KNOW[2]
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(251,191,36,.13),rgba(251,191,36,.05));"
        f"border:1px solid rgba(251,191,36,.35);border-radius:14px;"
        f"padding:.75rem 1.1rem;margin:.4rem 0 1.2rem;display:flex;align-items:flex-start;gap:.8rem'>"
        f"<span style='font-size:2rem;line-height:1.2'>{emoji}</span>"
        f"<div><div style='font-size:.68rem;font-weight:800;color:#F59E0B;letter-spacing:.07em;"
        f"text-transform:uppercase;margin-bottom:.2rem'>Did You Know?</div>"
        f"<div style='font-size:.97rem;color:#F1F5F9;font-weight:500'>{fact}</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### 📖 Moments That Stopped the World")
    st.caption("Stories so incredible, they're still talked about generations later.")

    _moments = [
        {
            "year":    "1950",
            "emoji":   "😱",
            "title":   "The Maracanazo",
            "teams":   "Uruguay vs Brazil",
            "verdict": "Uruguay wins — shocking Brazil in their own stadium",
            "story":   "Brazil built the world's largest stadium for this game, held a parade before it, and everyone expected them to win the World Cup on home soil. 200,000 fans packed in. Uruguay scored late and won 2–1. Brazil fans stood in silence. It's still called the greatest upset in World Cup history.",
            "color":   "#EF4444",
        },
        {
            "year":    "1958",
            "emoji":   "🌟",
            "title":   "The Kid Who Changed Everything",
            "teams":   "Brazil vs Sweden (Final)",
            "verdict": "Brazil wins 5–2",
            "story":   "A 17-year-old named Pelé played in the final and scored two incredible goals — including a chest trap and bicycle kick that left everyone speechless. After it went in, Sweden fans stood and applauded him. A 17-year-old. In the World Cup final.",
            "color":   "#009C3B",
        },
        {
            "year":    "1966",
            "emoji":   "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
            "title":   "England's Only World Cup",
            "teams":   "England vs Germany (Final)",
            "verdict": "England wins 4–2 at Wembley Stadium",
            "story":   "England invented soccer, but they'd never won the World Cup. On home soil, in front of a roaring crowd at Wembley, they finally did it. Geoff Hurst scored a hat-trick — the only hat-trick ever in a World Cup final. England has never won it since.",
            "color":   "#CF142B",
        },
        {
            "year":    "1970",
            "emoji":   "🎨",
            "title":   "The Most Beautiful Team Ever",
            "teams":   "Brazil — entire tournament",
            "verdict": "Brazil wins with the greatest team in history",
            "story":   "Brazil's 1970 team — with Pelé, Jairzinho, Rivelino, and Tostão — is still called the greatest soccer team ever assembled. They played with such joy, creativity, and skill that even rival fans cheered for them. Jairzinho scored in every single game.",
            "color":   "#009C3B",
        },
        {
            "year":    "1986",
            "emoji":   "🤌",
            "title":   "The Goal of the Century",
            "teams":   "Argentina vs England",
            "verdict": "Argentina wins 2–1",
            "story":   "In five seconds, Maradona took the ball in his own half, dribbled past five English defenders and the goalkeeper, and scored. It was voted the Greatest Goal in World Cup history. In the same game, he also scored with his hand — which he later called 'the Hand of God.'",
            "color":   "#74ACDF",
        },
        {
            "year":    "1994",
            "emoji":   "💔",
            "title":   "Baggio's Missed Penalty",
            "teams":   "Italy vs Brazil (Final)",
            "verdict": "Brazil wins on penalties",
            "story":   "Roberto Baggio was Italy's greatest player and hero. The World Cup final ended 0–0. In the shootout, Baggio stepped up for the final kick — if he missed, Italy lost. He missed over the bar. He stood alone with his head bowed while Brazil celebrated. One of sport's most heartbreaking images.",
            "color":   "#0066CC",
        },
        {
            "year":    "1998",
            "emoji":   "🇫🇷",
            "title":   "France's Greatest Night",
            "teams":   "France vs Brazil (Final)",
            "verdict": "France wins 3–0",
            "story":   "France hosted the World Cup — and everyone expected Brazil to win. Instead, Zidane scored two headers before halftime in Paris. A country that had never won erupted. One million people celebrated on the Champs-Élysées. Zidane became a national hero overnight.",
            "color":   "#002395",
        },
        {
            "year":    "2010",
            "emoji":   "🌍",
            "title":   "Africa Gets Its World Cup",
            "teams":   "South Africa hosts the world",
            "verdict": "Spain wins — but Africa wins too",
            "story":   "For the first time ever, the World Cup was played in Africa. The sound of vuvuzelas (plastic horns) filled stadiums. South Africa's players danced in the street. Spain won the tournament — but the real winner was Africa, showing the world the joy and spirit of an entire continent.",
            "color":   "#009B77",
        },
        {
            "year":    "2014",
            "emoji":   "🇩🇪",
            "title":   "The 7–1",
            "teams":   "Germany vs Brazil (Semifinal)",
            "verdict": "Germany wins 7–1 — Brazil stunned on home soil",
            "story":   "Brazil hosted the World Cup and were favorite to win. Then, in the semifinal in front of 60,000 Brazilian fans, Germany scored 7 goals. It took 29 minutes to score the first five. Brazilian fans cried in the stands. German fans barely celebrated out of respect. Called 'The Mineirazo.'",
            "color":   "#000000",
        },
        {
            "year":    "2022",
            "emoji":   "🐐",
            "title":   "Messi's Moment",
            "teams":   "Argentina vs France (Final)",
            "verdict": "Argentina wins on penalties after 3–3 draw",
            "story":   "Considered the greatest World Cup final ever played. Mbappé scored a hat-trick. Messi scored twice. France came back from 2–0 down to tie it 3–3. Penalties decided it. When Argentina won, the entire continent of South America celebrated. Messi finally had his World Cup.",
            "color":   "#74ACDF",
        },
    ]

    for m in _moments:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{m['color']}18,{m['color']}06);"
            f"border-left:4px solid {m['color']};border-radius:0 16px 16px 0;"
            f"padding:1rem 1.2rem;margin:.7rem 0'>"
            f"<div style='display:flex;align-items:center;gap:.8rem;margin-bottom:.4rem;flex-wrap:wrap'>"
            f"<span style='font-size:2rem'>{m['emoji']}</span>"
            f"<div>"
            f"<span style='background:{m['color']};color:white;border-radius:8px;"
            f"padding:.1rem .5rem;font-size:.78rem;font-weight:800;margin-right:.5rem'>{m['year']}</span>"
            f"<span style='font-size:1.2rem;font-weight:900;color:#F1F5F9'>{m['title']}</span>"
            f"</div></div>"
            f"<div style='font-size:.8rem;color:#94A3B8;margin-bottom:.35rem'>"
            f"⚽ {m['teams']} · {m['verdict']}</div>"
            f"<div style='font-size:.94rem;color:#CBD5E1;line-height:1.6'>{m['story']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 4 — HOSTS
# ─────────────────────────────────────────────────────────────────────────────
with _tabs[3]:
    emoji, fact = _DID_YOU_KNOW[3]
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(251,191,36,.13),rgba(251,191,36,.05));"
        f"border:1px solid rgba(251,191,36,.35);border-radius:14px;"
        f"padding:.75rem 1.1rem;margin:.4rem 0 1.2rem;display:flex;align-items:flex-start;gap:.8rem'>"
        f"<span style='font-size:2rem;line-height:1.2'>{emoji}</span>"
        f"<div><div style='font-size:.68rem;font-weight:800;color:#F59E0B;letter-spacing:.07em;"
        f"text-transform:uppercase;margin-bottom:.2rem'>Did You Know?</div>"
        f"<div style='font-size:.97rem;color:#F1F5F9;font-weight:500'>{fact}</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### 🌍 Every Host Country — All 22 World Cups")
    st.caption("The World Cup travels the globe. Here's everywhere it has been — and where it's going next.")

    _hosts = [
        (1930, "🇺🇾", "Uruguay",       "South America",  "First ever World Cup! Uruguay was chosen to celebrate their 100th birthday as a nation. The beautiful La Centenario stadium was built just for this tournament."),
        (1934, "🇮🇹", "Italy",          "Europe",         "Mussolini built new stadiums to show off Italy to the world. Italy won on home soil — but some say the refereeing was a bit suspicious..."),
        (1938, "🇫🇷", "France",         "Europe",         "The last World Cup before World War II. Held in Paris. Players had no idea it would be 12 years before they played again."),
        (1950, "🇧🇷", "Brazil",         "South America",  "Brazil built the Maracanã — then the world's largest stadium, holding 200,000 people. The final ended in heartbreak for Brazil."),
        (1954, "🇨🇭", "Switzerland",    "Europe",         "Known for the highest-scoring World Cup ever. Matches averaged over 5 goals per game! One quarterfinal ended 7–5."),
        (1958, "🇸🇪", "Sweden",         "Europe",         "Sweden hosted and made the final — but lost to a 17-year-old named Pelé. One of the most charming World Cups ever."),
        (1962, "🇨🇱", "Chile",          "South America",  "Chile had just had a massive earthquake, but rebuilt and hosted a remarkable World Cup. Brazil won again."),
        (1966, "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "England",       "Europe",         "England's only World Cup win. The Jules Rimet trophy was stolen and found by a dog named Pickles before the tournament!"),
        (1970, "🇲🇽", "Mexico",         "North America",  "The first World Cup shown in color on TV! Millions watched the beautiful Azteca stadium for the first time. Still considered the greatest World Cup tournament ever."),
        (1974, "🇩🇪", "West Germany",   "Europe",         "West Germany beat the Netherlands in the final. Johan Cruyff's Dutch team introduced 'Total Football' — a style that changed soccer forever."),
        (1978, "🇦🇷", "Argentina",      "South America",  "Argentina won for the first time on home soil. Ticker tape streamed from the stands. One of the most emotional finals ever."),
        (1982, "🇪🇸", "Spain",          "Europe",         "Italy won a dramatic tournament. 24 teams for the first time. Brazil played the most beautiful football but was eliminated before the final."),
        (1986, "🇲🇽", "Mexico",         "North America",  "Mexico hosted for the second time — after Colombia pulled out! Maradona had the greatest World Cup individual performance ever."),
        (1990, "🇮🇹", "Italy",          "Europe",         "The lowest-scoring, most defensive World Cup ever. Famous for Pavarotti singing Nessun Dorma in the opening ceremony."),
        (1994, "🇺🇸", "USA",            "North America",  "America's first World Cup! 3.5 million fans attended. Brazil won their 4th title. Baggio's missed penalty became iconic."),
        (1998, "🇫🇷", "France",         "Europe",         "France won on home soil for the first time. A million people celebrated in Paris. Zidane became a hero overnight."),
        (2002, "🇯🇵🇰🇷", "Japan & South Korea", "Asia", "First World Cup in Asia — and the first co-hosted by two countries. Biggest upsets ever: France went out in the group stage without scoring a goal!"),
        (2006, "🇩🇪", "Germany",        "Europe",         "Germany showed the world it could be fun and friendly. Italian fans celebrated in the streets. Zidane's shocking headbutt in the final ended his career."),
        (2010, "🇿🇦", "South Africa",   "Africa",         "First World Cup on African soil. Vuvuzelas filled every stadium. Spain won their only World Cup, beating Netherlands 1–0 in extra time."),
        (2014, "🇧🇷", "Brazil",         "South America",  "The World Cup of the 7–1. Brazil was demolished by Germany in the semifinal in their own country. Germany won the title."),
        (2018, "🇷🇺", "Russia",         "Europe",         "France won their second World Cup. Croatia, a tiny country of just 4 million people, made it all the way to the final against the odds."),
        (2022, "🇶🇦", "Qatar",          "Middle East",    "First World Cup in the Arab world. Played in winter (November-December) for the first time due to the heat. Argentina won in the greatest final ever played."),
        (2026, "🇺🇸🇨🇦🇲🇽", "USA · Canada · Mexico", "North America", "First World Cup with 48 teams! Three countries co-hosting for the first time ever. 16 venues across North America, including MetLife Stadium in New York for the final."),
    ]

    for yr, flag, country, continent, blurb in _hosts:
        is_current = yr == 2026
        border_color = "#FCD34D" if is_current else "rgba(255,255,255,.1)"
        bg_color = "rgba(251,191,36,.08)" if is_current else "rgba(30,41,59,.6)"
        now_badge = (
            "<span style='background:#FCD34D;color:#1E293B;border-radius:8px;"
            "padding:.08rem .45rem;font-size:.72rem;font-weight:900;margin-left:.5rem'>NOW ⚡</span>"
        ) if is_current else ""
        st.markdown(
            f"<div style='background:{bg_color};border:1px solid {border_color};"
            f"border-radius:12px;padding:.65rem 1rem;margin:.35rem 0;"
            f"display:flex;align-items:flex-start;gap:.9rem'>"
            f"<div style='text-align:center;min-width:56px'>"
            f"<div style='font-size:1.8rem;line-height:1'>{flag}</div>"
            f"<div style='font-size:.7rem;font-weight:800;color:#FCD34D;margin-top:.1rem'>{yr}</div>"
            f"</div>"
            f"<div style='flex:1'>"
            f"<div style='font-weight:800;font-size:1rem;color:#F1F5F9'>{country}{now_badge}"
            f"<span style='font-weight:400;font-size:.78rem;color:#64748B;margin-left:.5rem'>{continent}</span></div>"
            f"<div style='font-size:.86rem;color:#CBD5E1;margin-top:.18rem;line-height:1.5'>{blurb}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TAB 5 — EVOLUTION
# ─────────────────────────────────────────────────────────────────────────────
with _tabs[4]:
    emoji, fact = _DID_YOU_KNOW[4]
    st.markdown(
        f"<div style='background:linear-gradient(135deg,rgba(251,191,36,.13),rgba(251,191,36,.05));"
        f"border:1px solid rgba(251,191,36,.35);border-radius:14px;"
        f"padding:.75rem 1.1rem;margin:.4rem 0 1.2rem;display:flex;align-items:flex-start;gap:.8rem'>"
        f"<span style='font-size:2rem;line-height:1.2'>{emoji}</span>"
        f"<div><div style='font-size:.68rem;font-weight:800;color:#F59E0B;letter-spacing:.07em;"
        f"text-transform:uppercase;margin-bottom:.2rem'>Did You Know?</div>"
        f"<div style='font-size:.97rem;color:#F1F5F9;font-weight:500'>{fact}</div></div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### 📈 How the World Cup Has Grown")
    st.caption("From a small tournament in 1930 to the biggest sporting event on Earth.")

    # Growth timeline
    _milestones = [
        ("1930", "⚽", "13 teams, 18 matches", "The very first World Cup. Just 13 teams entered. The whole tournament took less than 3 weeks. Uruguay won, playing in front of 100,000 fans in Montevideo."),
        ("1954", "📺", "First on TV", "For the first time, people could watch World Cup matches on television. Millions watched from their living rooms. Soccer became a global TV event overnight."),
        ("1966", "🏆", "Jules Rimet Trophy stolen!", "The original World Cup trophy was stolen from an exhibition in London. A dog named Pickles found it wrapped in newspaper under a hedge. England went on to win the whole thing."),
        ("1970", "🎨", "First in color", "Mexico 1970 was the first World Cup broadcast in color TV. The bright green grass, colorful kits, and golden trophy made it the most beautiful thing anyone had ever seen on TV."),
        ("1970", "🔴", "Red & yellow cards introduced", "Before 1970, referees had to argue with players using words. In Mexico, referee Ken Aston invented red and yellow cards — so everyone understood the decision instantly, in any language."),
        ("1982", "🌍", "Expanded to 24 teams", "The World Cup grew from 16 to 24 teams, giving more countries a chance to compete. For the first time, a World Cup felt truly global."),
        ("1991", "👑", "Women's World Cup begins", "The first ever FIFA Women's World Cup was held in China. The USA won. A whole new era of the game began. Marta, Mia Hamm, and others became global icons."),
        ("1994", "💰", "3 billion viewers", "The 1994 World Cup in the USA was watched by 3.6 billion people worldwide — over half the world's entire population at the time."),
        ("1998", "🌐", "Expanded to 32 teams", "The World Cup grew again, to 32 teams from 32 countries — 8 groups of 4. This format lasted 24 years and produced some of the most memorable matches ever."),
        ("2026", "🚀", "Expanded to 48 teams!", "This year's World Cup is the biggest ever — 48 teams from 6 continents, 104 matches, 16 venues across 3 countries. More countries than ever get a chance to make history."),
    ]

    for yr, em, headline, detail in _milestones:
        st.markdown(
            f"<div style='display:flex;gap:1rem;margin:.5rem 0;align-items:flex-start'>"
            f"<div style='text-align:center;min-width:52px'>"
            f"<div style='font-size:1.8rem;line-height:1'>{em}</div>"
            f"<div style='font-size:.68rem;font-weight:800;color:#FCD34D;margin-top:.1rem'>{yr}</div>"
            f"</div>"
            f"<div style='flex:1;background:rgba(30,41,59,.7);border:1px solid rgba(255,255,255,.09);"
            f"border-radius:12px;padding:.65rem .9rem'>"
            f"<div style='font-weight:800;font-size:.98rem;color:#F1F5F9;margin-bottom:.2rem'>{headline}</div>"
            f"<div style='font-size:.88rem;color:#CBD5E1;line-height:1.55'>{detail}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    st.markdown("### 🔢 By the Numbers — Then vs. Now")

    _comparisons = [
        ("Teams",          "13",    "48",     "teams in 1930", "teams in 2026"),
        ("Matches",        "18",    "104",    "matches in 1930", "matches in 2026"),
        ("Host Countries", "1",     "3",      "host in 1930", "hosts in 2026"),
        ("TV Viewers",     "0",     "5 billion+", "watched on TV in 1930", "expected viewers in 2026"),
        ("Countries",      "41",    "211",    "FIFA members in 1930", "FIFA members today"),
        ("Prize Money",    "$0",    "$625M+",  "prize money in 1930", "prize money in 2026"),
    ]

    cols = st.columns(3)
    for i, (label, then, now, then_label, now_label) in enumerate(_comparisons):
        with cols[i % 3]:
            st.markdown(
                f"<div style='background:rgba(30,41,59,.8);border:1px solid rgba(255,255,255,.1);"
                f"border-radius:14px;padding:.9rem;text-align:center;margin:.35rem 0'>"
                f"<div style='font-size:.72rem;font-weight:700;color:#94A3B8;margin-bottom:.4rem;"
                f"text-transform:uppercase;letter-spacing:.05em'>{label}</div>"
                f"<div style='display:flex;align-items:center;justify-content:center;gap:.6rem'>"
                f"<div>"
                f"<div style='font-size:1.5rem;font-weight:900;color:#64748B'>{then}</div>"
                f"<div style='font-size:.62rem;color:#475569'>{then_label}</div>"
                f"</div>"
                f"<div style='color:#94A3B8;font-size:1.3rem'>→</div>"
                f"<div>"
                f"<div style='font-size:1.5rem;font-weight:900;color:#34D399'>{now}</div>"
                f"<div style='font-size:.62rem;color:#6EE7B7'>{now_label}</div>"
                f"</div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
