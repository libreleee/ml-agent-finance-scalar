# 시각화 스택 코드 변경사항 (Code Changes Summary)

> **요약**: 문서 생성은 완료되었습니다. 이 파일은 해당 문서들을 **실제로 구현**하기 위해 필요한 모든 코드/설정 변경사항을 설명합니다.

---

## 📊 변경사항 개요 (Change Overview)

### 추가될 서비스 (9개 신규 컨테이너)
1. **Superset** (BI Dashboard)
2. **Superset-DB** (PostgreSQL for Superset metadata)
3. **Superset-Redis** (Cache layer)
4. **Grafana** (Monitoring dashboards)
5. **OpenSearch** (Log storage)
6. **OpenSearch-Dashboards** (Log UI)
7. **Prometheus** (Metrics collection)
8. **Node-Exporter** (System metrics)
9. **Streamlit** (Unstructured data app)

### 추가될 디렉토리 구조
```
lakehouse-tick/
├── docker-compose.yml                 # ← 수정: 9개 서비스 추가
├── .env.example                       # ← 신규: 환경변수 템플릿
├── config/
│   ├── prometheus/
│   │   └── prometheus.yml             # ← 신규
│   ├── superset/
│   │   └── superset_config.py         # ← 신규
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── datasources/
│   │       │   ├── opensearch.yml     # ← 신규
│   │       │   └── prometheus.yml     # ← 신규
│   │       └── dashboards/
│   │           └── lakehouse-overview.json  # ← 신규 (예시)
│   ├── opensearch/
│   │   ├── opensearch.yml             # ← 신규
│   │   └── opensearch_dashboards.yml  # ← 신규
│   └── fluentd/
│       └── fluent.conf                # ← 신규 (선택사항)
├── streamlit-app/                     # ← 신규 (Streamlit 애플리케이션)
│   ├── app.py
│   ├── requirements.txt
│   ├── modules/
│   │   ├── iceberg_connector.py
│   │   └── s3_utils.py
│   └── pages/
│       ├── 01_Gallery.py
│       ├── 02_Search.py
│       └── 03_Statistics.py
├── logs/
│   ├── superset/                      # ← 신규 (로그 볼륨)
│   ├── grafana/                       # ← 신규
│   ├── streamlit/                     # ← 신규
│   └── opensearch/                    # ← 신규
└── scripts/
    └── setup-visualization.sh         # ← 신규 (자동화 스크립트)
```

---

## 🔧 상세 코드 변경사항

### 1️⃣ docker-compose.yml 확장 (약 500줄 추가)

#### A. Superset + PostgreSQL + Redis 추가

```yaml
# ============================================================================
# Visualization Layer: Apache Superset
# ============================================================================

superset-db:
  image: postgres:15
  container_name: superset-db
  environment:
    POSTGRES_DB: superset
    POSTGRES_USER: superset
    POSTGRES_PASSWORD: superset
  volumes:
    - superset-db-data:/var/lib/postgresql/data
  networks:
    - lakehouse-net
  healthcheck:
    test: ["CMD", "pg_isready", "-U", "superset", "-d", "superset"]
    interval: 10s
    timeout: 5s
    retries: 5

superset-redis:
  image: redis:7-alpine
  container_name: superset-redis
  ports:
    - "6380:6379"
  volumes:
    - superset-redis-data:/data
  networks:
    - lakehouse-net
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

superset:
  image: apache/superset:latest-dev
  container_name: superset
  depends_on:
    superset-db:
      condition: service_healthy
    superset-redis:
      condition: service_started
    trino:
      condition: service_started
  ports:
    - "8088:8088"
  environment:
    SUPERSET_SECRET_KEY: "${SUPERSET_SECRET_KEY:-CHANGE_THIS_TO_A_RANDOM_SECRET_KEY}"
    SQLALCHEMY_DATABASE_URI: postgresql://superset:superset@superset-db:5432/superset
    REDIS_HOST: superset-redis
    REDIS_PORT: 6379
    SUPERSET_LOAD_EXAMPLES: "no"
    SUPERSET_WEBSERVER_TIMEOUT: 60
    SUPERSET_ROW_LIMIT: 10000
  volumes:
    - superset-data:/app/superset_home
    - ./config/superset/superset_config.py:/app/pythonpath/superset_config.py:ro
    - ./logs/superset:/app/logs
  networks:
    - lakehouse-net
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8088/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
      reservations:
        cpus: '1'
        memory: 2G
  command: >
    bash -c "
    superset db upgrade &&
    superset fab create-admin --username admin --firstname Admin --lastname User --email admin@example.com --password admin || true &&
    superset init &&
    gunicorn -w 4 -b 0.0.0.0:8088 --timeout 60 superset.app:create_app()
    "
```

