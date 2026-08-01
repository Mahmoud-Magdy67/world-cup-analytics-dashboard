"""
data/real_wc26.py — Kaggle-only loader for the WC26 dashboard.

Source: https://www.kaggle.com/datasets/mominullptr/fifa-world-cup-2026-dataset
        CC0-1.0 (public domain). 12 CSVs in data/kaggle_wc26/, 9,369 total rows.
        Verified stats from sofascore.com + FIFA.com.

This module REPLACES the prior AWS Athena dependency (data/athena.py). Every
page calls these loaders; they read the Kaggle CSVs directly with pandas.

Public loaders (function names preserved from the prior athena-backed version
so existing `from data.real_wc26 import ...` imports in pages/*.py keep working):
  Tournament:
    get_real_wc26_data_source_status  -> DataSourceStatus
    get_real_wc26_summary             -> 1-row tournament KPIs
    get_real_wc26_outcome_counts      -> per-stage W/D/L + goals + a Total row
  Teams:
    get_real_wc26_teams               -> 48 teams (ids + names)
    get_real_wc26_team_strength       -> 48 teams + elo/fifa_rank/manager/market_value/wc26_goals
    get_real_wc26_team_stats          -> per-team W/D/L/goals_for/against
    get_real_wc26_match_team_stats    -> per-team avg in-match stats (possession, shots, ...)
    get_real_wc26_xg_by_team          -> per-team xG for/against
  Matches:
    get_real_wc26_matches             -> 104 matches (scores, xG, POTM, GKs, referee)
    get_real_wc26_matches_enriched    -> matches + per-team in-match stats (wide form)
    get_real_wc26_venues              -> 16 venues
    get_real_wc26_referees            -> 28 referees
    get_real_wc26_knockout_bracket    -> 32 knockout matches with winner
  Players:
    get_real_wc26_players             -> 1248 players (squad metadata)
    get_real_wc26_player_stats        -> 1248 players (tournament stats)
  NEW (Kaggle CSVs that the prior layer ignored):
    get_real_wc26_match_events        -> 834 events (goals/assists/cards/VAR) with minute
    get_real_wc26_match_lineups       -> 5408 lineup rows (XI + bench + minutes)
    get_real_wc26_match_prediction_features -> 104 rows x 66 cols of pre-match features

Stage ordering (used by chart axes in overview/matches/predictions pages):
  STAGE_ORDER = ["Group Stage", "Round of 32", "Round of 16",
                 "Quarter-finals", "Semi-finals", "Third-place match", "Final"]
"""
from dataclasses import dataclass
from typing import Optional, Dict
import pandas as pd
from data._kaggle_loader import _read, _teams, _referees_df, _venues, team_name, team_code


STAGE_ORDER = [
    "Group Stage",
    "Round of 32",
    "Round of 16",
    "Quarter-finals",
    "Semi-finals",
    "Third-place match",
    "Final",
]


@dataclass(frozen=True)
class DataSourceStatus:
    mode: str
    athena_enabled: bool
    note: str
    tables_available: Optional[Dict[str, int]] = None


# ---------------------------------------------------------------------------
# Data source status
# ---------------------------------------------------------------------------
def get_real_wc26_data_source_status() -> DataSourceStatus:
    """Health check: counts rows in each Kaggle CSV. No AWS dependency."""
    counts: Dict[str, int] = {}
    try:
        counts["teams"] = len(_teams())
        counts["matches_detailed"] = len(_read("matches_detailed"))
        counts["match_events"] = len(_read("match_events"))
        counts["match_lineups"] = len(_read("match_lineups"))
        counts["match_team_stats"] = len(_read("match_team_stats"))
        counts["match_prediction_features"] = len(_read("match_prediction_features"))
        counts["player_stats"] = len(_read("player_stats"))
        counts["squads_and_players"] = len(_read("squads_and_players"))
        counts["venues"] = len(_venues())
        counts["referees"] = len(_referees_df())
        return DataSourceStatus(
            "kaggle_local",
            False,
            "Local Kaggle WC26 dataset (mominullptr/fifa-world-cup-2026-dataset, CC0-1.0). "
            "12 CSVs, 9,369 rows. No AWS / network dependency — fully self-contained.",
            counts,
        )
    except Exception as e:
        return DataSourceStatus("kaggle_error", False, f"Kaggle CSV read failed: {str(e)[:150]}", None)


