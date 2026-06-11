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
