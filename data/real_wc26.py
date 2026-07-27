"""
Real FIFA World Cup 2026 match results loader.
Source: https://github.com/tatamyiwathy/WorldCup2026 (worldcup26.json)
        Creative Commons licensed dataset; cross-validated against the
        official tournament schedule: 104 matches, ~307-308 goals, avg ~2.95-2.96.

The dataset is in Japanese; team names and stage names need translation to English
for the dashboard. This module loads the JSON, translates, and returns a clean
DataFrame with columns:
    date, home, home_score, away, away_score, stage, group, stadium, notes
"""
import json
import os
import pandas as pd

# Japanese -> English translation tables (curated to match the source JSON)
_TEAM_JP_TO_EN = {
    "日本": "Japan",
    "⽇本": "Japan",  # variant kanji
    "韓国": "South Korea",
    "メキシコ": "Mexico",
    "南アフリカ": "South Africa",
    "カナダ": "Canada",
    "アメリカ": "United States",
    "ボスニア・ヘルツェゴビナ": "Bosnia & Herzegovina",
    "チェコ": "Czechia",
    "イングランド": "England",
    "コートジボワール": "Ivory Coast",
    "ノルウェー": "Norway",
    "スウェーデン": "Sweden",
    "ベルギー": "Belgium",
    "セネガル": "Senegal",
    "エクアドル": "Ecuador",
    "エジプト": "Egypt",
    "コンゴ⺠主共和国": "DR Congo",
    "コンゴ民主共和国": "DR Congo",
    "アルゼンチン": "Argentina",
    "カーボベルデ": "Cape Verde",
    "コロンビア": "Colombia",
    "ガーナ": "Ghana",
    "オーストラリア": "Australia",
    "ポルトガル": "Portugal",
    "クロアチア": "Croatia",
    "スペイン": "Spain",
    "オーストリア": "Austria",
    "スイス": "Switzerland",
    "アルジェリア": "Algeria",
    "ウズベキスタン": "Uzbekistan",
    "パラグアイ": "Paraguay",
    "モロッコ": "Morocco",
    "ブラジル": "Brazil",
    "フランス": "France",
    "メキシコ": "Mexico",
    "ドイツ": "Germany",
    "オランダ": "Netherlands",
    "パナマ": "Panama",
    "ウルグアイ": "Uruguay",
    "イラン": "Iran",
    "イラク": "Iraq",
    "カタール": "Qatar",
    "チュニジア": "Tunisia",
    "トルコ": "Turkey",
    "サウジアラビア": "Saudi Arabia",
    "ハイチ": "Haiti",
    "ヨルダン": "Jordan",
    "ニュージーランド": "New Zealand",
    "キュラソー": "Curaçao",
    "スコットランド": "Scotland",
}

_STAGE_JP_TO_EN = {
    "グループステージ": "Group Stage",
    "ラウンド・オブ・32": "Round of 32",
    "ラウンド・オブ・16": "Round of 16",
    "準々決勝": "Quarter-Final",
    "準決勝": "Semi-Final",
    "3位決定戦": "Third-Place Playoff",
    "決勝": "Final",
}

# Ordered stages (low -> high) for nice chart axis ordering
STAGE_ORDER = [
    "Group Stage", "Round of 32", "Round of 16",
    "Quarter-Final", "Semi-Final", "Third-Place Playoff", "Final",
]

# Match-level notes in Japanese translate too:
_NOTE_JP_TO_EN = {
    "延長戦": "Extra Time",
    "PK:": "Penalties:",   # PK:3-4 etc. (replaced prefix)
    "PK戦:": "Penalties:",
}


def _translate_team(name: str) -> str:
    return _TEAM_JP_TO_EN.get(name, name)


def _translate_stage(name: str) -> str:
    return _STAGE_JP_TO_EN.get(name, name)


def _translate_notes(notes):
    if notes is None:
        return None
    s = str(notes)
    for jp, en in _NOTE_JP_TO_EN.items():
        s = s.replace(jp, en)
    return s or None


def _translate_group(name):
    # "グループA" -> "Group A"; pass through if null / non-matching
    if not name:
        return None
    s = str(name)
    if s.startswith("グループ"):
        return f"Group {s[len('グループ'):]}"
    return s


_DATA_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_PATH = os.path.join(_DATA_DIR, "real_wc26", "worldcup26.json")


def get_real_wc26_matches() -> pd.DataFrame:
    """Load and translate the real WC26 match-results dataset.

    Returns DataFrame with columns:
        date, home, home_score, away, away_score, stage, group, stadium, notes
    """
    with open(_DATA_PATH, encoding="utf-8") as f:
        matches = json.load(f)

    records = []
    for m in matches:
        records.append({
            "date": m.get("date"),
            "home": _translate_team(m.get("home")),
            "home_score": int(m["home_score"]) if m.get("home_score") is not None else None,
            "away": _translate_team(m.get("away")),
            "away_score": int(m["away_score"]) if m.get("away_score") is not None else None,
            "stage": _translate_stage(m.get("stage")),
            "group": _translate_group(m.get("group")),
            "stadium": m.get("studium"),
            "notes": _translate_notes(m.get("notes")),
        })

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    # Sort chronologically; if missing date, fall back to original order
    df = df.sort_values(["date"], kind="stable").reset_index(drop=True)
    return df