# ---------------------------------------------------------------------------
# Tournament KPIs (Overview page)
# ---------------------------------------------------------------------------
def get_real_wc26_summary() -> pd.DataFrame:
    """One-row tournament KPIs: total_matches, total_goals, avg_goals_per_match,
    winner, runner_up, final_score, result_type, final_date, final_venue, final_city."""
    md = _read("matches_detailed")
    md = md.copy()
    md["date"] = pd.to_datetime(md["date"], errors="coerce")

    final = md[md["stage_name"] == "Final"]
    if final.empty:
        winner, runner, final_score, final_type = "", "", "", ""
        final_date, final_venue, final_city = "", "", ""
    else:
        f = final.iloc[0]
        if int(f["home_score"]) > int(f["away_score"]):
            winner, runner = f["home_team_name"], f["away_team_name"]
        elif int(f["away_score"]) > int(f["home_score"]):
            winner, runner = f["away_team_name"], f["home_team_name"]
        else:
            winner = runner = "draw"
        # Penalty shootout outcome?
        if pd.notna(f.get("home_penalty_score")) and pd.notna(f.get("away_penalty_score")):
            winner = f["home_team_name"] if int(f["home_penalty_score"]) > int(f["away_penalty_score"]) else f["away_team_name"]
            runner = f["away_team_name"] if winner == f["home_team_name"] else f["home_team_name"]
            final_type = "Penalty"
        else:
            final_type = f.get("result_type", "")
        final_score = f"{int(f['home_score'])}-{int(f['away_score'])}"
        final_date = str(f["date"].date()) if pd.notna(f["date"]) else ""
        final_venue = f.get("stadium_name", "")
        final_city = f.get("city", "")

    # Tournament total goals = regulation + extra time only.
    # Per the canonical FIFA/ESPN convention, penalty-shootout goals are a
    # tiebreaker, not field goals, so we exclude the 25 PK Shootout Goal
    # events. The PK count is exposed separately so the UI can show it.
    me = _read("match_events")
    team_goals = int((me["event_type"] == "Goal").sum())      # 308
    pk_goals = int((me["event_type"] == "Penalty Shootout Goal").sum())  # 25
    total_goals = team_goals
    n_matches = int(len(md))

    return pd.DataFrame([{
        "total_matches": n_matches,
        "total_goals": total_goals,
        "total_goals_with_pk": team_goals + pk_goals,           # 333 (full count incl. PK)
        "penalty_shootout_goals": pk_goals,                     # 25 (tiebreaker only)
        "avg_goals_per_match": round(total_goals / n_matches, 2) if n_matches else 0.0,
        "winner": winner,
        "runner_up": runner,
        "final_score": final_score,
        "result_type": final_type,
        "final_date": final_date,
        "final_venue": final_venue,
        "final_city": final_city,
    }])


