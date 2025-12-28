# ✅ 시각화 스택 개발 체크리스트 (Development Checklist)

> **용도**: 개발 및 배포시 이 파일 하나만 참고하면 됩니다.
> **상태**: 🎯 실행 가능한 모든 항목 포함

---

## 📋 사용 가이드

### 체크리스트 진행 방식
```
[ ]  미완료
[x]  완료
[~]  진행 중
```

### 참고 자료
- **개요**: README.md
- **빠른 참조**: QUICK_REFERENCE.md
- **상세 구현**: 01-tier1.md, 02-tier2.md, 03-tier3.md
- **코드 예시**: VISUALIZATION_STACK_CODE_CHANGES.md

---

## 🎯 Phase 0: 사전 준비 (30분)

### 0.1 환경 확인
- [ ] Docker 설치 확인 (`docker --version`)
- [ ] Docker Compose 설치 확인 (`docker-compose --version`)
- [ ] 최소 8GB 메모리 확인
- [ ] 50GB 디스크 여유 확인
- [ ] 포트 충돌 확인 (8088, 3000, 8501, 9200, 9090 등)

### 0.2 파일 준비
- [ ] 루트 디렉토리 확인: `/home/i/work/ai/lakehouse-tick/`
- [ ] `docker-compose.yml` 백업 생성
- [ ] `config/` 디렉토리 구조 확인

---

## 🏗️ Phase 1: Docker Compose 수정 (1시간)

### 1.0 공통 보완
- [ ] 이미지 태그 고정 (latest-dev 지양)
- [ ] 서비스별 리소스 제한/예약치 설정 (opensearch, trino, superset 등)
- [x] `.env` 변수 사용을 위한 env_file 또는 변수 치환 적용

### 1.1 Superset 스택 추가

#### A. PostgreSQL (Superset 메타스토어)
```yaml
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
```

- [x] `superset-db` 서비스 추가
- [x] 포트 설정 (5432 → 5432)
- [x] 볼륨 생성: `superset-db-data`
- [x] healthcheck 설정

#### B. Redis (캐시)
```yaml
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
```

- [x] `superset-redis` 서비스 추가
- [x] 포트 설정 (6380:6379)
- [x] 볼륨 생성: `superset-redis-data`
- [x] 메모리 제한 설정

#### C. Superset (BI 대시보드)
```yaml
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
  env_file:
    - .env
  environment:
    SUPERSET_SECRET_KEY: ${SUPERSET_SECRET_KEY}
    SQLALCHEMY_DATABASE_URI: postgresql://superset:superset@superset-db:5432/superset
    REDIS_HOST: superset-redis
    REDIS_PORT: 6379
    SUPERSET_ADMIN_USER: ${SUPERSET_ADMIN_USER}
    SUPERSET_ADMIN_PASSWORD: ${SUPERSET_ADMIN_PASSWORD}
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
  command: >
    bash -c "
    pip install --no-cache-dir 'trino[sqlalchemy]' &&
    superset db upgrade &&
    superset fab create-admin --username ${SUPERSET_ADMIN_USER} --firstname Admin --lastname User --email admin@example.com --password ${SUPERSET_ADMIN_PASSWORD} || true &&
    superset init &&
    gunicorn -w 4 -b 0.0.0.0:8088 --timeout 60 superset.app:create_app()
    "
```

- [x] `superset` 서비스 추가
- [x] 포트 설정 (8088:8088)
- [x] 환경변수 설정 (SECRET_KEY, DATABASE_URI, REDIS)
- [x] 볼륨 생성: `superset-data`
- [x] `superset_config.py` 마운트 경로 확인
- [~] Trino SQLAlchemy 드라이버 설치 확인 (개발: command, 운영: 커스텀 이미지 권장)
- [x] healthcheck 설정
- [x] 초기 admin 계정 자동 생성 command 설정

### 1.2 Grafana + OpenSearch 스택 추가

#### A. OpenSearch (로그 저장소)
```yaml
opensearch:
  image: opensearchproject/opensearch:2.11.1
  container_name: opensearch
  environment:
    - cluster.name=lakehouse-logs
    - node.name=opensearch-node1
    - discovery.type=single-node
    - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
    - OPENSEARCH_INITIAL_ADMIN_PASSWORD=${OPENSEARCH_PASSWORD}
  ports:
    - "9200:9200"
    - "9600:9600"
  volumes:
    - opensearch-data:/usr/share/opensearch/data
    - ./config/opensearch/opensearch.yml:/usr/share/opensearch/config/opensearch.yml:ro
  networks:
    - lakehouse-net
  healthcheck:
    test: ["CMD", "curl", "-ku", "admin:${OPENSEARCH_PASSWORD}", "https://localhost:9200/_cluster/health"]
    interval: 30s
    timeout: 10s
    retries: 5
    start_period: 60s
```

