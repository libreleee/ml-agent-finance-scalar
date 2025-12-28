import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from modules.iceberg_connector import get_iceberg_table
from modules.s3_utils import get_s3_client

st.set_page_config(
    page_title="Unstructured Data Explorer",
    page_icon="🖼️",
    layout="wide",
)

st.title("🖼️ Lakehouse Unstructured Data Explorer")

# Status checks
st.sidebar.header("System Status")
try:
    table = get_iceberg_table("media_db.image_metadata")
    st.sidebar.success("✅ Iceberg connected")
except Exception as exc:
    st.sidebar.error(f"❌ Iceberg error: {exc}")

try:
    s3 = get_s3_client()
    s3.list_buckets()
    st.sidebar.success("✅ S3 connected")
except Exception as exc:
    st.sidebar.error(f"❌ S3 error: {exc}")
