"""
Page 1: Tournament Analysis — Post-Tournament Review
FIFA World Cup 2026 retrospective using the real Kaggle dataset
(mominullptr/fifa-world-cup-2026-dataset, CC0): 104 matches, 308 goals,
2.96 avg/match. Spain defeated Argentina 1-0 (AET) in the Final on 2026-07-19
at MetLife Stadium, East Rutherford.
"""
from pages._shared_enhanced import st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import *
from data.real_wc26 import (
    get_real_wc26_matches, get_real_wc26_summary,
    get_real_wc26_outcome_counts, get_real_wc26_team_stats,
    get_real_wc26_xg_by_team, get_real_wc26_team_strength,
    get_real_wc26_knockout_bracket, STAGE_ORDER,
)

load_custom_css("overview")

page_header(
    "Tournament Analysis",
    "FIFA World Cup 2026 — post-tournament retrospective",
    image_url="assets/logo.png"
)

# ============================================================================
# LOAD DATA — all from the Kaggle dataset
# ============================================================================
with st.spinner("Loading tournament retrospective..."):
    real_matches = get_real_wc26_matches()
    real_summary = get_real_wc26_summary()
    real_outcomes = get_real_wc26_outcome_counts()
    real_team_stats = get_real_wc26_team_stats()
    teams_strength = get_real_wc26_team_strength()
    bracket = get_real_wc26_knockout_bracket()

if real_matches.empty:
    st.error("Failed to load tournament results from the Kaggle dataset.")
    st.stop()

real_s = real_summary.iloc[0]
total_matches = int(real_s.get('total_matches', 0) or 0)
total_goals = int(real_s.get('total_goals', 0) or 0)
avg_goals = float(real_s.get('avg_goals_per_match', 0) or 0)
winner = real_s.get('winner', 'Spain')
runner_up = real_s.get('runner_up', 'Argentina')
final_score = real_s.get('final_score', '1-0')
final_date = real_s.get('final_date')
final_venue = real_s.get('final_venue')
final_city = real_s.get('final_city')
result_type = real_s.get('result_type')

st.divider()

# ============================================================================
# HERO: SPAIN WON THE 2026 WORLD CUP
# ============================================================================
st.markdown(f"## 🏆 {winner} Won the 2026 World Cup")
spain_row = teams_strength[teams_strength['team_name'] == winner]
spain_elo = float(spain_row['elo_rating'].iloc[0]) if not spain_row.empty else 0
spain_rank = int(spain_row['fifa_ranking_pre_tournament'].iloc[0]) if not spain_row.empty else 0
spain_val = float(spain_row['squad_market_value_eur'].iloc[0]) if not spain_row.empty and 'squad_market_value_eur' in spain_row.columns else 0
spain_goals = int(real_team_stats[real_team_stats['team'] == winner]['goals_for'].iloc[0]) if not real_team_stats[real_team_stats['team'] == winner].empty else 0

hcol1, hcol2, hcol3, hcol4 = st.columns(4)
with hcol1:
    st.metric("FIFA Ranking (pre-tournament)", f"#{spain_rank}")
with hcol2:
    st.metric("Elo Rating", f"{spain_elo:.0f}")
with hcol3:
    st.metric("Squad Value", f"€{spain_val/1e9:.2f}B" if spain_val else "N/A")
with hcol4:
    st.metric("Tournament Goals", f"{spain_goals}")

st.success(
    f"**{winner}** defeated {runner_up} {final_score} "
    f"{'(' + result_type + ')' if result_type else ''} in the Final on "
    f"{final_date.strftime('%B %d, %Y') if final_date is not None and hasattr(final_date, 'strftime') else 'July 19, 2026'} "
    f"at {final_venue or 'MetLife Stadium'}, {final_city or 'East Rutherford'}. "
    f"Across {total_matches} matches and {total_goals} goals, {winner} lifted the trophy "
    f"as the champion of the expanded 48-team, 16-city, 3-nation tournament."
)

st.divider()

# ============================================================================
# TOURNAMENT AT A GLANCE
# ============================================================================
st.markdown("## 📊 Tournament at a Glance")

