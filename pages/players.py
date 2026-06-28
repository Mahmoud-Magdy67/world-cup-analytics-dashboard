from pages._shared import *
page_header('Player Analysis','Identify standout players by goals, assists, chance creation, and minutes played.')
df=get_players(); kpi_cards([("Players tracked",len(df),""),("Goals",int(df.goals.sum()),""),("Assists",int(df.assists.sum()),"")]); st.plotly_chart(px.bar(df,x="player",y=["goals","assists"],barmode="group",title="Goal contributions by player"),use_container_width=True)
