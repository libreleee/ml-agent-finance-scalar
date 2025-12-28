# 데이터 저장 아키텍처 (Lakehouse)

## 1. 메타데이터 계층
- Apache Iceberg는 테이블의 스키마, 파티션, 스냅샷, manifest 리스트 등을 `metadata` 디렉터리에 JSON/AVRO 파일 형태로 유지합니다.
- 예: `/tmp/iceberg_warehouse/option_ticks_db/bronze_option_ticks/metadata/v2.metadata.json`에는 현재 스키마·파티션 선언과 최신 스냅샷 정보가 들어 있고, `snap-*.avro`와 `*.metadata.json`이 시간 순서를 기록합니다.
- 이 메타데이터는 Hive Metastore(카탈로그)와 연결되어 Spark/Trino 같은 엔진이 동일한 테이블 구성과 스냅샷 히스토리를 읽을 수 있게 합니다.

## 2. 데이터 파일 계층
- 실제 레코드는 Parquet 파일로 저장됩니다.
- 경로 예시: `/tmp/iceberg_warehouse/option_ticks_db/bronze_option_ticks/data/timestamp_day=2025-12-22/00000-*.parquet`.
- Iceberg의 파티션(`timestamp_day`)에 따라 디렉터리가 분리되고, 각 파일은 `metadata`에 등록되어 트랜잭션적으로 사용됩니다.

## 3. 테스트/개발 환경 저장 옵션
- **로컬 디스크 (`file:///tmp/...`)**
  - 지금까지 `fspark.py` 테스트에서는 Iceberg warehouse를 `/tmp/iceberg_warehouse`에 두고 로컬 Parquet/metadata로 작동시켰습니다.
  - 단일 노드 개발에서는 빠르고 직관적이지만, 노드 재기동 시 데이터가 날아가거나 여러 노드 공유가 어려운 한계가 있습니다.
- **SeaweedFS S3 (s3a://lakehouse/warehouse)**
  - Docker Compose에 SeaweedFS Master/Volume/Filer/S3 서비스가 구성되어 있고, S3 gateway `http://localhost:8333`를 통해 객체 API를 제공합니다.
  - Iceberg의 warehouse URI와 Spark `fs.s3a.*` 설정을 S3 gateway에 맞추면 실제 테이블 데이터와 metadata를 S3 호환 저장소로 옮길 수 있습니다.
  - SeaweedFS는 테스트 불가피한 환경에서 S3 API를 가장 가볍게 구현하는 방식입니다.

## 4. 프로덕션/공유 환경 저장 옵션
- **진짜 S3 (AWS, GCS, Azure)**, **Ceph RGW**, **MinIO**, **Garage** 등 S3 호환 서비스로 warehouse를 지정하는 것이 기본입니다.
- Iceberg에서 `fs.s3a.endpoint`, `io-impl=org.apache.iceberg.aws.s3.S3FileIO`, `spark.hadoop.fs.s3a.*`를 일치시켜 객체 스토리지에 메타/데이터를 쓰게 됩니다.
- Hive Metastore는 S3 URI(`s3a://lakehouse/warehouse/`)를 사용해 테이블을 바라보고, Spark/Trino가 동일한 경로를 공유합니다.
- 객체 스토리지는 내구성과 확장성 측면에서 로컬보다 유리하며, SeaweedFS는 내부 S3 gateway로 이 옵션을 에뮬레이션합니다.

## 5. 정리
1. **메타데이터**는 Iceberg metadata 파일 + Hive Metastore 카탈로그에 저장됨.
2. **데이터**는 Parquet 파일로 Parquet/Manifest 등록되고 파티션 디렉터리에 분리됨.
3. **현재 테스트**는 로컬 `/tmp/iceberg_warehouse`를 사용했으며, SeaweedFS S3 gateway로 확장 가능.
4. **프로덕션에서는 S3/SeaweedFS/MinIO/Ceph RGW 같은 객체 스토리지를 일관되게 사용**해야 다중 엔진 공유와 내구성을 확보할 수 있음.

## 6. 스토리지 옵션 요약
- **로컬 파일 시스템 (file://)**: 단일 노드 개발/테스트에서 가장 단순. `/tmp` 같은 위치를 warehouse로 지정하면 Iceberg metadata와 Parquet 데이터를 빠르게 생성할 수 있지만 여러 워커나 컨테이너 간 공유는 별도 네트워크 드라이브가 필요합니다.
- **SeaweedFS (S3 compatible)**: 현재 구성. Docker Compose 내 SeaweedFS S3 게이트웨이(`http://localhost:8333`)를 통해 `fs.s3a.*` 설정만 맞추면 객체 스토리지처럼 동작합니다. 가볍고 설치/스케일이 쉬운 반면 Ceph 수준의 고급 기능(정책, 복제, 모니터링)은 직접 구축해야 함.
- **Ceph RGW / MinIO / Garage 등 온프레 S3 호환**: Iceberg/Hive 설정에서 `s3a://lakehouse/warehouse/`를 지정하고 `fs.s3a.endpoint`, 자격증명을 서비스에 주입하면 됩니다. S3 API를 그대로 활용하므로 대다수 클라우드 서비스와 호환됩니다.
- **관리형 퍼블릭 S3 (AWS/GCP/Azure)**: 운영 부담을 줄이고 SLA를 확보하는 실전 경로. 별도 운영 없이 Iceberg warehouse만 S3 경로로 바꾸면 되며, Vault 또는 Secrets Manager로 자격증명 관리하세요.
- **공유 Hadoop/HDFS 또는 NFS**: `hdfs://` 또는 `file:///mnt/share`와 같은 공유 스토리지를 Hive catalog가 읽도록 구성하면 Iceberg 테이블을 공유할 수 있습니다. `io-impl=org.apache.iceberg.hadoop.HadoopFileIO`로 설정해 Hadoop FileSystem을 활용합니다.
- **데이터베이스 전용 카탈로그 + 객체파일(예: Postgres catalog + local/NFS data)**: Iceberg catalog만 Postgres 등에 두고 실제 파일은 local/NFS/S3로 분리하면 메타/데이터를 유연하게 독립 운영 가능합니다.

필요한 스토리지를 선택할 때 목적(테스트 vs. 프로덕션), 운영 리소스, 내구성 요구를 고려해 위 옵션 중 적절한 조합을 고르면 됩니다.

필요하면 이 흐름도를 기반으로 `docker-compose` 또는 스크립트에 SeaweedFS/S3 설정을 추가해 드릴 수도 있습니다.