- [x] `opensearch` 서비스 추가
- [x] 포트 설정 (9200, 9600)
- [x] 환경변수 설정 (admin 비밀번호)
- [x] 볼륨 생성: `opensearch-data`
- [x] `opensearch.yml` 마운트 경로 확인
- [x] healthcheck 설정
- [x] JVM 메모리 설정

#### B. OpenSearch Dashboards (로그 UI)
```yaml
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
    OPENSEARCH_PASSWORD: ${OPENSEARCH_PASSWORD}
    OPENSEARCH_SSL_VERIFICATIONMODE: none
  networks:
    - lakehouse-net
```

- [x] `opensearch-dashboards` 서비스 추가
- [x] 포트 설정 (5601:5601)
- [x] 환경변수 설정
- [x] SSL 검증 설정 확인 (self-signed 환경)

#### C. Prometheus (메트릭 수집)
```yaml
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
```

- [x] `prometheus` 서비스 추가
- [x] 포트 설정 (9090:9090)
- [x] 설정 파일 마운트 확인
- [ ] Trino 메트릭 노출(JMX/Exporter) 설정 확인
- [x] 볼륨 생성: `prometheus-data`
- [x] healthcheck 설정

#### D. Node Exporter (시스템 메트릭)
```yaml
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
```

- [x] `node-exporter` 서비스 추가
- [x] 포트 설정 (9100:9100)
- [x] 볼륨 마운트 설정

#### E. Grafana (모니터링 대시보드)
```yaml
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
  env_file:
    - .env
  environment:
    GF_SECURITY_ADMIN_USER: admin
    GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    GF_INSTALL_PLUGINS: grafana-opensearch-datasource,grafana-clock-panel
    GF_AUTH_ANONYMOUS_ENABLED: "false"
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
```

- [x] `grafana` 서비스 추가
- [x] 포트 설정 (3000:3000)
- [x] 환경변수 설정 (admin 계정)
- [~] OPENSEARCH_PASSWORD 환경변수 전달 확인 (provisioning에서 사용)
- [x] 플러그인 설치 설정
- [x] 프로비저닝 볼륨 마운트
- [x] 볼륨 생성: `grafana-data`
- [x] healthcheck 설정

#### F. 로그 수집 에이전트 (선택)
- [ ] Fluent Bit 또는 Vector 추가 (Docker 로그/파일 로그를 OpenSearch로 전송)
- [ ] 인덱스 패턴/보존 정책 정의 (예: `logs-*`)

### 1.3 Streamlit 추가

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
    AWS_REGION: us-east-1
    HIVE_METASTORE_URI: thrift://hive-metastore:9083
    STREAMLIT_SERVER_PORT: 8501
    STREAMLIT_SERVER_HEADLESS: "true"
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
```

- [x] `streamlit` 서비스 추가
- [x] 포트 설정 (8501:8501)
- [x] 환경변수 설정 (S3, Hive, Streamlit)
- [x] 볼륨 설정 (app 코드, 로그)
- [x] healthcheck 설정
- [ ] (권장) Dockerfile로 의존성 고정/빌드하여 재시작 시 재설치 방지

### 1.4 Volumes 추가

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

- [x] `superset-data` 추가
- [x] `superset-db-data` 추가
- [x] `superset-redis-data` 추가
- [x] `grafana-data` 추가
- [x] `opensearch-data` 추가
- [x] `prometheus-data` 추가

---

## ⚙️ Phase 2: 설정 파일 생성 (1시간)

### 2.1 디렉토리 생성
- [x] `mkdir -p config/prometheus`
- [x] `mkdir -p config/superset`
- [x] `mkdir -p config/grafana/provisioning/datasources`
- [x] `mkdir -p config/grafana/provisioning/dashboards`
- [x] `mkdir -p config/opensearch`
- [x] `mkdir -p streamlit-app/modules`
- [x] `mkdir -p streamlit-app/pages`
- [x] `mkdir -p logs/{superset,grafana,streamlit,opensearch}`

### 2.2 Prometheus 설정 (config/prometheus/prometheus.yml)

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
```

