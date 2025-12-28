# Tier 1: 정형 데이터 시각화 (Superset + Trino)

## 📊 개요

**대상 데이터**: `hive_prod.option_ticks_db.bronze_option_ticks`
**사용 도구**: Apache Superset + Trino
**주요 기능**: BI 대시보드, 차트, SQL Lab
**사용자**: 마케팅 팀장, 비즈니스 분석가

---

## 🎯 아키텍처

```
┌──────────────────┐
│   정형 데이터     │
│  (Structured)    │
│                  │
│ option_ticks_db. │
│ bronze_option... │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│     Trino        │
│ (Query Engine)   │
│  Port: 8080      │
└────────┬─────────┘
         │
         ↓
┌──────────────────┐
│    Superset      │
│  (BI Dashboard)  │
│  Port: 8088      │
└────────┬─────────┘
         │
         ↓
   👤 Business Users
   (Line Charts, Dashboards)
```

---

## 📝 데이터 구조

### Bronze Layer Table

```sql
CREATE TABLE hive_prod.option_ticks_db.bronze_option_ticks (
    timestamp TIMESTAMP,
    symbol STRING,
    bid_price DOUBLE,
    bid_size INT,
    ask_price DOUBLE,
    ask_size INT,
    last_price DOUBLE,
    volume LONG,
    ingest_time TIMESTAMP
)
USING iceberg
PARTITIONED BY (days(timestamp))
```

### 샘플 데이터

| timestamp | symbol | bid_price | ask_price | last_price | volume |
|-----------|--------|-----------|-----------|------------|--------|
| 2025-12-25 14:00:00 | ESZ25C5000 | 108.0 | 108.5 | 108.3 | 2000 |
| 2025-12-25 14:01:00 | ESZ25C5000 | 108.2 | 108.7 | 108.5 | 1500 |

---

## 🚀 구현 단계 (6.1 Superset 체크리스트에서)

### A. Docker 환경 구성 (7개 항목)

```yaml
# docker-compose.yml에 추가
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
    SUPERSET_SECRET_KEY: "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY"
    SQLALCHEMY_DATABASE_URI: postgresql://superset:superset@superset-db:5432/superset
    REDIS_HOST: superset-redis
    REDIS_PORT: 6379
  volumes:
    - superset-data:/app/superset_home
  networks:
    - default
```

### B. 초기 설정

```bash
# 1. Admin 사용자 생성
docker exec -it superset superset fab create-admin \
  --username admin \
  --firstname Admin \
  --lastname User \
  --email admin@example.com \
  --password admin

# 2. 데이터베이스 마이그레이션
docker exec -it superset superset db upgrade

# 3. Superset 초기화
docker exec -it superset superset init
```

### C. Trino 데이터 소스 연결

**접속 URL**: http://localhost:8088
**초기 계정**: admin / admin

1. **Settings** → **Database Connections** → **+ Database**
2. **Trino** 선택
3. Connection URI 입력:
   ```
   trino://user@trino:8080/hive_prod
   ```
4. **Test Connection** → **Connect**

### D. 대시보드 구성

#### 차트 1: Line Chart (시간별 가격 변화)

```sql
SELECT
  timestamp,
  symbol,
  last_price
FROM hive_prod.option_ticks_db.bronze_option_ticks
WHERE timestamp >= CURRENT_DATE - INTERVAL '7' DAY
ORDER BY timestamp DESC
```

**Superset 설정**:
- Chart Type: `Time-series Line Chart`
- X-Axis: `timestamp`
- Metrics: `AVG(last_price)`
- Group by: `symbol`

#### 차트 2: Bar Chart (심볼별 거래량)

```sql
SELECT
  symbol,
  SUM(volume) as total_volume
FROM hive_prod.option_ticks_db.bronze_option_ticks
WHERE timestamp >= CURRENT_DATE - INTERVAL '7' DAY
GROUP BY symbol
ORDER BY total_volume DESC
```

**Superset 설정**:
- Chart Type: `Bar Chart`
- X-Axis: `symbol`
- Metrics: `SUM(volume)`

#### 차트 3: Pivot Table (일별 통계)

