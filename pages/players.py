from pages._shared import *
page_header('Player Analysis','Identify standout players by goals, assists, chance creation, and minutes played.')
df=get_mock_players(); kpi_cards([("Players tracked",len(df),"+6 mock"),("Goals",int(df.goals.sum()),"+21"),("Assists",int(df.assists.sum()),"+18")]); st.plotly_chart(px.bar(df,x="player",y=["goals","assists"],barmode="group",title="Goal contributions by player"),use_container_width=True)
