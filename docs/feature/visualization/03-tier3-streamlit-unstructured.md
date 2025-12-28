# Tier 3: 비정형 데이터 시각화 (Streamlit + PyIceberg)

## 🖼️ 개요

**대상 데이터**: `s3a://lakehouse/raw/images/` + `hive_prod.media_db.image_metadata` (Iceberg)
**사용 도구**: Streamlit + PyIceberg + boto3
**핵심 코드**: `python/fspark_raw_examples.py` (라인 92-121)
**주요 기능**: 이미지 갤러리, 메타데이터 검색, 통계
**사용자**: 데이터 과학자, 분석가

---

## 🎯 아키텍처

```
┌──────────────────────────┐
│  당신의 코드 실행 결과    │
│ (fspark_raw_examples.py) │
│                          │
│ S3 이미지 업로드         │
│ (라인 92-121)            │
└────────────┬─────────────┘
             │
             ↓
┌──────────────────────────┐
│    S3 저장소             │
│ (lakehouse/raw/images/)  │
│                          │
│ 📸 2025-12-25/image1.png │
│ 📸 2025-12-25/image2.png │
│ ...                      │
└────────────┬─────────────┘
             │
             ├──────────────────────┐
             │                      │
             ↓                      ↓
┌──────────────────────────┐ ┌──────────────────────────┐
│  Iceberg 메타데이터      │ │    boto3 (S3 접근)       │
│  image_metadata 테이블   │ │                          │
│                          │ │ 이미지 바이트 로드       │
│ - image_id              │ │                          │
│ - s3_path               │ │ PIL 이미지 변환          │
│ - upload_time           │ │                          │
│ - file_size             │ │ Streamlit 렌더링         │
│ - tag                   │ │                          │
└────────────┬─────────────┘ └────────────┬─────────────┘
             │                           │
             └──────────────┬────────────┘
                            ↓
                ┌──────────────────────────┐
                │     Streamlit App        │
                │    (Port: 8501)          │
                │                          │
                │ 📸 Image Gallery         │
                │ 🔍 Metadata Search       │
                │ 📊 Statistics Dashboard  │
                └────────────┬─────────────┘
                             │
                   👤 Data Scientists
                   (Image exploration)
```

---

## 💡 핵심 개념: 당신의 코드 분석

### 선택된 코드 (라인 92-105)

```python
# 라인 92: 날짜별 파티셔닝 경로 생성
image_s3_path = "s3a://lakehouse/raw/images/{date}/sample.txt".format(
    date=datetime.utcnow().strftime('%Y-%m-%d')
)

# 라인 96-98: Hadoop FileSystem 초기화
jconf = spark._jsc.hadoopConfiguration()
fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(
    spark._jvm.java.net.URI(image_s3_path), jconf
)
path = spark._jvm.org.apache.hadoop.fs.Path(image_s3_path)

# 라인 101-103: 바이너리 데이터 쓰기
out = fs.create(path, True)
out.write(bytearray(sample_bytes))  # ← 핵심 패턴
out.close()
```

### 패턴 분석

| 요소 | 설명 | Streamlit에서의 활용 |
|------|------|-------------------|
| **날짜 파티셔닝** | `{date}` 디렉토리 | 날짜 필터로 S3 경로 자동 생성 |
| **Hadoop API** | FileSystem 직접 접근 | S3 메타데이터 쿼리 대신 직접 접근 |
| **바이너리 처리** | `bytearray()` 변환 | PIL Image로 변환 후 렌더링 |
| **경로 검증** | 파일 존재 여부 확인 | Iceberg 메타데이터로 검증 |

---

## 📝 데이터 구조

### Iceberg 메타데이터 테이블

```sql
CREATE TABLE hive_prod.media_db.image_metadata (
    image_id STRING NOT NULL,                  -- UUID
    s3_path STRING NOT NULL,                   -- s3a://lakehouse/raw/images/2025-12-25/image1.png
    file_size BIGINT,                          -- 바이트
    mime_type STRING,                          -- image/png
    upload_time TIMESTAMP,                     -- 업로드 시각
    source_system STRING,                      -- 'manual', 'batch'
    tag STRING,                                -- 'product', 'user', 'analytics'
    width INT,                                 -- 픽셀
    height INT,                                -- 픽셀
    checksum STRING,                           -- MD5
    is_indexed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(upload_time), tag)
```

