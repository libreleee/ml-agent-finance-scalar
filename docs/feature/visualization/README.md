# 📊 Lakehouse 데이터 시각화 아키텍처 (3-Tier System)

## 🎯 개요

Lakehouse의 데이터 시각화는 **3개 계층으로 분리된 마이크로서비스 아키텍처**로 구성됩니다. 각 계층은 특정 데이터 유형과 사용자 요구사항에 최적화되어 있습니다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    데이터 시각화 3-Tier 아키텍처                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 Tier 1: 정형 데이터 시각화                                   │
│  ├─ 도구: Apache Superset + Trino                               │
│  ├─ 데이터: hive_prod.option_ticks_db.bronze_option_ticks      │
│  ├─ 사용자: 비즈니스 분석가, 마케팅 팀장                        │
│  └─ 기능: BI 대시보드, 차트, SQL Lab                           │
│                                                                 │
│  📈 Tier 2: 반정형 데이터 시각화                                │
│  ├─ 도구: Grafana + OpenSearch + Prometheus                    │
│  ├─ 데이터: hive_prod.logs_db.raw_logs (JSON meta)            │
│  ├─ 사용자: 데이터 엔지니어, DevOps 팀                         │
│  └─ 기능: 실시간 로그 모니터링, 시스템 메트릭, 알림             │
│                                                                 │
│  🖼️ Tier 3: 비정형 데이터 시각화                               │
│  ├─ 도구: Streamlit + PyIceberg + boto3                        │
│  ├─ 데이터: s3a://lakehouse/raw/images/ + image_metadata      │
│  ├─ 사용자: 데이터 사이언티스트, ML 엔지니어                   │
│  └─ 기능: 이미지 갤러리, 메타데이터 탐색, 통계 분석            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 계층별 문서 가이드

| Tier | 문서명 | 데이터 유형 | 주요 도구 | 대상 사용자 | 체크리스트 |
|------|--------|-----------|---------|-----------|----------|
| **1** | [Tier 1: 정형 데이터](./01-tier1-superset-trino-structured.md) | 구조화된 시계열 데이터 | Superset, Trino | BI 분석가 | 25개 |
| **2** | [Tier 2: 반정형 데이터](./02-tier2-grafana-opensearch-semistructured.md) | JSON 로그, 이벤트 데이터 | Grafana, OpenSearch | 데이터 엔지니어 | 20개 |
| **3** | [Tier 3: 비정형 데이터](./03-tier3-streamlit-unstructured.md) | 이미지, 멀티미디어 파일 | Streamlit, PyIceberg | 데이터 사이언티스트 | 15개 |

---

## 🏗️ 통합 데이터 계층별 GUI 아키텍처

### 브론즈 레이어 데이터 GUI 조회 방식

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Bronze Layer Tables                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1️⃣ 정형 데이터: bronze_option_ticks                              │
│     ├─ 컬럼: timestamp, symbol, bid_price, ask_price, volume      │
│     ├─ 파티션: days(timestamp)                                    │
│     └─ 저장소: Iceberg (하이브 메타스토어)                        │
│                                                                     │
│  2️⃣ 반정형 데이터: raw_logs                                       │
│     ├─ 컬럼: event_time, level, message, meta (JSON)             │
│     ├─ 파티션: days(event_time)                                  │
│     ├─ JSON 추출: json_extract_scalar(meta, '$.user')            │
│     └─ 저장소: Iceberg (하이브 메타스토어)                        │
│                                                                     │
│  3️⃣ 비정형 데이터: image_metadata + S3                           │
│     ├─ 메타데이터: image_id, s3_path, width, height, tag         │
│     ├─ 파티션: days(upload_time), tag                            │
│     ├─ 실제 파일: s3a://lakehouse/raw/images/{date}/             │
│     └─ 저장소: Iceberg + SeaweedFS (S3)                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
         ↓ ↓ ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    Visualization Layer (GUI)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  🎯 Tier 1: Superset + Trino                                       │