#### B. Grafana + OpenSearch + Prometheus 추가

```yaml
# ============================================================================
# Monitoring Layer: Grafana, OpenSearch, Prometheus
# ============================================================================

opensearch:
  image: opensearchproject/opensearch:2.11.1
  container_name: opensearch
  environment:
    - cluster.name=lakehouse-logs
    - node.name=opensearch-node1
    - discovery.type=single-node
    - bootstrap.memory_lock=true
    - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
    - OPENSEARCH_INITIAL_ADMIN_PASSWORD="${OPENSEARCH_PASSWORD:-Admin@123}"
  ulimits:
    memlock:
      soft: -1
      hard: -1
    nofile:
      soft: 65536
      hard: 65536
  ports:
    - "9200:9200"
    - "9600:9600"
  volumes:
    - opensearch-data:/usr/share/opensearch/data
    - ./config/opensearch/opensearch.yml:/usr/share/opensearch/config/opensearch.yml:ro
  networks:
    - lakehouse-net
  healthcheck:
    test: ["CMD", "curl", "-ku", "admin:Admin@123", "https://localhost:9200/_cluster/health"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s

opensearch-dashboards:
  image: opensearchproject/opensearch-dashboards:2.11.1
  container_name: opensearch-dashboards
  depends_on:
    opensearch:
      condition: service_healthy
  ports:
    - "5601:5601"
  environment:
    OPENSEARCH_HOSTS: '["https://opensearch:9200"]'
    OPENSEARCH_USERNAME: admin
    OPENSEARCH_PASSWORD: "${OPENSEARCH_PASSWORD:-Admin@123}"
  volumes:
    - ./config/opensearch/opensearch_dashboards.yml:/usr/share/opensearch-dashboards/config/opensearch_dashboards.yml:ro
  networks:
    - lakehouse-net

prometheus:
  image: prom/prometheus:v2.49.0
  container_name: prometheus
  ports:
    - "9090:9090"
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
    - '--storage.tsdb.path=/prometheus'
    - '--storage.tsdb.retention.time=30d'
  volumes:
    - ./config/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    - prometheus-data:/prometheus
  networks:
    - lakehouse-net
  healthcheck:
    test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
    interval: 30s
    timeout: 10s
    retries: 3

node-exporter:
  image: prom/node-exporter:v1.7.0
  container_name: node-exporter
  ports:
    - "9100:9100"
  command:
    - '--path.procfs=/host/proc'
    - '--path.sysfs=/host/sys'
  volumes:
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
    - /:/rootfs:ro
  networks:
    - lakehouse-net

grafana:
  image: grafana/grafana:10.3.0
  container_name: grafana
  depends_on:
    opensearch:
      condition: service_healthy
    prometheus:
      condition: service_started
  ports:
    - "3000:3000"
  environment:
    GF_SECURITY_ADMIN_USER: admin
    GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_PASSWORD:-admin}"
    GF_INSTALL_PLUGINS: grafana-opensearch-datasource,grafana-clock-panel
    GF_AUTH_ANONYMOUS_ENABLED: "false"
    GF_SERVER_ROOT_URL: http://localhost:3000
  volumes:
    - grafana-data:/var/lib/grafana
    - ./config/grafana/provisioning:/etc/grafana/provisioning:ro
    - ./logs/grafana:/var/log/grafana
  networks:
    - lakehouse-net
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 2G
```