total_teams = 48
total_venues = real_matches['stadium_name'].nunique() if 'stadium_name' in real_matches.columns else 16
total_hosts = real_matches['country'].nunique() if 'country' in real_matches.columns else 3

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Teams", total_teams)
with k2:
    st.metric("Matches Played", total_matches)
with k3:
    st.metric("Total Goals", total_goals)
with k4:
    st.metric("Avg Goals/Match", f"{avg_goals:.2f}")
with k5:
    st.metric("Host Nations", total_hosts)

st.write("")

# ============================================================================
# MATCH OUTCOME DISTRIBUTION
# ============================================================================
st.subheader("📊 Goals Per Stage — Where the Action Was")
st.caption("Average goals per match broke down sharply between the group format and the knockout pressure cooker.")

_stage_order = ['Group Stage', 'Round of 32', 'Round of 16', 'Quarter-finals', 'Semi-finals', 'Third-place match', 'Final']
stage_goals = real_matches.groupby('stage_name').apply(
    lambda x: pd.Series({
        'matches': len(x),
        'goals': int(x['home_score'].sum() + x['away_score'].sum()),
    })
).reset_index()
stage_goals['avg_goals'] = (stage_goals['goals'] / stage_goals['matches']).round(2)
stage_goals['stage_order'] = stage_goals['stage_name'].map({n: i for i, n in enumerate(_stage_order)})
stage_goals = stage_goals.sort_values('stage_order').drop(columns=['stage_order'])

col_sg1, col_sg2 = st.columns([3, 2])
with col_sg1:
    fig_gp = px.bar(
        stage_goals, x='stage_name', y='avg_goals',
        text=[f"{a:.2f}" for a in stage_goals['avg_goals']],
        color='avg_goals',
        color_continuous_scale=['#C8102E', '#F4C542', '#00FF00'],
        labels={'stage_name': 'Tournament Stage', 'avg_goals': 'Avg Goals / Match'},
        title="Average Goals Per Match by Stage",
    )
    fig_gp.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue'),
        showlegend=False, margin=dict(t=40, l=10, r=10, b=10),
        coloraxis_showscale=False,
    )
    st.plotly_chart(apply_dark_text_theme(fig_gp), width='stretch')
with col_sg2:
    st.dataframe(
        stage_goals.rename(columns={'stage_name': 'Stage', 'matches': 'Matches', 'goals': 'Goals', 'avg_goals': 'Avg/Match'}),
        column_config={
            'Matches': st.column_config.NumberColumn(format="%d"),
            'Goals': st.column_config.NumberColumn(format="%d"),
            'Avg/Match': st.column_config.NumberColumn(format="%.2f"),
        },
        hide_index=True, width='stretch',
    )

# Insight
_group_avg = stage_goals[stage_goals['stage_name'] == 'Group Stage']['avg_goals'].iloc[0] if not stage_goals[stage_goals['stage_name'] == 'Group Stage'].empty else 0
_ko_avg = stage_goals[stage_goals['stage_name'] != 'Group Stage']['avg_goals'].mean() if len(stage_goals[stage_goals['stage_name'] != 'Group Stage']) > 0 else 0
info_card(
    "AI Insight",
    f"The group stage averaged **{_group_avg:.2f} goals/match** across 72 fixtures, "
    f"delivering the bulk of the tournament's {total_goals} goals. "
    f"Knockout stages averaged **{_ko_avg:.2f}** — tighter defences and higher stakes "
    f"drove scoring down, with the Final itself a 1-0 affair settled in extra time."
)

st.divider()

# ============================================================================
# TOURNAMENT UPSETS — Elo-based analysis
# ============================================================================
st.subheader("⚡ Tournament Upsets — When Lower-Ranked Teams Struck")

# Elo explanation card (first mention)
info_card(
    "🧮 What is Elo Rating?",
    "**Elo** is a relative skill rating system originally designed for chess, now used across football analytics. "
    "Each team starts with a base rating (~1500), and points transfer from loser to winner after every match. "
    "The formula accounts for expected outcome: beating a much stronger team earns more points than beating a weaker one. "
    "In this dashboard, Elo is a **pre-tournament snapshot** from the Kaggle dataset — a transparent strength signal "
    "independent of FIFA rankings. Higher Elo = stronger recent competitive record."
)

