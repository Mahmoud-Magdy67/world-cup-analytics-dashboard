from pages._shared import *
page_header('Match Analysis','Review match schedule, venues, and fixture status.')
df=get_matches(); kpi_cards([("Matches",len(df),""),("Group stage",len(df[df.stage=="Group Stage"]),""),("Knockout",len(df[df.stage!="Group Stage"]),"")]); df_display=df[["match_number","match_date","stage","group_name","team","opponent","venue","city","status"]].head(20); st.dataframe(df_display,width='stretch'); st.plotly_chart(px.bar(df.groupby("stage").size().reset_index(name="count"),x="stage",y="count",color="stage",title="Matches by stage"),width='stretch')