#### C. Streamlit 추가

```yaml
# ============================================================================
# Application Layer: Streamlit
# ============================================================================

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
    AWS_REGION: us-east-1
    HIVE_METASTORE_URI: thrift://hive-metastore:9083
    STREAMLIT_SERVER_PORT: 8501
    STREAMLIT_SERVER_HEADLESS: "true"
    STREAMLIT_BROWSER_GATHER_USAGE_STATS: "false"
  volumes:
    - ./streamlit-app:/app
    - ./logs/streamlit:/app/logs
  networks:
    - lakehouse-net
  command: >
    bash -c "
    pip install --no-cache-dir -r requirements.txt &&
    streamlit run app.py --server.port=8501 --server.headless=true --server.address=0.0.0.0
    "
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 30s
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 2G
```

#### D. Volumes 추가

```yaml
volumes:
  # 기존
  warehouse:
  postgres-data:
  seaweedfs-data:

  # 신규
  superset-data:
  superset-db-data:
  superset-redis-data:
  grafana-data:
  opensearch-data:
  prometheus-data:
```

---

### 2️⃣ 환경 변수 파일 (.env.example 신규)

```bash
# ============================================================================
# Visualization Stack Configuration
# ============================================================================

# Superset Settings
SUPERSET_SECRET_KEY=your-super-secret-key-change-this-in-production
SUPERSET_ADMIN_USER=admin
SUPERSET_ADMIN_PASSWORD=admin

# Grafana Settings
GRAFANA_PASSWORD=admin

# OpenSearch Settings
OPENSEARCH_PASSWORD=Admin@123

# S3 Settings (SeaweedFS)
AWS_ACCESS_KEY_ID=seaweedfs_access_key
AWS_SECRET_ACCESS_KEY=seaweedfs_secret_key
AWS_ENDPOINT_URL_S3=http://seaweedfs-s3:8333

# Hive Metastore
HIVE_METASTORE_URI=thrift://hive-metastore:9083

# Network
LAKEHOUSE_NETWORK=lakehouse-net

# Storage
LAKEHOUSE_DATA_PATH=/home/iceberg/warehouse
LAKEHOUSE_S3_BUCKET=lakehouse
```

---

### 3️⃣ Prometheus 설정 (config/prometheus/prometheus.yml 신규)

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'lakehouse-monitor'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'trino'
    static_configs:
      - targets: ['trino:8080']

  - job_name: 'seaweedfs-master'
    static_configs:
      - targets: ['seaweedfs-master:9333']
```

---

### 4️⃣ Superset 설정 (config/superset/superset_config.py 신규)

```python
# ============================================================================
# Superset Configuration
# ============================================================================

import os
from datetime import timedelta

# Database
SQLALCHEMY_DATABASE_URI = os.getenv(
    'SQLALCHEMY_DATABASE_URI',
    'postgresql://superset:superset@superset-db:5432/superset'
)

# Cache
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5 minutes
    'CACHE_REDIS_HOST': 'superset-redis',
    'CACHE_REDIS_PORT': 6379,
    'CACHE_REDIS_DB': 0,
}

# Security
SECRET_KEY = os.getenv('SUPERSET_SECRET_KEY', 'change-me-in-production')
SUPERSET_WEBSERVER_TIMEOUT = 60
ROW_LIMIT = 10000

# Features
SUPERSET_FEATURE_FLAGS = {
    'ALLOW_USER_PROFILE_EDIT': True,
    'ENABLE_FORMULA_EDITING': True,
    'ENABLE_EXPLORE_JSON_CSRF_PROTECTION': False,
}

# Logging
LOGGING_CONFIGURATION = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/app/logs/superset.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'default',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['file'],
    },
}

# Session
PERMANENT_SESSION_LIFETIME = timedelta(days=7)

