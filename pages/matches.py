"""
Page 4: Match Analytics
Comprehensive analysis of World Cup 2026 matches, schedule, and venues.
Matches the official FWC26 Light Theme.
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from pages._shared_enhanced import load_custom_css, page_header, info_card
from data.athena import get_matches, get_match_predictions

# Apply CSS
load_custom_css()

# Header
page_header(
    "Match Analysis",
    "Comprehensive match schedule, venue analysis, and fixture insights.",
    image_url="assets/logo.png"
)

# ============================================================================
# LOAD DATA
# ============================================================================
with st.spinner("Loading match data..."):
    matches_df = get_matches()
    predictions_df = get_match_predictions()

if matches_df.empty:
    st.error("Failed to load match data from AWS Athena.")
    st.stop()

# Ensure proper data types
if 'match_date' in matches_df.columns:
    matches_df['match_date'] = pd.to_datetime(matches_df['match_date'])
if 'stadium_capacity' in matches_df.columns:
    matches_df['stadium_capacity'] = pd.to_numeric(matches_df['stadium_capacity'], errors='coerce')
if 'latitude' in matches_df.columns:
    matches_df['latitude'] = pd.to_numeric(matches_df['latitude'], errors='coerce')
if 'longitude' in matches_df.columns:
    matches_df['longitude'] = pd.to_numeric(matches_df['longitude'], errors='coerce')

# ============================================================================
# FILTERS
# ============================================================================
st.markdown("### 🎛️ Match Filters")
c1, c2, c3, c4 = st.columns(4)

stages = sorted(matches_df['stage'].dropna().unique().tolist()) if 'stage' in matches_df.columns else []
groups = sorted(matches_df['group_name'].dropna().unique().tolist()) if 'group_name' in matches_df.columns else []
venues = sorted(matches_df['venue'].dropna().unique().tolist()) if 'venue' in matches_df.columns else []
host_countries = sorted(matches_df['host_country'].dropna().unique().tolist()) if 'host_country' in matches_df.columns else []

sel_stage = c1.selectbox("📅 Stage", ["All"] + stages)
sel_group = c2.selectbox("👥 Group", ["All"] + groups)
sel_venue = c3.selectbox("🏟️ Venue", ["All"] + venues)
sel_host = c4.selectbox("🏳️ Host Country", ["All"] + host_countries)

filtered = matches_df.copy()
if sel_stage != "All":
    filtered = filtered[filtered['stage'] == sel_stage]
if sel_group != "All":
    filtered = filtered[filtered['group_name'] == sel_group]
if sel_venue != "All":
    filtered = filtered[filtered['venue'] == sel_venue]
if sel_host != "All":
    filtered = filtered[filtered['host_country'] == sel_host]

if filtered.empty:
    st.warning("No matches match the selected filters.")
    st.stop()

st.divider()

# ============================================================================
# KPIs
# ============================================================================
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Total Matches", len(matches_df))
with k2:
    if 'stage' in matches_df.columns:
        group_matches = len(matches_df[matches_df['stage'] == 'Group Stage'])
        st.metric("Group Stage", f"{group_matches}")
    else:
        st.metric("Group Stage", "N/A")
with k3:
    if 'stage' in matches_df.columns:
        knockout_matches = len(matches_df[matches_df['stage'] != 'Group Stage'])
        st.metric("Knockout Stage", f"{knockout_matches}")
    else:
        st.metric("Knockout Stage", "N/A")
with k4:
    if 'venue' in matches_df.columns:
        unique_venues = matches_df['venue'].nunique()
        st.metric("Venues Used", f"{unique_venues}")
    else:
        st.metric("Venues Used", "N/A")
with k5:
    if 'host_country' in matches_df.columns:
        unique_hosts = matches_df['host_country'].nunique()
        st.metric("Host Nations", f"{unique_hosts}")
    else:
        st.metric("Host Nations", "N/A")

st.divider()

# ============================================================================
# MATCH SCHEDULE TIMELINE
# ============================================================================
st.subheader("📅 Match Schedule Timeline")
if 'match_date' in filtered.columns and 'stage' in filtered.columns:
    # Create timeline
    timeline_df = filtered.copy()
    timeline_df['match_date'] = pd.to_datetime(timeline_df['match_date'])
    timeline_df = timeline_df.sort_values('match_date')
    
    fig_timeline = px.scatter(
        timeline_df,
        x='match_date',
        y='stage',
        color='stage',
        hover_data=['match_number', 'team', 'opponent', 'venue', 'city'],
        size_max=15,
        color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
        title="Match Schedule by Date and Stage"
    )
    fig_timeline.update_layout(
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color='#000000', family='Noto Sans'),
        title=dict(font=dict(family='Bebas Neue', size=18)),
        xaxis_title="Match Date",
        yaxis_title="Match Stage",
        height=400
    )
    st.plotly_chart(fig_timeline, width='stretch')
    
    info_card("Schedule Insight",
        f"The tournament spans from {timeline_df['match_date'].min().strftime('%b %d, %Y')} "
        f"to {timeline_df['match_date'].max().strftime('%b %d, %Y')}. "
        f"Group stage matches are concentrated in the first two weeks, "
        f"followed by knockout rounds in the final week."
    )
else:
    st.info("Date or stage information not available for timeline view.")
st.divider()

# ============================================================================
# VENUE ANALYSIS
# ============================================================================
st.subheader("🏟️ Venue Distribution & Capacity")
if 'venue' in filtered.columns and 'stadium_capacity' in filtered.columns:
    venue_stats = filtered.groupby('venue').agg(
        matches=('venue', 'size'),
        avg_capacity=('stadium_capacity', 'mean'),
        total_capacity=('stadium_capacity', 'sum'),
        city=('city', 'first'),
        host_country=('host_country', 'first')
    ).reset_index().sort_values('matches', ascending=False)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig_venue = px.bar(
            venue_stats.head(10),
            x='venue',
            y='matches',
            color='host_country',
            hover_data=['avg_capacity', 'city'],
            color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00'],
            title="Top 10 Venues by Number of Matches"
        )
        fig_venue.update_layout(
            paper_bgcolor='#ffffff',
            plot_bgcolor='#ffffff',
            font=dict(color='#000000', family='Noto Sans'),
            title=dict(font=dict(family='Bebas Neue', size=16)),
            xaxis_tickangle=-45,
            xaxis_title="Venue",
            yaxis_title="Number of Matches",
            height=400
        )
        st.plotly_chart(fig_venue, width='stretch')
    
    with col2:
        st.markdown("#### 📊 Venue Statistics")
        if not venue_stats.empty:
            biggest_venue = venue_stats.loc[venue_stats['stadium_capacity'].idxmax()]
            most_used = venue_stats.loc[venue_stats['matches'].idxmax()]
            
            st.metric("Largest Venue", f"{biggest_venue['venue']}", f"{int(biggest_venue['stadium_capacity']):,} seats")
            st.metric("Most Used Venue", f"{most_used['venue']}", f"{int(most_used['matches'])} matches")
            st.metric("Avg. Capacity", f"{int(venue_stats['stadium_capacity'].mean()):,} seats")
            
            # Geographic distribution
            if 'host_country' in venue_stats.columns:
                host_dist = venue_stats['host_country'].value_counts()
                st.markdown("**Matches by Host Country:**")
                for host, count in host_dist.items():
                    st.markdown(f"- {host}: {count} matches")
    
    st.divider()
    
    # Venue map
    if 'latitude' in venue_stats.columns and 'longitude' in venue_stats.columns:
        map_df = venue_stats.dropna(subset=['latitude', 'longitude'])
        if not map_df.empty:
            fig_map = px.scatter_geo(
                map_df,
                lat='latitude',
                lon='longitude',
                size='matches',
                color='host_country',
                hover_name='venue',
                hover_data=['city', 'matches', 'stadium_capacity'],
                projection='natural earth',
                title="World Cup 2026 Venue Locations",
                color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00']
            )
            fig_map.update_layout(
                paper_bgcolor='#ffffff',
                font=dict(color='#000000', family='Noto Sans'),
                title=dict(font=dict(family='Bebas Neue', size=16)),
                height=400
            )
            st.plotly_chart(fig_map, width='stretch')
            
            info_card("Venue Insight",
                f"The 2026 World Cup will be hosted across {len(host_countries)} countries "
                f"with {len(venue_stats)} unique venues. The geographic distribution "
                f"aims to maximize accessibility while showcasing North America's "
                f"world-class sporting infrastructure."
            )
else:
    st.info("Venue or capacity information not available for detailed analysis.")
st.divider()

# ============================================================================
# GROUP STAGE ANALYSIS
# ============================================================================
if 'group_name' in filtered.columns and 'stage' in filtered.columns:
    st.subheader("👥 Group Stage Composition")
    group_matches = filtered[filtered['stage'] == 'Group Stage'].copy()
    
    if not group_matches.empty:
        # Group breakdown
        group_stats = group_matches.groupby('group_name').agg(
            matches=('group_name', 'size'),
            teams=('team', lambda x: x.nunique() * 2),  # Each match has 2 teams
            avg_matches_per_team=('team', lambda x: x.value_counts().mean() * 2 if len(x.value_counts()) > 0 else 0)
        ).reset_index()
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_group = px.pie(
                group_stats,
                values='matches',
                names='group_name',
                title="Match Distribution by Group",
                color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00',
                                       '#FFA500', '#8B0000', '#006400', '#4B0082', '#2F4F4F',
                                       '#DC143C', '#008B8B']
            )
            fig_group.update_layout(
                paper_bgcolor='#ffffff',
                font=dict(color='#000000', family='Noto Sans'),
                title=dict(font=dict(family='Bebas Neue', size=16)),
                height=400
            )
            st.plotly_chart(fig_group, width='stretch')
        
        with col2:
            st.markdown("#### 📊 Group Statistics")
            if not group_stats.empty:
                st.metric("Groups", f"{len(group_stats)}")
                st.metric("Matches per Group", f"{group_stats['matches'].mean():.1f}")
                st.metric("Teams per Group", "4 (fixed)")
                
                # Show group details
                for _, row in group_stats.iterrows():
                    with st.expander(f"Group {row['group_name']} ({int(row['matches'])} matches)"):
                        # Get teams in this group
                        group_teams = sorted(group_matches[group_matches['group_name'] == row['group_name']]['team'].unique())
                        teams_str = ", ".join(group_teams)
                        st.markdown(f"**Teams:** {teams_str}")
                        
                        # Show sample matches
                        sample_matches = group_matches[group_matches['group_name'] == row['group_name']].head(3)
                        if not sample_matches.empty and 'match_date' in sample_matches.columns:
                            st.markdown("**Sample Matches:**")
                            for _, match in sample_matches.iterrows():
                                date_str = match['match_date'].strftime('%b %d') if pd.notnull(match['match_date']) else 'TBD'
                                st.markdown(f"- {date_str}: {match['team']} vs {match['opponent']}")
        
        st.divider()
        
        # Group stage_analysis")   # Changed from "stage_analysis" to "stage_analysis_unique" to avoid duplicate
        
        # Match frequency by date
        if 'match_date' in filtered.columns:
            date_counts = filtered.groupby('match_date').size().reset_index(name='matches_per_day')
            date_counts = date_counts.sort_values('match_date')
            
            fig_density = px.bar(
                date_counts,
                x='match_date',
                y='matches_per_day',
                color='matches_per_day',
                color_continuous_scale=['#ffffff', '#FF004D'],
                title="Match Density Throughout Tournament"
            )
            fig_density.update_layout(
                paper_bgcolor='#ffffff',
                plot_bgcolor='#ffffff',
                font=dict(color='#000000', family='Noto Sans'),
                title=dict(font=dict(family='Bebas Neue', size=16)),
                xaxis_title="Date",
                yaxis_title="Matches Per Day",
                height=300
            )
            st.plotly_chart(fig_density, width='stretch')
            
            peak_day = date_counts.loc[date_counts['matches_per_day'].idxmax()]
            info_card("Scheduling Insight",
                f"The busiest match day is {peak_day['match_date'].strftime('%b %d, %Y')} "
                f"with {int(peak_day['matches_per_day'])} matches scheduled. "
                f"This reflects the condensed group stage format where multiple "
                f"matches occur daily across different venues."
            )
else:
    st.info("Stage or date information not available for detailed scheduling analysis.")
st.divider()

# ============================================================================
# KNOCKOUT BRACKET PROJECTION
# ============================================================================
st.subheader("🏆 Knockout Stage Projection")
if 'stage' in filtered.columns:
    knockout_matches = filtered[filtered['stage'] != 'Group Stage'].copy()
    
    if not knockout_matches.empty:
        # Count matches by knockout stage
        knockout_counts = knockout_matches['stage'].value_counts().reset_index()
        knockout_counts.columns = ['stage', 'matches']
        
        # Order the stages logically — must match the real Athena values:
        # ['Final', 'Group Stage', 'Quarter-finals', 'Round of 16',
        #  'Round of 32', 'Semi-finals', 'Third Place']
        stage_order = ['Round of 32', 'Round of 16', 'Quarter-finals',
                       'Semi-finals', 'Third Place', 'Final']
        # Only keep categories that actually appear; this also avoids the
        # Pandas4Warning about values not in the dtype's categories.
        present_stages = set(knockout_counts['stage'].dropna().unique())
        ordered_present = [s for s in stage_order if s in present_stages]
        knockout_counts['stage'] = pd.Categorical(
            knockout_counts['stage'], categories=ordered_present, ordered=True)
        knockout_counts = knockout_counts.sort_values('stage')
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_ko = px.bar(
                knockout_counts,
                x='stage',
                y='matches',
                color='stage',
                text='matches',
                color_discrete_sequence=['#FF004D', '#7B00FF', '#00F0FF', '#00FF00', '#FF4D00', '#8B0000'],
                title="Knockout Stage Match Distribution"
            )
            fig_ko.update_layout(
                paper_bgcolor='#ffffff',
                plot_bgcolor='#ffffff',
                font=dict(color='#000000', family='Noto Sans'),
                title=dict(font=dict(family='Bebas Neue', size=16)),
                xaxis_title="Knockout Stage",
                yaxis_title="Number of Matches",
                showlegend=False,
                height=350
            )
            fig_ko.update_traces(textposition='outside')
            st.plotly_chart(fig_ko, width='stretch')
        
        with col2:
            st.markdown("#### 📊 Knockout Structure")
            st.markdown("""
            - **Round of 32**: 16 matches (32 teams → 16)
            - **Round of 16**: 8 matches (16 teams → 8)
            - **Quarter-finals**: 4 matches (8 teams → 4)
            - **Semifinals**: 2 matches (4 teams → 2)
            - **Third Place**: 1 match (losers of SF)
            - **Final**: 1 match (championship)
            """)
            st.metric("Total Knockout Matches", f"{int(knockout_counts['matches'].sum())}")
        
        st.divider()
        
        if predictions_df is not None and not predictions_df.empty:
            # Show win probabilities for upcoming knockout matches if available
            # Only select columns that actually exist in predictions_df (the
            # Athena predictions view carries 55 cols; the rename in
            # athena.py adds win/loss/draw, but be defensive across deployments).
            prob_cols = [c for c in ('match_number', 'win_probability', 'draw_probability', 'loss_probability')
                         if c in predictions_df.columns]
            if len(prob_cols) > 1:  # at least match_number + one prob col
                preds_subset = predictions_df[prob_cols].copy()
                ko_with_preds = knockout_matches.merge(
                    preds_subset,
                    on='match_number',
                    how='left'
                )
            else:
                ko_with_preds = knockout_matches.copy()

            if not ko_with_preds.empty and 'win_probability' in ko_with_preds.columns:
                st.markdown("#### 🔮 Match Win Probabilities (Available Data)")
                prob_display = ko_with_preds[['match_number', 'team', 'opponent', 'stage', 'win_probability']].copy()
                prob_display = prob_display.dropna(subset=['win_probability'])
                if not prob_display.empty:
                    prob_display['win_probability'] = (prob_display['win_probability'] * 100).round(1)
                    st.dataframe(
                        prob_display.head(10),
                        column_config={
                            "match_number": st.column_config.TextColumn("Match #"),
                            "team": st.column_config.TextColumn("Team"),
                            "opponent": st.column_config.TextColumn("Opponent"),
                            "stage": st.column_config.TextColumn("Stage"),
                            "win_probability": st.column_config.NumberColumn("Win %", format="%.1f%%")
                        },
                        hide_index=True,
                        width='stretch'
                    )
                else:
                    st.info("Win probability data not yet available for knockout matches.")
            else:
                st.info("Prediction data not available for match probability analysis.")
        else:
            st.info("Prediction data not loaded for probability analysis.")
    else:
        st.info("No knockout stage matches found in current filter.")
else:
    st.info("Stage information not available for knockout analysis.")
st.divider()

# ============================================================================
# TEAM SCHEDULE BALANCE
# ============================================================================
st.subheader("⚖️ Team Schedule Balance")
if 'team' in filtered.columns and 'match_date' in filtered.columns:
    # Calculate rest days between matches for each team
    team_schedule = filtered[['team', 'match_date']].copy()
    team_schedule['match_date'] = pd.to_datetime(team_schedule['match_date'])
    team_schedule = team_schedule.sort_values(['team', 'match_date'])
    
    team_schedule['days_rest'] = team_schedule.groupby('team')['match_date'].diff().dt.days
    
    rest_stats = team_schedule.groupby('team').agg(
        avg_rest=('days_rest', 'mean'),
        min_rest=('days_rest', 'min'),
        max_rest=('days_rest', 'max'),
        total_matches=('match_date', 'count')
    ).reset_index()
    
    # Filter out first matches (no prior rest)
    rest_stats = rest_stats[rest_stats['total_matches'] > 1]
    
    if not rest_stats.empty:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig_rest = px.scatter(
                rest_stats,
                x='avg_rest',
                y='min_rest',
                size='total_matches',
                color='min_rest',
                hover_data=['team', 'max_rest'],
                color_continuous_scale=['#FF0000', '#FFFF00', '#00FF00'],
                title="Team Rest Distribution: Avg vs Minimum Rest Days"
            )
            fig_rest.update_layout(
                paper_bgcolor='#ffffff',
                plot_bgcolor='#ffffff',
                font=dict(color='#000000', family='Noto Sans'),
                title=dict(font=dict(family='Bebas Neue', size=16)),
                xaxis_title="Average Rest Days Between Matches",
                yaxis_title="Minimum Rest Days Between Matches",
                height=400
            )
            st.plotly_chart(fig_rest, width='stretch')
        
        with col2:
            st.markdown("#### 📊 Rest Statistics")
            toughest = rest_stats.loc[rest_stats['min_rest'].idxmin()]
            best_rested = rest_stats.loc[rest_stats['min_rest'].idxmax()]
            
            st.metric("Toughest Schedule", 
                     f"{toughest['team']}", 
                     f"{int(toughest['min_rest'])} min rest")
            st.metric("Best Rested Team", 
                     f"{best_rested['team']}", 
                     f"{int(best_rested['min_rest'])} min rest")
            st.metric("League Avg. Rest", 
                     f"{rest_stats['avg_rest'].mean():.1f} days")
            
            # Teams with shortest turnaround
            quick_turns = rest_stats[rest_stats['min_rest'] <= 2]
            if not quick_turns.empty:
                st.markdown("**⚠️ Teams with ≤2 day turnaround:**")
                for _, team in quick_turns.iterrows():
                    st.markdown(f"- {team['team']} ({int(team['min_rest'])} days)")
        
        st.divider()
        
        info_card("Scheduling Equity Insight",
            f"Tournament scheduling aims to provide equitable rest between matches. "
            f"Teams with <3 days rest face increased injury risk and performance fatigue. "
            f"The current schedule shows {len(quick_turns)} teams with potentially challenging "
            f"turnarounds of 2 days or less between matches."
        )
    else:
        st.info("Insufficient match date data to calculate rest periods.")
else:
    st.info("Team or date information not available for schedule balance analysis.")
st.divider()

# ============================================================================
# MATCH DAYS CALENDAR VIEW
# ============================================================================
st.subheader("📅 Match Calendar by Date")
if 'match_date' in filtered.columns:
    # Create a calendar-like view
    calendar_df = filtered.copy()
    calendar_df['match_date'] = pd.to_datetime(calendar_df['match_date'])
    calendar_df['date_str'] = calendar_df['match_date'].dt.strftime('%b %d')
    calendar_df['day_of_week'] = calendar_df['match_date'].dt.day_name()
    
    # Group by date — carry an ISO date key for correct chronological sort
    # (date_str 'MMM DD' sorts alphabetically and breaks across months).
    calendar_df['date_iso'] = calendar_df['match_date'].dt.strftime('%Y-%m-%d')
    daily_matches = calendar_df.groupby(['date_iso', 'date_str', 'day_of_week']).agg(
        matches=('match_number', 'size'),
        teams=('team', lambda x: ', '.join(sorted(x.unique())[:4]) + ('...' if len(x.unique()) > 4 else ''))
    ).reset_index().sort_values('date_iso')
    
    if not daily_matches.empty:
        # Show as a table — drop the internal ISO sort key before display
        display_df = daily_matches.drop(columns=['date_iso']).rename(columns={
            'date_str': 'Date',
            'day_of_week': 'Day',
            'matches': '# Matches',
            'teams': 'Teams Playing'
        })
        st.dataframe(
            display_df,
            column_config={
                "Date": st.column_config.TextColumn("Date"),
                "Day": st.column_config.TextColumn("Day"),
                "# Matches": st.column_config.NumberColumn("# Matches", format="%d"),
                "Teams Playing": st.column_config.TextColumn("Teams Playing")
            },
            hide_index=True,
            width='stretch'
        )
        
        busiest_day = daily_matches.loc[daily_matches['matches'].idxmax()]
        info_card("Calendar Insight",
            f"The busiest match day is {busiest_day['date_str']} ({busiest_day['day_of_week']}) "
            f"with {int(busiest_day['matches'])} matches. This typically occurs during "
            f"the final group stage matchday when all groups play their final matches "
            f"on the same day to ensure competitive integrity."
        )
    else:
        st.info("No match date data available for calendar view.")
else:
    st.info("Match date information not available for calendar view.")
st.divider()

# ============================================================================
# ATTENDANCE & CAPACITY ANALYSIS
# ============================================================================
st.subheader("🎟️ Stadium Capacity & Attendance Potential")
if 'stadium_capacity' in filtered.columns:
    cap_data = filtered['stadium_capacity'].dropna()
    
    if not cap_data.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fig_cap = px.histogram(
                cap_data,
                nbins=15,
                color_discrete_sequence=['#FF004D'],
                title="Stadium Capacity Distribution"
            )
            fig_cap.update_layout(
                paper_bgcolor='#ffffff',
                plot_bgcolor='#ffffff',
                font=dict(color='#000000', family='Noto Sans'),
                title=dict(font=dict(family='Bebas Neue', size=16)),
                xaxis_title="Stadium Capacity",
                yaxis_title="Number of Venues",
                bargap=0.1
            )
            st.plotly_chart(fig_cap, width='stretch')
        
        with col2:
            st.metric("Average Capacity", f"{int(cap_data.mean()):,} seats")
            st.metric("Median Capacity", f"{int(cap_data.median()):,} seats")
            st.metric("Capacity Std Dev", f"{int(cap_data.std()):,} seats")
        
        with col3:
            total_seats = cap_data.sum()
            avg_attendance = total_seats * 0.85  # Assume 85% avg attendance
            st.metric("Total Seats Available", f"{int(total_seats):,}")
            st.metric("Est. Total Attendance", f"{int(avg_attendance):,}")
            st.metric("Venues >80k Seats", f"{(cap_data > 80000).sum()}")
        
        st.divider()
        
        # List largest venues
        if 'venue' in filtered.columns and 'city' in filtered.columns and 'host_country' in filtered.columns:
            largest_venues = filtered[['venue', 'city', 'host_country', 'stadium_capacity']].drop_duplicates()\
                .sort_values('stadium_capacity', ascending=False).head(5)
            
            st.markdown("#### 🏟️ Largest Venues")
            for _, venue in largest_venues.iterrows():
                st.markdown(f"- **{venue['venue']}** ({venue['city']}, {venue['host_country']}) "
                           f"- {int(venue['stadium_capacity']):,} seats")
        
        info_card("Capacity Insight",
            f"With an average venue capacity of {int(cap_data.mean()):,} seats, "
            f"the 2026 World Cup is positioned to set new attendance records. "
            f"The selection of large, modern stadiums across three host nations "
            f"reflects the tournament's expanded 48-team format and global appeal."
        )
    else:
        st.info("Stadium capacity data not available.")
else:
    st.info("Stadium capacity information not available.")
st.divider()

# ============================================================================
# DATA QUALITY & SOURCES
# ============================================================================
st.subheader("📊 Data Sources & Quality")
if 'match_number' in filtered.columns:
    max_match = filtered['match_number'].max()
    expected_matches = 208  # 48 teams: 72 group + 135 knockout = 207? Actually 104 group + 15*2-1 = 104+29=133? Let's check: 48 teams -> 12 groups of 4 -> 6 matches per group * 12 = 72 group stage. Then 32->16->8->4->2->1 + 3rd place = 16+8+4+2+1+1 = 32 knockout. Total = 72+32=104 matches. Wait, let me recalc...
    
    # Actually: 48 teams, 12 groups of 4 = 6 matches per group * 12 = 72 group stage matches
    # Knockout: R32 (16), R16 (8), QF (4), SF (2), F (1), 3rd (1) = 32 matches
    # Total = 104 matches
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Matches Loaded", f"{len(filtered)}")
        st.metric("Expected Total", f"104")
        if len(filtered) == 104:
            st.success("✅ Complete match schedule loaded")
        elif len(filtered) < 104:
            st.warning(f"⚠️ Missing {104 - len(filtered)} matches")
        else:
            st.info(f"ℹ️ {len(filtered) - 104} extra matches (may include placeholders)")
    
    with col2:
        # Check for missing critical data
        missing_cols = []
        for col in ['match_date', 'venue', 'stage', 'group_name']:
            if col not in filtered.columns or filtered[col].isna().all():
                missing_cols.append(col)
        
        if missing_cols:
            st.warning(f"⚠️ Missing data: {', '.join(missing_cols)}")
        else:
            st.success("✅ Core match data complete")
        
        # Date range
        if 'match_date' in filtered.columns and not filtered['match_date'].isna().all():
            date_range = f"{filtered['min_date'].strftime('%b %d')} to {filtered['max_date'].strftime('%b %d, %Y')}" if 'min_date' in dir(filtered) else "Date range available"
            st.info(f"📅 Tournament dates: {date_range}")
else:
    st.info("Match numbering system not available for data quality check.")

st.caption("Data sourced from AWS Athena table: matches | Last updated: " + 
          (matches_df['last_updated'].max().strftime('%Y-%m-%d') if 'last_updated' in matches_df.columns else 'N/A'))