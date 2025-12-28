# Streamlit Image Gallery 이미지 미표시 문제

## 증상
- Streamlit `🖼️ Image Gallery` 화면에서 **Total Images**가 2로 표시되지만 실제 이미지가 렌더링되지 않음.
- S3 연결 상태는 정상으로 표시됨.

## 원인
- 갤러리 페이지가 Iceberg 메타데이터만 조회하고, **S3 객체를 내려받아 렌더링하는 로직이 없음**.
- `mime_type` 값이 비어있는 경우가 있어 이미지 판별이 실패할 수 있음(확장자 fallback 필요).

## 조치
- S3 경로(`s3a://...` 또는 `s3://...`)를 파싱해 실제 바이너리를 가져오는 유틸을 추가.
- 갤러리에서 메타데이터를 기반으로 이미지 후보를 필터링하고, S3 객체를 내려받아 `st.image()`로 렌더링.
- `mime_type`이 없을 경우 파일 확장자로 이미지 여부 판별.

## 수정 전/수정 후

### 수정 전 (이미지 렌더링 로직 부재)
```python
# streamlit-app/pages/01_Gallery.py

df = load_metadata(selected_tag)
st.metric("Total Images", len(df))
```

### 수정 후 (S3 다운로드 + 이미지 렌더링)
```python
# streamlit-app/pages/01_Gallery.py

def is_image_row(row):
    mime_type = str(getattr(row, "mime_type", "") or "")
    if mime_type.startswith("image/"):
        return True
    s3_path = str(getattr(row, "s3_path", "") or "").lower()
    return s3_path.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))

image_rows = [row for row in df.itertuples(index=False) if is_image_row(row)]
st.metric("Total Images", len(image_rows))

for row in image_rows:
    image_bytes = fetch_object_bytes(row.s3_path)
    st.image(image_bytes, caption=row.image_id, use_column_width=True)
```

### 수정 후 (S3 유틸 추가)
```python
# streamlit-app/modules/s3_utils.py

def parse_s3_path(s3_path: str):
    ...

def fetch_object_bytes(s3_path: str):
    bucket, key = parse_s3_path(s3_path)
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
```

## 수정한 문서/소스 및 라인 번호
- `streamlit-app/modules/s3_utils.py`
  - `parse_s3_path` 함수 추가: L19-L31
  - `fetch_object_bytes` 함수 추가: L34-L38
- `streamlit-app/pages/01_Gallery.py`
  - S3 바이너리 로딩 및 렌더링 로직 추가: L24-L52

## 비고
- `sample.txt` 같은 비이미지 파일은 표시 대상에서 제외됨.
- 이미지가 계속 표시되지 않으면 `s3_path` 값과 S3 객체 접근 권한을 재확인 필요.