# SQL Alchemy
SQLALCHEMY_ECHO = False
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Babel Config for translations
BABEL_DEFAULT_LOCALE = 'en'
LANGUAGES = {
    'en': {'flag': 'us', 'name': 'English'},
    'ko': {'flag': 'kr', 'name': '한국어'},
}
```

---

### 5️⃣ OpenSearch 설정 (config/opensearch/opensearch.yml 신규)

```yaml
cluster.name: lakehouse-logs
node.name: opensearch-node1

discovery.type: single-node

# Network settings
network.host: 0.0.0.0
http.port: 9200

# Cluster settings
cluster.initial_master_nodes: ["opensearch-node1"]

# Performance
thread_pool.search.queue_size: 1000
thread_pool.bulk.queue_size: 1000

# Security (ensure HTTPS in production)
plugins.security.ssl.http.enabled: true
plugins.security.ssl.http.pemcert_filepath: certs/node1.pem
plugins.security.ssl.http.pemkey_filepath: certs/node1-key.pem
plugins.security.ssl.http.pemtrustedcas_filepath: certs/root-ca.pem
plugins.security.ssl.http.enforce_hostname_verification: false

plugins.security.ssl.transport.pemcert_filepath: certs/node1.pem
plugins.security.ssl.transport.pemkey_filepath: certs/node1-key.pem
plugins.security.ssl.transport.pemtrustedcas_filepath: certs/root-ca.pem
plugins.security.ssl.transport.enforce_hostname_verification: false

# Admin credentials (INTERNAL USE ONLY - NEVER COMMIT)
plugins.security.authcz.admin_dn:
  - "CN=admin,O=Example Com,ST=London,C=UK"

plugins.security.nodes_dn:
  - "CN=opensearch-node1,O=Example Com,ST=London,C=UK"

# Allow anonymous access for development (DISABLE IN PRODUCTION)
plugins.security.allow_default_init: true
```

---

### 6️⃣ OpenSearch Dashboards 설정 (config/opensearch/opensearch_dashboards.yml 신규)

```yaml
server.port: 5601
server.host: "0.0.0.0"

opensearch.hosts: ["https://opensearch:9200"]
opensearch.username: "admin"
opensearch.password: "Admin@123"

opensearch.ssl.verificationMode: "none"

opensearchDashboards.defaultAppId: "home"

logging.dest: /var/log/opensearch-dashboards/opensearch-dashboards.log
logging.verbose: false
```

---

### 7️⃣ Grafana Provisioning 설정

#### config/grafana/provisioning/datasources/opensearch.yml

```yaml
apiVersion: 1

datasources:
  - name: OpenSearch
    type: grafana-opensearch-datasource
    access: proxy
    url: https://opensearch:9200
    basicAuth: true
    basicAuthUser: admin
    basicAuthPassword: Admin@123
    isDefault: false
    jsonData:
      tlsSkipVerify: true
      logMessageField: message
      logLevelField: level
      esVersion: "7.10.0"
```

#### config/grafana/provisioning/datasources/prometheus.yml

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

---

### 8️⃣ Streamlit 애플리케이션 (streamlit-app/ 신규)

#### streamlit-app/requirements.txt

```
streamlit==1.30.0
pyiceberg==0.5.1
pandas==2.1.4
boto3==1.34.0
Pillow==10.1.0
pyarrow==14.0.0
trino==0.22.0
```

#### streamlit-app/app.py

```python
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.iceberg_connector import get_iceberg_table
from modules.s3_utils import get_s3_client

st.set_page_config(
    page_title="Unstructured Data Explorer",
    page_icon="🖼️",
    layout="wide"
)

st.title("🖼️ Lakehouse Unstructured Data Explorer")
st.markdown("---")

# Navigation
st.sidebar.header("Navigation")
st.sidebar.markdown("""
- **Gallery**: Browse images with filtering
- **Search**: Find images by metadata
- **Statistics**: View data insights
""")

st.sidebar.markdown("---")

