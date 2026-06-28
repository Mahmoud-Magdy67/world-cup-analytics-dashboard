from pages._shared import *
page_header('Player Analysis','Identify standout players by goals, assists, chance creation, and minutes played.')
df=get_players(); kpi_cards([("Players tracked",len(df),""),("Total goals",int(df.goals.sum()),""),("Total assists",int(df.assists.sum()),"")]); st.plotly_chart(px.bar(df.head(20),x="player_name",y=["goals","assists"],barmode="group",title="Goal contributions by player (top 20)"),use_container_width=True); st.dataframe(df[["player_name","nation_code","position","club_team","goals","assists","xg","xa","minutes"]],use_container_width=True)
