from pages._shared import *
page_header('Tournament Overview','High-level tournament health, scoring trends, and leading contenders.')
df=get_mock_teams(); kpi_cards([("Teams tracked",len(df),"+6 mock"),("Goals scored",int(df.goals_for.sum()),"+65"),("Top contender",df.iloc[0].team,"18%")]); st.plotly_chart(px.bar(df,x="team",y="rating",color="confederation",title="Mock team power ratings"),use_container_width=True)