│  ├─ SQL: SELECT timestamp, symbol, last_price                    │
│  │        FROM bronze_option_ticks                               │
│  │        WHERE timestamp >= CURRENT_DATE - 7 DAYS               │
│  ├─ 시각화: 라인 차트 (시간별 가격), 바 차트 (심볼별 거래량)      │
│  └─ 대시보드: "Lakehouse Analytics" (마케팅 팀장용)              │
│                                                                     │
│  📊 Tier 2: Grafana + OpenSearch                                  │
│  ├─ 쿼리: level:ERROR AND event_time:[now-1h TO now]            │
│  │        + json_extract_scalar(meta, '$.order_id')              │
│  ├─ 시각화: 시계열 그래프 (에러 추이), 파이 차트 (레벨 분포)     │
│  └─ 대시보드: "Data Quality" + "Performance" (데이터 엔지니어용)  │
│                                                                     │
│  🖼️ Tier 3: Streamlit                                             │
│  ├─ 쿼리: SELECT * FROM image_metadata                           │
│  │        WHERE tag = ? AND upload_time >= ?                     │
│  │        ORDER BY upload_time DESC                              │
│  ├─ 렌더링: S3 이미지 갤러리 (4열 그리드)                        │
│  │          + 메타데이터 expander (크기, 수정일, 태그)            │
│  └─ 기능: 필터 (태그, 날짜), 통계 (총 용량, 평균 크기)           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 데이터 유형별 조회 기능 비교표

| 기능 | Tier 1 (Superset) | Tier 2 (Grafana) | Tier 3 (Streamlit) |
|------|------------------|-----------------|------------------|
| **쿼리 언어** | SQL (Trino) | OpenSearch DSL | PyIceberg + SQL |
| **시각화 유형** | 차트, 대시보드, 테이블 | 시계열, 게이지, 로그 | 갤러리, 테이블, 메트릭 |
| **실시간성** | 캐시 (5분) | 실시간 | 5분 캐시 |
| **필터링** | GUI 필터 위젯 | Lucene 쿼리 | Streamlit selectbox |
| **알림** | 임계값 기반 | 조건 기반 | 없음 |
| **권한 관리** | RBAC + RLS | 사용자별 인덱스 | 없음 (앱 레벨) |
| **성능** | 1M 행 < 10초 | 로그 < 1초 | 이미지 < 3초 |
| **주요 사용자** | 비즈니스 팀 | DevOps/SRE | 데이터 사이언스 |

### 심화 기능 비교표 (상세 조회 기능)

| 조회 기능 | Tier 1 (Superset) | Tier 2 (Grafana) | Tier 3 (Streamlit) |
|----------|------------------|------------------|--------------------|
| **데이터 목록 조회** | ✅ (SQL) | ✅ (로그 스트림) | ✅ (메타데이터) |
| **필터링** | ✅ | ✅ | ✅ |
| **검색** | ✅ | ✅ | ✅ |
| **이미지/파일 표시** | ❌ | ❌ | ✅✅✅ (핵심 기능) |
| **차트/그래프** | ✅✅✅ (핵심 기능) | ✅✅ | ✅ |
| **실시간 모니터링** | ❌ | ✅✅✅ (핵심 기능) | ❌ |
| **SQL 쿼리 실행** | ✅✅✅ (핵심 기능) | ❌ | ⚠️ (제한적) |
| **메타데이터 탐색** | ⚠️ (제한적) | ⚠️ (제한적) | ✅✅✅ (핵심 기능) |
| **다중 데이터소스 조회** | ✅ (Trino 통합) | ❌ (로그만) | ❌ (Iceberg만) |
| **내보내기** | ✅ (CSV, Excel) | ⚠️ (JSON) | ✅ (CSV, DataFrame) |
| **대시보드 공유** | ✅ | ✅ | ❌ |
| **접근 제어** | ✅✅✅ (엄격) | ✅✅ (중간) | ⚠️ (앱 레벨) |

---

## 🚀 실제 사용 시나리오

### 시나리오 1: 마케팅 팀장 (Tier 1 사용자)

```
매일 아침 보고서 작성을 위해...

1. Superset 접속 (http://localhost:8088)
2. "Lakehouse Analytics" 대시보드 열기
3. 📊 어제 심볼별 거래량 확인 (바 차트)
   - ESZ25C5000: 2,500,000 ↑ 5% (전일 대비)
4. 📈 최근 7일 가격 추이 확인 (라인 차트)
   - 상승세 지속 → "마케팅 캠프 효과 있음!" 결론
5. 필터: 특정 심볼만 조회 (ESZ25C5000)
6. 5분 내 의사결정 완료 ✅

→ SQL Lab 없음, 코딩 없음, 직관적 UI만 사용
```

