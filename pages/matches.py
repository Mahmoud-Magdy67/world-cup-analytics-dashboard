from pages._shared import *
page_header('Match Analysis','Review mock match outcomes, scoring volume, expected goals, and attendance.')
df=get_mock_matches(); kpi_cards([("Matches",len(df),"+5 mock"),("Goals",int((df.home_goals+df.away_goals).sum()),"+17"),("Avg attendance",f"{df.attendance.mean():,.0f}","+mock")]); df["goals"]=df.home_goals+df.away_goals; st.plotly_chart(px.line(df,x="match",y=["goals","total_xg"],markers=True,title="Goals vs expected goals by match"),use_container_width=True)