def get_real_wc26_outcome_counts() -> pd.DataFrame:
    """Per-stage outcome counts (matches, home_wins, away_wins, draws, goals)
    plus a Total row. Mirrors the v_outcome_counts Athena view."""
    md = _read("matches_detailed").copy()
    md["home_score"] = pd.to_numeric(md["home_score"], errors="coerce")
    md["away_score"] = pd.to_numeric(md["away_score"], errors="coerce")
    md["total_goals"] = md["home_score"].fillna(0) + md["away_score"].fillna(0)
    md["home_win"] = (md["home_score"] > md["away_score"]).astype(int)
    md["away_win"] = (md["away_score"] > md["home_score"]).astype(int)
    md["draw"] = (md["home_score"] == md["away_score"]).astype(int)

    rows = []
    for stage in STAGE_ORDER:
        s = md[md["stage_name"] == stage]
        if s.empty:
            continue
        rows.append({
            "stage_name": stage,
            "matches": len(s),
            "home_wins": int(s["home_win"].sum()),
            "away_wins": int(s["away_win"].sum()),
            "draws": int(s["draw"].sum()),
            "goals": int(s["total_goals"].sum()),
        })
    if not rows:
        return pd.DataFrame(columns=["stage_name", "matches", "home_wins", "away_wins", "draws", "goals"])

    df = pd.DataFrame(rows)
    total = pd.DataFrame([{
        "stage_name": "Total",
        "matches": int(df["matches"].sum()),
        "home_wins": int(df["home_wins"].sum()),
        "away_wins": int(df["away_wins"].sum()),
        "draws": int(df["draws"].sum()),
        "goals": int(df["goals"].sum()),
    }])
    return pd.concat([df, total], ignore_index=True)


# ---------------------------------------------------------------------------
# Teams (Teams / Overview pages)
# ---------------------------------------------------------------------------
def get_real_wc26_teams() -> pd.DataFrame:
    """48 teams with id, name, FIFA code, group, confederation."""
    t = _teams()[["team_id", "team_name", "fifa_code", "group_letter", "confederation"]]
    return t.sort_values("team_name").reset_index(drop=True)


def get_real_wc26_team_strength() -> pd.DataFrame:
    """48 teams + Elo, FIFA ranking, manager, market value, plus WC26
    goals/assists totals aggregated from match_events."""
    t = _teams().copy()
    # WC26 goals/assists per team from match_events
    me = _read("match_events")
    goals = me[me["event_type"] == "Goal"].groupby("team_id").size().rename("wc26_goals")
    assists = me[me["event_type"] == "Assist"].groupby("team_id").size().rename("wc26_assists")
    t = t.merge(goals, on="team_id", how="left").merge(assists, on="team_id", how="left")
    t["wc26_goals"] = t["wc26_goals"].fillna(0).astype(int)
    t["wc26_assists"] = t["wc26_assists"].fillna(0).astype(int)

    # Squad market value: prefer teams.csv if present for this team
    # (can be overridden with Transfermarkt-corrected values),
    # else fall back to match_prediction_features.
    if "squad_market_value_eur" in t.columns:
        # Teams with NaN in teams.csv will fall back below
        pass
    else:
        t["squad_market_value_eur"] = pd.NA

    # Fill NaN values from match_prediction_features
    has_val = t["squad_market_value_eur"].notna()
    if not has_val.all():
        mpf = _read("match_prediction_features")
        home_val = mpf.groupby("home_team_id")["home_squad_total_value_eur"].max().rename("squad_market_value_eur_home")
        away_val = mpf.groupby("away_team_id")["away_squad_total_value_eur"].max().rename("squad_market_value_eur_away")
        t = t.merge(home_val, left_on="team_id", right_index=True, how="left")
        t = t.merge(away_val, left_on="team_id", right_index=True, how="left")
        fallback = t[["squad_market_value_eur_home", "squad_market_value_eur_away"]].max(axis=1)
        t["squad_market_value_eur"] = t["squad_market_value_eur"].fillna(fallback)
        t = t.drop(columns=["squad_market_value_eur_home", "squad_market_value_eur_away"])

    return t.sort_values("elo_rating", ascending=False).reset_index(drop=True)