# Status checks
st.sidebar.header("System Status")
try:
    table = get_iceberg_table("hive_prod.media_db.image_metadata")
    st.sidebar.success("✅ Iceberg connected")
except Exception as e:
    st.sidebar.error(f"❌ Iceberg error: {e}")

try:
    s3_client = get_s3_client()
    s3_client.list_buckets()
    st.sidebar.success("✅ S3 connected")
except Exception as e:
    st.sidebar.error(f"❌ S3 error: {e}")

st.markdown("""
Welcome to the Lakehouse Unstructured Data Explorer!

This application provides access to images and unstructured data stored in the lakehouse.
Use the sidebar to navigate to different features.
""")
```

#### streamlit-app/modules/iceberg_connector.py

```python
"""
Iceberg Catalog Connector Module
"""
import os
from pyiceberg.catalog import load_catalog

def get_iceberg_table(table_name: str):
    """
    Load an Iceberg table from the catalog

    Args:
        table_name: Table name in format 'catalog.database.table'

    Returns:
        pyiceberg.table.Table object

    Raises:
        Exception: If catalog connection fails
    """
    try:
        catalog = load_catalog("default", **{
            "type": "hive",
            "uri": os.getenv("HIVE_METASTORE_URI", "thrift://hive-metastore:9083"),
            "s3.endpoint": os.getenv("AWS_ENDPOINT_URL_S3", "http://seaweedfs-s3:8333"),
            "s3.access-key-id": os.getenv("AWS_ACCESS_KEY_ID", "seaweedfs_access_key"),
            "s3.secret-access-key": os.getenv("AWS_SECRET_ACCESS_KEY", "seaweedfs_secret_key"),
            "s3.path-style-access": "true"
        })

        return catalog.load_table(table_name)
    except Exception as e:
        raise Exception(f"Failed to load table '{table_name}': {str(e)}")
```

#### streamlit-app/modules/s3_utils.py

```python
"""
S3/SeaweedFS Utility Module
"""
import boto3
import os

def get_s3_client():
    """
    Create a boto3 S3 client configured for SeaweedFS

    Returns:
        boto3.client: S3 client instance
    """
    return boto3.client(
        's3',
        endpoint_url=os.getenv('AWS_ENDPOINT_URL_S3', 'http://seaweedfs-s3:8333'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'seaweedfs_access_key'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'seaweedfs_secret_key'),
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        verify=False  # SeaweedFS uses self-signed certs
    )

def list_images(bucket: str, prefix: str = "raw/images/"):
    """
    List all images in S3 bucket

    Args:
        bucket: S3 bucket name
        prefix: S3 key prefix

    Returns:
        List of image keys
    """
    client = get_s3_client()
    response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)

    if 'Contents' not in response:
        return []

    return [obj['Key'] for obj in response['Contents']]

def download_image(bucket: str, key: str) -> bytes:
    """
    Download image from S3

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        Image bytes
    """
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response['Body'].read()
```

#### streamlit-app/pages/01_Gallery.py

```python
import streamlit as st
import pandas as pd
from modules.iceberg_connector import get_iceberg_table
from modules.s3_utils import get_s3_client, download_image

st.set_page_config(page_title="Gallery", page_icon="🖼️", layout="wide")
st.title("🖼️ Image Gallery")

# Sidebar filters
st.sidebar.header("Filters")

tag_options = ['all', 'product', 'user', 'analytics']
selected_tag = st.sidebar.selectbox("Tag", tag_options)

date_range = st.sidebar.date_input("Upload Date Range", [])

min_size = st.sidebar.number_input("Min Size (KB)", 0, value=0)
max_size = st.sidebar.number_input("Max Size (KB)", 0, value=100000)