```sql
SELECT
  DATE(timestamp) as date,
  symbol,
  AVG(last_price) as avg_price,
  SUM(volume) as total_volume
FROM hive_prod.option_ticks_db.bronze_option_ticks
WHERE timestamp >= CURRENT_DATE - INTERVAL '30' DAY
GROUP BY DATE(timestamp), symbol
ORDER BY date DESC
```

#### 대시보드 통합

1. **Dashboards** → **+ Dashboard**
2. Dashboard Title: `"Lakehouse Analytics"`
3. 위 3개 차트 추가
4. 필터 추가: Date Range, Symbol
5. **Save**

---

## 📊 실제 사용 시나리오

### 시나리오: 마케팅 팀장

```
Superset 접속 (http://localhost:8088)
  ↓
"Lakehouse Analytics" 대시보드 클릭
  ↓
📊 일일 거래량 바 차트 확인
  ↓
📈 최근 7일 가격 추이 라인 차트 확인
  ↓
✅ "거래량이 5% 증가했으니 마케팅 캠프 성공!" 결론
  ↓
5초 내 의사결정 완료
```

---

## 🔍 SQL Lab (임시 쿼리 실행)

Superset의 **SQL Lab** 기능으로 실시간 쿼리 실행:

1. **SQL Lab** 탭 클릭
2. Database: `Trino` 선택
3. 다음 쿼리 입력:

```sql
-- 최근 24시간 심볼별 거래량
SELECT
  symbol,
  COUNT(*) as tick_count,
  AVG(last_price) as avg_price,
  MAX(last_price) as max_price,
  MIN(last_price) as min_price
FROM hive_prod.option_ticks_db.bronze_option_ticks
WHERE timestamp >= CURRENT_TIMESTAMP - INTERVAL '1' DAY
GROUP BY symbol
ORDER BY tick_count DESC
LIMIT 20
```

4. **Run** → 결과 즉시 확인
5. **Visualize** → 차트로 시각화

---

## 🎯 권장 구성

### 대시보드 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│  Lakehouse Analytics Dashboard (Admin / 2025-12-25)    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 Daily Volume (Bar Chart)                           │
│  ├─ ESZ25C5000: 2,500,000  ███████████                │
│  ├─ SPY25C400:  1,800,000  ████████                   │
│  └─ QQQ25C350:  1,200,000  ██████                     │
│                                                         │
│  📈 7-Day Price Trend (Line Chart)                     │
│  │                  ╱╲                                 │
│  │   Price    ╱╲  ╱  ╲  ╱╲                             │
│  │       ╱╲  ╱  ╲╱    ╲╱  ╲                            │
│  │  ╱╲╱  ╲╱                                            │
│  └──────────────────────────────────────────           │
│                                                         │
│  📊 30-Day Pivot Table                                 │
│  ┌──────┬────────┬────────┬────────┐                  │
│  │ Date │ Symbol │ Avg    │ Volume │                  │
│  ├──────┼────────┼────────┼────────┤                  │
│  │12-25 │ESZ25C  │108.3   │2,500k  │                  │
│  │12-24 │ESZ25C  │108.1   │2,300k  │                  │
│  └──────┴────────┴────────┴────────┘                  │
│                                                         │
│  🔍 Filters: [Date: 2025-12-25] [Symbol: All]        │
└─────────────────────────────────────────────────────────┘
```

---

## ⚙️ 성능 최적화

### 1. Materialized View 생성 (Trino)

대규모 데이터 조회 시 성능 향상:

```sql
CREATE MATERIALIZED VIEW hive_prod.option_ticks_db.mv_daily_stats AS
SELECT
  DATE(timestamp) as date,
  symbol,
  AVG(last_price) as avg_price,
  SUM(volume) as total_volume,
  COUNT(*) as tick_count
