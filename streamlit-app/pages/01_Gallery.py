import streamlit as st

from modules.iceberg_connector import get_iceberg_table
from modules.s3_utils import fetch_object_bytes

st.set_page_config(page_title="Gallery", page_icon="🖼️", layout="wide")
st.title("🖼️ Image Gallery")

# Sidebar filters
st.sidebar.header("Filters")
tag_options = ["all", "product", "user", "analytics"]
selected_tag = st.sidebar.selectbox("Tag", tag_options)


@st.cache_data(ttl=300)
def load_metadata(tag):
    table = get_iceberg_table("media_db.image_metadata")
    df = table.scan().to_pandas()
    if tag != "all":
        df = df[df["tag"] == tag]
    return df


df = load_metadata(selected_tag)
if df.empty:
    st.info("표시할 이미지가 없습니다.")
else:
    def is_image_row(row):
        mime_type = str(getattr(row, "mime_type", "") or "")
        if mime_type.startswith("image/"):
            return True
        s3_path = str(getattr(row, "s3_path", "") or "").lower()
        return s3_path.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))

    image_rows = [row for row in df.itertuples(index=False) if is_image_row(row)]
    st.metric("Total Images", len(image_rows))
    if not image_rows:
        st.warning("이미지 MIME 타입 데이터가 없습니다.")
    else:
        cols = st.columns(3)
        for idx, row in enumerate(image_rows):
            column = cols[idx % len(cols)]
            s3_path = getattr(row, "s3_path", None)
            caption = getattr(row, "image_id", "image")
            if not s3_path:
                column.warning(f"{caption}: s3_path 없음")
                continue
            try:
                image_bytes = fetch_object_bytes(s3_path)
                column.image(image_bytes, caption=caption, use_column_width=True)
            except Exception as exc:
                column.warning(f"{caption}: 이미지 로드 실패 ({exc})")