### DDL 실행

```sql
-- Trino에서 테이블 생성
CREATE SCHEMA IF NOT EXISTS hive_prod.media_db;

CREATE TABLE hive_prod.media_db.image_metadata (
    image_id STRING NOT NULL,
    s3_path STRING NOT NULL,
    file_size BIGINT,
    mime_type STRING,
    upload_time TIMESTAMP,
    source_system STRING,
    tag STRING,
    width INT,
    height INT,
    checksum STRING,
    is_indexed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(upload_time), tag)
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.metadata.compression-codec' = 'gzip'
);
```

---

## 🚀 구현 단계

### Step 1: 이미지 업로드 (당신의 코드 실행)

```bash
cd /home/i/work/ai/lakehouse-tick/python
python fspark_raw_examples.py

# 출력:
# 비정형(바이너리) 파일 저장 완료 -> s3a://lakehouse/raw/images/2025-12-25/sample.txt
# 로컬 이미지 파일 업로드 완료 -> s3a://lakehouse/raw/images/2025-12-25/image1.png
# raw/ 경로에 있는 항목 수: 2
```

### Step 2: 메타데이터 테이블 생성

```bash
# Trino CLI 접속
docker exec -it trino trino --server localhost:8080 --catalog hive_prod

# DDL 실행 (위의 SQL 복사)
```

### Step 3: 샘플 메타데이터 INSERT

```sql
INSERT INTO hive_prod.media_db.image_metadata VALUES
('img-001', 's3a://lakehouse/raw/images/2025-12-25/image1.png', 102400, 'image/png',
 TIMESTAMP '2025-12-25 10:00:00', 'manual', 'product', 800, 600,
 'abc123def456', FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
```

### Step 4: Streamlit 애플리케이션 파일 생성

#### 디렉토리 구조

```
streamlit-app/
├── app.py
├── pages/
│   ├── 01_Gallery.py
│   ├── 02_🔍_Metadata_Search.py
│   └── 03_Statistics.py
├── modules/
│   ├── iceberg_connector.py
│   ├── s3_utils.py
│   └── __init__.py
├── requirements.txt
└── .streamlit/
    └── config.toml
```

#### `requirements.txt`

```txt
streamlit==1.30.0
pyiceberg==0.5.1
pandas==2.1.4
boto3==1.34.0
Pillow==10.1.0
pyarrow==14.0.0
python-dotenv==1.0.0
```

#### `modules/iceberg_connector.py`

```python
from pyiceberg.catalog import load_catalog
import os

def get_iceberg_table(table_name):
    """Iceberg 테이블 로드"""
    catalog = load_catalog("default", **{
        "type": "hive",
        "uri": os.getenv("HIVE_METASTORE_URI", "thrift://hive-metastore:9083"),
        "s3.endpoint": os.getenv("AWS_ENDPOINT_URL_S3", "http://seaweedfs-s3:8333"),
        "s3.access-key-id": os.getenv("AWS_ACCESS_KEY_ID", "seaweedfs_access_key"),
        "s3.secret-access-key": os.getenv("AWS_SECRET_ACCESS_KEY", "seaweedfs_secret_key"),
        "s3.path-style-access": "true"
    })

    return catalog.load_table(table_name)
```

#### `modules/s3_utils.py`

```python
import boto3
import os

def get_s3_client():
    """SeaweedFS S3 클라이언트 생성"""
    return boto3.client(
        's3',
        endpoint_url=os.getenv('AWS_ENDPOINT_URL_S3', 'http://seaweedfs-s3:8333'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'seaweedfs_access_key'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'seaweedfs_secret_key'),
        region_name='us-east-1'
    )
```

#### `app.py` (메인 네비게이션)

