#!/usr/bin/env bash
# Parallel MapReduce job across all DataNodes (Hadoop Streaming with Python)
hdfs dfs -rm -r -f /earthscape/curated/monthly_summary
hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar \
  -D mapreduce.job.name="EarthScape monthly climate summary" \
  -D mapreduce.job.reduces=4 \
  -files mapper.py,reducer.py \
  -mapper "python3 mapper.py" -reducer "python3 reducer.py" \
  -input /earthscape/raw/*/year=*/month=*/region=*/ \
  -output /earthscape/curated/monthly_summary
hdfs dfs -cat /earthscape/curated/monthly_summary/part-* | head -20
# Local test without a cluster:
#   tail -n +2 ../data/sample_dataset.csv | python3 mapper.py | sort | python3 reducer.py | head
