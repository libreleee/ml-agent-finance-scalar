# 고가용성/고성능 클러스터 구성 대안 지침 (현 프로젝트 기준)

본 문서는 현재 프로젝트(SeaweedFS + Hive Metastore + Trino + Spark + Superset + Grafana + OpenSearch + Streamlit)를 **고가용성(HA)** 및 **고성능(HPC)** 관점에서 구성하는 대안을 정리한다. 운영 환경을 전제로 하며, 로컬 Docker 구성은 개발/PoC 용으로만 사용한다.

## 1. 권장 아키텍처 방향

### A. Kubernetes 기반 (de facto standard)
- 장점: 표준화, 오토스케일, 생태계 풍부, 운영 자동화 용이
- 단점: 학습/운영 난이도 증가

### B. Hadoop/YARN 기반
- 장점: 기존 Hadoop 스택 조직에 최적화, Spark 운영 친화적
- 단점: 컨테이너 기반 유연성 부족, 현대 MLOps 스택 연동 어려움

### C. 혼합형 (Storage + Query는 클러스터, 시각화는 독립 노드)
- 장점: 시각화 계층을 분리하여 장애 영향 최소화
- 단점: 네트워크/보안 정책 관리 필요

---

## 2. 서비스별 HA/성능 대안

### 2.1 SeaweedFS (S3 계층)
- **HA 구성**
  - Master: 3노드 이상 (Raft 기반)
  - Filer: 다중 인스턴스 + 외부 메타스토어(예: etcd/redis)
  - Volume: 다중 노드 분산
- **성능 포인트**
  - SSD 스토리지 사용
  - S3 Gateway 앞단에 L7 Load Balancer 배치
  - 고정된 Access Key/Secret 관리

### 2.2 Hive Metastore
- **HA 구성**
  - Metastore 서비스 다중 인스턴스
  - 메타스토어 DB(Postgres/MySQL)는 **HA DB**(Patroni/Cloud RDS)
- **성능 포인트**
  - DB 튜닝(커넥션 풀링, 인덱스 최적화)

### 2.3 Trino
- **HA 구성**
  - Coordinator + Worker 다중 노드
  - Coordinator는 **활성/대기** 구조 또는 다중 coordinator + LB 구성
- **성능 포인트**
  - Worker 노드 수평 확장
  - 메모리/쿼리 큐 관리
  - 스토리지/메타스토어 네트워크 지연 최소화

### 2.4 Spark
- **HA 구성**
  - Kubernetes 또는 YARN 클러스터 위에서 운영
  - Spark History Server 별도 구성
- **성능 포인트**
  - Executor 수/메모리 조정
  - Shuffle 서비스 최적화

### 2.5 Superset
- **HA 구성**
  - 다중 웹 인스턴스 + Redis 캐시 + 외부 메타 DB
  - Reverse Proxy (Nginx/Ingress) + Load Balancer
- **성능 포인트**
  - 캐시 활성화, 병렬 쿼리 제한 설정

### 2.6 Grafana / Prometheus
- **HA 구성**
  - Grafana: 다중 인스턴스 + 외부 DB
  - Prometheus: 기본은 단일, 대규모면 Thanos/VMStack 고려
- **성능 포인트**
  - 스토리지 분리(SSD)

### 2.7 OpenSearch
- **HA 구성**
  - 3노드 이상 (master/data 분리)
  - Dashboards는 다중 인스턴스 가능
- **성능 포인트**
  - 인덱스 샤딩 전략
  - SSD 및 전용 JVM 튜닝

---

## 3. 운영 환경별 추천 시나리오

### 시나리오 1) Kubernetes 표준
- SeaweedFS: Helm Chart
- Trino: Helm Chart
- Spark: Spark Operator
- Superset/Grafana/OpenSearch: Helm

### 시나리오 2) Hadoop/YARN 표준
- HDFS + YARN + Spark
- Hive Metastore는 별도 HA DB
- Trino 클러스터 별도 배포

### 시나리오 3) 클라우드 관리형
- S3/Blob Storage
- Managed Spark (EMR/Dataproc)
- Managed OpenSearch/Elasticsearch
- Managed DB (RDS/Cloud SQL)

---

## 4. 권장 체크리스트 (운영 전)

- [ ] 메타스토어 DB HA 구성 여부
- [ ] S3/스토리지 계층 이중화
- [ ] Trino/Spark 클러스터 노드 수평 확장
- [ ] 모니터링/로깅 스택 통합
- [ ] 인증/권한/네트워크 보안 정책 정리

---

## 5. 결론

현업에서 가장 많이 사용하는 표준은 **Kubernetes 기반 Spark + Trino + S3 스토리지** 조합이다. 기존 Hadoop 인프라가 있다면 YARN을 유지하는 것이 현실적이며, 운영 안정성을 위해 시각화 계층(Superset/Grafana/OpenSearch Dashboards)은 데이터 계층과 분리 운영하는 것이 권장된다.

