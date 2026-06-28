import pandas as pd
from services.database import get_connection
from services.picks import get_all_picks, get_all_users


def pick_result(picked_team: str, home_team: str, away_team: str,
                home_score, away_score) -> float | None:
    if home_score is None or away_score is None or pd.isna(home_score) or pd.isna(away_score):
        return None
    hs, as_ = int(home_score), int(away_score)
    if hs == as_:
        return 0.5
    winner = home_team if hs > as_ else away_team
    return 1.0 if picked_team == winner else 0.0


def _countries_won_per_user() -> dict[int, int]:
    """Count distinct countries where each user earned points (win or draw)."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT p.user_id, COUNT(DISTINCT p.picked_team) AS cnt
        FROM picks p
        JOIN matches m ON p.match_id = m.id
        WHERE m.status = 'completed'
          AND m.home_score IS NOT NULL
          AND (
              m.home_score = m.away_score
              OR (m.home_score > m.away_score AND p.picked_team = m.home_team)
              OR (m.away_score > m.home_score AND p.picked_team = m.away_team)
          )
        GROUP BY p.user_id
    """).fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def get_leaderboard() -> pd.DataFrame:
    users = get_all_users()
    picks_df = get_all_picks()

    if picks_df.empty or (picks_df['status'] == 'scheduled').all():
        users['total_points'] = 0.0
        users['correct_picks'] = 0
        users['draw_points'] = 0
        users['total_picks'] = 0
        users['countries_won'] = 0
        return users.sort_values('total_points', ascending=False).reset_index(drop=True)

    picks_df['result'] = picks_df.apply(
        lambda r: pick_result(
            r['picked_team'], r['home_team'], r['away_team'],
            r['home_score'], r['away_score']
        ),
        axis=1
    )

    completed = picks_df[picks_df['result'].notna()]

    agg = completed.groupby('user_id').agg(
        total_points=('result', 'sum'),
        correct_picks=('result', lambda x: (x == 1.0).sum()),
        draw_points=('result', lambda x: (x == 0.5).sum()),
        total_picks=('result', 'count'),
    ).reset_index()

    board = users.merge(agg, left_on='id', right_on='user_id', how='left')
    board[['total_points', 'correct_picks', 'draw_points', 'total_picks']] = \
        board[['total_points', 'correct_picks', 'draw_points', 'total_picks']].fillna(0)
    board['total_points'] = board['total_points'].astype(float)
    board['correct_picks'] = board['correct_picks'].astype(int)
    board['draw_points'] = board['draw_points'].astype(int)
    board['total_picks'] = board['total_picks'].astype(int)

    won_map = _countries_won_per_user()
    board['countries_won'] = board['id'].map(won_map).fillna(0).astype(int)

    return board.sort_values('total_points', ascending=False).reset_index(drop=True)


def get_group_standings() -> dict:
    """Returns {group_letter: [list of team dicts sorted by pts]}.
    Each dict has: team, flag, group, p, w, d, l, gf, ga, pts, gd."""
    conn = get_connection()
    matches = pd.read_sql(
        "SELECT * FROM matches WHERE status='completed' ORDER BY match_date, kickoff_time_et",
        conn,
    )
    teams = pd.read_sql(
        "SELECT name, flag_emoji, group_letter FROM teams "
        "WHERE group_letter IS NOT NULL AND group_letter != ''",
        conn,
    )
    conn.close()

    stats: dict = {}
    for _, t in teams.iterrows():
        g = t['group_letter']
        if pd.isna(g) or g == '':
            continue
        stats.setdefault(g, {})[t['name']] = dict(
            team=t['name'], flag=t['flag_emoji'], group=g,
            p=0, w=0, d=0, l=0, gf=0, ga=0,
        )

    for _, m in matches.iterrows():
        ht, at = m['home_team'], m['away_team']
        hs, as_ = int(m['home_score']), int(m['away_score'])
        team_row = teams[teams['name'] == ht]
        if team_row.empty:
            continue
        g = team_row.iloc[0]['group_letter']
        if g not in stats or ht not in stats[g] or at not in stats[g]:
            continue
        h = stats[g][ht]; a = stats[g][at]
        h['p'] += 1; a['p'] += 1
        h['gf'] += hs; h['ga'] += as_
        a['gf'] += as_; a['ga'] += hs
        if hs > as_:
            h['w'] += 1; a['l'] += 1
        elif hs < as_:
            a['w'] += 1; h['l'] += 1
        else:
            h['d'] += 1; a['d'] += 1

    result = {}
    for g, td in sorted(stats.items()):
        df = pd.DataFrame(list(td.values()))
        df['pts'] = df['w'] * 3 + df['d']
        df['gd']  = df['gf'] - df['ga']
        df = df.sort_values(
            ['pts', 'gd', 'gf', 'team'],
            ascending=[False, False, False, True],
        ).reset_index(drop=True)
        result[g] = df.to_dict('records')

    return result