- [x] `config/prometheus/prometheus.yml` 생성
- [x] Prometheus 전역 설정 확인
- [x] scrape_configs 확인

### 2.3 Superset 설정 (config/superset/superset_config.py)

```python
import os
from datetime import timedelta

# Database
SQLALCHEMY_DATABASE_URI = 'postgresql://superset:superset@superset-db:5432/superset'

# Cache
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_REDIS_HOST': 'superset-redis',
    'CACHE_REDIS_PORT': 6379,
}

# Security
SECRET_KEY = os.getenv('SUPERSET_SECRET_KEY', 'change-me-in-production')
SUPERSET_WEBSERVER_TIMEOUT = 60
ROW_LIMIT = 10000

# Features
SUPERSET_FEATURE_FLAGS = {
    'ALLOW_USER_PROFILE_EDIT': True,
    'ENABLE_FORMULA_EDITING': True,
}
```

- [x] `config/superset/superset_config.py` 생성
- [x] 데이터베이스 URI 확인
- [x] Redis 캐시 설정 확인
- [x] SECRET_KEY 설정 확인

### 2.4 OpenSearch 설정 (config/opensearch/opensearch.yml)

```yaml
cluster.name: lakehouse-logs
node.name: opensearch-node1
discovery.type: single-node
network.host: 0.0.0.0
http.port: 9200
```

- [x] `config/opensearch/opensearch.yml` 생성
- [x] 클러스터 이름 설정
- [x] 네트워크 설정 확인

### 2.5 Grafana 데이터 소스 (config/grafana/provisioning/datasources/opensearch.yml)

```yaml
apiVersion: 1

datasources:
  - name: OpenSearch
    type: grafana-opensearch-datasource
    access: proxy
    url: https://opensearch:9200
    basicAuth: true
    basicAuthUser: admin
    basicAuthPassword: ${OPENSEARCH_PASSWORD}
    isDefault: false
    jsonData:
      tlsSkipVerify: true
```

- [x] `config/grafana/provisioning/datasources/opensearch.yml` 생성
- [x] OpenSearch URL 설정
- [x] 인증 설정

### 2.6 Grafana 데이터 소스 (prometheus.yml)

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

- [x] `config/grafana/provisioning/datasources/prometheus.yml` 생성
- [x] Prometheus URL 설정

### 2.7 환경 설정 (.env 파일)

```bash
SUPERSET_SECRET_KEY=your-super-secret-key
SUPERSET_ADMIN_USER=admin
SUPERSET_ADMIN_PASSWORD=admin
GRAFANA_PASSWORD=admin
OPENSEARCH_PASSWORD=Admin@123
```

- [x] `.env` 파일 생성
- [x] 환경변수 설정
- [ ] 개발 환경: 기본값 유지 가능, 운영 전에는 반드시 변경

---

## 🐍 Phase 3: Streamlit 애플리케이션 생성 (2시간)

### 3.1 requirements.txt

```
streamlit==1.30.0
pyiceberg[hive]==0.5.1
pandas==2.1.4
boto3==1.34.0
Pillow==10.1.0
pyarrow==14.0.0
plotly==5.17.0
```

- [x] `streamlit-app/requirements.txt` 생성

### 3.2 app.py (메인)

```python
import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from modules.iceberg_connector import get_iceberg_table
from modules.s3_utils import get_s3_client

st.set_page_config(
    page_title="Unstructured Data Explorer",
    page_icon="🖼️",
    layout="wide"
)

st.title("🖼️ Lakehouse Unstructured Data Explorer")

# Status checks
st.sidebar.header("System Status")
try:
    table = get_iceberg_table("media_db.image_metadata")
    st.sidebar.success("✅ Iceberg connected")
except Exception as e:
    st.sidebar.error(f"❌ Iceberg error: {e}")
```

- [x] `streamlit-app/app.py` 생성
- [x] 기본 레이아웃 설정
- [x] 상태 확인 구현

### 3.3 modules/iceberg_connector.py

```python
import os
from pyiceberg.catalog import load_catalog

def get_iceberg_table(table_name: str):
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

- [x] `streamlit-app/modules/iceberg_connector.py` 생성
- [x] Iceberg 카탈로그 연결 함수 구현

### 3.4 modules/s3_utils.py

```python
import boto3
import os

def get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=os.getenv('AWS_ENDPOINT_URL_S3', 'http://seaweedfs-s3:8333'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'seaweedfs_access_key'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'seaweedfs_secret_key'),
        region_name=os.getenv('AWS_REGION', 'us-east-1'),
        verify=False
    )

