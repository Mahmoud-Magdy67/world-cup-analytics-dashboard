import pandas as pd
import plotly.express as px
import streamlit as st
from data.bigquery import *
def kpi_cards(items):
    cols=st.columns(len(items))
    for col,(label,value,delta) in zip(cols,items): col.metric(label,value,delta)
def page_header(title,description): st.title(title); st.caption(description)
