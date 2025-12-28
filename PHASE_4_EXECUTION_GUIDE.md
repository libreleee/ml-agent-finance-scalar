# 🚀 Phase 4-10 실행 가이드 (Execution Guide)

> **상태**: 모든 준비 완료 ✅
> **시작점**: Phase 4 (서비스 시작)
> **참고 자료**: `docs/feature/visualization/DEVELOPMENT_CHECKLIST.md`

---

## 📋 빠른 개요

현재 상태:
- ✅ Phase 0-3: 100% 완료 (환경 + 코드 모두 준비됨)
- ⏳ Phase 4-10: 실행 대기 (7개 phase, 104개 항목)

예상 소요 시간:
```
Phase 4: 30분  (서비스 시작)
Phase 5: 2시간  (데이터 준비)
Phase 6: 1시간  (Superset 설정)
Phase 7: 1시간  (Grafana 설정)
Phase 8: 30분   (Streamlit 테스트)
Phase 9: 1시간  (성능 검증)
Phase 10: 1시간 (보안 및 운영)
────────────────
합계: ~7.5시간
```

---

## 🎯 Phase 4: 서비스 시작 (30분)

### Step 1: 사전 점검

```bash
cd /home/i/work/ai/lakehouse-tick

# 1.1 현재 포트 상태 확인
echo "🔍 포트 점검..."
for port in 8088 3000 8501 9200 5601 9090 8080; do
  if netstat -tuln 2>/dev/null | grep -q ":$port "; then
    echo "⚠️ 포트 $port 이미 사용 중"
  else
    echo "✅ 포트 $port 사용 가능"
  fi
done

# 1.2 디스크 여유 확인
echo "💾 디스크 여유 확인..."
available=$(df /home/i/work/ai/lakehouse-tick | awk 'NR==2 {print $4}')
if [ $available -gt 50000000 ]; then
  echo "✅ 디스크 여유 충분 ($(($available/1024/1024))GB)"
else
  echo "⚠️ 디스크 여유 부족 ($(($available/1024/1024))GB)"
fi

# 1.3 메모리 확인
echo "🧠 메모리 확인..."
total=$(free -g | awk 'NR==2 {print $2}')
if [ $total -ge 8 ]; then
  echo "✅ 메모리 충분 (${total}GB)"
else
  echo "⚠️ 메모리 부족 (${total}GB, 권장 8GB 이상)"
fi
```

### Step 2: 서비스 시작

```bash
# 2.1 docker-compose 설정 검증
echo "🔍 docker-compose 검증..."
docker compose config > /dev/null && \
  echo "✅ docker-compose.yml 유효" || \
  echo "❌ docker-compose.yml 오류"

# 2.2 기존 컨테이너 정리 (선택사항)
echo "🧹 기존 컨테이너 확인..."
docker compose ps
# 필요시 정리: docker compose down

# 2.3 모든 서비스 시작
echo "🚀 서비스 시작 중..."
docker compose up -d

echo "⏳ 모든 서비스가 시작될 때까지 대기 중 (약 60초)..."
sleep 60

# 2.4 서비스 상태 확인
echo "📊 서비스 상태 확인..."
docker compose ps
```

### Step 3: 서비스 헬스 확인

```bash
# 3.1 각 서비스 헬스 체크 스크립트
echo "🏥 서비스 헬스 체크..."

# Superset
echo -n "Superset: "
curl -s -o /dev/null -w "Status %{http_code}\n" http://localhost:8088/health

# Grafana
echo -n "Grafana: "
curl -s -o /dev/null -w "Status %{http_code}\n" http://localhost:3000/api/health

# OpenSearch
echo -n "OpenSearch: "
curl -s -k -u admin:Admin@123 -o /dev/null -w "Status %{http_code}\n" https://localhost:9200/_cluster/health

# Streamlit
echo -n "Streamlit: "
curl -s -o /dev/null -w "Status %{http_code}\n" http://localhost:8501/_stcore/health

# Prometheus
echo -n "Prometheus: "
curl -s -o /dev/null -w "Status %{http_code}\n" http://localhost:9090/-/healthy

# Trino (기존 서비스)
echo -n "Trino: "
curl -s -o /dev/null -w "Status %{http_code}\n" http://localhost:8080/v1/info

# Hive Metastore (기존 서비스)
echo -n "Hive Metastore: "
if docker compose logs hive-metastore | grep -q "started"; then
  echo "Status 200 (logs ok)"
else
  echo "Status ??? (check logs)"
fi
```