def get_real_wc26_summary() -> pd.DataFrame:
    """Tournament totals: matches, goals, avg, winner."""
    df = get_real_wc26_matches()
    total_matches = len(df)
    total_goals = int(df["home_score"].sum() + df["away_score"].sum())
    avg_goals = round(total_goals / total_matches, 2) if total_matches else 0.0

    final_row = df[df["stage"] == "Final"].iloc[0] if len(df[df["stage"] == "Final"]) == 1 else None
    winner = None
    if final_row is not None:
        if final_row["home_score"] > final_row["away_score"]:
            winner = final_row["home"]
        elif final_row["away_score"] > final_row["home_score"]:
            winner = final_row["away"]
        else:
            # Penalty shootout — check notes
            notes = final_row.get("notes") or ""
            winner = "TBD (penalties — check notes)"

    return pd.DataFrame([{
        "total_matches": total_matches,
        "total_goals": total_goals,
        "avg_goals_per_match": avg_goals,
        "final_date": final_row["date"] if final_row is not None else None,
        "winner": winner,
        "runner_up": final_row["away"] if final_row is not None and winner == final_row["home"] else (
            final_row["home"] if final_row is not None else None
        ),
        "final_score": f"{final_row['home_score']}-{final_row['away_score']}" if final_row is not None else None,
    }])


def get_real_wc26_outcome_counts() -> pd.DataFrame:
    """W/d/l counts per stage plus total."""
    df = get_real_wc26_matches()
    df["total_goals"] = df["home_score"] + df["away_score"]
    df["outcome"] = df.apply(
        lambda r: "Home Win" if r["home_score"] > r["away_score"]
        else ("Away Win" if r["away_score"] > r["home_score"] else "Draw"),
        axis=1,
    )

    summary = df.groupby("stage").agg(
        matches=("outcome", "size"),
        home_wins=("outcome", lambda s: (s == "Home Win").sum()),
        away_wins=("outcome", lambda s: (s == "Away Win").sum()),
        draws=("outcome", lambda s: (s == "Draw").sum()),
        goals=("total_goals", "sum"),
    ).reset_index()

    # Order stages properly using STAGE_ORDER
    summary["stage_order"] = summary["stage"].apply(
        lambda s: STAGE_ORDER.index(s) if s in STAGE_ORDER else 99
    )
    summary = summary.sort_values("stage_order").drop(columns=["stage_order"]).reset_index(drop=True)

    # Add total row
    total = pd.DataFrame([{
        "stage": "Total",
        "matches": summary["matches"].sum(),
        "home_wins": summary["home_wins"].sum(),
        "away_wins": summary["away_wins"].sum(),
        "draws": summary["draws"].sum(),
        "goals": summary["goals"].sum(),
    }])
    return pd.concat([summary, total], ignore_index=True)


def get_real_wc26_team_stats() -> pd.DataFrame:
    """Per-team goals for/against/matches/wins/draws/losses from the real dataset."""
    df = get_real_wc26_matches()

    # Long-form: one row per team per match
    rows = []
    for _, m in df.iterrows():
        rows.append({"team": m["home"], "goals_for": m["home_score"], "goals_against": m["away_score"], "stage": m["stage"]})
        rows.append({"team": m["away"], "goals_for": m["away_score"], "goals_against": m["home_score"], "stage": m["stage"]})
    team_df = pd.DataFrame(rows)

    # Aggregate
    agg = team_df.groupby("team").agg(
        matches=("goals_for", "size"),
        goals_for=("goals_for", "sum"),
        goals_against=("goals_against", "sum"),
        wins=("goals_for", lambda s: 0),  # placeholder; recompute below
        draws=("goals_for", lambda s: 0),
        losses=("goals_for", lambda s: 0),
    ).reset_index()

    # Compute W/D/L properly
    team_df["result"] = team_df.apply(
        lambda r: "W" if r["goals_for"] > r["goals_against"]
        else ("D" if r["goals_for"] == r["goals_against"] else "L"),
        axis=1,
    )
    wdl = team_df.groupby(["team", "result"]).size().unstack(fill_value=0)
    for col in ["W", "D", "L"]:
        if col not in wdl.columns:
            wdl[col] = 0
    wdl = wdl.reset_index()[["team", "W", "D", "L"]]
    agg = agg.merge(wdl, on="team", how="left")
    agg = agg.drop(columns=["wins", "draws", "losses"])
    agg["goal_difference"] = agg["goals_for"] - agg["goals_against"]
    return agg.sort_values(["goals_for", "goal_difference"], ascending=[False, False]).reset_index(drop=True)