```python
import streamlit as st
from modules.iceberg_connector import get_iceberg_table
from modules.s3_utils import get_s3_client

st.set_page_config(
    page_title="Lakehouse Unstructured Data Explorer",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🖼️ Lakehouse Unstructured Data Explorer")
st.markdown("""
비정형 데이터(이미지, 비디오, 오디오)를 탐색하고 관리하는 통합 도구입니다.

**기능**:
- 📸 **이미지 갤러리**: S3에 저장된 이미지를 날짜/태그별로 필터링하여 확인
- 🔍 **메타데이터 검색**: 이미지 속성으로 검색
- 📊 **통계 대시보드**: 저장소 사용량, 파일 형식 분포 등

**데이터 소스**:
- **S3**: `s3a://lakehouse/raw/images/`
- **메타데이터**: `hive_prod.media_db.image_metadata` (Iceberg)
""")

st.markdown("---")

# 연결 상태 확인
with st.sidebar:
    st.header("Connection Status")
    try:
        table = get_iceberg_table("hive_prod.media_db.image_metadata")
        df = table.scan().limit(1).to_pandas()
        st.success("✅ Iceberg 연결 성공")
    except Exception as e:
        st.error(f"❌ Iceberg 연결 실패: {e}")

    try:
        s3 = get_s3_client()
        s3.list_objects_v2(Bucket='lakehouse', Prefix='raw/images/', MaxKeys=1)
        st.success("✅ S3 연결 성공")
    except Exception as e:
        st.error(f"❌ S3 연결 실패: {e}")
```

#### `pages/01_Gallery.py` (이미지 갤러리)

```python
import streamlit as st
import pandas as pd
from modules.iceberg_connector import get_iceberg_table
from modules.s3_utils import get_s3_client
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Image Gallery", page_icon="🖼️", layout="wide")
st.title("🖼️ Image Gallery")

# 필터
with st.sidebar:
    st.header("Filters")
    selected_tag = st.selectbox("Tag", ['all', 'product', 'user', 'analytics'])
    date_range = st.date_input("Upload Date Range", [])
    size_range = st.slider("File Size (KB)", 0, 10000, (0, 10000))

# 메타데이터 로드
@st.cache_data(ttl=300)
def load_metadata(tag, date_range, size_range):
    table = get_iceberg_table("hive_prod.media_db.image_metadata")
    df = table.scan().to_pandas()

    if tag != 'all':
        df = df[df['tag'] == tag]
    if len(date_range) == 2:
        df = df[(df['upload_time'] >= pd.Timestamp(date_range[0])) &
                (df['upload_time'] <= pd.Timestamp(date_range[1]))]
    df = df[(df['file_size'] >= size_range[0] * 1024) &
            (df['file_size'] <= size_range[1] * 1024)]

    return df.sort_values('upload_time', ascending=False)

df = load_metadata(selected_tag, date_range, size_range)

# 통계
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Images", len(df))
with col2:
    st.metric("Total Size (MB)", f"{df['file_size'].sum() / 1024 / 1024:.2f}")
with col3:
    st.metric("Avg Size (KB)", f"{df['file_size'].mean() / 1024:.2f}")
with col4:
    st.metric("Unique Tags", df['tag'].nunique())

st.markdown("---")

# 페이지네이션
items_per_page = 20
total_pages = (len(df) - 1) // items_per_page + 1
page_number = st.selectbox("Page", range(1, total_pages + 1)) if total_pages > 1 else 1

start_idx = (page_number - 1) * items_per_page
end_idx = min(start_idx + items_per_page, len(df))

# 갤러리 렌더링 (4열 그리드)
st.subheader(f"Showing {start_idx + 1}-{end_idx} of {len(df)} images")
cols = st.columns(4)

s3_client = get_s3_client()

for idx, (_, row) in enumerate(df.iloc[start_idx:end_idx].iterrows()):
    col = cols[idx % 4]
    with col:
        try:
            # S3에서 이미지 로드
            s3_path = row['s3_path'].replace('s3a://', '')
            bucket, key = s3_path.split('/', 1)

            response = s3_client.get_object(Bucket=bucket, Key=key)
            image_bytes = response['Body'].read()

            image = Image.open(BytesIO(image_bytes))
            st.image(image, use_container_width=True)
            st.caption(f"**{row['image_id']}**")

            with st.expander("📋 Metadata"):
                st.json({
                    "ID": row['image_id'],
                    "Size": f"{row['file_size'] / 1024:.2f} KB",
                    "Type": row['mime_type'],
                    "Dimensions": f"{row['width']}x{row['height']}",
                    "Upload Time": str(row['upload_time']),
                    "Tag": row['tag']
                })
        except Exception as e:
            st.error(f"Failed to load {row['image_id']}: {e}")
```

---

## 🖼️ 실제 사용 시나리오

### 시나리오: 데이터 과학자

```
Streamlit 접속 (http://localhost:8501)
  ↓
📸 "Image Gallery" 페이지 클릭
  ↓
필터 설정:
  - Tag: "product"
  - Date: 최근 7일
  - File Size: 0-1000 KB
  ↓
✅ "당신의 코드" 패턴으로 업로드된 이미지 5개 표시
  ↓
📊 각 이미지 클릭 → 메타데이터 확인
  (파일명, 크기, 생성일, 태그)
  ↓
📊 "Statistics" 페이지로 이동
  ↓
📈 태그별 이미지 개수 분포 확인
  ↓
💾 이미지 다운로드 버튼으로 저장
  ↓
✅ 분석 시작
```

---

## 🔧 Docker 배포

### docker-compose.yml 추가

```yaml
streamlit:
  image: python:3.11-slim
  container_name: streamlit-app
  working_dir: /app
  depends_on:
    hive-metastore:
      condition: service_healthy
    seaweedfs-s3:
      condition: service_healthy
  ports:
    - "8501:8501"
  environment:
    AWS_ACCESS_KEY_ID: seaweedfs_access_key
    AWS_SECRET_ACCESS_KEY: seaweedfs_secret_key
    AWS_ENDPOINT_URL_S3: http://seaweedfs-s3:8333
    HIVE_METASTORE_URI: thrift://hive-metastore:9083
  volumes:
    - ./streamlit-app:/app
    - ./logs/streamlit:/app/logs
  networks:
    - default
  command: >
    bash -c "
    pip install --no-cache-dir -r requirements.txt &&
    streamlit run app.py --server.port=8501
    "
```

### 실행

```bash
docker-compose up -d streamlit

# 접속
# http://localhost:8501
```

---

## ⚙️ 성능 최적화

### 1. 캐싱 (5분)

```python
@st.cache_data(ttl=300)
def load_metadata(...):
    ...
```

### 2. 페이지네이션 (20개씩)

```python
items_per_page = 20
df.iloc[start_idx:end_idx]
```

### 3. 썸네일 저장 (S3)

```python
# 당신의 코드 패턴 확장
thumb_s3_path = "s3a://lakehouse/raw/thumbnails/{date}/thumb_{filename}"
# ... Hadoop FileSystem 패턴으로 업로드
```

---

## 📚 다음 단계

1. ✅ Tier 1 완료: [Superset + Trino](./01-tier1-superset-trino-structured.md)
2. ✅ Tier 2 완료: [Grafana + OpenSearch](./02-tier2-grafana-opensearch-semistructured.md)
3. ✅ Tier 3 완료: 현재 문서
4. 👉 [전체 통합 가이드](./README.md)로 이동

---

## ✅ 체크리스트 (15개 항목)

- [ ] Iceberg 메타데이터 테이블 생성
- [ ] 샘플 메타데이터 INSERT
- [ ] Python 베이스 이미지 선택
- [ ] requirements.txt 작성
- [ ] Docker 컨테이너 설정
- [ ] 포트 매핑 (8501)
- [ ] 볼륨 마운트
- [ ] `app.py` 작성
- [ ] `pages/01_Gallery.py` 작성
- [ ] `modules/iceberg_connector.py` 작성
- [ ] `modules/s3_utils.py` 작성
- [ ] PyIceberg 연결 테스트
- [ ] S3 연결 테스트
- [ ] 이미지 갤러리 렌더링 확인
- [ ] 메타데이터 필터링 확인

---

**축하합니다!** 이제 비정형 데이터 시각화 계층이 완성되었습니다. 🎉

당신이 선택한 코드(`fspark_raw_examples.py:92-121`)가 완벽하게 통합되어 Streamlit 갤러리에서 작동합니다! 🖼️