st.caption("An upset is defined as a team with a lower pre-tournament Elo beating a higher-Elo opponent. The Elo gap shows how big the shock was.")

elo_map = dict(zip(teams_strength['team_name'], teams_strength['elo_rating']))
upsets = []
for _, r in real_matches.iterrows():
    h_elo = elo_map.get(r['home_team_name'], 0)
    a_elo = elo_map.get(r['away_team_name'], 0)
    h_score, a_score = r['home_score'], r['away_score']
    if pd.isna(h_score) or pd.isna(a_score):
        continue
    # Determine winner
    if h_score > a_score:
        match_winner, match_loser = r['home_team_name'], r['away_team_name']
        w_elo, l_elo = h_elo, a_elo
        score_str = f"{int(h_score)}-{int(a_score)}"
    elif a_score > h_score:
        match_winner, match_loser = r['away_team_name'], r['home_team_name']
        w_elo, l_elo = a_elo, h_elo
        score_str = f"{int(h_score)}-{int(a_score)}"
    else:
        # Draw → check PK
        hp, ap = r.get('home_penalty_score'), r.get('away_penalty_score')
        if pd.notna(hp) and pd.notna(ap):
            if hp > ap:
                match_winner, match_loser = r['home_team_name'], r['away_team_name']
                w_elo, l_elo = h_elo, a_elo
            else:
                match_winner, match_loser = r['away_team_name'], r['home_team_name']
                w_elo, l_elo = a_elo, h_elo
            score_str = f"{int(h_score)}-{int(a_score)} (PK {int(hp)}-{int(ap)})"
        else:
            continue  # true draw, no upset
    if w_elo < l_elo:
        upsets.append({
            'stage': r['stage_name'],
            'winner': match_winner,
            'loser': match_loser,
            'winner_elo': int(w_elo),
            'loser_elo': int(l_elo),
            'elo_gap': int(l_elo - w_elo),
            'score': score_str,
        })

upsets_df = pd.DataFrame(upsets).sort_values('elo_gap', ascending=False).reset_index(drop=True) if upsets else pd.DataFrame()

if not upsets_df.empty:
    col_up1, col_up2 = st.columns([3, 2])
    with col_up1:
        fig_upsets = px.bar(
            upsets_df.head(12), x='elo_gap', y='winner',
            orientation='h',
            text=[f"beat {l} ({le})" for l, le in zip(upsets_df.head(12)['loser'], upsets_df.head(12)['loser_elo'])],
            color='elo_gap',
            color_continuous_scale=['#F4C542', '#FF8C00', '#C8102E'],
            labels={'elo_gap': 'Elo Gap (favourite > underdog)', 'winner': 'Underdog Winner'},
            title="Biggest Upsets by Elo Gap",
        )
        fig_upsets.update_layout(
            yaxis=dict(autorange='reversed'),
            paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
            font=dict(color='#000000', family='Bebas Neue'),
            showlegend=False, margin=dict(t=40, l=10, r=10, b=10),
            coloraxis_showscale=False,
            height=400,
        )
        st.plotly_chart(apply_dark_text_theme(fig_upsets), width='stretch')
    with col_up2:
        st.dataframe(
            upsets_df.head(12)[['stage', 'winner', 'loser', 'winner_elo', 'loser_elo', 'elo_gap', 'score']],
            column_config={
                'stage': 'Stage',
                'winner': 'Winner',
                'loser': 'Loser',
                'winner_elo': st.column_config.NumberColumn("Elo", format="%d"),
                'loser_elo': st.column_config.NumberColumn("Elo", format="%d"),
                'elo_gap': st.column_config.NumberColumn("Gap", format="%d"),
                'score': 'Score',
            },
            hide_index=True, width='stretch',
        )

    biggest = upsets_df.iloc[0]
    info_card(
        "AI Insight",
        f"**{len(upsets_df)} upsets** across the tournament — "
        f"the biggest shock: **{biggest['winner']}** (Elo {biggest['winner_elo']}) beating "
        f"**{biggest['loser']}** (Elo {biggest['loser_elo']}, a {biggest['elo_gap']}-point gap) "
        f"in the {biggest['stage']} ({biggest['score']}). "
        f"Knockout football rewards tactical discipline over rating pedigree — "
        f"{sum(upsets_df['stage'] != 'Group Stage')}/{len(upsets_df)} upsets came in the knockout rounds."
    )
