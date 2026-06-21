import streamlit as st
import plotly.graph_objects as go

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    "<div style='text-align:center;padding:1.2rem 0 .4rem'>"
    "<div style='font-size:3.5rem;line-height:1'>🏆</div>"
    "<h1 style='font-size:2.4rem;font-weight:900;margin:.3rem 0 .1rem'>World Cup History</h1>"
    "<div style='color:#94A3B8;font-size:1.05rem'>92 years of the world's greatest tournament</div>"
    "</div>",
    unsafe_allow_html=True,
)

# ── Did You Know? — one per tab ───────────────────────────────────────────────
_DID_YOU_KNOW = [
    ("🇧🇷", "Brazil is the only country to have played in EVERY single World Cup — all 22 of them!"),
    ("👟", "Pelé was only 17 years old when he won his first World Cup in 1958. He's still the youngest ever World Cup winner!"),
    ("😱", "When the USA beat England 1–0 in 1950, most newspapers thought the final score was a typo. They didn't believe it."),
    ("⚽", "The 1958 World Cup had a surprise ending — the host nation Sweden lost the final 5–2 to Brazil."),
    ("🌍", "The 2026 World Cup is the first ever hosted by THREE countries at the same time: USA, Canada, and Mexico!"),
    ("📈", "The very first World Cup in 1930 had just 13 teams. Now 48 teams compete — nearly 4 times as many!"),
    ("🦁", "The very first World Cup mascot was 'World Cup Willie' — a lion wearing an England shirt — created for the 1966 World Cup in England."),
    ("⚡", "The fastest goal in World Cup history was scored in just 11 seconds. Turkish player Hakan Şükür scored it against South Korea in 2002."),
]

# ── Shared helper ─────────────────────────────────────────────────────────────
def _dyk_box(idx: int) -> None:
    emoji, fact = _DID_YOU_KNOW[idx]
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