# Load metadata
@st.cache_data(ttl=300)
def load_metadata(tag, date_range, min_size, max_size):
    try:
        table = get_iceberg_table("hive_prod.media_db.image_metadata")
        df = table.scan().to_pandas()

        if tag != 'all':
            df = df[df['tag'] == tag]

        if len(date_range) == 2:
            df = df[(df['upload_time'] >= pd.Timestamp(date_range[0])) &
                    (df['upload_time'] <= pd.Timestamp(date_range[1]))]

        df = df[(df['file_size'] >= min_size * 1024) &
                (df['file_size'] <= max_size * 1024)]

        return df
    except Exception as e:
        st.error(f"Failed to load metadata: {e}")
        return pd.DataFrame()

df = load_metadata(selected_tag, date_range, min_size, max_size)

# Statistics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Images", len(df))
with col2:
    total_size_mb = df['file_size'].sum() / 1024 / 1024 if len(df) > 0 else 0
    st.metric("Total Size (MB)", f"{total_size_mb:.2f}")
with col3:
    avg_size_kb = df['file_size'].mean() / 1024 if len(df) > 0 else 0
    st.metric("Avg Size (KB)", f"{avg_size_kb:.2f}")
with col4:
    st.metric("Unique Tags", df['tag'].nunique() if len(df) > 0 else 0)

st.markdown("---")

# Gallery
if len(df) > 0:
    st.subheader("Images")
    cols = st.columns(4)
    s3_client = get_s3_client()

    for idx, (_, row) in enumerate(df.iterrows()):
        col = cols[idx % 4]

        with col:
            try:
                s3_path = row['s3_path'].replace('s3a://', '')
                bucket, key = s3_path.split('/', 1)

                image_bytes = download_image(bucket, key)
                st.image(image_bytes, caption=row['image_id'], use_container_width=True)

                with st.expander("Metadata"):
                    st.json({
                        "ID": row['image_id'],
                        "Size": f"{row['file_size'] / 1024:.2f} KB",
                        "Type": row['mime_type'],
                        "Dimensions": f"{row['width']}x{row['height']}" if 'width' in row else "N/A",
                        "Upload Time": str(row['upload_time']),
                        "Tag": row['tag']
                    })
            except Exception as e:
                st.error(f"Failed to load {row['image_id']}: {e}")
else:
    st.info("No images found matching your filters")

# Data table
with st.expander("View Metadata Table"):
    st.dataframe(df, use_container_width=True)
```

#### streamlit-app/pages/02_Search.py

```python
import streamlit as st
import pandas as pd
from modules.iceberg_connector import get_iceberg_table

st.set_page_config(page_title="Search", page_icon="🔍", layout="wide")
st.title("🔍 Metadata Search")

# Search input
search_field = st.selectbox("Search By", ["image_id", "tag", "source_system"])
search_query = st.text_input("Search Query")

if search_query:
    @st.cache_data(ttl=300)
    def search_metadata(field, query):
        try:
            table = get_iceberg_table("hive_prod.media_db.image_metadata")
            df = table.scan().to_pandas()
            return df[df[field].astype(str).str.contains(query, case=False)]
        except Exception as e:
            st.error(f"Search failed: {e}")
            return pd.DataFrame()

    results = search_metadata(search_field, search_query)

    st.metric("Results Found", len(results))
    st.dataframe(results, use_container_width=True)
else:
    st.info("Enter a search query to begin")
```

#### streamlit-app/pages/03_Statistics.py

```python
import streamlit as st
import pandas as pd
from modules.iceberg_connector import get_iceberg_table
import plotly.express as px

st.set_page_config(page_title="Statistics", page_icon="📊", layout="wide")
st.title("📊 Statistics Dashboard")

@st.cache_data(ttl=300)
def load_stats():
    try:
        table = get_iceberg_table("hive_prod.media_db.image_metadata")
        return table.scan().to_pandas()
    except Exception as e:
        st.error(f"Failed to load statistics: {e}")
        return pd.DataFrame()

df = load_stats()

if len(df) > 0:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Images by Tag")
        tag_counts = df['tag'].value_counts()
        fig = px.bar(tag_counts, title="Count by Tag")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("File Size Distribution")
        fig = px.histogram(df, x='file_size', nbins=20, title="File Size Distribution (bytes)")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Upload Timeline")
    df['upload_date'] = pd.to_datetime(df['upload_time']).dt.date
    timeline = df.groupby('upload_date').size()
    fig = px.line(timeline, title="Images Uploaded Over Time")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data available")
