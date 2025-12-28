# 🎯 시작하기: 시각화 스택 배포 (Getting Started)

> **현재 상태**: 모든 준비 완료 ✅
> **다음 단계**: Phase 4 (서비스 시작) 실행
> **예상 소요 시간**: 7.5시간 (Phase 4-10 전체)

---

## 📍 당신은 여기에 있습니다

```
✅ Phase 0-3: 완료 (문서 + 코드 + 설정 모두 준비됨)
⏳ Phase 4-10: 실행 대기 (104개 항목)
```

### 현재 준비 상황

| 항목 | 상태 | 확인 |
|------|------|------|
| docker-compose.yml | ✅ 수정 완료 (19개 서비스) | [확인](#1-현재-준비-상황-확인) |
| 설정 파일 | ✅ 생성 완료 (prometheus, superset, grafana, opensearch) | [확인](#1-현재-준비-상황-확인) |
| .env 파일 | ✅ 생성 완료 | [확인](#1-현재-준비-상황-확인) |
| Streamlit 앱 | ✅ 코드 완료 | [확인](#1-현재-준비-상황-확인) |
| 문서 | ✅ 완료 (4,162줄) | [확인](#2-문서-구조) |
| 체크리스트 | ✅ 202개 항목 준비 | [확인](#3-개발-순서) |

---

## 1️⃣ 현재 준비 상황 확인

실행 전에 현재 상태를 확인하세요:

```bash
cd /home/i/work/ai/lakehouse-tick

# 1.1 docker-compose.yml 검증
echo "🔍 docker-compose 검증..."
docker compose config > /dev/null && echo "✅ Valid" || echo "❌ Error"

# 1.2 설정 파일 확인
echo "📁 설정 파일 확인..."
ls -la config/
ls -la config/prometheus/
ls -la config/grafana/provisioning/
ls -la config/superset/
ls -la config/opensearch/

# 1.3 .env 파일 확인
echo "🔐 .env 파일 확인..."
cat .env

# 1.4 Streamlit 앱 확인
echo "🖼️ Streamlit 앱 확인..."
ls -la streamlit-app/
tree streamlit-app/

# 1.5 서비스 수 확인
echo "🐳 서비스 수 확인..."
docker compose config --services | wc -l
```

---

## 2️⃣ 문서 구조

모든 문서는 `docs/feature/visualization/` 폴더에 있습니다:

```
docs/feature/visualization/
│
├─ 📘 README.md ⭐
│   └─ 3-Tier 아키텍처 개요, 기능 비교표, 사용 시나리오
│
├─ 🛠️ DEVELOPMENT_CHECKLIST.md 🔥 (개발용)
│   └─ 202개 체크리스트 (Phase 0-10)
│   └─ 모든 코드 포함 (docker-compose, config, Python)
│   └─ 직접 복사-붙여넣기 가능
│
├─ 📚 Tier별 상세 가이드 (학습용)
│   ├─ 01-tier1-superset-trino-structured.md
│   ├─ 02-tier2-grafana-opensearch-semistructured.md
│   └─ 03-tier3-streamlit-unstructured.md
│
├─ ⚡ QUICK_REFERENCE.md
│   └─ 5분 빠른 참조, Q&A, 문제 해결
│
└─ 📋 VISUALIZATION_STACK_CODE_CHANGES.md
   └─ 코드 예시, 설정 템플릿, 전체 구현
```

### 문서 선택 가이드

| 상황 | 참고 문서 |
|------|---------|
| "전체 개요를 알고 싶어" | [README.md](docs/feature/visualization/README.md) |
| "지금 배포하고 싶어" | [DEVELOPMENT_CHECKLIST.md](docs/feature/visualization/DEVELOPMENT_CHECKLIST.md) + [PHASE_4_EXECUTION_GUIDE.md](PHASE_4_EXECUTION_GUIDE.md) |
| "Superset만 알고 싶어" | [01-tier1-superset-trino-structured.md](docs/feature/visualization/01-tier1-superset-trino-structured.md) |
| "Grafana만 알고 싶어" | [02-tier2-grafana-opensearch-semistructured.md](docs/feature/visualization/02-tier2-grafana-opensearch-semistructured.md) |
| "Streamlit만 알고 싶어" | [03-tier3-streamlit-unstructured.md](docs/feature/visualization/03-tier3-streamlit-unstructured.md) |
| "문제 해결하고 싶어" | [QUICK_REFERENCE.md](docs/feature/visualization/QUICK_REFERENCE.md) |
| "코드 예시를 보고 싶어" | [VISUALIZATION_STACK_CODE_CHANGES.md](docs/feature/visualization/VISUALIZATION_STACK_CODE_CHANGES.md) |

---

## 3️⃣ 개발 순서

### 📋 추천 진행 순서

#### 1단계: 이해 (10분)
```bash
# 1. 3-Tier 아키텍처 이해
cat docs/feature/visualization/README.md | head -100

# 2. 현재 상태 확인
cat IMPLEMENTATION_STATUS.md
```

#### 2단계: 실행 (7.5시간)
```bash
# 1. Phase 4 시작 (30분)
#    - 서비스 시작
#    - 헬스 확인
cat PHASE_4_EXECUTION_GUIDE.md | sed -n '/^## 🎯 Phase 4/,/^## 🎯 Phase 5/p'

# 2. Phase 5 실행 (2시간)
#    - 데이터 준비
#    - 메타데이터 테이블 생성
cat PHASE_4_EXECUTION_GUIDE.md | sed -n '/^## 🎯 Phase 5/,/^## 🎯 Phase 6/p'

# 3. Phase 6-10 순차 실행
#    - Superset 설정
#    - Grafana 설정
#    - Streamlit 테스트
#    - 성능 검증
#    - 보안 및 운영
```

#### 3단계: 검증 (30분)
```bash
# 모든 서비스 접속 확인
# 각 도구에서 샘플 대시보드/쿼리 실행
# 성능 벤치마크 실행
```

---

## 4️⃣ 빠른 시작 (바로 배포하고 싶다면)

### 한눈에 보기

```bash
cd /home/i/work/ai/lakehouse-tick

# 1️⃣ 사전 체크
docker compose config > /dev/null && echo "✅ Ready"

# 2️⃣ 서비스 시작
docker compose up -d

# 3️⃣ 상태 확인 (60초 대기 후)
sleep 60
docker compose ps

# 4️⃣ 헬스 체크
curl -s http://localhost:8088/health && echo "✅ Superset"
curl -s http://localhost:3000/api/health && echo "✅ Grafana"
curl -s http://localhost:8501/_stcore/health && echo "✅ Streamlit"

# 5️⃣ 브라우저 접속
# Superset: http://localhost:8088 (admin/admin)
# Grafana: http://localhost:3000 (admin/admin)
# Streamlit: http://localhost:8501
# OpenSearch: http://localhost:5601 (admin/Admin@123)
# Prometheus: http://localhost:9090
# Trino: http://localhost:8080
```

---

## 5️⃣ 자세한 진행 가이드

모든 단계를 자세히 따라가려면 **[PHASE_4_EXECUTION_GUIDE.md](PHASE_4_EXECUTION_GUIDE.md)** 를 참고하세요.

이 문서에는 다음이 포함됩니다:

```
Phase 4: 서비스 시작 (30분)
├─ 사전 점검 (포트, 디스크, 메모리)
├─ 서비스 시작 (docker compose up)
├─ 헬스 확인 (curl 헬스 체크)
└─ 로그 모니터링

Phase 5: 데이터 준비 (2시간)
├─ Iceberg 테이블 생성
├─ 샘플 데이터 준비
└─ 데이터 검증

Phase 6: Superset 설정 (1시간)
├─ Trino 데이터 소스 추가
├─ 샘플 대시보드 생성
└─ 권한 설정

Phase 7: Grafana 설정 (1시간)
├─ OpenSearch/Prometheus 데이터 소스 추가
├─ 샘플 대시보드 생성
└─ 알림 규칙 설정

Phase 8: Streamlit 테스트 (30분)
├─ 앱 접속
├─ 필터 기능 테스트
└─ 갤러리 렌더링 확인

Phase 9: 성능 검증 (1시간)
├─ 응답 시간 측정
├─ 리소스 사용률 확인
└─ 기준과 비교

Phase 10: 보안 및 운영 (1시간)
├─ 비밀번호 강화
├─ 백업 설정
├─ 로깅 구성
└─ 운영 가이드
```

---

## 6️⃣ 각 도구별 접속 정보

### 🔑 로그인 정보

| 도구 | URL | 사용자 | 비밀번호 | 포트 |
|------|-----|--------|---------|------|
| **Superset** | http://localhost:8088 | admin | admin | 8088 |
| **Grafana** | http://localhost:3000 | admin | admin | 3000 |
| **OpenSearch Dashboards** | http://localhost:5601 | admin | Admin@123 | 5601 |
| **Streamlit** | http://localhost:8501 | (없음) | (없음) | 8501 |
| **Prometheus** | http://localhost:9090 | (없음) | (없음) | 9090 |
| **Trino UI** | http://localhost:8080 | (없음) | (없음) | 8080 |

### 📡 서비스 현황

```bash
# 모든 서비스 상태 확인
docker compose ps

# 특정 서비스 로그
docker compose logs -f superset
docker compose logs -f grafana
docker compose logs -f streamlit-app

# 리소스 사용률
docker stats
```

---

## 7️⃣ 예상 소요 시간

```
전체 배포: ~7.5시간

Phase 별 소요 시간:
┌─────────────┬───────────┐
│ Phase 4     │ 30분      │ 서비스 시작
├─────────────┼───────────┤
│ Phase 5     │ 2시간     │ 데이터 준비
├─────────────┼───────────┤
│ Phase 6     │ 1시간     │ Superset 설정
├─────────────┼───────────┤
│ Phase 7     │ 1시간     │ Grafana 설정
├─────────────┼───────────┤
│ Phase 8     │ 30분      │ Streamlit 테스트
├─────────────┼───────────┤
│ Phase 9     │ 1시간     │ 성능 검증
├─────────────┼───────────┤
│ Phase 10    │ 1시간     │ 보안 및 운영
└─────────────┴───────────┘
합계: 7시간 30분

(실제 소요 시간은 시스템 사양에 따라 다를 수 있습니다)
```

---

## 8️⃣ 문제 발생 시

### 즉시 확인 사항

```bash
# 1. 서비스 상태
docker compose ps | grep -v "Up"

# 2. 포트 충돌
netstat -tuln | grep -E '8088|3000|8501'

# 3. 로그 확인
docker compose logs --tail=50

# 4. 메모리/디스크
free -h && df -h
```

### 자세한 문제 해결

[QUICK_REFERENCE.md](docs/feature/visualization/QUICK_REFERENCE.md)의 "문제 해결" 섹션을 참고하세요.

```
- 서비스가 시작되지 않음
- 데이터베이스 연결 실패
- 성능 저하
- 메모리 부족
- 포트 이미 사용 중
```

---

## ✅ 체크리스트

### 배포 전

```bash
□ docker-compose.yml 검증 완료
□ 포트 8088, 3000, 8501, 9200, 5601, 9090 사용 가능 확인
□ 최소 8GB 메모리 확인
□ 최소 50GB 디스크 여유 확인
□ .env 파일 비밀번호 확인 (필요시 변경)
□ config/ 디렉토리 파일 확인
□ streamlit-app/ 디렉토리 확인
```

### 배포 중

```bash
□ Phase 4: 서비스 시작
  □ docker compose up -d 실행
  □ 모든 컨테이너 Up 상태 확인
  □ 헬스 체크 통과

□ Phase 5: 데이터 준비
  □ 이미지 메타데이터 테이블 생성
  □ 샘플 데이터 삽입
  □ 데이터 조회 확인

□ Phase 6: Superset 설정
  □ 웹 접속 성공
  □ Trino 데이터 소스 추가
  □ 샘플 대시보드 생성

□ Phase 7: Grafana 설정
  □ 웹 접속 성공
  □ 데이터 소스 추가 (Prometheus, OpenSearch)
  □ 샘플 대시보드 생성

□ Phase 8: Streamlit 테스트
  □ 앱 접속 성공
  □ 갤러리 렌더링 확인
  □ 필터 기능 테스트

□ Phase 9: 성능 검증
  □ 응답 시간 측정
  □ 리소스 사용률 확인
  □ 성능 기준 충족

□ Phase 10: 보안 및 운영
  □ 비밀번호 변경 완료
  □ 백업 스크립트 설정
  □ 로깅 구성 완료
```

---

## 🎯 다음 단계

### 지금 바로 하기

**1단계 (지금)**: 이 문서 읽기 ✓

**2단계 (5분)**: [README.md](docs/feature/visualization/README.md) 읽기
```bash
cat docs/feature/visualization/README.md | head -200
```

**3단계 (30분)**: [PHASE_4_EXECUTION_GUIDE.md](PHASE_4_EXECUTION_GUIDE.md) Phase 4 섹션 읽기
```bash
sed -n '/^## 🎯 Phase 4/,/^### Step 4/p' PHASE_4_EXECUTION_GUIDE.md
```

**4단계 (시작)**: 서비스 시작
```bash
docker compose up -d
docker compose ps
```

### 진행 중 참고

- **체크리스트 업데이트**: [DEVELOPMENT_CHECKLIST.md](docs/feature/visualization/DEVELOPMENT_CHECKLIST.md)의 체크박스 표시
- **문제 발생 시**: [QUICK_REFERENCE.md](docs/feature/visualization/QUICK_REFERENCE.md) 참고
- **상세 정보 필요**: Tier별 상세 가이드 참고

---

## 📞 지원

### 자주 묻는 질문

```
Q: 모든 Phase를 한 번에 해야 하나?
A: 아니오. Phase 4부터 하나씩 진행 가능합니다.

Q: 기존 서비스에 영향이 있나?
A: 아니오. 기존 7개 서비스는 그대로 유지되고 9개 신규 서비스만 추가됩니다.

Q: 롤백이 가능한가?
A: 네. docker compose down 하면 모든 신규 서비스가 제거됩니다.

Q: 재시작 후에도 데이터가 유지되나?
A: 네. Named volumes에 저장되므로 유지됩니다.

Q: 운영 비용이 얼마나 드나?
A: 로컬 개발 환경은 추가 비용 없음. 클라우드는 서비스 크기에 따라 달라집니다.
```

### 더 알아보기

- 아키텍처 설계: [README.md](docs/feature/visualization/README.md)
- Superset 가이드: [01-tier1-superset-trino-structured.md](docs/feature/visualization/01-tier1-superset-trino-structured.md)
- Grafana 가이드: [02-tier2-grafana-opensearch-semistructured.md](docs/feature/visualization/02-tier2-grafana-opensearch-semistructured.md)
- Streamlit 가이드: [03-tier3-streamlit-unstructured.md](docs/feature/visualization/03-tier3-streamlit-unstructured.md)
- 빠른 참조: [QUICK_REFERENCE.md](docs/feature/visualization/QUICK_REFERENCE.md)

---

## 🚀 지금 시작하세요!

```bash
# Phase 4 시작
cd /home/i/work/ai/lakehouse-tick
docker compose up -d
docker compose ps

# 또는 자세한 가이드 따라가기
cat PHASE_4_EXECUTION_GUIDE.md
```

---

**Happy Visualization! 🎉**

모든 준비가 완료되었습니다. Phase 4부터 시작하면 2-3시간 내에 전체 시각화 스택이 완성될 것입니다.