---

## 6. 하드웨어 구성 예시 (온프렘 기준)

> 아래 구성은 **중소~중견 규모** 기준 예시이며, 트래픽/데이터량에 따라 선형 확장한다.

### 6.1 서버 대수 및 역할 (예시)

- **Control Plane (K8s 마스터)**: 3대
  - 사양: 8 vCPU / 32GB RAM / 500GB SSD
- **Data/Compute 노드**: 6~12대
  - 사양: 32~64 vCPU / 128~256GB RAM / NVMe 2~4TB
- **Storage 노드 (SeaweedFS Volume 전용)**: 4~8대
  - 사양: 16~32 vCPU / 64~128GB RAM / HDD 20~80TB + SSD 캐시
- **Ops/Observability 노드**: 2대
  - 사양: 8~16 vCPU / 32~64GB RAM / SSD 1~2TB
- **Edge/Gateway 노드**: 2대
  - 사양: 8 vCPU / 16~32GB RAM / SSD 200~500GB

### 6.2 L4/L7 구성 (소프트웨어/하드웨어)

- **L4 (TCP 로드밸런서)**  
  - 권장: **HAProxy/Keepalived(소프트웨어)**  
  - 대규모/보안 요구 시: F5/AVI 등 **하드웨어 L4**
- **L7 (HTTP/HTTPS 리버스 프록시)**  
  - 권장: **Nginx/Envoy/Traefik(소프트웨어)**  
  - TLS 종료/인증서 관리 + WAF 연동 고려

> 현실적으로는 L4+L7 모두 소프트웨어가 대부분이며, 하드웨어는 대규모 트래픽이나 보안 규정이 있을 때만 사용.

---

## 7. 네트워크 구성 예시 (상세)

### 7.1 네트워크 분리 (VLAN/서브넷)

- **VLAN 10 (관리망)**: K8s Control Plane, 모니터링, 운영자 접근
- **VLAN 20 (데이터망)**: Spark/Trino/SeaweedFS 내부 통신
- **VLAN 30 (서비스망)**: Superset/Grafana/OpenSearch Dashboards 외부 노출
- **VLAN 40 (스토리지망)**: Volume 노드 간 복제/IO 전용

### 7.2 권장 대역폭

- **데이터망/스토리지망**: 25GbE 이상 권장 (최소 10GbE)
- **관리망/서비스망**: 1~10GbE

### 7.3 포트/접근 흐름 (핵심)

- 외부 → L7 → (Superset/Grafana/OpenSearch Dashboards/Streamlit)
- 내부 → Trino (Coordinator → Worker)
- Spark → SeaweedFS S3 (S3 Gateway)
- Hive Metastore ↔ Postgres (메타 DB)
- 모니터링 → 모든 서비스 메트릭

---

## 8. 네트워크 구성도 (텍스트 다이어그램)

```
           [ Internet / User ]
                   |
               [ L7 LB ]
          (Nginx/Envoy/Traefik)
                   |
     +-------------+-------------+
     |             |             |
 [Superset]   [Grafana]   [OpenSearch Dashboards]
     |             |             |
     +-------------+-------------+
                   |
             [ L4 LB ]
            (HAProxy/Keepalived)
                   |
        +----------+----------+
        |                     |
   [Trino Coord]        [OpenSearch Cluster]
        |                     |
   [Trino Workers]      [OpenSearch Data Nodes]
        |
   [Spark Cluster]
        |
   [SeaweedFS S3 Gateway] --- [SeaweedFS Filer/Master]
        |
   [SeaweedFS Volume Nodes]
        |
   [Postgres (Metastore DB)]
```

---

## 9. 운영 팁 (현 프로젝트 매핑)

- **Spark**: 항상 실행되는 클러스터(K8s/YARN) 위에 잡 제출
- **Trino**: Coordinator 1 + Worker N (N은 스케일 기준)
- **SeaweedFS**: Master 3 + Filer 2 + Volume 다수
- **Superset/Grafana/OpenSearch Dashboards**: L7 뒤에서 다중 인스턴스

---

## 10. 요약

- **서버 대수**: 최소 3(컨트롤) + 6(컴퓨트) + 4(스토리지) + 2(운영) + 2(게이트웨이)
- **L4/L7**: 대부분 소프트웨어(HAProxy + Nginx/Envoy), 고규모 시 하드웨어 고려
- **네트워크 분리**: 관리/서비스/데이터/스토리지 네트워크 분리 권장

---

## 11. 서버/서비스 배치 요약 (Docker + Kubernetes 기준)

> 모든 서비스는 **컨테이너(Docker 이미지)**로 패키징하고, **Kubernetes** 위에서 배포한다는 가정이다.

### 11.1 노드 구성 및 서비스 매핑 (한눈에 보기)

