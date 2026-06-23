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


def get_team_group_status(team: str, group_letter: str) -> dict:
    """Return a kid-friendly status dict for a team in the group stage.
    2026 format: top-2 from each group advance automatically; 8 best 3rd-place also advance."""
    standings = get_group_standings()
    group = standings.get(group_letter, [])

    for i, row in enumerate(group):
        if row['team'] != team:
            continue
        pos     = i + 1
        pts     = row['pts']
        played  = row['p']
        remaining = max(0, 3 - played)

        if played == 0:
            status, color = "Yet to play", "#64748B"
        elif played >= 3:
            if pos <= 2:
                status, color = "Advanced ✅", "#4ADE80"
            elif pos == 3:
                status, color = "Best 3rd — TBD", "#FCD34D"
            else:
                status, color = "Eliminated ❌", "#F87171"
        elif played == 2:
            if pts >= 6:
                status, color = "In great shape", "#4ADE80"
            elif pts >= 4:
                status, color = "In great shape", "#86EFAC"
            elif pts >= 3:
                status, color = "Still alive", "#FCD34D"
            elif pts >= 1:
                status, color = "Needs a win", "#FB923C"
            else:
                status, color = "In trouble", "#F87171"
        else:  # played == 1
            if pts == 3:
                status, color = "Strong start", "#4ADE80"
            elif pts == 1:
                status, color = "Still alive", "#FCD34D"
            else:
                status, color = "Needs points", "#FB923C"

        return {
            'position': pos,
            'pts': pts,
            'played': played,
            'remaining': remaining,
            'w': row['w'], 'd': row['d'], 'l': row['l'],
            'gf': row['gf'], 'ga': row['ga'], 'gd': row['gd'],
            'record': f"{row['w']}W-{row['d']}D-{row['l']}L",
            'status': status,
            'status_color': color,
            'group': group_letter,
        }

    return {'status': 'Unknown', 'status_color': '#94A3B8', 'position': 0, 'pts': 0,
            'played': 0, 'remaining': 3, 'record': '—'}