else:
    st.info("No upset data available.")

st.divider()

# ============================================================================
# ELO-BASED POWER RANKINGS (replaces pre-tournament prediction rankings)
# ============================================================================
st.subheader("🔮 Elo Power Rankings — Top 15")
st.caption("Elo ratings from the Kaggle pre-tournament dataset. Higher Elo = stronger team going into the tournament.")

# Rank by Elo descending
strength_sorted = teams_strength.sort_values('elo_rating', ascending=False).reset_index(drop=True)
strength_sorted['elo_rank'] = strength_sorted.index + 1
top15 = strength_sorted.head(15).copy()

fig_rank = px.bar(
    top15, x='elo_rating', y='team_name',
    orientation='h', color='confederation',
    color_discrete_map={'UEFA': '#00F0FF', 'CONMEBOL': '#FF004D',
                        'CONCACAF': '#7B00FF', 'AFC': '#00FF00', 'CAF': '#FFA500', 'OFC': '#FFD700'},
    labels={'elo_rating': 'Elo Rating', 'team_name': 'Team', 'confederation': 'Confederation'},
    title="Top 15 Teams by Pre-Tournament Elo Rating",
)
fig_rank.update_layout(
    yaxis=dict(autorange='reversed'),
    paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
    font=dict(color='#000000', family='Bebas Neue'),
    margin=dict(t=40, l=10, r=10, b=10),
)
# Highlight the actual champion
if not spain_row.empty:
    fig_rank.add_annotation(
        x=spain_elo, y=winner,
        text="🏆 Champion", showarrow=True, arrowhead=2, arrowcolor='#00FF00',
        font=dict(color='#009922', size=14), yshift=8,
    )
st.plotly_chart(apply_dark_text_theme(fig_rank), width='stretch')

disp_cols = ['elo_rank', 'team_name', 'confederation', 'elo_rating',
             'fifa_ranking_pre_tournament', 'squad_market_value_eur', 'wc26_goals']
disp_cols = [c for c in disp_cols if c in top15.columns]
st.dataframe(
    top15[disp_cols].rename(columns={
        'elo_rank': 'Elo Rank', 'team_name': 'Team', 'confederation': 'Confederation',
        'elo_rating': 'Elo', 'fifa_ranking_pre_tournament': 'FIFA Rank',
        'squad_market_value_eur': 'Squad €', 'wc26_goals': 'WC26 Goals',
    }),
    column_config={
        "Elo": st.column_config.NumberColumn(format="%.0f"),
        "Squad €": st.column_config.NumberColumn(format="€%,.0f"),
        "WC26 Goals": st.column_config.NumberColumn(format="%d"),
    },
    hide_index=True, width='stretch',
)

info_card(
        "AI Insight",
        f"{winner} entered the tournament with an Elo of {spain_elo:.0f} "
        f"(FIFA rank #{spain_rank}) and went on to outscore opponents "
        f"{spain_goals}-{int(real_team_stats[real_team_stats['team']==winner]['goals_against'].iloc[0]) if not real_team_stats[real_team_stats['team']==winner].empty else 0} "
        f"across the tournament. The concentration of UEFA + CONMEBOL sides at the top of the "
        f"Elo ladder maps to the eventual semifinal lineup — the champion came from the European elite, "
        f"as the Elo ranking would have suggested."
    )

st.divider()

# ============================================================================
# GOALS ANALYSIS
# ============================================================================
st.subheader("🥅 Goals Analysis — Which Teams Delivered?")

