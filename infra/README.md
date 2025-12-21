# Infra

## 구성
- MLflow(5000) + MinIO(9000/9001)
- Redis(6379)
- ClickHouse(8123, 9000 -> compose에서 9002로 노출)

## 실행
```bash
docker compose up -d
```

## ClickHouse 스키마 적용
```bash
bash infra/init_clickhouse.sh
```