def get_real_wc26_team_stats() -> pd.DataFrame:
    """Per-team W/D/L/goals_for/against computed from matches_detailed."""
    md = _read("matches_detailed").copy()
    md["home_score"] = pd.to_numeric(md["home_score"], errors="coerce")
    md["away_score"] = pd.to_numeric(md["away_score"], errors="coerce")

    home = md[["home_team_name", "home_score", "away_score"]].rename(columns={
        "home_team_name": "team", "home_score": "gf", "away_score": "ga",
    })
    home["W"] = (home["gf"] > home["ga"]).astype(int)
    home["D"] = (home["gf"] == home["ga"]).astype(int)
    home["L"] = (home["gf"] < home["ga"]).astype(int)

    away = md[["away_team_name", "home_score", "away_score"]].rename(columns={
        "away_team_name": "team", "away_score": "gf", "home_score": "ga",
    })
    away["W"] = (away["gf"] > away["ga"]).astype(int)
    away["D"] = (away["gf"] == away["ga"]).astype(int)
    away["L"] = (away["gf"] < away["ga"]).astype(int)

    combined = pd.concat([home, away], ignore_index=True)
    agg = combined.groupby("team").agg(
        matches=("team", "size"),
        goals_for=("gf", "sum"),
        goals_against=("ga", "sum"),
        W=("W", "sum"),
        D=("D", "sum"),
        L=("L", "sum"),
    ).reset_index()
    agg["goal_difference"] = agg["goals_for"] - agg["goals_against"]
    return agg.sort_values(["goals_for", "goal_difference"], ascending=[False, False]).reset_index(drop=True)


def get_real_wc26_match_team_stats() -> pd.DataFrame:
    """Per-team average in-match stats (possession, shots, corners, etc.)
    aggregated from match_team_stats.csv. Replaces the prior
    v_match_team_stats_agg Athena view."""
    mts = _read("match_team_stats").copy()
    t = _teams()[["team_id", "team_name"]]
    agg = mts.groupby("team_id").agg(
        matches=("match_id", "size"),
        avg_possession=("possession_pct", "mean"),
        avg_shots=("total_shots", "mean"),
        avg_shots_on_target=("shots_on_target", "mean"),
        avg_corners=("corners", "mean"),
        avg_fouls=("fouls", "mean"),
        avg_offsides=("offsides", "mean"),
        avg_saves=("saves", "mean"),
    ).reset_index().round(2)
    agg = agg.merge(t, on="team_id", how="left")
    return agg.sort_values("team_name").reset_index(drop=True)


