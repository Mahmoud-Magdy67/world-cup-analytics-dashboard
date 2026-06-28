from pages._shared import *
page_header('Predictions / Model Results','Explore model predictions for tournament winner.')
df=get_predictions(); kpi_cards([("Teams modeled",len(df),""),("Top win prob",f"{df.win_probability.max():.0%}",""),("Methods",df.model_method.nunique(),"")]); st.plotly_chart(px.bar(df.sort_values("win_probability",ascending=False),x="team",y="win_probability",color="model_method",title="Tournament win probability"),use_container_width=True)