if not real_team_stats.empty:
    top10_goals = real_team_stats.head(10).copy()

    fig_goals = go.Figure()
    fig_goals.add_trace(go.Bar(
        name='Goals For', x=top10_goals['team'], y=top10_goals['goals_for'],
        marker_color='#00F0FF',
    ))
    fig_goals.add_trace(go.Bar(
        name='Goals Against', x=top10_goals['team'], y=top10_goals['goals_against'],
        marker_color='#FF004D',
    ))
    fig_goals.update_layout(
        barmode='group',
        title="Top 10 Teams by Goals Scored (Real WC26 Results)",
        xaxis_title='Team', yaxis_title='Goals',
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue'),
        margin=dict(t=40, l=10, r=10, b=10),
    )
    st.plotly_chart(apply_dark_text_theme(fig_goals), width='stretch')

    st.markdown("#### Per-Team Goal Metrics")
    st.dataframe(
        real_team_stats.rename(columns={
            'team': 'Team', 'matches': 'Matches', 'goals_for': 'Goals For',
            'goals_against': 'Goals Against', 'W': 'W', 'D': 'D', 'L': 'L',
            'goal_difference': 'GD',
        }),
        column_config={
            "Goals For": st.column_config.NumberColumn(format="%d"),
            "Goals Against": st.column_config.NumberColumn(format="%d"),
            "GD": st.column_config.NumberColumn(format="%+d"),
            "Matches": st.column_config.NumberColumn(format="%d"),
        },
        hide_index=True, width='stretch',
    )

    # Overperformance vs Elo rank
    if not strength_sorted.empty:
        merged = real_team_stats.merge(
            strength_sorted[['team_name', 'elo_rank', 'elo_rating']],
            left_on='team', right_on='team_name', how='left',
        )
        merged['actual_goals_rank'] = merged['goals_for'].rank(ascending=False).astype(int)
        merged['delta_rank'] = merged['elo_rank'] - merged['actual_goals_rank']
        
        # Show BOTH top underperformers (negative delta) AND top overperformers (positive delta)
        merged_valid = merged.dropna(subset=['elo_rank']).copy()
        top_over = merged_valid.sort_values('delta_rank', ascending=False).head(8)  # highest positive
        top_under = merged_valid.sort_values('delta_rank', ascending=True).head(8)  # lowest negative
        opp = pd.concat([top_over, top_under]).drop_duplicates('team').sort_values('delta_rank', ascending=False)

        st.markdown("#### 📈 Over- vs Underperformers (actual goals vs pre-tournament Elo rank)")
        op_df = opp[['team', 'elo_rank', 'actual_goals_rank', 'delta_rank', 'goals_for']].rename(
            columns={
                'team': 'Team', 'elo_rank': 'Elo Rank',
                'actual_goals_rank': 'Goals Rank', 'delta_rank': 'Rank Δ',
                'goals_for': 'Goals For',
            }
        )
        op_df['Rank Δ'] = op_df['Rank Δ'].apply(
            lambda x: f"+{int(x)} ⬆" if x > 0 else (f"{int(x)} ⬇" if x < 0 else "0")
        )
        st.dataframe(op_df, hide_index=True, width='stretch')
        info_card(
            "AI Insight",
            "The 'Rank Δ' column compares each team's pre-tournament Elo rank with their "
            "actual goals-scored rank across the 104 matches. Positive deltas (⬆) mark "
            "teams that outscored their Elo expectation — genuine overperformers vs the prior."
        )
else:
    st.info("No goals data available.")

st.divider()

# ============================================================================
# TOURNAMENT PROGRESSION — KNOCKOUT BRACKET
# ============================================================================
st.subheader("🏆 Knockout Bracket")

if not bracket.empty:
    # Display bracket table sorted by stage order then date
    bracket_sorted = bracket.copy()
    bracket_sorted['stage_order'] = bracket_sorted['stage_name'].apply(
        lambda s: STAGE_ORDER.index(s) if s in STAGE_ORDER else 99)
    bracket_sorted = bracket_sorted.sort_values(['stage_order', 'date']).drop(columns=['stage_order'])

    display = bracket_sorted[['date', 'stage_name', 'home_team_name', 'away_team_name',
                               'home_score', 'away_score', 'result_type', 'winner']].copy()
    display['date'] = pd.to_datetime(display['date'], errors='coerce').dt.strftime('%b %d')
    display = display.rename(columns={
        'date': 'Date', 'stage_name': 'Stage',
        'home_team_name': 'Home', 'away_team_name': 'Away',
        'home_score': 'H', 'away_score': 'A',
        'result_type': 'Result', 'winner': 'Winner',
    })
    st.dataframe(display, hide_index=True, width='stretch')

    info_card(
        "Bracket Insight",
        f"32 knockout matches culminated in {winner} defeating {runner_up} {final_score} "
        f"{'(' + result_type + ')' if result_type else ''} in the Final. "
        f"The expanded 48-team format introduced a Round of 32, adding an extra knockout hurdle "
        f"and a total of 8 matches required to lift the trophy (up from 7 in the 32-team era)."
    )