def get_real_wc26_xg_by_team() -> pd.DataFrame:
    """Per-team xG for/against aggregated from matches_detailed (home_xg, away_xg).
    Mirrors the prior get_xg_by_team() Athena query."""
    md = _read("matches_detailed").copy()
    md["home_xg"] = pd.to_numeric(md["home_xg"], errors="coerce")
    md["away_xg"] = pd.to_numeric(md["away_xg"], errors="coerce")

    home = md[["home_team_name", "home_xg", "away_xg"]].rename(columns={
        "home_team_name": "team", "home_xg": "xg_for", "away_xg": "xg_against",
    })
    away = md[["away_team_name", "home_xg", "away_xg"]].rename(columns={
        "away_team_name": "team", "away_xg": "xg_for", "home_xg": "xg_against",
    })
    combined = pd.concat([home, away], ignore_index=True)
    agg = combined.groupby("team").agg(
        matches=("team", "size"),
        xg_for=("xg_for", "sum"),
        xg_against=("xg_against", "sum"),
    ).reset_index().round(2)
    return agg.sort_values("xg_for", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Matches (Matches page)
# ---------------------------------------------------------------------------
def get_real_wc26_matches() -> pd.DataFrame:
    """104 matches from matches_detailed with stage, scores, xG, venue,
    referee, POTM, GKs. Sorted by date then match_id."""
    md = _read("matches_detailed").copy()
    md["date"] = pd.to_datetime(md["date"], errors="coerce")
    return md.sort_values(["date", "match_id"], kind="stable").reset_index(drop=True)


def get_real_wc26_matches_enriched() -> pd.DataFrame:
    """Wide-form matches joined with per-team in-match stats (possession,
    shots, corners, fouls, saves) and venue capacity/lat/lon. Mirrors the
    prior v_matches_enriched Athena view.

    Columns expected by pages/matches.py:
      match_id, date, stage_name, home_team_name, home_fifa_code, home_team_id,
      away_team_name, away_fifa_code, away_team_id,
      home_score, away_score, home_penalty_score, away_penalty_score,
      home_xg, away_xg, referee_name,
      stadium_name, city, country,
      venue_capacity, venue_latitude, venue_longitude, venue_elevation,
      home_possession, home_shots, home_shots_on_target,
      home_corners, home_fouls, home_saves,
      away_possession, away_shots, away_shots_on_target,
      away_corners, away_fouls, away_saves
    """
    md = _read("matches_detailed").copy()
    md["date"] = pd.to_datetime(md["date"], errors="coerce")
    # matches_detailed has names + fifa codes but not team_id; pull ids from teams.csv
    t = _teams()[["team_id", "fifa_code"]]
    md = md.merge(t.rename(columns={"team_id": "home_team_id", "fifa_code": "home_fifa_code"}),
                  on="home_fifa_code", how="left")
    md = md.merge(t.rename(columns={"team_id": "away_team_id", "fifa_code": "away_fifa_code"}),
                  on="away_fifa_code", how="left")
    # Wide-pivot match_team_stats: rows of (match_id, team_id, ...) -> home_/away_ cols
    mts = _read("match_team_stats").copy()
    home_stats = mts.rename(columns={
        "team_id": "home_team_id", "possession_pct": "home_possession",
        "total_shots": "home_shots", "shots_on_target": "home_shots_on_target",
        "corners": "home_corners", "fouls": "home_fouls", "saves": "home_saves",
        "offsides": "home_offsides",
    })[["match_id", "home_team_id", "home_possession", "home_shots", "home_shots_on_target",
        "home_corners", "home_fouls", "home_saves", "home_offsides"]]
    away_stats = mts.rename(columns={
        "team_id": "away_team_id", "possession_pct": "away_possession",
        "total_shots": "away_shots", "shots_on_target": "away_shots_on_target",
        "corners": "away_corners", "fouls": "away_fouls", "saves": "away_saves",
        "offsides": "away_offsides",
    })[["match_id", "away_team_id", "away_possession", "away_shots", "away_shots_on_target",
        "away_corners", "away_fouls", "away_saves", "away_offsides"]]

    v = _venues().rename(columns={"elevation_meters": "venue_elevation"})
    out = (md
           .merge(home_stats, on=["match_id", "home_team_id"], how="left")
           .merge(away_stats, on=["match_id", "away_team_id"], how="left")
           .merge(v[["stadium_name", "capacity", "latitude", "longitude", "venue_elevation"]],
                  on="stadium_name", how="left")
           .rename(columns={"capacity": "venue_capacity",
                            "latitude": "venue_latitude",
                            "longitude": "venue_longitude"}))
    return out.sort_values(["date", "match_id"], kind="stable").reset_index(drop=True)


def get_real_wc26_venues() -> pd.DataFrame:
    """16 venues with capacity, lat/lon, elevation."""
    v = _venues().rename(columns={"elevation_meters": "elevation"})
    return v.sort_values("capacity", ascending=False).reset_index(drop=True)


def get_real_wc26_referees() -> pd.DataFrame:
    """28 referees with country and avg cards per game."""
    return _referees_df().sort_values("avg_cards_per_game", ascending=False).reset_index(drop=True)


def get_real_wc26_knockout_bracket() -> pd.DataFrame:
    """Knockout-stage matches with computed winner, ordered by stage depth."""
    md = _read("matches_detailed").copy()
    md["date"] = pd.to_datetime(md["date"], errors="coerce")
    ko = md[md["stage_name"].isin(["Round of 32", "Round of 16", "Quarter-finals",
                                    "Semi-finals", "Third-place match", "Final"])].copy()

    def _winner(row):
        h, a = row["home_score"], row["away_score"]
        if pd.notna(row.get("home_penalty_score")) and pd.notna(row.get("away_penalty_score")):
            return row["home_team_name"] if row["home_penalty_score"] > row["away_penalty_score"] else row["away_team_name"]
        if h > a: return row["home_team_name"]
        if a > h: return row["away_team_name"]
        return "draw"

    ko["winner"] = ko.apply(_winner, axis=1)
    order = {s: i for i, s in enumerate(STAGE_ORDER)}
    ko["_order"] = ko["stage_name"].map(order).fillna(99).astype(int)
    return ko.sort_values(["_order", "date"], kind="stable").drop(columns="_order").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Players (Players page — also re-exported from real_wc26_players for convenience)
# ---------------------------------------------------------------------------
def get_real_wc26_players() -> pd.DataFrame:
    """1248 squad players with tournament context. The detailed per-player
    stats live in data/real_wc26_players.py — this loader gives a slim
    squad-only view (id, name, team, club, market value)."""
    sp = _read("squads_and_players")
    t = _teams()[["team_id", "team_name", "fifa_code", "confederation"]]
    out = sp.merge(t, on="team_id", how="left")
    return out.sort_values("market_value_eur", ascending=False).reset_index(drop=True)


def get_real_wc26_player_stats() -> pd.DataFrame:
    """1248 players with tournament performance stats (matches/minutes/goals/
    assists/cards/rating) merged to team + squad metadata."""
    ps = _read("player_stats")
    sp = _read("squads_and_players")[["player_id", "club_team", "market_value_eur",
                                        "caps", "date_of_birth", "height_cm"]]
    t = _teams()[["team_id", "team_name", "fifa_code", "confederation"]]
    out = ps.merge(t, on="team_id", how="left").merge(sp, on="player_id", how="left")
    return out.sort_values(["goals", "assists"], ascending=[False, False]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# NEW loaders (Kaggle CSVs that the prior Athena layer did not expose)
# ---------------------------------------------------------------------------
def get_real_wc26_match_events() -> pd.DataFrame:
    """834 match events with player/team/minute, joined to readable names.

    Columns: event_id, match_id, minute, event_type, team_id, player_id,
             team_name, fifa_code, player_name, position.
    Event types: Goal, Assist, Yellow Card, Red Card, VAR Review,
                 Penalty Shootout Goal, Penalty Shootout Miss.

    Use this to render per-match goal/assist timelines and per-player
    event logs. (Previously: only the matches_detailed score column was
    available, with no per-event detail.)"""
    me = _read("match_events")
    t = _teams()[["team_id", "team_name", "fifa_code"]]
    ps = _read("player_stats")[["player_id", "player_name", "position"]]
    out = me.merge(t, on="team_id", how="left").merge(ps, on="player_id", how="left")
    out = out.sort_values(["match_id", "minute"], kind="stable").reset_index(drop=True)
    return out


def get_real_wc26_match_lineups() -> pd.DataFrame:
    """5408 lineup rows: per-match per-player XI/bench with minutes played.

    Columns: lineup_id, match_id, player_id, team_id, is_starting_xi,
             tactical_position, minutes_played, player_name, team_name.

    Use this to verify per-player minutes and squad-rotation analyses."""
    ml = _read("match_lineups")
    t = _teams()[["team_id", "team_name", "fifa_code"]]
    ps = _read("player_stats")[["player_id", "player_name"]]
    out = ml.merge(t, on="team_id", how="left").merge(ps, on="player_id", how="left")
    return out.sort_values(["match_id", "team_id", "is_starting_xi"],
                            ascending=[True, True, False]).reset_index(drop=True)


def get_real_wc26_match_prediction_features() -> pd.DataFrame:
    """104 rows × 66 cols: pre-match feature vector for each WC26 match.

    Includes real pre-tournament Elo (home_elo, away_elo), FIFA rank,
    squad total market value, squad avg age, host flag, rest days,
    pre-tournament rolling form (avg goals/xG/possession/shots/saves/
    corners/fouls/offsides), referee avg cards, venue elevation, and
    the actual outcome (home_score, away_score, match_result, xG).

    This is the data source for the Predictions page's
    'Elo-rank strength vs actual outcomes' view — no fabricated
    championship probabilities, just real measurements."""
    return _read("match_prediction_features")
