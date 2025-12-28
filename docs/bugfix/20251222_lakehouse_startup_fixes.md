# Lakehouse Stack 초기 구축 버그 수정 리포트

**날짜:** 2025-12-22
**작성자:** GitHub Copilot

---

## 1. Hive Metastore JDBC 드라이버 누락 문제

### 증상
`hive-metastore` 컨테이너가 시작 직후 종료되며, 로그에 `java.lang.ClassNotFoundException: org.postgresql.Driver` 에러 발생.

### 원인
Apache Hive 4.0.0 기본 이미지에는 PostgreSQL 연결을 위한 JDBC 드라이버가 포함되어 있지 않음.

### 조치
1. 호스트의 `./hive-jars/` 디렉토리에 `postgresql-42.5.4.jar` 파일을 다운로드.
2. `docker-compose.yml`에서 해당 파일을 컨테이너 내부의 라이브러리 경로로 마운트.

### 수정 파일 및 위치
- **파일명:** [docker-compose.yml](docker-compose.yml)
- **라인:** [L46](docker-compose.yml#L46)
  ```yaml
  - ./hive-jars/postgresql-42.5.4.jar:/opt/hive/lib/postgresql.jar
  ```

---

## 2. Spark-Iceberg 컨테이너 즉시 종료 문제

### 증상
`spark-iceberg` 컨테이너가 실행된 후 아무런 에러 메시지 없이 즉시 종료됨.

### 원인
`docker-compose.yml`의 `command` 설정이 리스트 형식으로 되어 있어, 이미지의 `entrypoint.sh`가 전체 명령어를 인식하지 못하고 첫 번째 인자만 실행하고 종료됨.

### 조치
전체 명령어를 하나의 문자열로 묶고 `bash -lc`를 통해 실행하도록 수정하여 환경 변수 로드 및 프로세스 유지를 보장함.

### 수정 파일 및 위치
- **파일명:** [docker-compose.yml](docker-compose.yml)
- **라인:** [L81-L82](docker-compose.yml#L81-L82)
  ```yaml
  command:
    - "bash -lc \"jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token='' --NotebookApp.password='' --NotebookApp.allow_origin='*' --NotebookApp.notebook_dir='/home/iceberg'\""
  ```

---

## 3. Postgres 헬스체크 DB 접속 에러

### 증상
Postgres 컨테이너 로그에 `FATAL: database "hive" does not exist` 메시지가 반복적으로 출력됨.

### 원인
`pg_isready` 명령어가 기본적으로 사용자 이름과 동일한 데이터베이스(`hive`)에 접속을 시도했으나, 실제 생성된 DB 이름은 `metastore`였음.

### 조치
헬스체크 명령어에 `-d metastore` 옵션을 추가하여 명시적으로 데이터베이스를 지정함.

### 수정 파일 및 위치
- **파일명:** [docker-compose.yml](docker-compose.yml)
- **라인:** [L30](docker-compose.yml#L30)
  ```yaml
  test: ["CMD", "pg_isready", "-U", "hive", "-d", "metastore"]
  ```

---

## 4. 서비스 시작 순서 및 의존성 최적화

### 증상
DB나 스토리지(MinIO)가 완전히 준비되기 전에 상위 서비스(Hive, Spark)가 시작되어 연결 실패 발생.

### 원인
단순한 `depends_on`은 컨테이너의 '실행'만 보장할 뿐, 내부 서비스의 '준비 완료' 상태를 보장하지 않음.

### 조치
각 서비스에 `healthcheck`를 추가하고, `depends_on`에 `condition: service_healthy` 설정을 적용함.

### 수정 파일 및 위치
- **파일명:** [docker-compose.yml](docker-compose.yml)
- **주요 라인:**
    - MinIO 헬스체크: [L16-L20](docker-compose.yml#L16-L20)
    - Postgres 헬스체크: [L28-L33](docker-compose.yml#L28-L33)
    - Hive 의존성: [L38-L42](docker-compose.yml#L38-L42)
    - Spark 의존성: [L60-L64](docker-compose.yml#L60-L64)