def _classify_status(pos: int, rows: list[dict]) -> tuple[str, str]:
    """Conservative group-stage status label for one team.

    pos  : 0-indexed position in a sorted standings list (0 = currently 1st).
    rows : all team dicts for the group with 'pts' and 'p' (played) fields.
    Returns (label, hex_color).

    2026 format: top-2 per group advance automatically.
    Conservative: never marks Advanced/Eliminated unless mathematically certain
    (ignores tiebreakers — call it a draw when uncertain).
    """
    row    = rows[pos]
    pts    = row['pts']
    played = row['p']
    rem    = max(0, 3 - played)
    my_max = pts + rem * 3

    n = len(rows)
    other_curr = [rows[j]['pts']                                        for j in range(n) if j != pos]
    other_max  = [rows[j]['pts'] + max(0, 3 - rows[j]['p']) * 3        for j in range(n) if j != pos]

    if played == 0:
        return "🟡 Still alive", "#94A3B8"

    # ── Group fully complete — pos already reflects tiebreakers from sort ─────
    if all(r['p'] >= 3 for r in rows):
        if pos == 0:
            return "🔒 Locked 1st", "#4ADE80"
        elif pos == 1:
            return "🔒 Locked 2nd", "#4ADE80"
        elif pos == 2:
            return "🟡 3rd place", "#FCD34D"   # may advance as best 3rd-place team
        else:
            return "❌ Eliminated", "#F87171"

    # ── Eliminated ────────────────────────────────────────────────────────────
    # At least 2 other teams already have strictly more pts than my maximum.
    # Points only increase, so those leads are permanent.
    if sum(1 for p in other_curr if p > my_max) >= 2:
        return "❌ Eliminated", "#F87171"

    # ── Guaranteed top-2 ─────────────────────────────────────────────────────
    # At most 1 other team can ever surpass my CURRENT pts (worst case for me).
    can_pass_me = sum(1 for mx in other_max if mx > pts)
    if can_pass_me <= 1:
        # Locked 1st: no other team can even reach my current pts
        if all(mx < pts for mx in other_max):
            return "🔒 Locked 1st", "#4ADE80"
        # Locked 2nd: guaranteed top-2 AND I can never overtake current 1st place
        if pos > 0 and my_max < rows[0]['pts']:
            return "🔒 Locked 2nd", "#4ADE80"
        return "✅ Advanced", "#4ADE80"

    # ── Currently in top 2 but not guaranteed ────────────────────────────────
    if pos < 2:
        return "🟢 In good shape", "#86EFAC"

    # ── Not in top 2 — still has a path ──────────────────────────────────────
    # Still alive: can surpass 2nd place's current points with own wins alone
    if my_max > rows[1]['pts']:
        return "🟡 Still alive", "#FCD34D"

    # Needs help: can only tie 2nd place on pts — needs tiebreaker + other results
    return "🟠 Needs help", "#FB923C"


def classify_group_statuses(group_rows: list[dict]) -> list[dict]:
    """Add 'status' and 'status_color' keys to every team dict in a sorted group list.

    Mutates in-place and also returns the list, so callers can do:
        rows = classify_group_statuses(get_group_standings()['A'])
    """
    for i, row in enumerate(group_rows):
        lbl, col = _classify_status(i, group_rows)
        row['status']       = lbl
        row['status_color'] = col
    return group_rows


def get_combined_leaderboard() -> list[dict]:
    """Merge group stage + KO Live scores into one sorted list.

    Columns per user: user_id, name, avatar, theme_color,
                      group_pts, ko_live_pts, total_pts, rank
    Total = group_pts + ko_live_pts (Full Bracket excluded from display).
    """
    from services.ko_picks import get_ko_live_leaderboard

    group_board = get_leaderboard()
    ko_map = {s["user_id"]: s for s in get_ko_live_leaderboard()}

    result = []
    for _, row in group_board.iterrows():
        uid = int(row["id"])
        grp = float(row["total_points"])
        ko  = float(ko_map.get(uid, {}).get("total", 0.0))
        result.append({
            "user_id":     uid,
            "name":        str(row["name"]),
            "avatar":      str(row["avatar"]),
            "theme_color": str(row.get("theme_color", "")),
            "group_pts":   grp,
            "ko_live_pts": ko,
            "total_pts":   grp + ko,
        })

    result.sort(key=lambda x: (-x["total_pts"], x["name"]))
    for i, r in enumerate(result):
        r["rank"] = i + 1
    return result


def get_team_group_status(team: str, group_letter: str) -> dict:
    """Return a kid-friendly status dict for a team in the group stage.
    2026 format: top-2 from each group advance automatically."""
    standings = get_group_standings()
    group     = standings.get(group_letter, [])

    for i, row in enumerate(group):
        if row['team'] != team:
            continue
        status, color = _classify_status(i, group)
        return {
            'position':  i + 1,
            'pts':       row['pts'],
            'played':    row['p'],
            'remaining': max(0, 3 - row['p']),
            'w': row['w'], 'd': row['d'], 'l': row['l'],
            'gf': row['gf'], 'ga': row['ga'], 'gd': row['gd'],
            'record':       f"{row['w']}W-{row['d']}D-{row['l']}L",
            'status':       status,
            'status_color': color,
            'group':        group_letter,
        }

    return {
        'status': 'Unknown', 'status_color': '#94A3B8',
        'position': 0, 'pts': 0, 'played': 0, 'remaining': 3, 'record': '—',
    }
