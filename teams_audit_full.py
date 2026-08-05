import pandas as pd
import numpy as np
from data.real_wc26 import (
    get_real_wc26_team_strength, get_real_wc26_match_team_stats,
    get_real_wc26_teams, get_real_wc26_matches
)

teams_strength = get_real_wc26_team_strength()
team_match_stats = get_real_wc26_match_team_stats()
teams = get_real_wc26_teams()
matches = get_real_wc26_matches()

home_rows = matches.rename(columns={
    'home_team_name': 'team', 'away_team_name': 'opponent',
    'home_score': 'goals_for', 'away_score': 'goals_against',
})[['match_id', 'team', 'goals_for', 'goals_against']]
away_rows = matches.rename(columns={
    'away_team_name': 'team', 'home_team_name': 'opponent',
    'away_score': 'goals_for', 'home_score': 'goals_against',
})[['match_id', 'team', 'goals_for', 'goals_against']]
goals_per_team = pd.concat([home_rows, away_rows], ignore_index=True)
goals_agg = goals_per_team.groupby('team').agg(
    matches=('match_id', 'size'),
    goals_for=('goals_for', 'sum'),
    goals_against=('goals_against', 'sum'),
).reset_index()
goals_agg['goal_difference'] = goals_agg['goals_for'] - goals_agg['goals_against']

match_stats_agg = team_match_stats.groupby('team_name').agg(
    avg_possession=('avg_possession', 'mean'),
    avg_shots=('avg_shots', 'mean'),
    avg_shots_on_target=('avg_shots_on_target', 'mean'),
    avg_corners=('avg_corners', 'mean'),
    avg_fouls=('avg_fouls', 'mean'),
    avg_saves=('avg_saves', 'mean'),
    matches=('matches', 'mean'),
).reset_index()

df = teams_strength.merge(goals_agg, left_on='team_name', right_on='team', how='left').drop(columns=['team'], errors='ignore')
df = df.merge(match_stats_agg, on='team_name', how='left')

def zscore_to_60_95(series, low=60, high=95):
    s = pd.to_numeric(series, errors='coerce')
    std = s.std(skipna=True)
    if std is None or std == 0 or np.isnan(std):
        return pd.Series([77.5] * len(s), index=s.index)
    z = (s - s.mean()) / std
    out = low + (z.clip(-2, 2) + 2) / 4 * (high - low)
    return out

df['attack_strength'] = zscore_to_60_95(df['goals_for'] / df['matches_x'])
df['defense_strength'] = zscore_to_60_95(-(df['goals_against'] / df['matches_x']))
df['midfield_strength'] = zscore_to_60_95(df['avg_possession'])
df['gk_strength'] = zscore_to_60_95(df['avg_saves'])
df['avg_ovr_top11'] = zscore_to_60_95(df['elo_rating'])

# 4. ATTACK vs DEFENSE MATRIX
avg_atk = df['attack_strength'].mean()
avg_def = df['defense_strength'].mean()
elite = df[(df['attack_strength'] > avg_atk) & (df['defense_strength'] > avg_def)]

# 5. ELO vs SQUAD VALUE
trend_df = df.dropna(subset=['elo_rating', 'squad_market_value_eur']).copy()
x = trend_df['squad_market_value_eur'].values
y = trend_df['elo_rating'].values
coeffs = np.polyfit(x, y, 1)
trend_df['expected_elo'] = np.polyval(coeffs, x)
trend_df['elo_residual'] = trend_df['elo_rating'] - trend_df['expected_elo']
over = trend_df.nlargest(3, 'elo_residual')
under = trend_df.nsmallest(3, 'elo_residual')

# 6. CONFEDERATION STRENGTH
if 'confederation' in df.columns and df['confederation'].nunique() > 1:
    confed_stats = df.groupby('confederation').agg(
        avg_elo=('elo_rating', 'mean'),
        avg_attack=('attack_strength', 'mean'),
        avg_defense=('defense_strength', 'mean'),
        avg_midfield=('midfield_strength', 'mean'),
        avg_value=('squad_market_value_eur', 'mean'),
        team_count=('team_name', 'count'),
        wc26_goals=('wc26_goals', 'sum'),
    ).reset_index().sort_values('avg_elo', ascending=False)

# 7. GROUP OF DEATH
if 'group_letter' in df.columns and 'elo_rating' in df.columns:
    group_analysis = df.groupby('group_letter').agg(
        avg_elo=('elo_rating', 'mean'),
        std_elo=('elo_rating', 'std'),
        min_elo=('elo_rating', 'min'),
        max_elo=('elo_rating', 'max'),
        team_count=('team_name', 'count'),
        total_value=('squad_market_value_eur', 'sum'),
        total_wc26_goals=('wc26_goals', 'sum'),
    ).reset_index().sort_values('avg_elo', ascending=False)
    hardest = group_analysis.iloc[0]
    easiest = group_analysis.iloc[-1]