### 시나리오 2: 데이터 엔지니어 (Tier 2 사용자)

```
야간 배치 작업 후 에러 로그 조사...

1. Grafana 접속 (http://localhost:3000)
2. "Data Quality" 대시보드 열기
3. ⚠️ 에러 로그 급증 (최근 1시간에 250개)
4. OpenSearch Dashboards로 상세 조회
   - Query: level:ERROR AND event_time:[now-1h TO now]
5. 검색 결과에서 "S3 업로드 실패" 패턴 발견
6. meta.order_id로 원인 추적
   - → "SeaweedFS 연결 타임아웃" 원인 파악
7. DevOps 팀에 슬랙 알림 발송 ✅

→ OpenSearch DSL 쿼리, 실시간 로그 스트림 활용
```

### 시나리오 3: 데이터 사이언티스트 (Tier 3 사용자)

```
새로운 이미지 분류 모델 학습용 데이터셋 구성...

1. Streamlit 앱 접속 (http://localhost:8501)
2. 사이드바 필터 설정
   - Tag: "product"
   - Upload Date: 최근 30일
   - File Size: 100KB ~ 1MB
3. 🖼️ 이미지 갤러리에서 시각적 확인 (4열 그리드)
4. 메타데이터 expander 클릭
   - 각 이미지의 해상도, 파일 크기, 체크섬 확인
5. "View Metadata Table" 클릭
   - 전체 메타데이터를 DataFrame으로 export
6. CSV 다운로드 또는 Jupyter에서 분석 ✅

→ Python + PyIceberg 활용, 실험적 탐색
```

---

## 🔧 빠른 시작 가이드

### 1단계: 각 Tier별 문서 읽기

**첫 번째 방문**: 이 README에서 3-Tier 아키텍처 이해
- 데이터 유형 파악 (정형/반정형/비정형)
- 사용자 역할 매핑 (누가 어떤 Tier를 사용할지)

**깊이 있는 학습**:
- 💼 비즈니스 분석가 → [Tier 1](./01-tier1-superset-trino-structured.md) 문서 읽기
- 🔧 데이터 엔지니어 → [Tier 2](./02-tier2-grafana-opensearch-semistructured.md) 문서 읽기
- 🤖 데이터 사이언티스트 → [Tier 3](./03-tier3-streamlit-unstructured.md) 문서 읽기

### 2단계: docker-compose.yml 확장

```bash
# 현재 프로젝트의 docker-compose.yml에 다음 서비스 추가:
# - Superset 스택 (3개 컨테이너)
# - Grafana 스택 (5개 컨테이너)
# - Streamlit 앱 (1개 컨테이너)

cd /home/i/work/ai/lakehouse-tick
docker-compose up -d

# 상태 확인
docker-compose ps
```

### 3단계: 각 도구 초기화

**Superset** (Tier 1):
```bash
docker exec -it superset superset fab create-admin \
  --username admin --email admin@example.com --password admin
docker exec -it superset superset db upgrade
```

**Grafana** (Tier 2):
```bash
# http://localhost:3000 접속 (admin/admin)
# Configuration → Data Sources → OpenSearch, Prometheus 추가
```

**Streamlit** (Tier 3):
```bash
# http://localhost:8501 자동 실행됨
# Iceberg 메타데이터 테이블 생성 필요
```

### 4단계: 샘플 데이터 준비

```bash
# Tier 1: bronze_option_ticks 데이터는 fspark.py에서 생성됨
# Tier 2: raw_logs 데이터는 fspark_raw_examples.py:50-85 참고
# Tier 3: image_metadata 테이블 생성
docker exec -it trino trino --server localhost:8080 --catalog hive_prod << 'EOF'
CREATE SCHEMA IF NOT EXISTS hive_prod.media_db;

CREATE TABLE hive_prod.media_db.image_metadata (
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
EOF
```

### 5단계: 접속 테스트