### Step 4: 로그 모니터링

```bash
# 문제 발생 시 로그 확인
echo "📋 실시간 로그 모니터링 (Ctrl+C 로 종료)..."
docker compose logs -f

# 또는 특정 서비스만
docker compose logs -f superset
docker compose logs -f grafana
docker compose logs -f streamlit-app
```

### Phase 4 완료 확인 체크리스트

```
[ ] 모든 서비스가 'Up' 상태인지 확인
[ ] 모든 헬스 체크에서 Status 200 또는 'up' 응답
[ ] 로그에 에러 메시지가 없음
[ ] 각 서비스 포트에 브라우저로 접속 가능
```

---

## 🎯 Phase 5: 데이터 준비 (2시간)

### Step 1: Iceberg 테이블 생성

```bash
# 1.1 Trino CLI 접속
docker compose exec trino trino \
  --server localhost:8080 \
  --catalog hive_prod \
  --execute "SHOW SCHEMAS"

# 1.2 이미지 메타데이터 테이블 생성
docker compose exec trino trino \
  --server localhost:8080 \
  --catalog hive_prod \
  << 'EOF'
CREATE SCHEMA IF NOT EXISTS media_db;

CREATE TABLE IF NOT EXISTS hive_prod.media_db.image_metadata (
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

echo "✅ image_metadata 테이블 생성 완료"
```

### Step 2: 샘플 데이터 준비

```bash
# 2.1 fspark_raw_examples.py 실행 (이미지 업로드)
cd /home/i/work/ai/lakehouse-tick/python
python fspark_raw_examples.py

# 2.2 메타데이터 샘플 데이터 삽입
docker compose exec trino trino \
  --server localhost:8080 \
  --catalog hive_prod \
  << 'EOF'
INSERT INTO hive_prod.media_db.image_metadata VALUES
('img-001', 's3a://lakehouse/raw/images/2025-12-25/sample1.png', 102400, 'image/png', TIMESTAMP '2025-12-25 10:00:00', 'manual', 'product', 800, 600, 'abc123', TIMESTAMP '2025-12-25 10:00:00'),
('img-002', 's3a://lakehouse/raw/images/2025-12-25/sample2.png', 204800, 'image/png', TIMESTAMP '2025-12-25 11:00:00', 'manual', 'user', 1024, 768, 'def456', TIMESTAMP '2025-12-25 11:00:00'),
('img-003', 's3a://lakehouse/raw/images/2025-12-25/sample3.png', 153600, 'image/png', TIMESTAMP '2025-12-25 12:00:00', 'manual', 'analytics', 1200, 900, 'ghi789', TIMESTAMP '2025-12-25 12:00:00');
EOF

echo "✅ 샘플 데이터 삽입 완료"

# 2.3 데이터 확인
docker compose exec trino trino \
  --server localhost:8080 \
  --catalog hive_prod \
  --execute "SELECT COUNT(*) as count FROM hive_prod.media_db.image_metadata;"
```

### Phase 5 완료 확인 체크리스트

```
[ ] image_metadata 테이블 생성됨
[ ] 샘플 데이터 3개 이상 삽입됨
[ ] 데이터 쿼리 가능 (COUNT 성공)
[ ] S3에 이미지 파일 존재 확인
```

---

## 🎯 Phase 6: Superset 설정 (1시간)

### Step 1: Superset 접속 및 초기화

```bash
# 1.1 브라우저에서 접속
# http://localhost:8088
# 로그인: admin / admin

# 1.2 초기 설정 (필요시)
# 설정 → 기본 설정 → 확인

echo "✅ Superset 접속 성공"
```

### Step 2: Trino 데이터 소스 추가