```

---

### 9️⃣ 설정 디렉토리 구조 정리

```bash
# 생성할 디렉토리들
mkdir -p config/prometheus
mkdir -p config/superset
mkdir -p config/grafana/provisioning/{datasources,dashboards}
mkdir -p config/opensearch
mkdir -p streamlit-app/{modules,pages}
mkdir -p logs/{superset,grafana,streamlit,opensearch}
mkdir -p scripts
```

---

### 🔟 자동화 설정 스크립트 (scripts/setup-visualization.sh 신규)

```bash
#!/bin/bash

# ============================================================================
# Visualization Stack Setup Script
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📊 Setting up Lakehouse Visualization Stack..."

# 1. Create directories
echo "📁 Creating directories..."
mkdir -p "$PROJECT_ROOT/config/prometheus"
mkdir -p "$PROJECT_ROOT/config/superset"
mkdir -p "$PROJECT_ROOT/config/grafana/provisioning/{datasources,dashboards}"
mkdir -p "$PROJECT_ROOT/config/opensearch"
mkdir -p "$PROJECT_ROOT/streamlit-app/{modules,pages}"
mkdir -p "$PROJECT_ROOT/logs/{superset,grafana,streamlit,opensearch}"

# 2. Create .env from example if not exists
echo "🔧 Checking environment configuration..."
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "✅ Created .env from template (edit with your values)"
else
    echo "✅ .env already exists"
fi

# 3. Start services
echo "🚀 Starting visualization services..."
cd "$PROJECT_ROOT"
docker-compose up -d superset-db superset-redis superset
docker-compose up -d opensearch opensearch-dashboards grafana prometheus node-exporter
docker-compose up -d streamlit

# 4. Wait for services
echo "⏳ Waiting for services to be healthy..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8088/health > /dev/null 2>&1; then
        echo "✅ Superset ready"
        break
    fi
    echo "⏳ Waiting for Superset... ($((attempt+1))/$max_attempts)"
    sleep 5
    attempt=$((attempt+1))
done

