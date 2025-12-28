import os

from pyiceberg.catalog import load_catalog


def get_iceberg_table(table_name: str):
    catalog = load_catalog(
        "default",
        **{
            "type": "hive",
            "uri": os.getenv("HIVE_METASTORE_URI", "thrift://hive-metastore:9083"),
            "s3.endpoint": os.getenv("AWS_ENDPOINT_URL_S3", "http://seaweedfs-s3:8333"),
            "s3.access-key-id": os.getenv("AWS_ACCESS_KEY_ID", "seaweedfs_access_key"),
            "s3.secret-access-key": os.getenv(
                "AWS_SECRET_ACCESS_KEY", "seaweedfs_secret_key"
            ),
            "s3.path-style-access": "true",
        },
    )
    return catalog.load_table(table_name)