def parse_s3_path(s3_path: str):
    if s3_path.startswith("s3a://"):
        s3_path = s3_path[len("s3a://"):]
    elif s3_path.startswith("s3://"):
        s3_path = s3_path[len("s3://"):]
    else:
        raise ValueError(f"Unsupported S3 path: {s3_path}")
    bucket, _, key = s3_path.partition("/")
    if not bucket or not key:
        raise ValueError(f"Incomplete S3 path: {s3_path}")
    return bucket, key

def fetch_object_bytes(s3_path: str):
    bucket, key = parse_s3_path(s3_path)
    client = get_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
```

- [x] `streamlit-app/modules/s3_utils.py` 생성
- [x] S3 클라이언트 함수 구현

### 3.5 pages/01_Gallery.py

```python
import streamlit as st
import pandas as pd
from modules.iceberg_connector import get_iceberg_table
from modules.s3_utils import fetch_object_bytes

st.set_page_config(page_title="Gallery", page_icon="🖼️", layout="wide")
st.title("🖼️ Image Gallery")

# Sidebar filters
st.sidebar.header("Filters")
tag_options = ['all', 'product', 'user', 'analytics']
selected_tag = st.sidebar.selectbox("Tag", tag_options)

@st.cache_data(ttl=300)
def load_metadata(tag):
    table = get_iceberg_table("media_db.image_metadata")
    df = table.scan().to_pandas()
    if tag != 'all':
        df = df[df['tag'] == tag]
    return df

df = load_metadata(selected_tag)

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

- [x] `streamlit-app/pages/01_Gallery.py` 생성
- [x] 갤러리 필터링 구현
- [x] 메타데이터 로드 구현
- [x] S3 이미지 렌더링 구현

### 3.6 pages/02_Search.py

```python
import streamlit as st
import pandas as pd
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
```

- [x] `streamlit-app/pages/02_Search.py` 생성
- [x] 검색 기능 구현

### 3.7 pages/03_Statistics.py

```python
import streamlit as st
import pandas as pd
from modules.iceberg_connector import get_iceberg_table
import plotly.express as px

st.set_page_config(page_title="Statistics", page_icon="📊", layout="wide")
st.title("📊 Statistics Dashboard")

@st.cache_data(ttl=300)
def load_stats():
    table = get_iceberg_table("media_db.image_metadata")
    return table.scan().to_pandas()

df = load_stats()
if len(df) > 0:
    tag_counts = df['tag'].value_counts()
    fig = px.bar(tag_counts, title="Count by Tag")
    st.plotly_chart(fig, use_container_width=True)
```

- [x] `streamlit-app/pages/03_Statistics.py` 생성
- [x] 통계 시각화 구현
- [ ] 대용량 대비: 필요한 컬럼/필터만 읽고 limit/pagination 적용

### 3.8 modules/__init__.py

- [x] `streamlit-app/modules/__init__.py` 생성 (빈 파일)

---

## 🚀 Phase 4: 서비스 시작 (30분)

### 4.1 Docker Compose 검증
- [ ] `docker-compose config` 실행 (오류 확인)
- [ ] 기존 컨테이너 상태 확인: `docker ps -a`
- [ ] 기존 이미지 확인: `docker images`

### 4.2 이미지 다운로드
- [ ] `docker-compose pull` 실행 (모든 이미지 다운로드)

### 4.3 서비스 시작 (순차적)

#### Step 1: 기본 인프라 (이미 실행 중인지 확인)
- [ ] Seaweedfs 클러스터 확인: `docker logs seaweedfs-s3 | tail -5`
- [ ] Hive Metastore 확인: `docker logs hive-metastore | tail -5`
- [ ] Trino 확인: `docker logs trino | tail -5`

#### Step 2: Superset 스택 시작
```bash
docker-compose up -d superset-db superset-redis superset
```
- [ ] Superset-db 시작 대기 (healthcheck 확인)
- [ ] Superset-redis 시작 대기
- [ ] Superset 시작 (초기화 스크립트 실행)
- [ ] 로그 확인: `docker logs superset | grep -E "initialize|listening"`
- [ ] 접속 확인: http://localhost:8088 (admin/admin)