```bash
# Superset UI에서:
# 1. Settings (⚙️) → Database Connections → + Database
# 2. Trino 선택
# 3. URI: trino://user@trino:8080/hive_prod
# 4. "Test Connection" → "Connect"

echo "📝 Superset UI에서 위 단계 진행"
echo "URL: http://localhost:8088"
```

### Step 3: 샘플 대시보드 생성

```bash
# Superset UI에서:
# 1. Data → Datasets → + Dataset
# 2. Database: Trino, Schema: option_ticks_db, Table: bronze_option_ticks
# 3. Create Dataset → Create Chart
# 4. Chart Type: Time-series Line Chart
# 5. X-Axis: timestamp, Metrics: AVG(last_price)
# 6. "Save as Chart"

echo "📝 Superset UI에서 샘플 대시보드 생성"
echo "URL: http://localhost:8088"
```

### Phase 6 완료 확인 체크리스트

```
[ ] Superset 브라우저 접속 성공
[ ] admin 로그인 성공
[ ] Trino 데이터 소스 연결 성공
[ ] 샘플 대시보드 생성 완료
[ ] SQL Lab에서 SELECT * FROM ... LIMIT 10 실행 성공
```

---

## 🎯 Phase 7: Grafana 설정 (1시간)

### Step 1: Grafana 접속 및 초기화

```bash
# 1.1 브라우저에서 접속
# http://localhost:3000
# 로그인: admin / admin

# 1.2 비밀번호 변경 (선택사항)
# 프롬프트가 나타나면 설정

echo "✅ Grafana 접속 성공"
```

### Step 2: 데이터 소스 추가

```bash
# Grafana UI에서:
# 1. Configuration (⚙️) → Data Sources → Add data source
#
# A. Prometheus 추가
#    - Type: Prometheus
#    - URL: http://prometheus:9090
#    - Save & Test
#
# B. OpenSearch 추가
#    - Type: OpenSearch
#    - URL: https://opensearch:9200
#    - Auth: Basic auth (admin / Admin@123)
#    - Skip TLS Verify: ON
#    - Save & Test

echo "📝 Grafana UI에서 위 단계 진행"
echo "URL: http://localhost:3000"
```

### Step 3: 샘플 대시보드 생성

```bash
# Grafana UI에서:
# 1. Create → Dashboard
# 2. Add panel
# 3. Data Source: Prometheus
# 4. Query: rate(node_cpu_seconds_total[5m])
# 5. Visualization: Graph
# 6. Save

echo "📝 Grafana UI에서 샘플 대시보드 생성"
echo "URL: http://localhost:3000"
```

### Phase 7 완료 확인 체크리스트

```
[ ] Grafana 브라우저 접속 성공
[ ] admin 로그인 성공
[ ] Prometheus 데이터 소스 연결 성공
[ ] OpenSearch 데이터 소스 연결 성공
[ ] 샘플 대시보드 생성 완료
[ ] 메트릭 그래프 표시 확인
```

---

## 🎯 Phase 8: Streamlit 테스트 (30분)

### Step 1: Streamlit 앱 접속

```bash
# 1.1 브라우저에서 접속
# http://localhost:8501

# 1.2 페이지 확인
# - Home (갤러리 페이지)
# - 검색 페이지
# - 통계 페이지

echo "✅ Streamlit 앱 접속 성공"
```

### Step 2: 기능 테스트

```bash
# Streamlit UI에서:
# 1. 사이드바 필터 테스트
#    - Tag 선택
#    - Date Range 선택
#    - File Size 필터
#
# 2. 갤러리 렌더링 확인
#    - 이미지 표시 확인
#    - 메타데이터 expander 클릭
#
# 3. 통계 메트릭 확인
#    - Total Images
#    - Total Size
#    - Avg Size
#
# 4. 데이터 테이블 확인
#    - "View Metadata Table" expander

echo "📝 Streamlit UI에서 기능 테스트"
echo "URL: http://localhost:8501"
```

### Phase 8 완료 확인 체크리스트

```
[ ] Streamlit 앱 브라우저 접속 성공
[ ] 갤러리 페이지 로드 성공
[ ] 필터 기능 작동
[ ] 이미지 표시 확인
[ ] 메타데이터 조회 확인
[ ] 통계 메트릭 표시 확인
```

