from pages._shared import *
page_header('Tournament Overview','High-level tournament health, scoring trends, and leading contenders.')
df=get_teams(); kpi_cards([("Teams tracked",len(df),""),("Goals scored",int(df.goals_for.sum()),""),("Top contender",df.iloc[0].team,f"{df.iloc[0].win_probability:.0%}")]); st.plotly_chart(px.bar(df,x="team",y="rating",color="confederation",title="Team power ratings"),use_container_width=True)
