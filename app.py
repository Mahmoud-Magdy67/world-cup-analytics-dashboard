import streamlit as st
st.set_page_config(page_title="World Cup Analytics Dashboard", page_icon="⚽", layout="wide")
PAGE_TITLES=["Tournament Overview","Team Performance","Player Analysis","Match Analysis","Predictions / Model Results","Data & Methodology"]
PAGES=[st.Page("pages/overview.py",title="Tournament Overview"),st.Page("pages/teams.py",title="Team Performance"),st.Page("pages/players.py",title="Player Analysis"),st.Page("pages/matches.py",title="Match Analysis"),st.Page("pages/predictions.py",title="Predictions / Model Results"),st.Page("pages/methodology.py",title="Data & Methodology")]
def build_navigation(): return st.navigation(PAGES)
def main(): st.sidebar.title("World Cup Analytics"); st.sidebar.info("Mock-data first release. BigQuery wiring is intentionally disabled."); build_navigation().run()
if __name__=="__main__": main()