# 5. Print status
echo ""
echo "=========================================="
echo "✅ Visualization Stack Setup Complete!"
echo "=========================================="
echo ""
echo "📊 Service URLs:"
echo "  - Superset:            http://localhost:8088 (admin/admin)"
echo "  - Grafana:             http://localhost:3000 (admin/admin)"
echo "  - OpenSearch Dashboards: http://localhost:5601 (admin/Admin@123)"
echo "  - Streamlit:           http://localhost:8501"
echo "  - Prometheus:          http://localhost:9090"
echo "  - Trino UI:            http://localhost:8080/ui"
echo ""
echo "📝 Next steps:"
echo "  1. Configure Trino data source in Superset"
echo "  2. Create dashboards in Superset"
echo "  3. Add OpenSearch data source to Grafana"
echo "  4. Upload sample images for Streamlit"
echo ""
```

---

## 📝 변경사항 요약표

| 항목 | 파일/디렉토리 | 변경 유형 | 라인 수 | 설명 |
|------|-------------|----------|--------|------|
| **docker-compose.yml** | 루트 | 수정 | +500 | 9개 신규 서비스 추가 |
| **.env.example** | 루트 | 신규 | 30 | 환경 변수 템플릿 |
| **prometheus.yml** | config/prometheus/ | 신규 | 40 | 메트릭 수집 설정 |
| **superset_config.py** | config/superset/ | 신규 | 70 | 캐시, 보안, 로깅 설정 |
| **opensearch.yml** | config/opensearch/ | 신규 | 40 | 클러스터 및 보안 설정 |
| **opensearch_dashboards.yml** | config/opensearch/ | 신규 | 15 | OpenSearch Dashboards 설정 |
| **datasources/*.yml** | config/grafana/provisioning/ | 신규 | 30 | Grafana 데이터 소스 자동 설정 |
| **app.py** | streamlit-app/ | 신규 | 60 | Streamlit 메인 앱 |
| **pages/01_Gallery.py** | streamlit-app/pages/ | 신규 | 100 | 이미지 갤러리 페이지 |
| **pages/02_Search.py** | streamlit-app/pages/ | 신규 | 40 | 메타데이터 검색 페이지 |
| **pages/03_Statistics.py** | streamlit-app/pages/ | 신규 | 50 | 통계 대시보드 페이지 |
| **iceberg_connector.py** | streamlit-app/modules/ | 신규 | 40 | Iceberg 연결 모듈 |
| **s3_utils.py** | streamlit-app/modules/ | 신규 | 60 | S3 유틸리티 모듈 |
| **requirements.txt** | streamlit-app/ | 신규 | 10 | Python 의존성 |
| **setup-visualization.sh** | scripts/ | 신규 | 80 | 자동화 설정 스크립트 |
| **로그 디렉토리** | logs/ | 신규 | - | 4개 서비스 로그 저장소 |
| **TOTAL** | - | - | **~1,120줄** | - |

---

## 🎯 구현 순서

### Phase 1: 설정 파일 생성 (30분)
1. docker-compose.yml 확장
2. .env.example 생성
3. config/ 디렉토리 하위 설정 파일 생성

### Phase 2: 서비스 시작 (15분)
```bash
docker-compose up -d superset-db superset-redis superset
docker-compose up -d opensearch opensearch-dashboards grafana prometheus node-exporter
docker-compose up -d streamlit
```

### Phase 3: Streamlit 애플리케이션 배포 (1시간)
1. streamlit-app/ 디렉토리 생성
2. Python 파일 생성 (app.py, modules/*, pages/*)
3. requirements.txt 설정
4. 컨테이너 재시작

### Phase 4: 데이터 준비 (30분)
1. Iceberg 테이블 생성 (image_metadata)
2. 샘플 이미지 업로드
3. Trino에서 메타데이터 검증

### Phase 5: 대시보드 설정 (2시간)
1. Superset에서 Trino 데이터 소스 연결
2. Superset 대시보드 생성
3. Grafana 데이터 소스 연결
4. Grafana 대시보드 생성

---

## ✅ 배포 전 체크리스트

- [ ] docker-compose.yml 확장 완료
- [ ] .env 파일 설정 완료
- [ ] config/ 하위 설정 파일 생성 완료
- [ ] streamlit-app/ Python 코드 작성 완료
- [ ] 로그 디렉토리 생성 완료
- [ ] Docker 이미지 사용 가능 확인 (offline 환경인 경우)
- [ ] 네트워크 포트 충돌 확인 (8088, 3000, 8501, 9200, 9090 등)
- [ ] 디스크 공간 확인 (최소 20GB)
- [ ] 메모리 여유 확인 (최소 8GB 권장)

---

## 📞 트러블슈팅

### "No space left on device" 오류
```bash
# 디스크 사용량 확인
docker system df

# 불필요한 이미지/컨테이너/볼륨 정리
docker system prune -a --volumes
```

### Superset 컨테이너가 시작되지 않음
```bash
# 로그 확인
docker logs superset

# Redis 연결 확인
docker logs superset-redis

# PostgreSQL 연결 확인
docker logs superset-db
```

### Streamlit에서 Iceberg 연결 실패
```bash
# Hive Metastore 상태 확인
docker logs hive-metastore

# Streamlit 환경 변수 확인
docker exec streamlit-app env | grep HIVE
docker exec streamlit-app env | grep AWS
```

---

이 문서는 **문서화 완료 상태**에서 **실제 구현**으로 전환하는 데 필요한 모든 코드와 설정을 설명합니다.

**다음 단계**:
1. 이 문서의 코드를 실제 파일로 생성
2. docker-compose.yml 수정
3. Docker 컨테이너 시작
4. 각 서비스에 접속하여 설정 완료