#### Step 3: OpenSearch + Grafana 스택 시작
```bash
docker-compose up -d opensearch opensearch-dashboards prometheus node-exporter grafana
```
- [ ] OpenSearch 시작 대기 (healthcheck 확인)
- [ ] OpenSearch Dashboards 시작 대기
- [ ] Prometheus 시작 대기
- [ ] Node Exporter 시작 대기
- [ ] Grafana 시작 대기
- [ ] 접속 확인: http://localhost:3000 (admin/admin)
- [ ] OpenSearch 접속: http://localhost:5601 (admin/${OPENSEARCH_PASSWORD}, 기본값: Admin@123)

#### Step 4: Streamlit 시작
```bash
docker-compose up -d streamlit
```
- [ ] Streamlit 시작 (pip install 대기)
- [ ] 로그 확인: `docker logs streamlit-app | grep -E "Streamlit|Listening"`
- [ ] 접속 확인: http://localhost:8501

### 4.4 모든 서비스 상태 확인
```bash
docker-compose ps
```
- [ ] 모든 컨테이너가 `Up (healthy)` 상태
- [ ] 포트 매핑 확인
- [ ] healthcheck 통과 확인

---

## 📊 Phase 5: 데이터 준비 (2시간)

### 5.0 시각화 대상 데이터셋 정합성
- [ ] Superset 예시(`option_ticks_db`)와 Streamlit 예시(`media_db`) 중 실제 목표 데이터셋으로 통일
- [ ] 스키마/샘플 데이터가 대시보드와 앱에서 동일하게 조회되는지 확인

### 5.1 Iceberg 메타데이터 테이블 생성

```sql
CREATE SCHEMA IF NOT EXISTS media_db;

CREATE TABLE IF NOT EXISTS media_db.image_metadata (
    image_id STRING,
    s3_path STRING,
    file_size BIGINT,
    mime_type STRING,
    upload_time TIMESTAMP,
    source_system STRING,
    tag STRING,
    width INT,
    height INT,
    checksum STRING,
    created_at TIMESTAMP
)
WITH (
    format = 'PARQUET',
    partitioning = ARRAY['day(upload_time)', 'tag']
);
```

- [ ] Trino CLI 접속: `docker exec -it trino trino --server localhost:8080`
- [ ] 스키마 생성
- [ ] 테이블 생성
- [ ] 테이블 확인: `SHOW TABLES FROM media_db;`

### 5.2 샘플 데이터 준비

```bash
# Python 스크립트로 샘플 이미지 생성 및 S3 업로드
# (fspark_raw_examples.py:92-121 참고)
python python/fspark_raw_examples.py
```

- [ ] 샘플 이미지 5개 S3에 업로드
- [ ] S3 경로 확인: `s3a://lakehouse/raw/images/{date}/`

### 5.3 메타데이터 INSERT

```sql
INSERT INTO media_db.image_metadata VALUES
('img-001', 's3a://lakehouse/raw/images/2025-12-25/image1.png', 102400, 'image/png', TIMESTAMP '2025-12-25 10:00:00', 'manual', 'product', 800, 600, 'abc123', TIMESTAMP '2025-12-25 10:00:00');
```

- [ ] 메타데이터 INSERT 실행
- [ ] 데이터 확인: `SELECT COUNT(*) FROM media_db.image_metadata;`

---

## ⚙️ Phase 6: Superset 설정 (1시간)

### 6.1 Trino 데이터 소스 추가
1. [ ] http://localhost:8088 접속 (admin/admin)
2. [ ] **Settings** → **Database Connections** → **+ Database**
3. [ ] **Trino** 선택
4. [ ] Connection URI: `trino://user@trino:8080/hive_prod`
5. [ ] **Test Connection** 클릭
6. [ ] **Connect** 클릭

### 6.2 데이터셋 생성
1. [ ] **Data** → **Datasets** → **+ Dataset**
2. [ ] Database: **Trino** 선택
3. [ ] Schema: **option_ticks_db** 선택
4. [ ] Table: **bronze_option_ticks** 선택
5. [ ] **Create Dataset and Create Chart** 클릭

### 6.3 차트 생성: Line Chart (시간별 가격 변화)
```sql
SELECT timestamp, symbol, last_price
FROM hive_prod.option_ticks_db.bronze_option_ticks
WHERE timestamp >= CURRENT_DATE - INTERVAL '7' DAY
ORDER BY timestamp
```
- [ ] SQL 입력
- [ ] Chart Type: **Time-series Line Chart** 선택
- [ ] X-Axis: **timestamp**
- [ ] Metrics: **AVG(last_price)**
- [ ] Group by: **symbol**
- [ ] **Save** 클릭

