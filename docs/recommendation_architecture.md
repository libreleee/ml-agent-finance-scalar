# 권장 아키텍처 및 기술 스택 요약 (요약본)

> 본 문서는 신뢰성, 안정성, 유지보수성, 현업 채택률을 기준으로 한 추천 스택을 요약합니다.

---

## 핵심 권장 스택 (de facto standard) ✅
- 스토리지: **S3 (cloud)** 또는 **Ceph RGW (on‑prem)**
  - 이유: S3 호환 인터페이스는 에코시스템 전반의 사실상 표준.
  - 주의: 2025년 일부 S3 구현의 오픈소스 정책 변경(예: MinIO)으로 장기적 리스크 존재 → **Ceph(RGW)를 주 권장(온프레)**

> **참고:** 본 문서는 Ceph(RGW)를 우선 권장하는 관점으로 작성되었습니다. 아래의 기타 오픈소스 대안들은 참고용으로만 열거되어 있으며, 프로덕션 도입 시 Ceph 검토를 우선 권장합니다.
  
  ### Ceph가 담당하는 레이어 (짧은 설명)
  - 객체 저장: Iceberg/Parquet 등 테이블 파일을 안전하게 보관하는 객체 스토리지입니다.
  - 데이터 내구성/복제: OSD/RADOS 레이어에서 복제 또는 erasure coding으로 내구성을 제공합니다.
  - RGW(S3 API): 서비스(Glue/Hive/Spark/Trino/앱)가 사용하는 S3 호환 엔드포인트를 제공합니다.
  - 운영·모니터링: 모니터링(Prometheus), OSD 관리, 스케일링 및 장애 복구 등의 운영 책임을 집니다.

- 테이블 포맷: **Apache Iceberg** (ACID, 시간여행, 멀티엔진 지원)
- 메타/카탈로그: **Hive Metastore** (오픈 표준), 데이터 카탈로그: **Amundsen / DataHub**

- 처리 엔진: **Apache Spark** (배치) + **Apache Flink** (실시간)
- 분산 SQL: **Trino** (Iceberg와 상호운용성 우수)

- ML/DL: **PyTorch** (모델 개발), 분산 학습 도구: **Ray / DeepSpeed / Horovod**
- MLOps: **MLflow**(실험 추적·레지스트리) + **Feast**(피쳐스토어)

- 오케스트레이션: **Apache Airflow** (배치 워크플로우) + **Argo Workflows / ArgoCD** (K8s GitOps)
- 서빙: **KServe / BentoML / Seldon Core**

- 플랫폼: **Kubernetes**(컨테이너 오케스트레이션)
- 모니터링: **Prometheus + Grafana**, 로깅: **ELK / OpenTelemetry**

- 벡터 검색(임베딩): **Milvus / Weaviate** (또는 관리형 Pinecone)

---

## 왜 이 구성이 좋은가 (핵심 포인트) 🎯
- 널리 채택되어 생태계 지원·문서·툴이 풍부합니다.
- 확장성·내구성·운영성(모니터링·백업·복구) 관점에서 검증된 조합입니다.
- Iceberg + Hive Metastore + Trino 조합은 다양한 쿼리/처리 엔진에서 데이터 레이크를 안정적으로 공유할 수 있게 해줍니다.

---

## 이 리포지토리(프로젝트)와 매핑 — 우선 권장 작업 목록 🔧
1. **기존 S3 기반 스토어 → Ceph(RGW) 전환 준비**
   - 작성된 `docs/ceph-migration.md`를 기반으로 단계 수행
2. **설정 일관화**
   - `hive-site.xml`, `python/fspark.py`, `trino-config/*`에서 S3 엔드포인트/자격증명/`warehouse` 경로 통일 (권장: `s3a://lakehouse/warehouse/`)
3. **카탈로그/테이블 포맷 표준화**
   - Iceberg 사용으로 표준화(이미 사용 중) — 버전 호환성 점검
4. **CI/오케스트레이션 준비**
   - Airflow / Argo 연계 시 pipeline 예시 스크립트 추가
5. **MLOps 준비 (옵션)**
   - `mlflow` 서비스 docker-compose 항목 추가 또는 K8s 배포 템플릿 추가
6. **보안 및 운영**
   - TLS(HTTPS) 적용, 키/시크릿 관리(Secrets), 모니터링(dashboards)
   - **키 주입 원칙:** RGW가 준비된 뒤 사용자(access/secret)를 생성하고 Vault/K8s Secret/Docker Secret으로 보관한 후 서비스에 안전하게 주입하세요. 키는 절대 코드에 커밋하지 마십시오.

---

## 빠른 체크리스트 (테스트/검증) ✅
- [ ] RGW(S3) 접근: `aws --endpoint-url http://RGW:PORT s3 ls`
- [ ] Hive 메타에서 `s3a://lakehouse/warehouse/` 접근 확인
- [ ] Spark에서 `SHOW DATABASES IN hive_prod` 정상 동작
- [ ] Trino에서 Iceberg 테이블 쿼리 확인
- [ ] 간단한 DF 쓰기/읽기 테스트(테이블 생성 → SELECT)

---

## 다음 제안 (우선순위)
1. `docker-compose.yml` 백업 → 이전 S3 서비스 제거(또는 주석 처리) → 새 compose 파일 생성(외부 RGW 사용 권장) — 제가 자동으로 수행 가능
2. 구성 파일들(hive-site.xml, fspark.py, trino) 자동 동기화 및 테스트 스크립트 추가
3. MLflow/Feast 등의 MLOps 컴포넌트 추가 제안서 작성

---

원하시면 다음 작업(예: `docker-compose.yml` 백업 및 변환)을 바로 수행하겠습니다. 어떤 것을 먼저 실행할까요?

---

