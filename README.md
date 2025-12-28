# ml-agent-finance-scalar

옵션(콜/풋) **틱데이터(XML)** + **코드 파일(XML)**을 기반으로

- **오프라인(Research/Training Factory)**: Spark + Iceberg + Ray + MLflow로
  - ETL(Bronze/Silver/Gold)
  - 피처/라벨 생성
  - 워크포워드/튜닝/백테스트 병렬
  - 모델/전략 승격(Registry)
- **런타임(Runtime Trading Agent)**: Production 모델을 로드하여
  - 실시간(분 단위) 피처 계산
  - 추론
  - 리스크 게이트
  - 주문/로그

까지 이어지는 “실전 트레이딩 에이전트 팀”의 **레퍼런스 설계/구축 템플릿**입니다.

> 작성일: 2025-12-20 (KST)  
> 이 레포는 **HFT가 아닌 분단위(1m~5m) 전략**을 전제로 합니다.

---

## 0. 이 레포에 포함된 샘플 데이터

`data/sample_xml/`

- `202601_20251201_TICK_CALL.xml`
- `202601_20251201_TICK_PUT.xml`
- `202601_20251219_CODE_CALL.xml`
- `202601_20251219_CODE_PUT.xml`

샘플 XML 스키마(요약):

### Tick (CALL/PUT 공통)
- `ymcode` (예: 202601)
- `code` (예: B0161530 / C0161300)
- `strike` (행사가)
- `idate` (yyyymmdd)
- `itime` (hhmmss)
- `tdate` (ISO-8601, KST 포함)
- `tcnt` (tick sequence)
- `c` (체결가)
- `o` (open)
- `h` (high)
- `l` (low)
- `oi` (open interest, 샘플에서는 0)
- `ccnt` (체결건수/카운트 성격, 샘플)

### Code (CALL/PUT 공통)
- `ymcode`
- `code`
- `lastday` (행사가/기초 정보로 쓰는 값으로 추정, 도메인 정의 필요)

---

## 1. 큰 그림

- 오프라인은 **재현성/대규모 실험**이 핵심(실시간성 거의 불필요)
- 런타임은 **지연/안정성/리스크/주문**이 핵심(에이전트 동작 시에만 실시간 필요)

자세한 내용은:
- `docs/10_offline_mainline_A_build_run.md`
- `docs/20_runtime_architecture.md`

---

## 2. 빠른 시작(로컬, Docker)

> 이 레포는 “로컬 실행 가능한 뼈대”를 제공합니다.  
> Spark/Iceberg 실행은 환경(Windows/WSL/Linux)에 따라 세팅이 달라질 수 있으니 문서를 따라가세요.

0) 필수 구성 요소 확인

```bash
bash scripts/00_check_prerequisites.sh
```

1) 서비스 올리기(MLflow + MinIO + Nessie + Redis)

```bash
docker compose up -d
```

2) Spark에서 Iceberg 테이블 만들고 샘플 XML 적재

```bash
bash scripts/01_spark_shell.sh
# 이후 docs/10_offline_mainline_A_build_run.md 의 Spark SQL/ETL 단계대로 실행
```

3) 학습(예: LightGBM + Ray + MLflow)

```bash
python -m ml.train_lgbm_ray_mlflow --help
```

---

## 3. 문서 인덱스

- 오프라인(Research/Training)
  - `docs/10_offline_mainline_A_build_run.md`
  - `docs/30_data_schemas.md`
  - `docs/31_spark_etl_pyspark_iceberg_skeleton.md`
  - `docs/40_checklist.md`
- 런타임(Runtime Trading)
  - `docs/20_runtime_architecture.md`
  - `docs/21_feature_spec.md`

- 다이어그램
  - `diagrams/offline_A.mmd`
  - `diagrams/runtime_agent.mmd`

---

## 4. (중요) 실전 트레이딩 안전장치

이 레포는 투자 자문이 아니라 **시스템/아키텍처 템플릿**입니다.  
실전 투입 시 아래는 필수입니다:

- 거래소/브로커 규정 준수
- 주문/체결 실패 안전(fail-safe)
- 리스크 한도(손실/노출/연속손실/슬리피지) 게이트
- 모니터링/알림/롤백
- “리플레이 기반 회귀 테스트”로 승격 검증

체크리스트는 `docs/40_checklist.md` 참고.

---

## 5. 라이선스

MIT
