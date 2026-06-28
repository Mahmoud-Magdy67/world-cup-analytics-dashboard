from pages._shared import *
from data.bigquery import ALLOWED_BIGQUERY_DATASET_PLACEHOLDERS, GCP_PROJECT_ID, READ_ONLY_RULE
page_header('Data & Methodology','Document data sources and BigQuery integration.')
status=get_data_source_status(); kpi_cards([("Data mode",status.mode,""),("BigQuery enabled",str(status.bigquery_enabled),""),("Project",GCP_PROJECT_ID,"")]); st.write(status.note); st.write(f"**{READ_ONLY_RULE}**"); method_df=pd.DataFrame({"source":["Teams","Players","Matches","Predictions"],"records":[len(get_teams()),len(get_players()),len(get_matches()),len(get_predictions())]}); st.plotly_chart(px.pie(method_df,names="source",values="records",title="Data coverage"),use_container_width=True)