### 6.4 차트 생성: Bar Chart (거래량)
```sql
SELECT symbol, SUM(volume) as total_volume
FROM hive_prod.option_ticks_db.bronze_option_ticks
WHERE timestamp >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY symbol
ORDER BY total_volume DESC
```
- [ ] SQL 입력
- [ ] Chart Type: **Bar Chart** 선택
- [ ] X-Axis: **symbol**
- [ ] Metrics: **SUM(volume)**
- [ ] **Save** 클릭

### 6.5 대시보드 생성
1. [ ] **Dashboards** → **+ Dashboard**
2. [ ] Title: **"Lakehouse Analytics"**
3. [ ] 생성한 차트 2개 추가
4. [ ] 필터 추가: Date Range, Symbol
5. [ ] **Save** 클릭

---

## 📈 Phase 7: Grafana 설정 (1시간)

### 7.1 데이터 소스 확인
1. [ ] http://localhost:3000 접속 (admin/admin)
2. [ ] **Configuration** (⚙️) → **Data Sources**
3. [ ] **OpenSearch** 데이터 소스 확인 (자동 프로비저닝)
4. [ ] **Prometheus** 데이터 소스 확인 (자동 프로비저닝)
5. [ ] OpenSearch 인덱스/데이터 유입 확인 (로그 수집 에이전트 동작)

### 7.2 샘플 대시보드 생성
1. [ ] **Dashboards** → **+ New Dashboard**
2. [ ] **+ Add a new panel** 클릭
3. [ ] **Panel Title**: "System CPU Usage"
4. [ ] Data Source: **Prometheus** 선택
5. [ ] Query: `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
6. [ ] **Save** 클릭

### 7.3 알림 규칙 설정 (선택사항)
1. [ ] **Alerting** → **Alert Rules** → **Create Alert Rule**
2. [ ] Condition 설정
3. [ ] Notification Channel 설정
4. [ ] **Save** 클릭

---

## 🖼️ Phase 8: Streamlit 테스트 (30분)

### 8.1 앱 접속
- [ ] http://localhost:8501 접속
- [ ] 페이지 로드 확인

### 8.2 시스템 상태 확인 (사이드바)
- [ ] ✅ Iceberg connected
- [ ] ✅ S3 connected

### 8.3 기능 테스트
1. [ ] **Gallery** 페이지 방문
   - [ ] 이미지 로드 확인
   - [ ] 태그 필터 작동 확인
   - [ ] 날짜 범위 필터 작동 확인

2. [ ] **Search** 페이지 방문
   - [ ] 검색 기능 작동 확인
   - [ ] 결과 반환 확인

3. [ ] **Statistics** 페이지 방문
   - [ ] 그래프 렌더링 확인
   - [ ] 통계 계산 확인

---

## ✨ Phase 9: 성능 검증 (1시간)

### 9.1 Superset 성능
- [ ] 대시보드 로딩 시간 측정 (목표: < 5초)
- [ ] 차트 렌더링 시간 측정 (목표: < 3초)
- [ ] SQL Lab 쿼리 실행 시간 (목표: < 30초)

### 9.2 Grafana 성능
- [ ] 대시보드 로딩 시간 측정 (목표: < 5초)
- [ ] 실시간 메트릭 업데이트 확인

### 9.3 Streamlit 성능
- [ ] 앱 로딩 시간 측정 (목표: < 3초)
- [ ] 갤러리 렌더링 시간 (목표: < 3초)
- [ ] 검색 응답 시간 (목표: < 5초)

### 9.4 리소스 사용률
```bash
docker stats
```
- [ ] CPU 사용률 확인
- [ ] 메모리 사용률 확인
- [ ] 네트워크 I/O 확인

---

## 🔒 Phase 10: 보안 및 운영 (1시간)

### 10.1 비밀번호 변경
- [ ] 운영 전 Superset admin 비밀번호 변경 (개발 환경은 기본값 유지 가능)
- [ ] 운영 전 OpenSearch admin 비밀번호 변경 (개발 환경은 기본값 유지 가능)
- [ ] 운영 전 Grafana admin 비밀번호 변경 (개발 환경은 기본값 유지 가능)

### 10.2 로깅 확인
```bash
docker logs <container-name> | grep ERROR
```
- [ ] Superset 로그 확인
- [ ] Grafana 로그 확인
- [ ] OpenSearch 로그 확인
- [ ] Streamlit 로그 확인

### 10.3 백업 설정
- [ ] Superset 메타스토어 백업 스크립트 작성
- [ ] Grafana 설정 백업 스크립트 작성

### 10.4 모니터링 설정
- [ ] Prometheus 메트릭 수집 확인
- [ ] Grafana 대시보드 모니터링 확인

---

## 📊 최종 검증 체크리스트

### 모든 서비스 정상 작동
- [ ] Superset: http://localhost:8088 ✅
- [ ] Grafana: http://localhost:3000 ✅
- [ ] OpenSearch Dashboards: http://localhost:5601 ✅
- [ ] Streamlit: http://localhost:8501 ✅
- [ ] Prometheus: http://localhost:9090 ✅
- [ ] Trino UI: http://localhost:8080/ui ✅

### 데이터 조회 가능
- [ ] Superset에서 Trino 데이터 조회 가능
- [ ] Grafana에서 OpenSearch 로그 조회 가능
- [ ] Streamlit에서 이미지 로드 가능

### 성능 기준 충족
- [ ] Superset 대시보드: < 5초
- [ ] Streamlit 앱: < 3초
- [ ] Grafana 대시보드: < 5초

---

## 🎯 운영 가이드

### 일일 점검
```bash
# 모든 서비스 상태 확인
docker-compose ps