st.divider()

# ============================================================================
# CONFEDERATION ANALYSIS
# ============================================================================
st.subheader("🌍 Confederation Breakdown")

if 'confederation' in teams_strength.columns:
    confed_stats = teams_strength.groupby('confederation').agg(
        teams=('team_name', 'size'),
        avg_elo=('elo_rating', 'mean'),
        total_market_value=('squad_market_value_eur', 'sum'),
        wc26_goals=('wc26_goals', 'sum'),
    ).reset_index().sort_values('avg_elo', ascending=False)

    fig_conf = px.bar(
        confed_stats, x='confederation', y='avg_elo',
        color='total_market_value',
        color_continuous_scale=['#FFFFFF', '#00F0FF', '#7B00FF', '#FF004D'],
        labels={'confederation': 'Confederation', 'avg_elo': 'Average Elo Rating',
                'total_market_value': 'Total Squad Value (€)'},
        title="Confederation Strength — Average Elo Rating",
    )
    fig_conf.update_layout(
        paper_bgcolor='#ffffff', plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Bebas Neue'),
        margin=dict(t=40, l=10, r=10, b=10),
    )
    st.plotly_chart(apply_dark_text_theme(fig_conf), width='stretch')

    st.dataframe(
        confed_stats.rename(columns={
            'confederation': 'Confederation', 'teams': 'Teams', 'avg_elo': 'Avg Elo',
            'total_market_value': 'Total Squad €', 'wc26_goals': 'WC26 Goals',
        }),
        column_config={
            "Avg Elo": st.column_config.NumberColumn(format="%.0f"),
            "Total Squad €": st.column_config.NumberColumn(format="€%,.0f"),
            "WC26 Goals": st.column_config.NumberColumn(format="%d"),
        },
        hide_index=True, width='stretch',
    )

    info_card(
        "AI Insight",
        "UEFA held the deepest pool of Elo strength and squad market value, "
        "reflecting the European elite (Spain, France, England, Netherlands, Germany, Portugal). "
        "CONMEBOL — Argentina, Brazil, Colombia — was the second pole. The expanded 48-team "
        "format dilutes the CONCACAF/AFC/CAF long tail further. "
        f"{winner}'s win is a validation of the UEFA-inner-circle thesis."
    )

st.divider()

# ============================================================================
# TOURNAMENT FORMAT CONTEXT
# ============================================================================
st.subheader("🏟️ Tournament Format & Hosting")
ctx_c1, ctx_c2 = st.columns(2)
with ctx_c1:
    st.markdown('''
    ### THE LARGEST WORLD CUP IN HISTORY
    THE 2026 EDITION EXPANDED TO 48 TEAMS AND 104 MATCHES, FUNDAMENTALLY ALTERING THE PATH TO THE FINAL.
    A NEW ROUND OF 32 INTRODUCED AN EXTRA KNOCKOUT HURDLE, INCREASING VARIANCE AND REDUCING THE PREDICTABILITY OF THE CHAMPION.
    TEAMS MUST SURVIVE 8 MATCHES TO LIFT THE TROPHY INSTEAD OF 7.
    ''')
with ctx_c2:
    st.markdown('''
    ### TRAVEL AND ALTITUDE DYNAMICS
    HOSTED ACROSS 16 CITIES IN THE USA, MEXICO, AND CANADA, GEOGRAPHIC STRATEGY WAS CRITICAL.
    TEAMS PLAYING IN MEXICO CITY (2,200 M / 7,350 FT ELEVATION) FACED SEVERE PHYSIOLOGICAL DEMANDS.
    HOST-CONTINENT ADVANTAGE BENEFITED CONCACAF SIDES, WHILE CROSS-COUNTRY TRAVEL FATIGUED SQUADS DRAWN INTO COAST-TO-COAST GROUP ASSIGNMENTS.
    ''')
