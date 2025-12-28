# Tier 2: 반정형 데이터 시각화 (Grafana + OpenSearch)

## 📋 개요

**대상 데이터**: `hive_prod.logs_db.raw_logs` (JSON meta 컬럼)
**사용 도구**: Grafana + OpenSearch + Prometheus
**주요 기능**: 실시간 로그 모니터링, 시스템 메트릭, 알림
**사용자**: 데이터 엔지니어, DevOps 팀

---

## 🎯 아키텍처

```
┌──────────────────────┐
│   반정형 데이터      │
│ (Semi-Structured)   │
│                      │
│ raw_logs 테이블      │
│ (JSON meta 컬럼)     │
└──────────┬───────────┘
           │
           ├─────────────────┐
           │                 │
           ↓                 ↓
┌──────────────────┐ ┌──────────────────┐
│   OpenSearch     │ │   Prometheus     │
│ (Log Storage)    │ │ (Metrics)        │
│  Port: 9200      │ │  Port: 9090      │
└──────────┬───────┘ └──────────┬───────┘
           │                    │
           │                    │
           └────────┬───────────┘
                    ↓
            ┌──────────────────┐
            │    Grafana       │
            │  (Monitoring)    │
            │  Port: 3000      │
            └────────┬─────────┘
                     │
           👤 Data Engineers
           (Real-time logs, Alerts)
```

---

## 📝 데이터 구조

### Bronze Layer Table

```sql
CREATE TABLE hive_prod.logs_db.raw_logs (
    event_time TIMESTAMP,
    level STRING,              -- INFO, WARN, ERROR
    message STRING,             -- 로그 메시지
    meta STRING,               -- JSON 문자열
    ingest_time TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(event_time))
```

### 샘플 데이터

```json
{
  "event_time": "2025-12-25T10:00:00",
  "level": "INFO",
  "message": "trade executed",
  "meta": "{\"user\": \"trader01\", \"order_id\": \"ord-1001\"}",
  "ingest_time": "2025-12-25T10:00:05"
}
```

### JSON 메타데이터 추출

```sql
SELECT
  event_time,
  level,
  message,
  json_extract_scalar(meta, '$.user') as user,
  json_extract_scalar(meta, '$.order_id') as order_id
FROM hive_prod.logs_db.raw_logs
WHERE level = 'ERROR'
ORDER BY event_time DESC
```

---

## 🚀 구현 단계

### A. OpenSearch 클러스터 구성

```yaml
# docker-compose.yml에 추가
opensearch:
  image: opensearchproject/opensearch:2.11.1
  container_name: opensearch
  environment:
    - cluster.name=lakehouse-logs
    - node.name=opensearch-node1
    - discovery.type=single-node
    - "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m"
    - OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin@123
  ports:
    - "9200:9200"
    - "9600:9600"
  volumes:
    - opensearch-data:/usr/share/opensearch/data
  networks:
    - default
```

### B. Prometheus 설정

`config/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

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

### C. Grafana 설정

```yaml
# docker-compose.yml에 추가
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
    GF_SECURITY_ADMIN_PASSWORD: admin
    GF_INSTALL_PLUGINS: grafana-opensearch-datasource,grafana-clock-panel
  volumes:
    - grafana-data:/var/lib/grafana
  networks:
    - default
