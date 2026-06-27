from pages._shared import *
page_header('Predictions / Model Results','Explore first-pass mock model outputs before real BigQuery predictions are connected.')
df=get_mock_predictions(); kpi_cards([("Teams modeled",len(df),"+6"),("Top win prob",f"{df.win_probability.max():.0%}","mock"),("Methods",df.model_method.nunique(),"+3")]); st.plotly_chart(px.bar(df,x="team",y="win_probability",color="model_method",title="Mock tournament win probability"),use_container_width=True)