# 에러 로그 확인
docker-compose logs --tail=50 | grep ERROR
```

### 주간 점검
- [ ] 백업 실행
- [ ] 성능 메트릭 검토
- [ ] 디스크 사용량 확인

### 월간 점검
- [ ] Iceberg 테이블 최적화
- [ ] OpenSearch 인덱스 정리
- [ ] Prometheus 데이터 정리

---

## 📞 문제 해결

### Superset이 시작되지 않음
```bash
# 로그 확인
docker logs superset

# PostgreSQL 확인
docker logs superset-db

# Redis 확인
docker logs superset-redis
```

### Streamlit 에러
```bash
# 로그 확인
docker logs streamlit-app

# Iceberg 연결 테스트
docker exec streamlit-app python -c "
from modules.iceberg_connector import get_iceberg_table
table = get_iceberg_table('hive_prod.media_db.image_metadata')
print(f'Tables: {len(table.scan().to_pandas())}')
"
```

### Grafana 데이터 소스 연결 실패
```bash
# OpenSearch 확인
# .env 사용 시 먼저 export 필요: export OPENSEARCH_PASSWORD=Admin@123
curl -ku admin:${OPENSEARCH_PASSWORD} https://localhost:9200/_cluster/health

# Prometheus 확인
curl http://localhost:9090/-/healthy
```

---

## 📊 최종 접근 가능 도구 요약

배포 완료 후 다음 도구들에 접근 가능합니다:

| # | 도구 | URL | 로그인 | 목적 | 포트 | 상태 |
|---|------|-----|--------|------|------|------|
| **1** | 📊 **Superset** | http://localhost:8088 | admin/admin | BI 대시보드 (정형 데이터) | 8088 | 🚀 Phase 6 후 |
| **2** | 📈 **Grafana** | http://localhost:3000 | admin/admin | 실시간 모니터링 | 3000 | 🚀 Phase 7 후 |
| **3** | 🖼️ **Streamlit** | http://localhost:8501 | (없음) | 이미지 갤러리 (비정형 데이터) | 8501 | 🚀 Phase 8 후 |
| **4** | 📝 **OpenSearch Dashboards** | http://localhost:5601 | admin/Admin@123 | 로그 탐색 및 분석 | 5601 | 🚀 Phase 4 후 |
| **5** | 🔥 **Prometheus** | http://localhost:9090 | (없음) | 메트릭 수집 및 쿼리 | 9090 | 🚀 Phase 4 후 |
| **6** | 🔧 **Trino UI** | http://localhost:8080 | (없음) | 쿼리 모니터링 (기존) | 8080 | 🚀 기존 서비스 |

---

## 📋 빠른 참고표

### 각 Tier별 목적과 구성

| Tier | 이름 | 데이터 유형 | 주 도구 | 보조 도구 | 사용 사례 |
|------|------|-----------|--------|---------|---------|
| **Tier 1** | BI 대시보드 | 정형 (Structured) | Superset | Trino, PostgreSQL, Redis | 매출 분석, KPI 추적, 경영 대시보드 |
| **Tier 2** | 실시간 모니터링 | 반정형 (Semi-structured) | Grafana | OpenSearch, Prometheus | 시스템 모니터링, 로그 분석, 알림 |
| **Tier 3** | 이미지 갤러리 | 비정형 (Unstructured) | Streamlit | PyIceberg, boto3, S3 | 이미지 탐색, 메타데이터 검색, 통계 |

---

## 🚀 배포 단계별 도구 활성화 일정

```
Phase 0-3: 준비 (아무것도 실행 안 됨)
    ↓