```
✅ Superset: http://localhost:8088 (admin/admin)
✅ Grafana: http://localhost:3000 (admin/admin)
✅ Streamlit: http://localhost:8501 (인증 없음)
✅ Trino UI: http://localhost:8080/ui
✅ OpenSearch: https://localhost:9200 (admin/Admin@123)
```

---

## 📊 전체 체크리스트

### Tier 1: Superset 체크리스트 (25개 항목)
→ [상세 가이드](./01-tier1-superset-trino-structured.md#-체크리스트-25개-항목) 참고

- [ ] Docker Superset/Redis/PostgreSQL 컨테이너 추가
- [ ] Admin 사용자 생성
- [ ] Trino 데이터 소스 연결
- [ ] 샘플 차트 3개 생성 (Line, Bar, Pivot)
- [ ] 대시보드 1개 생성
- [ ] ... (총 25개)

### Tier 2: Grafana 체크리스트 (20개 항목)
→ [상세 가이드](./02-tier2-grafana-opensearch-semistructured.md#-체크리스트-20개-항목) 참고

- [ ] OpenSearch 컨테이너 추가
- [ ] OpenSearch Dashboards 컨테이너 추가
- [ ] Prometheus 데이터 소스 추가
- [ ] 샘플 대시보드 5개 생성
- [ ] 알림 규칙 3개 생성
- [ ] ... (총 20개)

### Tier 3: Streamlit 체크리스트 (15개 항목)
→ [상세 가이드](./03-tier3-streamlit-unstructured.md#-체크리스트-15개-항목) 참고

- [ ] Streamlit 컨테이너 추가
- [ ] PyIceberg 연결 테스트
- [ ] image_metadata 메타데이터 테이블 생성
- [ ] 갤러리 페이지 구현
- [ ] 필터링 기능 구현
- [ ] ... (총 15개)

### 통합 테스트 체크리스트 (10개 항목)

- [ ] fspark_raw_examples.py 실행 (샘플 이미지 5개 업로드)
- [ ] image_metadata 테이블 생성
- [ ] Streamlit 갤러리에서 이미지 확인
- [ ] Superset에서 bronze_option_ticks 조회
- [ ] Superset 대시보드 시각화 확인
- [ ] Grafana에서 OpenSearch 로그 수집 확인
- [ ] Grafana 대시보드 메트릭 확인
- [ ] 전체 서비스 접속 URL 테스트
- [ ] 성능 측정 (응답시간, CPU/메모리)
- [ ] 장애 복구 테스트 (컨테이너 재시작)

---

## 🏢 아키텍처 설계 원칙

### 1. 마이크로서비스 패턴 (Microservices Architecture)

**왜 각각 별도 컨테이너인가?**

| 관점 | 단일 컨테이너 | 별도 컨테이너 (✅ 현업 표준) |
|------|-------------|--------------------------|
| 현업 채택률 | 5% | **95%** |
| 독립 스케일링 | ❌ 불가 | ✅ 가능 (Superset만 2개 Pod) |
| 장애 격리 | ❌ 전체 영향 | ✅ 격리된 도메인 |
| 배포 전략 | ❌ 모두 동시 | ✅ 개별 롤링 업데이트 |
| 개발 생산성 | ❌ 복잡한 프로세스 | ✅ 팀별 독립 개발 |

**현업 사례**:
- **Netflix**: Superset, Trino, Grafana 모두 별도 Kubernetes Pod
- **Uber**: 데이터 플랫폼 각 계층 마이크로서비스 분리
- **Airbnb**: BI/모니터링/앱 레이어 독립 배포

### 2. 데이터 계층 분리 (Three-Layer Data Strategy)

**Bronze Layer (원본 데이터)**
```
정형: option_ticks_db.bronze_option_ticks (Iceberg)
반정형: logs_db.raw_logs (Iceberg + JSON meta)
비정형: s3a://lakehouse/raw/images/ (SeaweedFS)
```

**각 계층의 이점**:
- **정형**: 성능 최적화 가능, 복잡한 분석 가능
- **반정형**: 스키마 유연성, 실시간 처리 가능
- **비정형**: 원본 보존, 메타데이터 기반 탐색

### 3. 사용자 역할별 도구 선택

```
마케팅 팀장 → Superset (No-code BI)
        ↓ SQL 작성 능력 불필요
데이터 엔지니어 → Grafana (DevOps style)
        ↓ OpenSearch DSL 숙지
데이터 사이언티스트 → Streamlit (Code-friendly)
        ↓ Python 코딩
```

---

## 📚 추가 자료

### 개별 Tier 문서
- [📊 Tier 1: Apache Superset + Trino (정형 데이터)](./01-tier1-superset-trino-structured.md)
- [📈 Tier 2: Grafana + OpenSearch (반정형 데이터)](./02-tier2-grafana-opensearch-semistructured.md)
- [🖼️ Tier 3: Streamlit + PyIceberg (비정형 데이터)](./03-tier3-streamlit-unstructured.md)

### 상위 문서
- [📋 Data Visualization Options Overview](../data-visualization-options.md) - 포괄적 개요 및 아키텍처 전략

### 관련 구현 코드
- [🐍 fspark.py](../../python/fspark.py) - Tier 1 정형 데이터 생성
- [🐍 fspark_raw_examples.py](../../python/fspark_raw_examples.py) - Tier 2/3 데이터 생성

---

## ⚠️ 트러블슈팅 빠른 참고

| 문제 | 증상 | 해결책 |
|------|------|--------|
| Superset ↔ Trino 연결 실패 | `Connection test failed` | [Tier 1 문서 참고](./01-tier1-superset-trino-structured.md#-트러블슈팅) |
| Grafana ↔ OpenSearch SSL 오류 | `Bad Gateway` | [Tier 2 문서 참고](./02-tier2-grafana-opensearch-semistructured.md#-트러블슈팅) |
| Streamlit에서 이미지 로드 안 됨 | `Failed to load img-001` | [Tier 3 문서 참고](./03-tier3-streamlit-unstructured.md#-트러블슈팅) |
| 쿼리가 너무 느림 | 응답시간 > 30초 | 각 Tier 문서의 성능 최적화 섹션 참고 |
| 컨테이너 중복 포트 오류 | `Port 8088 already in use` | `docker-compose down` 후 재시작 |

---

## 🎓 학습 경로

```
Step 1: 이 README 읽기 (5분)
  ↓
Step 2: 해당 Tier 문서 읽기 (20분 per Tier)
  ↓
Step 3: docker-compose.yml에 서비스 추가 (10분)
  ↓
Step 4: 체크리스트 수행 (1-2시간 per Tier)
  ↓
Step 5: 실제 데이터로 테스트 (30분)
  ↓
✅ 완료!
```

---

## 📞 지원 및 피드백

각 Tier 문서의 **트러블슈팅** 섹션을 먼저 확인하세요.
- Tier 1 이슈 → [01-tier1 Troubleshooting](./01-tier1-superset-trino-structured.md#-트러블슈팅)
- Tier 2 이슈 → [02-tier2 Troubleshooting](./02-tier2-grafana-opensearch-semistructured.md#-트러블슈팅)
- Tier 3 이슈 → [03-tier3 Troubleshooting](./03-tier3-streamlit-unstructured.md#-트러블슈팅)

---

## 🛠️ 개발 시작하기

**개발 및 배포 시에는 이 파일 하나만 사용하세요:**
### 👉 [DEVELOPMENT_CHECKLIST.md](./DEVELOPMENT_CHECKLIST.md)

이 파일에는 다음이 포함되어 있습니다:
- ✅ 10 Phase 단계별 체크리스트
- 📋 모든 docker-compose 설정 코드
- ⚙️ 모든 설정 파일 내용
- 🐍 모든 Python 코드
- 🚀 서비스 시작 명령어
- 🔒 보안 및 운영 가이드

**학습용 상세 문서:**
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 5분 빠른 참조
- [VISUALIZATION_STACK_CODE_CHANGES.md](./VISUALIZATION_STACK_CODE_CHANGES.md) - 추가 코드 예시

---

**축하합니다!** 이제 Lakehouse의 3-Tier 데이터 시각화 아키텍처를 이해했습니다.
**개발 시작하기**: [DEVELOPMENT_CHECKLIST.md](./DEVELOPMENT_CHECKLIST.md) 👈