FROM hive_prod.option_ticks_db.bronze_option_ticks
GROUP BY DATE(timestamp), symbol
```

### 2. Redis 캐시 설정

`superset_config.py`:

```python
CACHE_CONFIG = {
    'CACHE_TYPE': 'RedisCache',
    'CACHE_DEFAULT_TIMEOUT': 300,  # 5분
    'CACHE_REDIS_HOST': 'superset-redis',
    'CACHE_REDIS_PORT': 6379,
}
```

### 3. 쿼리 타임아웃

```python
SQLALCHEMY_ENGINE_OPTIONS = {
    'connect_args': {'timeout': 60},
}
```

---

## 🔒 보안 및 권한 관리

### RBAC (Role-Based Access Control) 설정

1. **Settings** → **Security** → **Enable RBAC**
2. 역할 5개 생성:
   - **Admin**: 모든 권한
   - **Analyst**: 대시보드 조회, SQL Lab 쿼리 실행
   - **Viewer**: 대시보드 읽기만 가능
   - **Developer**: 대시보드/차트 개발
   - **Ops**: 시스템 모니터링

### Row-Level Security (RLS)

사용자별로 특정 심볼만 조회하도록 제한:

```python
# Superset RLS Rule
{
  "database": "Trino",
  "clause": "symbol = '<USER_SYMBOL>'"
}
```

---

## 📈 성능 기준

| 메트릭 | 목표 | 실제 (로컬) |
|--------|------|----------|
| Superset 대시보드 로딩 | < 5초 | 3-7초 |
| 차트 렌더링 | < 3초 | 2-4초 |
| Trino 쿼리 응답 (100만 행) | < 10초 | 5-15초 |
| SQL Lab 쿼리 실행 | < 30초 | 10-20초 |

---

## 🚨 트러블슈팅

### 문제 1: Superset에서 Trino 연결 실패

**증상**: `Connection test failed: could not connect to server`

**해결**:
```bash
# 1. Trino 상태 확인
docker exec -it trino curl -f http://localhost:8080/v1/info

# 2. 네트워크 연결 확인
docker exec -it superset ping trino

# 3. Trino 로그 확인
docker logs trino | tail -50
```

### 문제 2: 쿼리가 너무 느림

**원인**: 파티션 프루닝 미적용
**해결**:
```sql
-- ❌ 나쁜 예: 파티션 컬럼 미사용
SELECT * FROM bronze_option_ticks WHERE symbol = 'ESZ25C5000'

-- ✅ 좋은 예: 파티션 컬럼 사용
SELECT * FROM bronze_option_ticks
WHERE timestamp >= CURRENT_DATE - INTERVAL '1' DAY
AND symbol = 'ESZ25C5000'
```

---

## 📚 다음 단계

1. ✅ 이 가이드를 따라 Superset 설정 완료
2. 👉 [Tier 2: 반정형 데이터 (Grafana + OpenSearch)](./02-tier2-grafana-opensearch-semistructured.md)로 이동
3. 👉 [Tier 3: 비정형 데이터 (Streamlit)](./03-tier3-streamlit-unstructured.md)로 이동

---

## ✅ 체크리스트 (25개 항목)

- [ ] Docker Superset/Redis/PostgreSQL 컨테이너 추가
- [ ] Admin 사용자 생성
- [ ] 데이터베이스 마이그레이션 실행
- [ ] Trino 데이터 소스 연결
- [ ] Iceberg 카탈로그 인식 확인
- [ ] 데이터셋 3개 생성
- [ ] 차트 3개 생성 (Line, Bar, Pivot)
- [ ] 대시보드 1개 생성
- [ ] 필터 설정 (날짜, 심볼)
- [ ] RBAC 활성화
- [ ] 역할 5개 생성
- [ ] 데이터 소스 권한 설정
- [ ] RLS 규칙 설정
- [ ] Audit logging 활성화
- [ ] Redis 캐시 타임아웃 설정
- [ ] Materialized View 생성
- [ ] 쿼리 타임아웃 설정
- [ ] 컨테이너 리소스 제약 설정
- [ ] 로그 볼륨 마운트
- [ ] 환경 변수 `.env` 파일 작성
- [ ] 백업 스크립트 작성
- [ ] 알림 규칙 3개 설정
- [ ] Superset 대시보드 로딩 시간 측정
- [ ] 성능 벤치마크 실행
- [ ] 운영 문서 작성

---

**축하합니다!** 이제 정형 데이터 시각화 계층이 완성되었습니다. 🎉