# ── Tab labels ────────────────────────────────────────────────────────────────
_tab_labels = [
    "🏆 Champions",
    "⭐ Legends",
    "🔥 Greatest Upsets",
    "📖 Great Moments",
    "🌍 Hosts",
    "📈 Evolution",
    "🦁 Animals & Mascots",
    "📚 Records",
]
_tabs = st.tabs(_tab_labels)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — CHAMPIONS
# ═════════════════════════════════════════════════════════════════════════════
with _tabs[0]:
    _dyk_box(0)
    st.markdown("### 🏆 Who Has Won the Most?")

    _champions = [
        ("🇧🇷", "Brazil",    5, [1958,1962,1970,1994,2002], "#009C3B"),
        ("🇩🇪", "Germany",   4, [1954,1974,1990,2014],      "#000000"),
        ("🇮🇹", "Italy",     4, [1934,1938,1982,2006],      "#0066CC"),
        ("🇦🇷", "Argentina", 3, [1978,1986,2022],           "#74ACDF"),
        ("🇫🇷", "France",    2, [1998,2018],                "#002395"),
        ("🇺🇾", "Uruguay",   2, [1930,1950],                "#5EB6E4"),
        ("🏴󠁧󠁢󠁥󠁮󠁧󠁿", "England",   1, [1966],                       "#CF142B"),
        ("🇪🇸", "Spain",     1, [2010],                     "#AA151B"),
    ]

    for flag, country, wins, years, color in _champions:
        trophies  = "🏆" * wins
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
        (1930,"🇺🇾","Uruguay"),(1934,"🇮🇹","Italy"),(1938,"🇮🇹","Italy"),
        (1950,"🇺🇾","Uruguay"),(1954,"🇩🇪","Germany"),(1958,"🇧🇷","Brazil"),
        (1962,"🇧🇷","Brazil"),(1966,"🏴󠁧󠁢󠁥󠁮󠁧󠁿","England"),(1970,"🇧🇷","Brazil"),
        (1974,"🇩🇪","Germany"),(1978,"🇦🇷","Argentina"),(1982,"🇮🇹","Italy"),
        (1986,"🇦🇷","Argentina"),(1990,"🇩🇪","Germany"),(1994,"🇧🇷","Brazil"),
        (1998,"🇫🇷","France"),(2002,"🇧🇷","Brazil"),(2006,"🇮🇹","Italy"),
        (2010,"🇪🇸","Spain"),(2014,"🇩🇪","Germany"),(2018,"🇫🇷","France"),
        (2022,"🇦🇷","Argentina"),
    ]

    for row_start in range(0, len(_all_winners), 4):
        row  = _all_winners[row_start:row_start + 4]
        cols = st.columns(len(row))
        for col, (yr, flg, name) in zip(cols, row):
            with col:
                st.markdown(
                    f"<div style='background:rgba(30,41,59,.8);border:1px solid rgba(255,255,255,.1);"
                    f"border-radius:12px;padding:.7rem;text-align:center;margin:.2rem 0'>"
                    f"<div style='font-size:.72rem;font-weight:700;color:#94A3B8;margin-bottom:.1rem'>{yr}</div>"
                    f"<div style='font-size:2rem;line-height:1.2'>{flg}</div>"
                    f"<div style='font-size:.82rem;font-weight:800;margin-top:.2rem;color:#F1F5F9'>{name}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # Future trophy boxes
    st.markdown("#### 🔮 What's Next?")
    fut_cols = st.columns(2)
    for col, (yr, host, msg) in zip(fut_cols, [
        (2026, "🇺🇸🇨🇦🇲🇽  USA · Canada · Mexico", "Who will write the next chapter?"),
        (2030, "🌍  100th Anniversary — Multi-Continent", "The future is unwritten."),
    ]):
        col.markdown(
            f"<div style='background:rgba(251,191,36,.08);border:2px dashed rgba(251,191,36,.45);"
            f"border-radius:16px;padding:1rem 1.1rem;text-align:center;margin:.2rem 0'>"
            f"<div style='font-size:.7rem;font-weight:800;color:#F59E0B;letter-spacing:.06em;"
            f"text-transform:uppercase;margin-bottom:.3rem'>{yr} World Cup</div>"
            f"<div style='font-size:2.2rem;line-height:1.2'>🏆</div>"
            f"<div style='font-size:.9rem;font-weight:900;margin-top:.35rem;color:#FCD34D'>TBD</div>"
            f"<div style='font-size:.75rem;color:#94A3B8;margin:.2rem 0;line-height:1.3'>{host}</div>"
            f"<div style='font-size:.7rem;color:#64748B;font-style:italic;margin-top:.15rem'>{msg}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Champions world map
    st.markdown("### 🗺️ Where Do Champions Come From?")
    _champ_iso3  = ["BRA","DEU","ITA","ARG","FRA","URY","GBR","ESP"]
    _champ_names = ["Brazil","Germany","Italy","Argentina","France","Uruguay","England","Spain"]
    _champ_wins  = [5, 4, 4, 3, 2, 2, 1, 1]
    _champ_text  = [f"{n} — {w}× champion" for n, w in zip(_champ_names, _champ_wins)]

    _fig_champ = go.Figure(go.Choropleth(
        locations=_champ_iso3, z=_champ_wins, locationmode="ISO-3",
        text=_champ_text,
        colorscale=[[0,"#92400E"],[0.5,"#F59E0B"],[1,"#FCD34D"]],
        showscale=False,
        marker_line_color="white", marker_line_width=0.8,
        hovertemplate="%{text}<extra></extra>",
    ))
    _fig_champ.update_layout(
        geo=dict(showframe=False, showcoastlines=True, coastlinecolor="#94A3B8",
                 showland=True, landcolor="#E2E8F0", showocean=True, oceancolor="#DBEAFE",
                 projection_type="natural earth"),
        margin=dict(l=0,r=0,t=0,b=0), height=300,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(_fig_champ, use_container_width=True, config={"staticPlot": True})

    # Geography stats
    st.markdown("#### Champion Geography")
    _geo_cols = st.columns(4)
    _geo_data = [
        ("🌍", "Europe", "5 nations, 12 titles", "Germany 4, Italy 4, France 2, England 1, Spain 1"),
        ("🌎", "South America", "3 nations, 10 titles", "Brazil 5, Argentina 3, Uruguay 2"),
        ("🌏", "Rest of World", "0 titles", "No champion yet from Africa, Asia, or Oceania"),
        ("🏆", "Most Recent", "Argentina 2022", "Lionel Messi's greatest moment in Qatar"),
    ]
    for col, (em, region, stat, note) in zip(_geo_cols, _geo_data):
        col.markdown(
            f"<div style='background:rgba(30,41,59,.8);border:1px solid rgba(255,255,255,.1);"
            f"border-radius:12px;padding:.75rem;text-align:center'>"
            f"<div style='font-size:1.6rem'>{em}</div>"
            f"<div style='font-size:.72rem;font-weight:700;color:#94A3B8;text-transform:uppercase;"
            f"letter-spacing:.04em;margin:.2rem 0'>{region}</div>"
            f"<div style='font-size:.92rem;font-weight:800;color:#FCD34D;line-height:1.2'>{stat}</div>"
            f"<div style='font-size:.68rem;color:#64748B;margin-top:.2rem;line-height:1.3'>{note}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — LEGENDS
# ═════════════════════════════════════════════════════════════════════════════
with _tabs[1]:
    _dyk_box(1)
    st.markdown("### ⭐ The Greatest Players in World Cup History")
    st.caption("These players made the whole world stop and watch.")

    # image_url and youtube_url are optional — included for future use
    _legends = [
        {"emoji":"🌟","name":"Pelé","flag":"🇧🇷","country":"Brazil","years":"1958–1970",
         "cups":"🏆🏆🏆","wow":"3-time World Cup champion — at 17, 21, and 30",
         "story":"The greatest of all time. Pelé won THREE World Cups and scored 77 goals for Brazil. He was so good that countries declared a ceasefire during a war just to watch him play!",
         "color":"#009C3B","image_url":None,"youtube_url":"https://www.youtube.com/results?search_query=Pele+1958+World+Cup+goals"},
        {"emoji":"🤌","name":"Diego Maradona","flag":"🇦🇷","country":"Argentina","years":"1982–1994",
         "cups":"🏆","wow":"Scored the 'Goal of the Century' and the 'Hand of God' in the same match",
         "story":"In 1986 he dribbled past 5 defenders and a goalkeeper for what was voted the greatest goal ever. In the same match, he also scored with his hand. Pure, electric, unforgettable.",
         "color":"#74ACDF","image_url":None,"youtube_url":"https://www.youtube.com/results?search_query=Maradona+Goal+of+the+Century+1986"},
        {"emoji":"🐐","name":"Lionel Messi","flag":"🇦🇷","country":"Argentina","years":"2006–2022",
         "cups":"🏆","wow":"Finally won it all in 2022 at age 35 — one of sport's greatest stories",
         "story":"Many say Messi is the best player ever. After four heartbreaking World Cups, he finally lifted the trophy in Qatar 2022. The whole world exhaled with him.",
         "color":"#74ACDF","image_url":None,"youtube_url":None},
        {"emoji":"🕺","name":"Zinédine Zidane","flag":"🇫🇷","country":"France","years":"1998–2006",
         "cups":"🏆","wow":"Scored twice in the 1998 final with his head",
         "story":"France's greatest ever player. Elegant, powerful, unstoppable. He scored two headers in the 1998 World Cup final on home soil in front of 80,000 fans. Became a national legend overnight.",
         "color":"#002395","image_url":None,"youtube_url":"https://www.youtube.com/results?search_query=Zidane+1998+World+Cup+final+headers"},
        {"emoji":"👽","name":"Ronaldo (R9)","flag":"🇧🇷","country":"Brazil","years":"1994–2006",
         "cups":"🏆🏆","wow":"Scored 15 World Cup goals — and came back from a mystery illness to win it",
         "story":"'The Phenomenon.' Unstoppable speed, deadly finishing. He collapsed with a mysterious seizure the night before the 2002 final — then went out and scored twice to win the cup.",
         "color":"#009C3B","image_url":None,"youtube_url":None},
        {"emoji":"🦜","name":"Garrincha","flag":"🇧🇷","country":"Brazil","years":"1958–1966",
         "cups":"🏆🏆","wow":"Never lost a World Cup match — ever",
         "story":"'Little Bird' Garrincha had legs bent from childhood illness, but could dribble past any defender in the world. He played in 12 World Cup games and never finished on the losing side. Brazil won both their titles with him on the field.",
         "color":"#009C3B","image_url":None,"youtube_url":None},
        {"emoji":"💣","name":"Gerd Müller","flag":"🇩🇪","country":"Germany","years":"1970–1974",
         "cups":"🏆","wow":"Scored 14 goals in just 2 World Cups — a record that stood for 40 years",
         "story":"'Der Bomber.' Short, stocky, and absolutely lethal in the penalty box. He scored 14 goals in just 13 World Cup games. His winner in the 1974 final gave West Germany the trophy. One of the purest goalscorers who ever lived.",
         "color":"#000000","image_url":None,"youtube_url":None},
        {"emoji":"🦅","name":"Franz Beckenbauer","flag":"🇩🇪","country":"Germany","years":"1966–1974",
         "cups":"🏆","wow":"Won as player AND later as coach — only the second person ever",
         "story":"Called 'Der Kaiser' (The Emperor). He changed how defenders play — attacking with elegance rather than just defending. One of only two people to ever win the World Cup as both player and coach.",
         "color":"#000000","image_url":None,"youtube_url":None},
        {"emoji":"🌀","name":"Johan Cruyff","flag":"🇳🇱","country":"Netherlands","years":"1974",
         "cups":"🥈","wow":"Invented 'Total Football' — a system that changed soccer forever",
         "story":"Cruyff's 1974 Netherlands team introduced Total Football, where every player could play every position. They dazzled the world. Even though they lost the final, their style influenced every great team that came after.",
         "color":"#FF4E00","image_url":None,"youtube_url":None},
        {"emoji":"💫","name":"Roberto Baggio","flag":"🇮🇹","country":"Italy","years":"1990–1998",
         "cups":"🥈","wow":"Carried Italy to the 1994 final — then missed the decisive penalty",
         "story":"'The Divine Ponytail.' Italy's greatest player of the 1990s. He dragged Italy through the 1994 World Cup almost single-handedly. Then, in the final, he missed the last penalty and stood with his head bowed. One of sport's most iconic moments.",
         "color":"#0066CC","image_url":None,"youtube_url":"https://www.youtube.com/results?search_query=Roberto+Baggio+1994+penalty+miss"},
        {"emoji":"🎩","name":"Xavi","flag":"🇪🇸","country":"Spain","years":"2002–2014",
         "cups":"🏆","wow":"The heartbeat of Spain's greatest-ever team",
         "story":"Xavi didn't run fast or score many goals — but no one saw the game better. His precise passing was the engine of Spain's tiki-taka system that won Euro 2008, the 2010 World Cup, and Euro 2012 in a row. He redefined what a midfielder could be.",
         "color":"#AA151B","image_url":None,"youtube_url":None},
        {"emoji":"🌈","name":"Andrés Iniesta","flag":"🇪🇸","country":"Spain","years":"2002–2018",
         "cups":"🏆","wow":"Scored the goal that won Spain their only World Cup",
         "story":"In the 2010 World Cup Final with the score 0–0 in extra time, Iniesta controlled a pass, turned, and scored the most important goal in Spanish soccer history. He dedicated it to a friend who had died young. One perfect moment.",
         "color":"#AA151B","image_url":None,"youtube_url":"https://www.youtube.com/results?search_query=Iniesta+2010+World+Cup+final+goal"},
        {"emoji":"🎭","name":"Ronaldinho","flag":"🇧🇷","country":"Brazil","years":"2002–2006",
         "cups":"🏆","wow":"Won the 2002 World Cup with the most creative goal of the tournament",
         "story":"The king of joy. Ronaldinho played with a smile so wide it felt like he was doing a magic show, not competing. His free kick that looped over England keeper David Seaman in 2002 left the whole world confused — including Seaman. Brazil won the trophy, and Ronaldinho was its brightest spark.",
         "color":"#009C3B","image_url":None,"youtube_url":None},
        {"emoji":"⚡","name":"Kylian Mbappé","flag":"🇫🇷","country":"France","years":"2018–present",
         "cups":"🏆","wow":"Won the World Cup at 19 — scored a hat-trick in the 2022 final",
         "story":"The fastest player in international soccer. He won the World Cup at just 19 and scored a hat-trick in the greatest final ever played — and still ended up on the losing side. Many people believe he will win the World Cup again.",
         "color":"#002395","image_url":None,"youtube_url":None},
    ]

    for leg in _legends:
        bg = leg["color"]
        yt_btn = ""
        if leg.get("youtube_url"):
            yt_btn = (
                f"<a href='{leg['youtube_url']}' target='_blank' "
                f"style='display:inline-block;background:rgba(239,68,68,.15);color:#FCA5A5;"
                f"border:1px solid rgba(239,68,68,.3);border-radius:8px;"
                f"padding:.18rem .55rem;font-size:.72rem;font-weight:700;text-decoration:none;"
                f"margin-top:.35rem'>▶ Watch Highlights</a>"
            )
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{bg}22,{bg}08);"
            f"border:1px solid {bg}44;border-radius:18px;"
            f"padding:1rem 1.25rem;margin:.6rem 0;"
            f"display:flex;align-items:flex-start;gap:1.1rem'>"
            f"<div style='text-align:center;min-width:60px'>"
            f"<div style='font-size:2.8rem;line-height:1'>{leg['emoji']}</div>"
            f"<div style='font-size:1.6rem;margin-top:.15rem'>{leg['flag']}</div>"
            f"</div>"
            f"<div style='flex:1'>"
            f"<div style='display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap'>"
            f"<span style='font-size:1.3rem;font-weight:900;color:#F1F5F9'>{leg['name']}</span>"
            f"<span style='font-size:.82rem;color:#94A3B8'>{leg['country']} · {leg['years']}</span>"
            f"<span style='font-size:1.1rem'>{leg['cups']}</span>"
            f"</div>"
            f"<div style='font-size:.8rem;font-weight:700;color:#FCD34D;margin:.2rem 0 .35rem'>✨ {leg['wow']}</div>"
            f"<div style='font-size:.91rem;color:#CBD5E1;line-height:1.55'>{leg['story']}</div>"
            f"{yt_btn}"
            f"</div></div>",
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — GREATEST UPSETS
# ═════════════════════════════════════════════════════════════════════════════
with _tabs[2]:
    _dyk_box(2)
    st.markdown("### 🔥 When the Impossible Happened")
    st.caption("The moments nobody saw coming — and the underdogs everyone fell in love with.")

    # Reusable data structure — add more entries here as needed
    _world_cup_upsets = [
        {
            "year":         "1950",
            "emoji":        "🇺🇸",
            "title":        "USA Shocks England",
            "matchup":      "USA 1–0 England",
            "upset_label":  "The result newspapers thought was a typo",
            "story":        "England were considered the best team in the world — they had invented the game, after all. Most sportswriters dismissed USA as amateurs. When the final score came through that USA had won 1–0, several newspapers assumed it was a telegraph error and printed '10–1 England' instead. It really happened. It still counts.",
            "color":        "#3B82F6",
        },
        {
            "year":         "1966",
            "emoji":        "🇰🇵",
            "title":        "North Korea Stuns Italy",
            "matchup":      "North Korea 1–0 Italy",
            "upset_label":  "Four-time champion Italy sent home by a mystery team",
            "story":        "Italy were four-time World Cup champions. North Korea were complete unknowns — so unknown that most fans in England didn't even know where the country was. Pak Doo-ik's winner sent Italy crashing out. When the Italian team returned home, fans pelted them with rotten vegetables at the airport.",
            "color":        "#EF4444",
        },
        {
            "year":         "1982",
            "emoji":        "🇩🇿",
            "title":        "Algeria Defeats West Germany",
            "matchup":      "Algeria 2–1 West Germany",
            "upset_label":  "The first African team to beat a European giant",
            "story":        "Algeria had never played in the World Cup before. West Germany were the reigning European champions and one of the best teams in the world. Algeria won 2–1 in one of the biggest shocks in World Cup history. Despite the win, Algeria was eliminated after Germany and Austria played a suspicious 1–0 draw that sent both teams through — a scandal that changed World Cup rules forever.",
            "color":        "#10B981",
        },
        {
            "year":         "1990",
            "emoji":        "🇨🇲",
            "title":        "Cameroon Reaches the Quarterfinals",
            "matchup":      "Beat Argentina, Romania, Colombia",
            "upset_label":  "38-year-old Roger Milla made the world fall in love",
            "story":        "Cameroon were the first African team to reach the quarterfinals. They beat defending champion Argentina in the opening game — a result nobody predicted. Then 38-year-old substitute Roger Milla came on, scored, and celebrated by dancing around the corner flag. The world went absolutely crazy for him. He became the oldest player ever to score at a World Cup.",
            "color":        "#10B981",
        },
        {
            "year":         "2002",
            "emoji":        "🇸🇳",
            "title":        "Senegal Beats Defending Champions France",
            "matchup":      "Senegal 1–0 France",
            "upset_label":  "The champion eliminated without scoring a single goal",
            "story":        "France had won the World Cup just four years earlier in 1998 — and arrived in 2002 with their squad from that triumph. Senegal were playing in their very first World Cup. Papa Bouba Diop scored. France failed to score in all three group games and were eliminated. The celebration in Dakar stretched for miles.",
            "color":        "#10B981",
        },
        {
            "year":         "2002",
            "emoji":        "🇰🇷",
            "title":        "South Korea Reaches the Semifinals",
            "matchup":      "Beat Spain, Italy, Portugal",
            "upset_label":  "The first Asian team to ever reach a World Cup semifinal",
            "story":        "Co-hosting with Japan, South Korea pulled off the most incredible run in World Cup history. They knocked out defending finalist Portugal, then Italy (four-time champions), then Spain (two-time champions) — all on penalty shootouts. When the final whistle blew against Spain, millions of red-clad fans in Seoul's streets made so much noise people thought an earthquake had hit. The first Asian team in a World Cup semifinal.",
            "color":        "#EF4444",
        },
        {
            "year":         "2014",
            "emoji":        "🇨🇷",
            "title":        "Costa Rica Wins the 'Group of Death'",
            "matchup":      "Finished above England, Italy & Uruguay",
            "upset_label":  "A group containing three former World Cup champions",
            "story":        "Group D contained England, Italy, and Uruguay — three former World Cup champions. Costa Rica were supposed to lose all three games. Instead, they topped the group — beating Uruguay 3–1 and Italy 1–0. Nobody had predicted them to win a single point. They eventually lost to the Netherlands on penalties in the quarterfinals after one of the most heroic defensive performances anyone had ever seen.",
            "color":        "#3B82F6",
        },
        {
            "year":         "2022",
            "emoji":        "🇸🇦",
            "title":        "Saudi Arabia Defeats Argentina",
            "matchup":      "Saudi Arabia 2–1 Argentina",
            "upset_label":  "Argentina had gone 36 games unbeaten. Ended in minutes.",
            "story":        "Argentina arrived as one of the favorites, on an unbeaten run of 36 games stretching back years. Messi scored a penalty to give them the lead. Then Saudi Arabia scored twice in five minutes of the second half. Argentina's bench sat in stunned silence. Saudi Arabia's players and bench went absolutely berserk. Saudi Arabia declared a national holiday the next day.",
            "color":        "#10B981",
        },
        {
            "year":         "2022",
            "emoji":        "🇲🇦",
            "title":        "Morocco Reaches the Semifinals",
            "matchup":      "Beat Belgium, Spain, Portugal",
            "upset_label":  "First African — and first Arab — team to reach a World Cup semifinal",
            "story":        "Morocco knocked out Belgium (World #2), Spain (former World Cup champions), and Portugal (home of Cristiano Ronaldo) on their way to history. When they beat Portugal in the quarterfinals, celebrations erupted across the Arab world, in Morocco, and in Moroccan communities around the globe. Their goalkeeper Yassine Bounou didn't concede a single goal in the knockout rounds until the semifinal.",
            "color":        "#F59E0B",
        },
    ]

    for m in _world_cup_upsets:
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
            f"⚽ {m['matchup']} · <em>{m['upset_label']}</em></div>"
            f"<div style='font-size:.94rem;color:#CBD5E1;line-height:1.6'>{m['story']}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — GREAT MOMENTS
# ═════════════════════════════════════════════════════════════════════════════
with _tabs[3]:
    _dyk_box(3)
    st.markdown("### 📖 Moments That Stopped the World")
    st.caption("Stories so incredible, they're still talked about generations later.")

    # youtube_url is optional — when present, shows a Watch Highlights button
    _moments = [
        {"year":"1950","emoji":"😱","title":"The Maracanazo","teams":"Uruguay vs Brazil",
         "verdict":"Uruguay wins — shocking Brazil in their own stadium",
         "story":"Brazil built the world's largest stadium for this game, held a parade before it, and everyone expected them to win. 200,000 fans packed in. Uruguay scored late and won 2–1. Brazil fans stood in silence. It's still called the greatest upset in World Cup history.",
         "color":"#EF4444","youtube_url":None},
        {"year":"1958","emoji":"🌟","title":"The Kid Who Changed Everything","teams":"Brazil vs Sweden (Final)",
         "verdict":"Brazil wins 5–2",
         "story":"A 17-year-old named Pelé played in the final and scored two incredible goals — including a chest trap and bicycle kick that left everyone speechless. After it went in, Sweden fans stood and applauded. A 17-year-old. In the World Cup final.",
         "color":"#009C3B","youtube_url":"https://www.youtube.com/results?search_query=Pele+1958+World+Cup+final+goals"},
        {"year":"1966","emoji":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","title":"England's Only World Cup","teams":"England vs Germany (Final)",
         "verdict":"England wins 4–2 at Wembley Stadium",
         "story":"England invented soccer, but they'd never won the World Cup. On home soil, in front of a roaring crowd at Wembley, they finally did it. Geoff Hurst scored a hat-trick — the only hat-trick ever in a World Cup final. England has never won it since.",
         "color":"#CF142B","youtube_url":"https://www.youtube.com/results?search_query=1966+World+Cup+final+England+Germany+highlights"},
        {"year":"1970","emoji":"🎨","title":"The Most Beautiful Team Ever","teams":"Brazil — entire tournament",
         "verdict":"Brazil wins with the greatest team in history",
         "story":"Brazil's 1970 team — with Pelé, Jairzinho, Rivelino, and Tostão — is still called the greatest soccer team ever assembled. They played with such joy, creativity, and skill that even rival fans cheered for them. Jairzinho scored in every single game.",
         "color":"#009C3B","youtube_url":None},
        {"year":"1986","emoji":"🤌","title":"The Goal of the Century","teams":"Argentina vs England",
         "verdict":"Argentina wins 2–1",
         "story":"In five seconds, Maradona took the ball in his own half, dribbled past five English defenders and the goalkeeper, and scored. Voted the Greatest Goal in World Cup history. In the same game, he also scored with his hand — which he later called 'the Hand of God.'",
         "color":"#74ACDF","youtube_url":"https://www.youtube.com/results?search_query=Maradona+Goal+of+the+Century+1986"},
        {"year":"1994","emoji":"💔","title":"Baggio's Missed Penalty","teams":"Italy vs Brazil (Final)",
         "verdict":"Brazil wins on penalties",
         "story":"Roberto Baggio was Italy's greatest player and hero. The World Cup final ended 0–0. In the shootout, Baggio stepped up for the final kick — if he missed, Italy lost. He missed over the bar. He stood alone with his head bowed while Brazil celebrated. One of sport's most heartbreaking images.",
         "color":"#0066CC","youtube_url":"https://www.youtube.com/results?search_query=Baggio+penalty+miss+1994+World+Cup+final"},
        {"year":"1998","emoji":"🇫🇷","title":"France's Greatest Night","teams":"France vs Brazil (Final)",
         "verdict":"France wins 3–0",
         "story":"France hosted the World Cup — and everyone expected Brazil to win. Instead, Zidane scored two headers before halftime in Paris. A country that had never won erupted. One million people celebrated on the Champs-Élysées. Zidane became a national hero overnight.",
         "color":"#002395","youtube_url":"https://www.youtube.com/results?search_query=Zidane+1998+World+Cup+final+headers"},
        {"year":"2006","emoji":"😲","title":"Zidane's Headbutt","teams":"France vs Italy (Final)",
         "verdict":"Italy wins on penalties",
         "story":"The World Cup Final was a masterpiece — until Zidane, in his last professional game ever, headbutted Italian defender Materazzi in the chest and was sent off with a red card. He walked past the World Cup trophy on his way out. The image of him passing that golden trophy — his head down — is one of the most surreal moments in sports.",
         "color":"#002395","youtube_url":"https://www.youtube.com/results?search_query=Zidane+headbutt+Materazzi+2006+World+Cup"},
        {"year":"2010","emoji":"🌍","title":"Africa Gets Its World Cup","teams":"South Africa hosts the world",
         "verdict":"Spain wins — but Africa wins too",
         "story":"For the first time ever, the World Cup was played in Africa. The sound of vuvuzelas filled stadiums across an entire continent. Spain won — but the real winner was Africa, proving to the world it could host the greatest sporting event on Earth.",
         "color":"#009B77","youtube_url":None},
        {"year":"2014","emoji":"🇩🇪","title":"The 7–1","teams":"Germany vs Brazil (Semifinal)",
         "verdict":"Germany wins 7–1 — Brazil stunned on home soil",
         "story":"Brazil hosted the World Cup and were favorites to win. In the semifinal in front of 60,000 Brazilian fans, Germany scored seven goals — five in 18 minutes. Brazilian fans cried in the stands. German fans barely celebrated out of respect. Called 'The Mineirazo.'",
         "color":"#000000","youtube_url":"https://www.youtube.com/results?search_query=Germany+Brazil+7-1+2014+World+Cup"},
        {"year":"2022","emoji":"🐐","title":"Messi's Moment","teams":"Argentina vs France (Final)",
         "verdict":"Argentina wins on penalties after 3–3 draw",
         "story":"Considered the greatest World Cup final ever played. Mbappé scored a hat-trick. Messi scored twice. France came back from 2–0 down to tie 3–3. Penalties decided it. When Argentina won, the entire continent of South America celebrated. Messi finally had his World Cup.",
         "color":"#74ACDF","youtube_url":"https://www.youtube.com/results?search_query=2022+World+Cup+final+Argentina+France+highlights"},
    ]

    for m in _moments:
        yt_btn = ""
        if m.get("youtube_url"):
            yt_btn = (
                f"<a href='{m['youtube_url']}' target='_blank' "
                f"style='display:inline-block;background:rgba(239,68,68,.15);color:#FCA5A5;"
                f"border:1px solid rgba(239,68,68,.3);border-radius:8px;"
                f"padding:.18rem .55rem;font-size:.72rem;font-weight:700;text-decoration:none;"
                f"margin-top:.4rem'>▶ Watch Highlights</a>"
            )
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
            f"{yt_btn}"
            f"</div>",
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — HOSTS
# ═════════════════════════════════════════════════════════════════════════════
with _tabs[4]:
    _dyk_box(4)
    st.markdown("### 🌍 Every Host Country — All 23 World Cups")
    st.caption("The World Cup travels the globe. Here's everywhere it has been — and where it's going next.")

    _hosts = [
        (1930,"🇺🇾","Uruguay",          "South America", "First ever World Cup! Uruguay was chosen to celebrate their 100th birthday as a nation. The beautiful La Centenario stadium was built just for this tournament."),
        (1934,"🇮🇹","Italy",             "Europe",        "Mussolini built new stadiums to show off Italy to the world. Italy won on home soil — but some say the refereeing was a bit suspicious..."),
        (1938,"🇫🇷","France",            "Europe",        "The last World Cup before World War II. Players had no idea it would be 12 years before they played again."),
        (1950,"🇧🇷","Brazil",            "South America", "Brazil built the Maracanã — then the world's largest stadium, holding 200,000 people. The final ended in heartbreak for Brazil."),
        (1954,"🇨🇭","Switzerland",       "Europe",        "Known for the highest-scoring World Cup ever — matches averaged over 5 goals per game. One quarterfinal ended 7–5!"),
        (1958,"🇸🇪","Sweden",            "Europe",        "Sweden hosted and made the final — but lost to a 17-year-old named Pelé. One of the most charming World Cups ever."),
        (1962,"🇨🇱","Chile",             "South America", "Chile had just had a massive earthquake, but rebuilt and hosted a remarkable World Cup. Brazil won again."),
        (1966,"🏴󠁧󠁢󠁥󠁮󠁧󠁿","England",          "Europe",        "England's only World Cup win. The Jules Rimet trophy was stolen and found by a dog named Pickles before the tournament!"),
        (1970,"🇲🇽","Mexico",            "North America", "The first World Cup shown in color on TV! Still considered the greatest World Cup tournament ever played."),
        (1974,"🇩🇪","West Germany",      "Europe",        "West Germany beat the Netherlands in the final. Johan Cruyff's Dutch team introduced Total Football — a style that changed soccer forever."),
        (1978,"🇦🇷","Argentina",         "South America", "Argentina won for the first time on home soil. Ticker tape streamed from the stands. One of the most emotional finals ever."),
        (1982,"🇪🇸","Spain",             "Europe",        "Italy won a dramatic tournament. 24 teams for the first time. Brazil played the most beautiful football but was eliminated before the final."),
        (1986,"🇲🇽","Mexico",            "North America", "Mexico hosted for the second time. Maradona had the greatest individual World Cup performance ever seen."),
        (1990,"🇮🇹","Italy",             "Europe",        "The lowest-scoring, most defensive World Cup ever. Famous for Pavarotti singing Nessun Dorma in the opening ceremony."),
        (1994,"🇺🇸","USA",               "North America", "America's first World Cup! 3.5 million fans attended. Brazil won their 4th title. Baggio's missed penalty became iconic."),
        (1998,"🇫🇷","France",            "Europe",        "France won on home soil for the first time. A million people celebrated in Paris. Zidane became a national hero overnight."),
        (2002,"🇯🇵🇰🇷","Japan & S. Korea","Asia",         "First World Cup in Asia and the first co-hosted by two countries. South Korea became the first Asian team to reach the semifinals."),
        (2006,"🇩🇪","Germany",           "Europe",        "Germany showed the world it could host in style. Zidane's shocking headbutt in the final ended his career."),
        (2010,"🇿🇦","South Africa",      "Africa",        "First World Cup on African soil. Vuvuzelas filled every stadium. Spain won their only World Cup."),
        (2014,"🇧🇷","Brazil",            "South America", "The World Cup of the 7–1. Germany demolished Brazil on Brazilian soil. Germany went on to win the title."),
        (2018,"🇷🇺","Russia",            "Europe",        "France won their second World Cup. Croatia, 4 million people strong, made it all the way to the final."),
        (2022,"🇶🇦","Qatar",             "Middle East",   "First World Cup in the Arab world. Played in November–December for the first time. Argentina won in the greatest final ever played."),
        (2026,"🇺🇸🇨🇦🇲🇽","USA · Canada · Mexico","North America","First World Cup with 48 teams! Three countries co-hosting for the first time. 16 venues, including MetLife Stadium for the final."),
    ]

    for yr, flag, country, continent, blurb in _hosts:
        is_current   = yr == 2026
        border_color = "#FCD34D" if is_current else "rgba(255,255,255,.1)"
        bg_color     = "rgba(251,191,36,.08)" if is_current else "rgba(30,41,59,.6)"
        now_badge    = (
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

    # Host countries map
    st.markdown("### 🗺️ The World Cup Travels the Globe")
    st.caption("Colors show how many times each country has hosted.")

    _host_counts = {
        "URY":1,"ITA":2,"FRA":2,"BRA":2,"CHE":1,"SWE":1,"CHL":1,"GBR":1,
        "MEX":3,"DEU":2,"ARG":1,"ESP":1,"USA":2,"JPN":1,"KOR":1,"ZAF":1,
        "RUS":1,"QAT":1,"CAN":1,
    }
    _hc_iso  = list(_host_counts.keys())
    _hc_vals = list(_host_counts.values())
    _hc_names= {"URY":"Uruguay","ITA":"Italy","FRA":"France","BRA":"Brazil",
                 "CHE":"Switzerland","SWE":"Sweden","CHL":"Chile","GBR":"England",
                 "MEX":"Mexico","DEU":"Germany","ARG":"Argentina","ESP":"Spain",
                 "USA":"USA","JPN":"Japan","KOR":"South Korea","ZAF":"South Africa",
                 "RUS":"Russia","QAT":"Qatar","CAN":"Canada"}
    _hc_text = [f"{_hc_names.get(c,'?')} — hosted {v}×" for c, v in zip(_hc_iso, _hc_vals)]

    _fig_host = go.Figure(go.Choropleth(
        locations=_hc_iso, z=_hc_vals, locationmode="ISO-3",
        text=_hc_text,
        colorscale=[[0,"#1D4ED8"],[0.5,"#3B82F6"],[1,"#93C5FD"]],
        showscale=True,
        colorbar=dict(title="Times Hosted", tickvals=[1,2,3], ticktext=["1×","2×","3×"],
                      len=0.6, thickness=12),
        marker_line_color="white", marker_line_width=0.8,
        hovertemplate="%{text}<extra></extra>",
    ))
    _fig_host.update_layout(
        geo=dict(showframe=False, showcoastlines=True, coastlinecolor="#94A3B8",
                 showland=True, landcolor="#E2E8F0", showocean=True, oceancolor="#DBEAFE",
                 projection_type="natural earth"),
        margin=dict(l=0,r=0,t=0,b=0), height=320,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(_fig_host, use_container_width=True)

    st.markdown(
        "<div style='background:rgba(251,191,36,.08);border:1px solid rgba(251,191,36,.3);"
        "border-radius:12px;padding:.7rem 1rem;margin:.4rem 0;font-size:.88rem;color:#CBD5E1'>"
        "⭐ <b style='color:#FCD34D'>2026 Special:</b> USA, Canada, and Mexico become the first three nations "
        "ever to co-host a World Cup together — making 2026 a unique moment in history.</div>",
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 6 — EVOLUTION
# ═════════════════════════════════════════════════════════════════════════════
with _tabs[5]:
    _dyk_box(5)
    st.markdown("### 📈 How the World Cup Has Grown")
    st.caption("From a small tournament in 1930 to the biggest sporting event on Earth.")

    _milestones = [
        ("1930","⚽","13 teams, 18 matches","The very first World Cup. Just 13 teams entered. Uruguay won, playing in front of 100,000 fans in Montevideo."),
        ("1954","📺","First on TV","For the first time, people could watch World Cup matches on television. Soccer became a global TV event overnight."),
        ("1966","🏆","Jules Rimet Trophy stolen!","The original trophy was stolen from an exhibition in London. A dog named Pickles found it wrapped in newspaper under a hedge. England went on to win the whole thing."),
        ("1970","🎨","First in color","Mexico 1970 was the first World Cup broadcast in color TV. The green grass, colorful kits, and golden trophy made it the most beautiful thing anyone had seen on TV."),
        ("1970","🔴","Red & yellow cards introduced","Before 1970, referees argued with players using words. In Mexico, referee Ken Aston invented colored cards — so everyone understood the decision instantly, in any language."),
        ("1982","🌍","Expanded to 24 teams","The World Cup grew from 16 to 24 teams. For the first time, a World Cup felt truly global."),
        ("1994","💰","3.6 billion viewers","The 1994 World Cup in the USA was watched by 3.6 billion people — over half the world's population at the time."),
        ("1998","🌐","Expanded to 32 teams","The World Cup grew to 32 teams — 8 groups of 4. This format lasted 24 years and produced some of the most memorable matches ever."),
        ("2026","🚀","Expanded to 48 teams!","This year's World Cup is the biggest ever — 48 teams, 104 matches, 16 venues across 3 countries. More countries than ever get a chance to make history."),
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
        ("Teams",          "13",     "48",       "teams in 1930",       "teams in 2026"),
        ("Matches",        "18",     "104",      "matches in 1930",     "matches in 2026"),
        ("Host Countries", "1",      "3",        "host in 1930",        "hosts in 2026"),
        ("TV Viewers",     "0",      "5B+",      "on TV in 1930",       "expected in 2026"),
        ("FIFA Members",   "41",     "211",      "FIFA members in 1930","FIFA members today"),
        ("Prize Money",    "$0",     "$625M+",   "prize money in 1930", "prize money in 2026"),
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
                f"<div><div style='font-size:1.5rem;font-weight:900;color:#64748B'>{then}</div>"
                f"<div style='font-size:.62rem;color:#475569'>{then_label}</div></div>"
                f"<div style='color:#94A3B8;font-size:1.3rem'>→</div>"
                f"<div><div style='font-size:1.5rem;font-weight:900;color:#34D399'>{now}</div>"
                f"<div style='font-size:.62rem;color:#6EE7B7'>{now_label}</div></div>"
                f"</div></div>",
                unsafe_allow_html=True,
            )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 7 — ANIMALS & MASCOTS
# ═════════════════════════════════════════════════════════════════════════════
with _tabs[6]:
    _dyk_box(6)

    # ── Team nicknames / animals ──────────────────────────────────────────────
    st.markdown("### 🦁 Famous Team Animals")
    st.caption("Every national team has an animal — or a creature — that represents them. Here are the best ones.")

    # (emoji, country, nickname, fun_fact)
    _team_animals = [
        ("🦁","England",      "Three Lions",          "England's three lions come from the royal coat of arms — used since King Richard the Lionheart in the 1190s. One of the most iconic symbols in sports."),
        ("🦅","USA",          "The Stars & Stripes",  "The bald eagle is America's national bird. It has eyesight so powerful it can spot a fish from a mile up in the sky. As fearless as any team in the tournament."),
        ("🦊","Algeria",      "Desert Foxes",         "The fennec fox is the clever, fast, cunning animal of the Sahara. It uses its enormous ears to hear insects underground. Perfect for a team known for surprising bigger opponents."),
        ("🐘","Ivory Coast",  "The Elephants",        "Elephants are the most powerful animals in Africa — and Ivory Coast's team has the strength and presence to match. They never forget a loss. They come back stronger."),
        ("🐓","France",       "Les Bleus / The Rooster","The Gallic Rooster is a centuries-old symbol of France — representing courage, pride, and the French spirit. The rooster crows to start each new day."),
        ("🦁","Morocco",      "Atlas Lions",          "Named after the Atlas Mountains that tower over Morocco. The Atlas Lion was a real lion species — bigger and more powerful than African lions — that once roamed North Africa."),
        ("🐆","Cameroon",     "Indomitable Lions",    "'Indomitable' means impossible to defeat, impossible to tame. Cameroon's lions have been shocking the world since 1990, when they beat Argentina and reached the quarterfinals."),
        ("🦅","Nigeria",      "Super Eagles",         "Nigeria's eagle is called 'super' for a reason — the team is known for electric attacking play and speed that makes defenders look like they're standing still."),
        ("🐆","South Africa", "Bafana Bafana",        "It means 'The Boys' in Zulu — the most affectionate team nickname in the tournament. South Africa hosted the 2010 World Cup and brought unbelievable energy."),
        ("🐺","Mexico",       "El Tri / The Wolf",    "Mexico's ancient Aztec traditions used powerful animals as warriors' symbols. The wolf represents cunning, speed, and the pack mentality of Mexico's intense team culture."),
        ("🐉","Wales",        "The Dragons",          "Wales has had a red dragon on its flag for over 1,500 years — one of the oldest national symbols in the world. The Dragon means power, mystery, and pride."),
        ("🦌","Germany",      "Die Mannschaft",       "Germany uses an eagle on its crest. But their nickname 'Die Mannschaft' means simply 'The Team' — because they believe in the collective over any individual."),
        ("🦁","Senegal",      "Teranga Lions",        "'Teranga' means hospitality in Wolof — the spirit of welcoming all people. Senegal's Lions are known for their warmth off the pitch and ferocity on it."),
        ("🐺","Serbia",       "Eagles & Wolves",      "Serbia's white eagle appears on their flag, but their passionate fan culture also celebrates the wolf. Serbia's supporters are among the most intense in Europe."),
        ("🦅","Ecuador",      "La Tri",               "Ecuador's Andean condor soars over volcanoes and cloud forests. With a wingspan of 10 feet, it's the world's largest flying bird. Ecuador's team soars to unexpected heights."),
        ("🐊","Australia",    "Socceroos",            "Socceroo = Soccer + Kangaroo. The kangaroo is the most recognizable Australian animal. It can only move forward — never backward. Perfect for an attacking team."),
        ("🦁","Ghana",        "Black Stars",          "Named after the black star on Ghana's flag — a symbol of African freedom and unity. The first sub-Saharan African country to gain independence, Ghana blazed a trail for a continent."),
        ("🌵","Saudi Arabia", "Green Falcons",        "The falcon is the national bird of Saudi Arabia — a symbol of courage, freedom, and speed. Falconry is a 2,000-year-old tradition in the Arabian Peninsula."),
        ("🦅","Iran",         "Team Melli",           "'Melli' means national. Iran's symbol is a lion and sun — used for hundreds of years. Iranian fans are among the most passionate and colorful in the world."),
        ("🌸","Japan",        "Samurai Blue",         "The samurai were Japan's legendary warriors for over 700 years. Samurai Blue captures both Japan's warrior spirit and their iconic blue kit. Disciplined, fearless, and precise."),
        ("🦁","Colombia",     "Los Cafeteros",        "Colombia's nickname refers to their coffee farmers — the heart of Colombian culture. But their lion crest and the roar of 50 million fans tells you they mean serious business."),
        ("🦋","Brazil",       "Seleção / Canarinho",  "'Canarinho' means Little Canary — named for their bright yellow kit. But Brazil's football is more like a carnival than a caged bird. The most free and beautiful style in the world."),
    ]

    for row_start in range(0, len(_team_animals), 3):
        row  = _team_animals[row_start:row_start + 3]
        cols = st.columns(len(row))
        for col, (em, country, nickname, fact) in zip(cols, row):
            with col:
                st.markdown(
                    f"<div style='background:rgba(30,41,59,.8);border:1px solid rgba(255,255,255,.1);"
                    f"border-radius:14px;padding:.85rem .8rem;margin:.3rem 0;height:100%'>"
                    f"<div style='font-size:2rem;line-height:1;margin-bottom:.3rem'>{em}</div>"
                    f"<div style='font-weight:900;font-size:.95rem;color:#F1F5F9'>{country}</div>"
                    f"<div style='font-size:.75rem;color:#FCD34D;font-weight:700;margin:.12rem 0'>{nickname}</div>"
                    f"<div style='font-size:.76rem;color:#94A3B8;line-height:1.45'>{fact}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # ── World Cup Mascots ─────────────────────────────────────────────────────
    st.markdown("### 🎭 Every World Cup Mascot")
    st.caption("Every World Cup since 1966 has had an official mascot. Here they all are.")

    # (year, emoji, name, host, description, image_url placeholder)
    _mascots = [
        ("1966","🦁","World Cup Willie",  "England",        "The very first World Cup mascot! A friendly lion wearing a Union Jack shirt. Willie became so popular that he was turned into toys, books, and songs. He changed how the world thought about World Cup branding.", None),
        ("1970","👦","Juanito",           "Mexico",         "A cheerful Mexican boy wearing the full national kit and a traditional sombrero. Juanito represented the joy and celebration of Mexico — a country that was putting on the tournament for the first time.", None),
        ("1974","👦👦","Tip and Tap",     "West Germany",   "Twin boys wearing the West Germany kit — one in white, one in a bib. They were named after common phrases in German children's songs. The first time a World Cup had two mascots!", None),
        ("1978","🤠","Gauchito",          "Argentina",      "A young boy dressed as a gaucho — the iconic Argentine cowboy of the Pampas grasslands, with a hat, scarf, and whip. A perfect symbol for a tournament won dramatically by Argentina on home soil.", None),
        ("1982","🍊","Naranjito",         "Spain",          "An orange! Literally, a smiling orange wearing a soccer kit. Named after Spain's famous citrus fruit. Naranjito became one of the most beloved mascots ever — simple, cheerful, and totally unique.", None),
        ("1986","🌶️","Pique",            "Mexico",         "A jalapeño pepper wearing a sombrero and moustache. Mexico had just suffered a devastating earthquake before the tournament, but Pique captured the country's determination to celebrate and move forward.", None),
        ("1990","🇮🇹","Ciao",            "Italy",          "The most artistic mascot ever — a person made entirely out of soccer balls, with an Italian tricolor body. 'Ciao' means both hello and goodbye in Italian. Simple, clever, and very Italian.", None),
        ("1994","🐶","Striker",           "USA",            "A cartoon dog kicking a soccer ball. Striker was created to introduce soccer to American kids — friendly, energetic, and perfectly American in his enthusiasm. The most toylike mascot ever.", None),
        ("1998","🐓","Footix",            "France",         "A blue rooster — France's national symbol — holding a soccer ball. Footix was designed to look both modern and traditionally French. He wore the French blue kit and had a cheerful, confident look.", None),
        ("2002","🛸","Ato, Kaz & Nik",   "Japan & S.Korea","Three futuristic aliens with soccer ball faces — representing the tournament's bold step into a new continent for the first time. Forward-looking and a little strange, just like the tournament itself!", None),
        ("2006","🦁","Goleo VI",          "Germany",        "A lion who spoke — and wore a jersey but no shorts! Goleo was paired with a talking ball named Pille. He divided opinion but became famous for his very German directness.", None),
        ("2010","🐆","Zakumi",            "South Africa",   "A leopard with dreadlocks and a South African green-and-gold kit. His name came from 'ZA' (South Africa's country code) and 'kumi' (the number 10 in many African languages). Full of African style.", None),
        ("2014","🐢","Fuleco",            "Brazil",         "An armadillo — one of the most unique animals in South America — that rolls into a ball shape (like a soccer ball). His name combined 'futebol' (soccer) and 'ecologia' (ecology), promoting environmental awareness.", None),
        ("2018","🐺","Zabivaka",          "Russia",         "'Zabivaka' means 'the one who scores' in Russian. A cool, confident wolf wearing sunglasses and a Russian kit. He became one of the most popular mascots in recent years — friendly, stylish, and a little mysterious.", None),
        ("2022","👻","La'eeb",            "Qatar",          "A floating, ghostlike creature made of a keffiyeh (traditional Arab headdress). 'La'eeb' means 'super-skilled player' in Arabic. Completely unlike any mascot before — imaginative and culturally meaningful.", None),
        ("2026","❓","TBD",              "USA·Canada·Mexico","The 2026 mascot hasn't been fully revealed yet! Whatever they choose will need to represent three countries, three cultures, and the biggest World Cup in history.", None),
    ]

    for yr, em, name, host, desc, img_url in _mascots:
        is_current = yr == "2026"
        border = "rgba(251,191,36,.4)" if is_current else "rgba(255,255,255,.1)"
        bg     = "rgba(251,191,36,.07)" if is_current else "rgba(30,41,59,.7)"
        st.markdown(
            f"<div style='background:{bg};border:1px solid {border};"
            f"border-radius:12px;padding:.7rem 1rem;margin:.4rem 0;"
            f"display:flex;align-items:flex-start;gap:.9rem'>"
            f"<div style='text-align:center;min-width:56px'>"
            f"<div style='font-size:2rem;line-height:1'>{em}</div>"
            f"<div style='font-size:.68rem;font-weight:800;color:#FCD34D;margin-top:.1rem'>{yr}</div>"
            f"</div>"
            f"<div style='flex:1'>"
            f"<div style='font-weight:900;font-size:1rem;color:#F1F5F9'>{name}"
            f"<span style='font-weight:400;font-size:.78rem;color:#64748B;margin-left:.5rem'>{host}</span></div>"
            f"<div style='font-size:.86rem;color:#CBD5E1;margin-top:.18rem;line-height:1.5'>{desc}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 8 — RECORDS
# ═════════════════════════════════════════════════════════════════════════════
with _tabs[7]:
    _dyk_box(7)
    st.markdown("### 📚 World Cup Records & Superlatives")
    st.caption("The fastest, the youngest, the biggest, the most dramatic — facts that make you say 'Whoa!'")

    _records = [
        {
            "emoji":    "👶",
            "category": "Youngest World Cup Champion",
            "holder":   "Pelé",
            "detail":   "17 years old · Brazil · 1958",
            "story":    "Most teenagers worry about school. Pelé won the World Cup. He remains the youngest person to ever win a World Cup — and he went on to win it two more times after that.",
            "color":    "#009C3B",
        },
        {
            "emoji":    "⚡",
            "category": "Fastest Goal Ever",
            "holder":   "Hakan Şükür (Turkey)",
            "detail":   "11 seconds · Turkey vs South Korea · 2002",
            "story":    "The referee had barely blown his whistle when Şükür received the ball and scored. 11 seconds. The match had barely started. It's the fastest goal in the entire history of the World Cup — and may never be beaten.",
            "color":    "#EF4444",
        },
        {
            "emoji":    "⚽",
            "category": "Most World Cup Goals (All Time)",
            "holder":   "Miroslav Klose (Germany)",
            "detail":   "16 goals across 4 World Cups (2002–2014)",
            "story":    "Klose played in 4 World Cups and scored 16 goals — more than any player in history, male or female. He broke Ronaldo's record with his 15th goal in the 7–1 semifinal against Brazil in 2014 — on Brazilian soil.",
            "color":    "#000000",
        },
        {
            "emoji":    "🎯",
            "category": "Most Goals in One Tournament",
            "holder":   "Just Fontaine (France)",
            "detail":   "13 goals in 6 games · 1958 World Cup",
            "story":    "Just Fontaine scored 13 goals in just one World Cup — a record that has stood for 66 years. He almost didn't even play; he was a last-minute replacement. No other player has scored more than 8 in a single tournament.",
            "color":    "#002395",
        },
        {
            "emoji":    "🏟️",
            "category": "Largest World Cup Crowd",
            "holder":   "Maracanã Stadium, Brazil",
            "detail":   "~200,000 fans · Uruguay vs Brazil · 1950 Final",
            "story":    "Brazil built the Maracanã to be the world's largest stadium for the 1950 World Cup. The final drew approximately 200,000 fans — a number impossible at any stadium today. Uruguay's win in front of that crowd is still called one of sport's greatest shocks.",
            "color":    "#EF4444",
        },
        {
            "emoji":    "🏆",
            "category": "Most World Cup Championships",
            "holder":   "Brazil",
            "detail":   "5 titles · 1958, 1962, 1970, 1994, 2002",
            "story":    "No country has won the World Cup more than Brazil. They are the only team to have qualified for every single World Cup (all 22). Their 1970 team is still considered the greatest team ever assembled.",
            "color":    "#009C3B",
        },
        {
            "emoji":    "👴",
            "category": "Oldest World Cup Player",
            "holder":   "Essam El-Hadary (Egypt)",
            "detail":   "45 years, 161 days · Egypt vs Saudi Arabia · 2018",
            "story":    "El-Hadary became the oldest player in World Cup history at 45 years old — and saved a penalty in the process! He told reporters before the game: 'Age is just a number. I still feel 25 inside.'",
            "color":    "#F59E0B",
        },
        {
            "emoji":    "🥅",
            "category": "Best World Cup Goalkeeper Performance",
            "holder":   "Lev Yashin (Soviet Union)",
            "detail":   "1958–1966 · The Black Spider",
            "story":    "Lev Yashin is the only goalkeeper to ever win the Ballon d'Or (world's best player award). At the 1966 World Cup, he saved everything thrown at him. He once said: 'A goalkeeper's job is to save shots. To save easy shots is normal. To save impossible shots — that is art.'",
            "color":    "#64748B",
        },
        {
            "emoji":    "🔥",
            "category": "Longest World Cup Unbeaten Run",
            "holder":   "Brazil",
            "detail":   "13 consecutive games unbeaten (1958–1966)",
            "story":    "Brazil went 13 World Cup games without losing — winning in 1958 and 1962, and reaching the group stage in 1966. That run included Pelé's 1958 debut win and the 1962 Garrincha-led triumph. Nobody has come close to matching it.",
            "color":    "#009C3B",
        },
        {
            "emoji":    "🌍",
            "category": "Most World Cups Hosted",
            "holder":   "Mexico",
            "detail":   "3 tournaments · 1970, 1986, and 2026",
            "story":    "Mexico is the only country to have hosted three separate World Cups. The 1970 edition at the Azteca — seen in color TV for the first time — is still considered the greatest World Cup ever. In 2026, Mexico makes history by co-hosting for the third time.",
            "color":    "#009C3B",
        },
        {
            "emoji":    "🎯",
            "category": "Most Appearances in the World Cup",
            "holder":   "Brazil",
            "detail":   "22 consecutive appearances · Every World Cup since 1930",
            "story":    "Brazil has appeared in every single World Cup since the first one in 1930 — an unbroken streak of 22 tournaments. No other country is even close. Brazil has played more World Cup games and scored more World Cup goals than any nation on Earth.",
            "color":    "#009C3B",
        },
        {
            "emoji":    "😲",
            "category": "Biggest Score in World Cup History",
            "holder":   "Hungary vs El Salvador",
            "detail":   "10–1 · 1982 World Cup in Spain",
            "story":    "Hungary scored 10 goals in a single match against El Salvador in 1982 — the largest margin of victory in World Cup history. László Kiss came off the bench and scored a hat-trick in just 7 minutes. El Salvador had qualified for only their second ever World Cup.",
            "color":    "#64748B",
        },
    ]

    for rec in _records:
        st.markdown(
            f"<div style='background:linear-gradient(135deg,{rec['color']}18,{rec['color']}06);"
            f"border:1px solid {rec['color']}44;border-radius:16px;"
            f"padding:1rem 1.2rem;margin:.65rem 0;"
            f"display:flex;align-items:flex-start;gap:1rem'>"
            f"<div style='text-align:center;min-width:52px'>"
            f"<div style='font-size:2.2rem;line-height:1'>{rec['emoji']}</div>"
            f"</div>"
            f"<div style='flex:1'>"
            f"<div style='font-size:.65rem;font-weight:800;color:{rec['color']};text-transform:uppercase;"
            f"letter-spacing:.07em;margin-bottom:.15rem'>{rec['category']}</div>"
            f"<div style='font-size:1.15rem;font-weight:900;color:#F1F5F9;line-height:1.2'>{rec['holder']}</div>"
            f"<div style='font-size:.78rem;color:#FCD34D;font-weight:700;margin:.2rem 0'>{rec['detail']}</div>"
            f"<div style='font-size:.91rem;color:#CBD5E1;line-height:1.55'>{rec['story']}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
