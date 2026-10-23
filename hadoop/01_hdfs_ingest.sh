#!/usr/bin/env bash
# EarthScape – load raw climate data into HDFS with a partitioned layout
#   /earthscape/raw/<source>/year=YYYY/month=MM/region=<region>/part.csv
# Partitioning by year/month/region lets Hive/Impala/Spark prune folders and read only what a query needs.
set -e
LOCAL=${1:-../data/sample_dataset.csv}
BASE=/earthscape
hdfs dfs -mkdir -p $BASE/raw $BASE/curated $BASE/stream $BASE/models $BASE/archive
hdfs dfs -setrep -R 3 $BASE                      # 3 replicas = fault tolerance
python3 - "$LOCAL" <<'PY'
import sys, os, pandas as pd
df = pd.read_csv(sys.argv[1]); df["year"] = df.date.str[:4]; df["month"] = df.date.str[5:7]
for (src, y, m, r), g in df.groupby(["source", "year", "month", "region"]):
    d = f"/tmp/earthscape_parts/{src}/year={y}/month={m}/region={r.replace(' ', '_')}"; os.makedirs(d, exist_ok=True)
    g.drop(columns=["year", "month"]).to_csv(f"{d}/part-0000.csv", index=False, header=False)
print("partitions written")
PY
hdfs dfs -put -f /tmp/earthscape_parts/* $BASE/raw/
hdfs dfs -put -f ../data/stations.csv $BASE/curated/
hdfs dfs -du -h $BASE/raw | head -20
echo "HDFS ingestion complete"
