from pages._shared import *
from data.bigquery import ALLOWED_BIGQUERY_DATASET_PLACEHOLDERS, GCP_PROJECT_ID, BIGQUERY_DATASET, READ_ONLY_RULE
page_header('Data & Methodology','Document data sources and BigQuery integration.')
status=get_data_source_status(); kpi_cards([("Data mode",status.mode,""),("BigQuery enabled",str(status.bigquery_enabled),""),("Project",f"{GCP_PROJECT_ID}.{BIGQUERY_DATASET}","")]); st.write(status.note); st.write(f"**{READ_ONLY_RULE}**"); 
if status.tables_available:
    st.write("### Available Tables")
    table_df=pd.DataFrame([{"Table":k,"Rows":v} for k,v in status.tables_available.items()])
    st.dataframe(table_df,width='stretch')
else:
    st.write("Table metadata unavailable in current mode")
st.write("**Source Tables:**")
st.write("- wc26_dashboard_comprehensive_v15_live (48 teams, comprehensive predictions)")
st.write("- v_winner_prediction_dashboard_v15_live_10m (48 teams, stage probabilities)")
st.write("- v_real_player_rows_enriched_v8 (32,957 player records)")
st.write("- v_team_schedule (208 matches)")
st.write("**Model:** V15_LIVE_FULL_MONTE_CARLO - 10,000,000 tournament simulations")
