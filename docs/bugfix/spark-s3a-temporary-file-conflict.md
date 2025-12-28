# Spark S3A `_temporary` 파일 충돌로 JSON 저장 실패 (Bugfix 기록)

## 개요

Spark가 SeaweedFS(S3)로 JSON 로그를 저장하는 과정에서 `_temporary` 경로가 **파일로 남아** 디렉터리 생성이 실패하며 작업이 중단되는 문제가 발생했다.

---

## 1) 증상

실행 중 아래 에러로 중단:

```
org.apache.hadoop.fs.FileAlreadyExistsException: Can't make directory for path
's3a://lakehouse/raw/logs/date=YYYY-MM-DD/_temporary' since it is a file.
```

---

## 2) 원인

이전 실행이 비정상 종료되면서 `_temporary` 경로가 **파일 형태로 남음**.  
Spark는 쓰기 작업 시작 시 `_temporary` 디렉터리를 생성하는데, 파일이 이미 존재해 실패한다.

---

## 3) 조치

- Spark 실행 전에 `_temporary` 경로를 자동 삭제하도록 소스에 정리 로직 추가
- 실패 시 경고 로그만 출력하고 진행

---

## 4) 수정 전/후 소스

### 수정 전 (발췌)

```python
raw_json_path = "s3a://lakehouse/raw/logs/date={date}/".format(date=datetime.utcnow().strftime('%Y-%m-%d'))

# 샘플 반정형 데이터
sample_logs = [
    ...
]

df_logs = spark.createDataFrame(sample_logs)
df_logs.write.mode("append").json(raw_json_path)
```

### 수정 후 (발췌)

```python
raw_json_path = "s3a://lakehouse/raw/logs/date={date}/".format(date=datetime.utcnow().strftime('%Y-%m-%d'))

# Clean up leftover _temporary marker from previous failed writes (S3A treats it as a file)
try:
    jconf = spark._jsc.hadoopConfiguration()
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(
        spark._jvm.java.net.URI(raw_json_path),
        jconf,
    )
    temp_path = spark._jvm.org.apache.hadoop.fs.Path(raw_json_path + "_temporary")
    if fs.exists(temp_path):
        fs.delete(temp_path, True)
        print("정리됨: 이전 _temporary 경로 삭제 ->", temp_path)
except Exception as e:
    print("경고: _temporary 정리 실패 ->", e)

# 샘플 반정형 데이터
sample_logs = [
    ...
]

df_logs = spark.createDataFrame(sample_logs)
df_logs.write.mode("append").json(raw_json_path)
```

---

## 5) 적용 파일

- `python/fspark_raw_examples.py`

---

## 6) 참고

S3A 커밋 과정에서 `_temporary`는 정상적으로 생성/삭제되는 임시 경로다.  
비정상 종료 시 파일이 남으면 동일 prefix에 대한 다음 쓰기 작업이 실패할 수 있다.