# 8. TACTICAL BALANCE INDEX
balance_df = df.copy()
balance_df['balance_score'] = balance_df[['attack_strength', 'defense_strength', 'midfield_strength']].std(axis=1)
balance_df['overall_strength'] = balance_df[['attack_strength', 'defense_strength', 'midfield_strength']].mean(axis=1)
most_balanced = balance_df.nsmallest(3, 'balance_score')
most_imbalanced = balance_df.nlargest(3, 'balance_score')

# Output to file
with open('teams_audit_results.txt', 'w') as f:
    f.write("=" * 80 + "\n")
    f.write("TEAMS PAGE AUDIT - ALL NUMBERS CROSS-CHECKED\n")
    f.write("=" * 80 + "\n\n")

    # 4. ATTACK vs DEFENSE
    f.write("4. ATTACK vs DEFENSE MATRIX\n")
    f.write(f"   Avg Attack: {avg_atk:.1f}, Avg Defense: {avg_def:.1f}\n")
    f.write(f"   Elite Balance teams: {len(elite)}\n")
    for _, r in elite.sort_values(['attack_strength','defense_strength'], ascending=False).iterrows():
        f.write(f"     {r['team_name']:15s} Atk={r['attack_strength']:.1f} Def={r['defense_strength']:.1f}\n")

    # 5. ELO vs SQUAD VALUE
    f.write("\n5. ELO vs SQUAD VALUE\n")
    f.write("   Overperformers (Elo > expected for value):\n")
    for _, r in over.iterrows():
        f.write(f"     + {r['team_name']:15s} Elo={r['elo_rating']:.0f} Residual={r['elo_residual']:+.0f}\n")
    f.write("   Underperformers (Elo < expected for value):\n")
    for _, r in under.iterrows():
        f.write(f"     - {r['team_name']:15s} Elo={r['elo_rating']:.0f} Residual={r['elo_residual']:+.0f}\n")

    # 6. CONFEDERATION STRENGTH
    f.write("\n6. CONFEDERATION STRENGTH\n")
    for _, r in confed_stats.iterrows():
        val = f"€{r['avg_value']/1e9:.2f}B" if pd.notna(r['avg_value']) else 'N/A'
        f.write(f"   {r['confederation']:8s} Teams={int(r['team_count']):2d} Elo={r['avg_elo']:.0f} "
              f"Atk={r['avg_attack']:.1f} Def={r['avg_defense']:.1f} Mid={r['avg_midfield']:.1f} "
              f"Val={val} Goals={int(r['wc26_goals'])}\n")

    # 7. GROUP OF DEATH
    f.write("\n7. GROUP OF DEATH\n")
    for _, r in group_analysis.iterrows():
        val = f"€{r['total_value']/1e9:.2f}B" if pd.notna(r['total_value']) else 'N/A'
        f.write(f"   Group {r['group_letter']:1s} AvgElo={r['avg_elo']:.0f} Std={r['std_elo']:.0f} "
              f"Range={r['min_elo']:.0f}-{r['max_elo']:.0f} Val={val} Goals={int(r['total_wc26_goals'])}\n")
    f.write(f"   Hardest: Group {hardest['group_letter']} (Avg Elo {hardest['avg_elo']:.0f})\n")
    f.write(f"   Easiest: Group {easiest['group_letter']} (Avg Elo {easiest['avg_elo']:.0f})\n")
    f.write(f"   Elo Gap: {hardest['avg_elo'] - easiest['avg_elo']:.0f}\n")

    # 8. TACTICAL BALANCE INDEX
    f.write("\n8. TACTICAL BALANCE INDEX\n")
    f.write("   Most Balanced (lowest std dev):\n")
    for _, r in most_balanced.iterrows():
        f.write(f"     {r['team_name']:15s} Balance={r['balance_score']:.2f} Overall={r['overall_strength']:.1f}\n")
    f.write("   Most Imbalanced (highest std dev):\n")
    for _, r in most_imbalanced.iterrows():
        f.write(f"     {r['team_name']:15s} Balance={r['balance_score']:.2f} Overall={r['overall_strength']:.1f}\n")

    f.write("\n" + "=" * 80 + "\n")
    f.write("AUDIT COMPLETE\n")
    f.write("=" * 80 + "\n")