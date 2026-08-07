import streamlit as st  # noqa
st.set_page_config(page_title="World Cup Analytics Dashboard", page_icon="⚽", layout="wide")
PAGE_TITLES=["Tournament Overview","Team Performance","Player Analysis","Match Analysis","Predictions / Model Results","Data & Methodology"]
PAGES=[st.Page("pages/overview.py",title="Tournament Overview"),st.Page("pages/teams.py",title="Team Performance"),st.Page("pages/players.py",title="Player Analysis"),st.Page("pages/matches.py",title="Match Analysis"),st.Page("pages/predictions.py",title="Predictions / Model Results"),st.Page("pages/methodology.py",title="Data & Methodology")]
def build_navigation(): return st.navigation(PAGES)
def main():
    st.sidebar.title("World Cup Analytics")
    from data.real_wc26 import get_real_wc26_data_source_status
    status = get_real_wc26_data_source_status()
    if status.mode == "s3_live":
        st.sidebar.success("☁️ Live from AWS S3")
        st.sidebar.caption(f"s3://wc26-kaggle-data/kaggle_wc26/")
        if status.tables_available:
            n_tables = len(status.tables_available)
            st.sidebar.caption(f"{n_tables} tables loaded from S3")
    elif status.athena_enabled:
        st.sidebar.success(f"Live data: AWS Athena ({status.mode})")
        if status.tables_available:
            n_tables = len(status.tables_available)
            st.sidebar.caption(f"{n_tables} tables/views in worldcup_2026")
    else:
        st.sidebar.info(f"📊 {status.note[:100]}")
    build_navigation().run()
if __name__=="__main__": main()
# deploy trigger: 2026-08-07-ui-v2
