from pages._shared import *
page_header('Team Performance','Compare national teams by rating, goals, expected goals, and defensive strength.')
df=get_teams(); kpi_cards([("Teams",len(df),""),("Avg rating",f"{df.rating.mean():.1f}",""),("Total goals",int(df.goals_for.sum()),"")]); st.plotly_chart(px.scatter(df,x="xg",y="goals_for",size="rating",color="confederation",hover_name="team",title="Team goals vs expected goals"),use_container_width=True)
