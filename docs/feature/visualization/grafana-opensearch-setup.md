# Grafana 대시보드 및 OpenSearch 설정 가이드

본 문서는 로컬 환경에서 Grafana와 OpenSearch를 연동하고, 기본 대시보드 확인까지 진행하는 절차를 정리한다.

## 1. 사전 확인

- Grafana: http://localhost:3000
- OpenSearch: http://localhost:9200
- OpenSearch Dashboards: http://localhost:5601
- Prometheus: http://localhost:9090

## 2. Grafana 로그인

- ID: `admin`
- Password: `.env`의 `GRAFANA_PASSWORD` 값

## 3. Grafana 데이터 소스 설정

### 3.1 Prometheus 데이터 소스 확인

1. Grafana 접속 → 좌측 **Connections** → **Data sources**
2. 목록에 `Prometheus`가 있는지 확인
3. 없으면 **Add data source** → **Prometheus** 선택
4. URL: `http://prometheus:9090`
5. **Save & Test** 클릭

### 3.2 OpenSearch 데이터 소스 설정

1. Grafana 접속 → 좌측 **Connections** → **Data sources**
2. 목록에 `OpenSearch`가 있는지 확인
3. 없으면 **Add data source** → **OpenSearch** 선택
4. URL: `http://opensearch:9200`
5. Access: `Server` 유지
6. **Save & Test** 클릭

> 참고: OpenSearch 보안 플러그인을 비활성화한 로컬 구성이라 인증 정보는 불필요함.

## 4. Grafana 대시보드 확인 방법

### 4.1 기본 테스트 패널 생성 (Prometheus)

1. **Dashboards** → **New** → **New dashboard**
2. **Add visualization**
3. Data source에서 `Prometheus` 선택
4. Query에 `up` 입력
5. 그래프가 표시되면 정상

### 4.2 OpenSearch 연결 테스트

1. **Connections** → **Data sources** → `OpenSearch`
2. **Save & Test** 결과가 `OK`이면 정상

## 5. OpenSearch Dashboards 확인

1. 접속: http://localhost:5601
2. 상단 메뉴 **Stack Management** → **Index Patterns**
3. 인덱스가 없으면, OpenSearch에 데이터 인덱싱 후 생성

## 6. 자주 발생하는 문제

- Grafana 접속 불가
  - `docker compose ps`로 `grafana` 컨테이너 상태 확인
  - 3000 포트 점유 여부 확인: `ss -lntp | rg 3000`

- OpenSearch unhealthy
  - `curl -s http://localhost:9200` 응답 확인
  - healthcheck가 HTTPS로 설정되어 있으면 HTTP로 수정 필요

## 7. 확인 체크리스트

- [ ] Grafana 접속 가능 (http://localhost:3000)
- [ ] Prometheus 데이터 소스 연결 성공
- [ ] OpenSearch 데이터 소스 연결 성공
- [ ] 대시보드에서 `up` 메트릭 확인
- [ ] OpenSearch Dashboards 접속 가능 (http://localhost:5601)
