import streamlit as st

from modules.iceberg_connector import get_iceberg_table

st.set_page_config(page_title="Search", page_icon="🔍", layout="wide")
st.title("🔍 Metadata Search")

search_field = st.selectbox("Search By", ["image_id", "tag", "source_system"])
search_query = st.text_input("Search Query")


if search_query:
    @st.cache_data(ttl=300)
    def search_metadata(field, query):
        table = get_iceberg_table("media_db.image_metadata")
        df = table.scan().to_pandas()
        return df[df[field].astype(str).str.contains(query, case=False)]

    results = search_metadata(search_field, search_query)
    st.metric("Results Found", len(results))
