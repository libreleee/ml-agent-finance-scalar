import plotly.express as px
import streamlit as st

from modules.iceberg_connector import get_iceberg_table

st.set_page_config(page_title="Statistics", page_icon="📊", layout="wide")
st.title("📊 Statistics Dashboard")


@st.cache_data(ttl=300)
def load_stats():
    table = get_iceberg_table("media_db.image_metadata")
    return table.scan().to_pandas()


df = load_stats()
if len(df) > 0:
    tag_counts = df["tag"].value_counts()
    fig = px.bar(tag_counts, title="Count by Tag")
    st.plotly_chart(fig, use_container_width=True)