---

## 🎯 Phase 9: 성능 검증 (1시간)

### Step 1: 응답 시간 측정

```bash
# 1.1 Superset 대시보드 로딩 시간
echo "⏱️ Superset 성능 측정..."
time curl -s -o /dev/null http://localhost:8088/api/v1/dashboards

# 1.2 Streamlit 앱 로딩 시간
echo "⏱️ Streamlit 성능 측정..."
time curl -s -o /dev/null http://localhost:8501

# 1.3 Grafana 대시보드 로딩 시간
echo "⏱️ Grafana 성능 측정..."
time curl -s -o /dev/null http://localhost:3000/api/search

# 1.4 Trino 쿼리 성능
echo "⏱️ Trino 쿼리 성능 측정..."
time docker compose exec trino trino \
  --server localhost:8080 \
  --catalog hive_prod \
  --execute "SELECT COUNT(*) FROM hive_prod.option_ticks_db.bronze_option_ticks;"
```

### Step 2: 리소스 사용률 모니터링

```bash
# 2.1 Docker 컨테이너 리소스 사용률
echo "📊 리소스 사용률..."
docker stats --no-stream

# 2.2 시스템 전체 리소스
echo "🖥️ 시스템 리소스..."
free -h
df -h
top -b -n 1 | head -20
```

### Step 3: 성능 기준과 비교

```
예상 성능 기준:
- Superset 대시보드: < 5초 (목표)
- Streamlit 갤러리: < 3초 (목표)
- Grafana 대시보드: < 2초 (목표)
- Trino 쿼리 (100만 행): < 10초 (목표)

메모리 사용:
- 전체: < 8GB (권장 최소 8GB)
- 각 서비스: < 2GB (일반적)

디스크:
- 남은 공간: > 10GB (최소)
```

### Phase 9 완료 확인 체크리스트

```
[ ] 대시보드 로딩 시간 < 5초
[ ] 쿼리 응답 시간 < 10초
[ ] 메모리 사용률 < 80%
[ ] CPU 사용률 안정적 (< 70%)
[ ] 디스크 여유 충분 (> 10GB)
```

---

## 🎯 Phase 10: 보안 및 운영 (1시간)

### Step 1: 비밀번호 강화

```bash
# 1.1 .env 파일 비밀번호 변경
nano .env

# 변경 항목:
# SUPERSET_SECRET_KEY=your-super-secret-key  (변경)
# SUPERSET_ADMIN_PASSWORD=admin  (변경)
# GRAFANA_PASSWORD=admin  (변경)
# OPENSEARCH_PASSWORD=Admin@123  (변경)

# 1.2 새 비밀번호로 재시작
docker compose down
docker compose up -d
```

### Step 2: 백업 설정

```bash
# 2.1 백업 디렉토리 생성
mkdir -p /backups/lakehouse
chmod 700 /backups/lakehouse

# 2.2 정기 백업 스크립트 생성
cat > /backups/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/lakehouse/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "🔄 백업 시작..."

# Superset DB
docker compose exec -T superset-db pg_dump -U superset superset > $BACKUP_DIR/superset.sql

# Grafana
docker compose exec -T grafana tar -czf - /var/lib/grafana > $BACKUP_DIR/grafana.tar.gz

# 설정 파일
tar -czf $BACKUP_DIR/config.tar.gz ./config ./streamlit-app

echo "✅ 백업 완료: $BACKUP_DIR"
EOF

chmod +x /backups/backup.sh

# 2.3 크론 작업 설정 (매일 자정)
# crontab -e
# 0 0 * * * /backups/backup.sh
```

### Step 3: 로깅 및 모니터링

```bash
# 3.1 컨테이너 로그 확인
docker compose logs --tail=100 > /backups/logs/all-services.log

# 3.2 시스템 로그 모니터링 (선택사항)
# journalctl -u docker -f

# 3.3 성능 로그 수집
docker stats --no-stream > /backups/logs/stats-$(date +%Y%m%d_%H%M%S).log
```

### Step 4: 보안 검증