## 참고 — 기타 오픈소스 대안 (참고용)
아래는 Ceph(RGW)를 우선 권장하는 관점에서 **참고용**으로 열거한 오픈소스 대안들입니다. 실제 도입 검토 시에는 Ceph를 우선 검토하세요.

- **Ceph (RGW)**
  - 장점: 엔터프라이즈급 내구성·복제·운영 기능, 멀티테넌시 지원
  - 단점: 운영 복잡도·운영 리소스 필요
  - 권장: 대규모 온프레/장기 운영, DR·리전 복제 등 고가용성 요구 시


- **SeaweedFS + S3 gateway**
  - 장점: 매우 경량·수평 확장 쉬움, 빠른 배포, 낮은 운영비, 분산 파일 시스템 기능 포함 (Filer, Volume, Master 컴포넌트)
  - 단점: Ceph 수준의 고급 정책·복제 기능은 제한적
  - 권장: 비용 민감한 소규모 온프레 환경, 단순 파일 스토리지 목적, 빠른 테스트/개발

- **Garage (오픈소스 S3 호환 스토리지 프로젝트)**
  - 장점: 가벼운 분산 S3 호환 스토리지로 빠른 테스트/배포용으로 적합, 커뮤니티 구성 요소(Operator/UI 등) 존재
  - 단점: 프로젝트 성숙도 및 커뮤니티 규모가 상대적으로 작아 엔터프라이즈 지원/장기 운영 시 추가 검증 필요
  - 권장: 소규모 온프레나 PoC, S3 호환 간단 테스트 목적

- **OpenStack Swift + Swift3 / s3proxy**
  - 장점: 오랜 기간 운영된 오픈소스 객체 스토리지, 검증된 설치 사례 다수
  - 단점: 설정·운영 복잡도는 다소 있음
  - 권장: 기존 OpenStack 환경 통합 시

- **K8s 네이티브 오퍼레이터(예: Garage/SeaweedFS Operator)**
  - 장점: Kubernetes 환경에서 S3 호환 스토리지 운영 자동화, 빠른 롤아웃
  - 단점: 프로젝트별 지원 수준 차이 존재
  - 권장: K8s 기반의 민첩한 개발/테스트/소규모 프로덕션
### 선택 가이드 (한줄 요약)
- 대규모·엔터프라이즈 온프레: **Ceph**
- 경량·빠른 배포 / 소규모: **Garage** 또는 **SeaweedFS**
- OpenStack 통합: **Swift**
- Kubernetes 네이티브: **K8s 네이티브 오퍼레이터(예: Garage/SeaweedFS Operator)**

---

원하시면 이 중 2개 후보(오픈소스)를 골라 `docker-compose` 또는 `k8s` 배포 예시 및 테스트 스크립트를 생성해 드리겠습니다.

- 관리형 S3 (권장)
  - 예: **AWS S3**, **Google Cloud Storage**, **Azure Blob Storage**
  - 장점: 운영 부담 최소(SLA·보안·백업·스케일 자동화), 광범위한 생태계 호환성
  - 권장 사용처: 운영 부담을 줄이고 안정성을 우선시하는 경우

- 경량 Self-hosted
  - **Garage / SeaweedFS (S3 gateway)**
    - 장점: 설치·운영 간단, S3 호환, 경량·수평 확장 쉬움
    - 단점: Ceph 수준의 고급 정책·복제 기능은 제한적
    - 권장 사용처: 개발/테스트, 소규모 프로덕션, 비용 민감한 온프레 환경

- Kubernetes 네이티브 경량 옵션
  - **K8s 오퍼레이터(예: Garage/SeaweedFS Operator)**
  - 장점: k8s 네이티브 배포 및 관리, 빠른 롤아웃
  - 권장 사용처: Kubernetes 기반 인프라에서 민첩하게 시작할 때

- 상용 온프레 엔터프라이즈
  - 예: **Scality RING**, **Cloudian HyperStore**, **NetApp Object 솔루션**
  - 장점: 엔터프라이즈 지원·통합 기능, 운영 편의성
  - 단점: 높은 비용, 벤더 종속성
  - 권장 사용처: 대규모 온프레/레거시 통합이 필요한 경우

- 저비용 S3 호환 서비스
  - 예: **Backblaze B2**, **Wasabi**, **DigitalOcean Spaces**
  - 장점: 저렴한 스토리지 비용(장기 보관에서 경제적)
  - 권장 사용처: 아카이빙, 비용 최적화가 중요한 워크로드

### 선택 가이드 (한줄 요약)
- 운영 부담 최소화/신뢰성: **관리형 S3**
- 빠른 테스트/소규모 운영: **Garage** 또는 **SeaweedFS** (로컬 경량 대안)
- 비용/단순 확장 우선: **SeaweedFS** 또는 **저비용 S3 서비스**
- 엔터프라이즈 온프레 장기 운영: **Ceph** 또는 **상용 온프레 솔루션**

---

원하시면 이 중 2개 후보를 골라 `docker-compose` 또는 `k8s` 배포 예시 및 테스트 스크립트를 생성해 드리겠습니다.

---

## 현재 프로젝트 선택: SeaweedFS
본 프로젝트에서는 Ceph의 복잡성으로 인해 **SeaweedFS**를 로컬 테스트용 S3 호환 스토리지로 선택했습니다.
- **구성**: Master, Volume, Filer, S3 게이트웨이 컴포넌트로 구성.
- **엔드포인트**: http://localhost:8333 (S3 API)
- **키**: seaweedfs_access_key / seaweedfs_secret_key (테스트용)
- **장점**: Docker로 쉽게 실행, 파일 시스템 기능 포함, 빠른 시작.
- **참고**: 프로덕션에서는 외부 Ceph 클러스터 권장.