Phase 4: 서비스 시작 ✅
    └─ 모든 서비스 실행 시작
    └─ Prometheus, OpenSearch 활성화

Phase 5: 데이터 준비 ✅
    └─ Iceberg 테이블 생성
    └─ 샘플 데이터 준비

Phase 6: Superset 설정 ✅
    └─ Superset (http://localhost:8088) 사용 가능
    └─ Trino 데이터 소스 연결
    └─ BI 대시보드 생성

Phase 7: Grafana 설정 ✅
    └─ Grafana (http://localhost:3000) 사용 가능
    └─ OpenSearch Dashboards (http://localhost:5601) 사용 가능
    └─ 모니터링 대시보드 생성

Phase 8: Streamlit 테스트 ✅
    └─ Streamlit (http://localhost:8501) 사용 가능
    └─ 이미지 갤러리 테스트
    └─ 메타데이터 검색 기능 테스트

Phase 9: 성능 검증 ✅
    └─ 모든 도구 성능 벤치마크
    └─ 응답 시간 측정

Phase 10: 보안 및 운영 ✅
    └─ 비밀번호 강화
    └─ 백업 자동화
    └─ 로깅 구성
```

---

## 🎯 도구별 주요 작업

### 1️⃣ Superset (BI 대시보드)

**용도**: 정형 데이터 시각화 및 BI 분석

**Phase 6에서 설정**:
- [ ] Trino 데이터 소스 추가
- [ ] `option_ticks_db.bronze_option_ticks` 데이터셋 생성
- [ ] 시계열 차트 (가격 추이)
- [ ] 막대 차트 (거래량)
- [ ] 대시보드 통합

**접근 주소**: http://localhost:8088
**기본 계정**: admin/admin

---

### 2️⃣ Grafana (실시간 모니터링)

**용도**: 시스템 모니터링 및 알림

**Phase 7에서 설정**:
- [ ] Prometheus 데이터 소스 연결
- [ ] OpenSearch 데이터 소스 연결
- [ ] CPU 사용률 그래프
- [ ] 메모리 사용률 그래프
- [ ] 디스크 공간 게이지
- [ ] 알림 규칙 설정

**접근 주소**: http://localhost:3000
**기본 계정**: admin/admin

---

### 3️⃣ Streamlit (이미지 갤러리)

**용도**: 비정형 데이터 (이미지) 탐색 및 분석

**Phase 8에서 테스트**:
- [ ] 갤러리 페이지 - 이미지 4열 그리드
- [ ] 검색 페이지 - 메타데이터 검색
- [ ] 통계 페이지 - 태그별 카운트, 크기 분포
- [ ] 필터 기능 - 태그, 날짜, 크기로 필터링

**접근 주소**: http://localhost:8501
**인증**: 없음 (공개)

---

### 4️⃣ OpenSearch Dashboards (로그 분석)

**용도**: 시스템 로그 탐색 및 분석

**Phase 4에서 활성화**:
- [ ] 인덱스 생성 (`logs-*` 패턴)
- [ ] 로그 스트림 확인
- [ ] Discover에서 로그 검색
- [ ] 대시보드 생성 (선택)

**접근 주소**: http://localhost:5601
**기본 계정**: admin/Admin@123

---

### 5️⃣ Prometheus (메트릭 수집)

**용도**: 시스템 메트릭 수집 및 쿼리

**Phase 4에서 활성화**:
- [ ] Node Exporter 메트릭 수집
- [ ] Prometheus UI에서 쿼리 실행
- [ ] Grafana에서 시각화

**접근 주소**: http://localhost:9090
**인증**: 없음 (공개)

---

## ✅ 완료!

모든 단계를 완료하면 Lakehouse 시각화 스택이 완성됩니다! 🎉

**축하합니다!** 🎊 이제 다음을 사용할 수 있습니다:
- ✅ Superset으로 데이터 분석
- ✅ Grafana로 시스템 모니터링
- ✅ Streamlit으로 이미지 탐색
- ✅ OpenSearch로 로그 분석
- ✅ Prometheus로 메트릭 추적

더 자세한 정보는 [docs/feature/visualization/README.md](../README.md) 참고