```bash
# 4.1 포트 접근 제한 (방화벽)
# Ubuntu firewall 예시:
sudo ufw allow 8088/tcp  # Superset
sudo ufw allow 3000/tcp  # Grafana
sudo ufw allow 8501/tcp  # Streamlit
sudo ufw allow 9090/tcp  # Prometheus

# 4.2 SSL/TLS 설정 (프로덕션)
# nginx 또는 reverse proxy 설정 필요

# 4.3 접근 로그 확인
docker compose logs superset | grep -i "login\|error" | tail -20
docker compose logs grafana | grep -i "login\|error" | tail -20
```

### Phase 10 완료 확인 체크리스트

```
[ ] 비밀번호 변경 완료
[ ] 백업 스크립트 생성 완료
[ ] 첫 번째 백업 실행 완료
[ ] 로그 모니터링 설정 완료
[ ] 포트 방화벽 설정 완료 (필요시)
[ ] 운영 가이드 문서화 완료
```

---

## ✅ 최종 검증

모든 Phase 완료 후 다음을 확인하세요:

```bash
# 최종 상태 확인
docker compose ps

# 모든 서비스 헬스 체크
echo "🏥 최종 헬스 체크..."
curl -s http://localhost:8088/health && echo "✅ Superset"
curl -s http://localhost:3000/api/health && echo "✅ Grafana"
curl -s http://localhost:8501/_stcore/health && echo "✅ Streamlit"
curl -s http://localhost:9090/-/healthy && echo "✅ Prometheus"

# 모든 포트 접근 확인
echo "🌐 포트 접근 확인..."
for url in \
  "http://localhost:8088" \
  "http://localhost:3000" \
  "http://localhost:8501" \
  "http://localhost:9090" \
  "http://localhost:8080"; do
  echo -n "$url: "
  curl -s -o /dev/null -w "Status %{http_code}\n" $url
done
```

---

## 📚 참고 자료

| 문서 | 용도 |
|------|------|
| [DEVELOPMENT_CHECKLIST.md](docs/feature/visualization/DEVELOPMENT_CHECKLIST.md) | 상세 체크리스트 (202개 항목) |
| [README.md](docs/feature/visualization/README.md) | 3-Tier 아키텍처 개요 |
| [QUICK_REFERENCE.md](docs/feature/visualization/QUICK_REFERENCE.md) | 빠른 참조 및 Q&A |
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | 현재 진행 상황 |

---

## 🆘 문제 해결

### 서비스가 시작되지 않음

```bash
# 1. 로그 확인
docker compose logs superset

# 2. 포트 충돌 확인
netstat -tuln | grep -E '8088|3000|8501'

# 3. 디스크/메모리 확인
df -h
free -h

# 4. 컨테이너 재시작
docker compose restart superset
```

### 데이터베이스 연결 실패

```bash
# 1. 데이터베이스 상태 확인
docker compose exec superset-db pg_isready -U superset -d superset

# 2. Trino 상태 확인
curl http://localhost:8080/v1/info

# 3. 네트워크 확인
docker network ls
docker network inspect lakehouse-net
```

### 성능 저하

```bash
# 1. 메모리 사용률 확인
docker stats

# 2. 쿼리 최적화
# EXPLAIN 쿼리 계획 확인
# 파티션 pruning 적용

# 3. 캐시 설정 확인
# Superset: Redis 설정
# Grafana: Panel 캐시 설정
```

---

## 🎉 축하합니다!

모든 Phase를 완료하면 다음을 사용 가능합니다:

✅ **Superset** - BI 대시보드 (http://localhost:8088)
✅ **Grafana** - 실시간 모니터링 (http://localhost:3000)
✅ **Streamlit** - 이미지 갤러리 (http://localhost:8501)
✅ **OpenSearch** - 로그 관리 (http://localhost:5601)
✅ **Prometheus** - 메트릭 (http://localhost:9090)
✅ **Trino** - 쿼리 엔진 (http://localhost:8080)

---

**다음 단계**: DEVELOPMENT_CHECKLIST.md의 Phase 4 항목을 체크박스로 표시하며 진행하세요! 🚀