```

---

## 📊 대시보드 구성

### 접속 정보

- **URL**: http://localhost:3000
- **초기 계정**: admin / admin

### 대시보드 1: Lakehouse Overview (전체 시스템 상태)

**패널 1: 시스템 CPU 사용률**
```
Data Source: Prometheus
Query: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
Visualization: Graph
Alert: CPU > 80%
```

**패널 2: 디스크 사용량**
```
Data Source: Prometheus
Query: 100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)
Visualization: Gauge
Alert: Disk > 90%
```

**패널 3: 메모리 사용률**
```
Data Source: Prometheus
Query: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100
Visualization: Graph
```

### 대시보드 2: Data Quality (데이터 품질)

**패널 1: 에러 로그 추이**
```
Data Source: OpenSearch
Index: logs-*
Query: level:ERROR
Visualization: Time series
```

**패널 2: 로그 레벨별 분포**
```
Data Source: OpenSearch
Query: level:(INFO OR WARN OR ERROR)
Aggregation: Terms(level)
Visualization: Pie chart
```

**패널 3: 사용자별 거래 추적**
```
Data Source: OpenSearch
Query: meta.user:*
Aggregation: Terms(meta.user)
Visualization: Bar chart
```

### 대시보드 3: Performance (쿼리 성능)

**패널 1: Trino 쿼리 응답시간**
```
Data Source: Prometheus
Query: rate(trino_query_execution_time[5m])
Visualization: Graph
```

**패널 2: 시스템 I/O**
```
Data Source: Prometheus
Query: rate(node_disk_io_time_seconds_total[5m])
Visualization: Graph
```

---

## 🔍 OpenSearch 로그 검색

### 검색 패턴

**OpenSearch Dashboards 접속**: http://localhost:5601

#### 검색 1: 최근 에러 로그

```
{
  "query": {
    "bool": {
      "must": [
        { "match": { "level": "ERROR" } }
      ],
      "filter": [
        { "range": { "event_time": { "gte": "now-1h" } } }
      ]
    }
  }
}
```

#### 검색 2: 특정 사용자의 거래

```
{
  "query": {
    "bool": {
      "must": [
        { "match": { "meta.user": "trader01" } }
      ]
    }
  }
}
```

#### 검색 3: 특정 주문의 로그 추적

```
{
  "query": {
    "match": {
      "meta.order_id": "ord-1001"
    }
  }
}
```

---

## 🚨 알림 규칙 설정

### Alert 1: CPU 사용률 > 80%

1. **Alerting** → **Create Alert Rule**
2. **Data Source**: Prometheus
3. **Query**:
   ```
   100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
   ```
4. **Condition**: `> 80`
5. **For**: 5 minutes
6. **Notification Channel**: Slack / Email

### Alert 2: 디스크 용량 > 90%

1. **Data Source**: Prometheus
2. **Query**:
   ```
   100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)
   ```
3. **Condition**: `> 90`
4. **Notification Channel**: Slack

### Alert 3: 에러 로그 급증

1. **Data Source**: OpenSearch
2. **Query**: `level:ERROR`
3. **Condition**: Count > 50 in 10 minutes
4. **Notification Channel**: Email

---

## 📈 실제 사용 시나리오

### 시나리오: 데이터 엔지니어

```
Grafana 접속 (http://localhost:3000)
  ↓
"Lakehouse Overview" 대시보드 클릭
  ↓
⚠️ CPU 사용률 85% 발견 (빨간 경고)
  ↓
OpenSearch Dashboards로 이동
  ↓
"level:ERROR" 검색 → 최근 100개 에러 로그 확인
  ↓
"2025-12-25T10:30:00 Failed to write to S3" 에러 발견
  ↓
meta.order_id로 원인 추적
  ↓
✅ "SeaweedFS 연결 타임아웃" 문제 파악
  ↓
DevOps 팀에 알림 발송
```

---

## 🔧 로그 수집 파이프라인 (Filebeat)

### 설정 (filebeat.yml)

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /home/iceberg/logs/*.log
      - /var/log/seaweedfs/*.log
      - /opt/hive/logs/*.log

processors:
  - add_kubernetes_metadata:
  - drop_event.when.regexp:
      message: "^DBG"

output.opensearch:
  hosts: ["opensearch:9200"]
  username: "admin"
  password: "Admin@123"
  index: "logs-%{+yyyy.MM.dd}"
```

---

## 📊 OpenSearch 인덱스 템플릿

```json
{
  "index_patterns": ["logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "timestamp": {
          "type": "date"
        },
        "level": {
          "type": "keyword"
        },
        "message": {
          "type": "text"
        },
        "meta": {
          "type": "object",
          "properties": {
            "user": {
              "type": "keyword"
            },
            "order_id": {
              "type": "keyword"
            }
          }
        },
        "service": {
          "type": "keyword"
        }
      }
    }
  }
}
```

---

## ⚙️ 성능 최적화

### 1. 인덱스 로테이션

```bash
# 매일 자정에 새 인덱스 생성
0 0 * * * curl -X POST "opensearch:9200/logs-$(date +\%Y.\%m.\%d)/_doc"
```

### 2. 오래된 인덱스 삭제

```bash
# 30일 이상 된 인덱스 삭제
curl -X DELETE "opensearch:9200/logs-$(date -d '30 days ago' +%Y.%m.%d)"
```

### 3. Prometheus 데이터 보존

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

# 30일 데이터 보존
command:
  - '--storage.tsdb.retention.time=30d'
```

---

## 🔒 보안 설정

### OpenSearch 권한 관리

```bash
# Admin 권한 부여
curl -X PUT "opensearch:9200/_plugins/_security/api/users/analyst" \
  -H "Content-Type: application/json" \
  -u admin:Admin@123 \
  -d '{
    "password": "analyst_password",
    "opendistro_security_roles": ["logstash", "kibana_user"]
  }'
```

### Grafana RBAC

1. **Administration** → **Users**
2. 사용자별 역할 할당:
   - **Admin**: 모든 대시보드 접근
   - **Editor**: 대시보드 수정 가능
   - **Viewer**: 읽기만 가능

---

## 🚨 트러블슈팅

### 문제 1: OpenSearch 연결 실패

**증상**: `Bad Gateway`

**해결**:
```bash
# OpenSearch 헬스 확인
curl -ku admin:Admin@123 https://localhost:9200/_cluster/health

# Grafana에서 "Skip TLS Verify" 활성화
```

### 문제 2: 로그가 수집되지 않음

**원인**: Filebeat 설정 오류

**해결**:
```bash
# Filebeat 로그 확인
docker logs filebeat | grep ERROR

# 경로 권한 확인
ls -la /home/iceberg/logs/
```

---

## 📚 다음 단계

1. ✅ Tier 1 완료: [Superset + Trino](./01-tier1-superset-trino-structured.md)
2. ✅ Tier 2 완료: 현재 문서
3. 👉 [Tier 3: 비정형 데이터 (Streamlit)](./03-tier3-streamlit-unstructured.md)로 이동

---

## ✅ 체크리스트 (20개 항목)

- [ ] OpenSearch 컨테이너 추가
- [ ] OpenSearch Dashboards 컨테이너 추가
- [ ] 초기 admin 비밀번호 설정
- [ ] Single-node 모드 설정
- [ ] 포트 매핑 (9200, 9600)
- [ ] 볼륨 마운트
- [ ] JVM 힙 크기 설정
- [ ] Filebeat 컨테이너 추가
- [ ] 로그 수집 경로 설정
- [ ] 인덱스 템플릿 작성
- [ ] Grafana 컨테이너 추가
- [ ] 초기 admin 비밀번호 설정
- [ ] OpenSearch 플러그인 설치
- [ ] Prometheus 데이터 소스 추가
- [ ] 샘플 대시보드 5개 생성
- [ ] 알림 채널 설정
- [ ] 알림 규칙 3개 생성
- [ ] 대시보드 JSON export
- [ ] Provisioning 디렉토리 구성
- [ ] Git 버전 관리 설정

---

**축하합니다!** 이제 반정형 데이터 시각화 계층이 완성되었습니다. 🎉