| 노드 그룹 | 대수(예시) | 주요 서비스(컨테이너) | 비고 |
|---|---:|---|---|
| K8s Control Plane | 3 | kube-apiserver, etcd, controller-manager, scheduler | 고가용성 필수 |
| Edge/LB | 2 | Nginx/Envoy/Traefik, HAProxy/Keepalived | L7/L4 엔드포인트 |
| Observability | 2 | Prometheus, Grafana, Loki/ELK(선택) | 모니터링 전용 |
| Storage (SeaweedFS) | 4~8 | seaweedfs-master, seaweedfs-filer, seaweedfs-volume, seaweedfs-s3 | Master/Filer는 다중 인스턴스 |
| Metadata DB | 2~3 | Postgres(HA) / Patroni | Hive Metastore DB |
| Query (Trino) | 3~10 | trino-coordinator(1), trino-worker(N) | N은 워크로드 기준 |
| Compute (Spark) | 6~12 | spark-driver, spark-executor | Spark on K8s |
| Visualization | 3~6 | superset, opensearch-dashboards, streamlit | 필요 시 수평 확장 |
| Search (OpenSearch) | 3~9 | opensearch-master, opensearch-data | master/data 분리 권장 |

### 11.2 최소 구성 예시 (총 12~16대)

- Control Plane 3대  
- Edge/LB 2대  
- Storage 4대  
- Query/Compute 4~6대  
- Observability 1~2대  

### 11.3 중형 구성 예시 (총 24~32대)

- Control Plane 3대  
- Edge/LB 2대  
- Storage 6~8대  
- Query 6~8대  
- Compute 8~12대  
- Observability 2대  
- Search 3~5대  

---

## 12. 실제 배치 시 체크포인트

- 모든 서비스는 **Docker 이미지**로 빌드 후 **K8s 배포(Helm/Operator)**로 운영
- L4/L7는 **전용 노드에서 실행**하고 내부망과 외부망을 분리
- Trino/Spark는 **컴퓨트 노드 풀**을 분리하여 스케줄링
- OpenSearch는 **전용 스토리지 노드**에 배치 권장

---

## 13. 최소 서버 수 구성 (서비스 공존 허용)

> 최소 서버 수를 목표로 할 경우 **고가용성/성능은 제한**된다.  
> 장애 허용이 어렵고 유지보수 창(점검 시간)이 필요하다.

### 13.1 최소 구성 A (6대, 소규모)

- **노드1 (Control+Edge)**: K8s Control Plane + L4/L7 (HAProxy/Nginx)
- **노드2 (Control)**: K8s Control Plane
- **노드3 (Control)**: K8s Control Plane
- **노드4 (Compute+Query)**: Spark Executors + Trino Worker + Superset/Streamlit
- **노드5 (Storage)**: SeaweedFS Volume + S3 Gateway + Hive Metastore
- **노드6 (Search+Obs)**: OpenSearch + Grafana/Prometheus

### 13.2 최소 구성 B (8대, 운영 안정성 확보)

- **노드1~3**: K8s Control Plane
- **노드4~5**: Compute/Query (Spark + Trino)
- **노드6**: Storage (SeaweedFS + Hive Metastore)
- **노드7**: Search (OpenSearch)
- **노드8**: Visualization + Observability (Superset/Grafana/Prometheus)

### 13.3 서비스 공존 허용 목록

| 서비스 조합 | 공존 가능 여부 | 비고 |
|---|---|---|
| Superset + Streamlit | 가능 | 저부하 환경 OK |
| Trino Worker + Spark Executor | 제한적 가능 | 메모리 경쟁 주의 |
| OpenSearch + Grafana/Prometheus | 가능 | 디스크/CPU 여유 필요 |
| SeaweedFS Volume + Metastore | 제한적 가능 | IO 병목 가능 |
| L4/L7 + Control Plane | 가능 | 장애 시 전체 영향 |

> 최소 구성은 **개발/PoC**에 적합하며, 운영 환경은 최소 12대 이상 권장.

---

## 14. HA 관점 분리 운영 권장 서비스

- **스토리지 계층**: SeaweedFS Volume/Master/Filer, S3 Gateway
- **메타데이터 DB**: Hive Metastore DB(Postgres/MySQL)
- **쿼리 엔진**: Trino Coordinator, Trino Worker
- **검색/인덱싱**: OpenSearch (master/data 노드)
- **분산 컴퓨트**: Spark Driver/Executor
- **모니터링 핵심**: Prometheus (대규모 환경 기준)
- **시각화 계층**(Superset/Grafana/Streamlit)은 공존 가능하지만, 운영 안정성을 원하면 분리 권장

### Kafka (HA 기준)

- **Kafka 브로커**: 전용 노드 권장 (IO/네트워크 민감)
- **컨트롤러(KRaft) 또는 Zookeeper**: 별도 노드 권장
- **Kafka Connect**: 별도 노드 권장 (대량 ingest 시 필수)

> HA를 목표로 하면 Kafka는 다른 서비스와 공존하지 않는 것이 정석이다.

