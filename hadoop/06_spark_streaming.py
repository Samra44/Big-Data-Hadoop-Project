"""Real-time layer: Kafka topic 'climate-readings' → Spark Structured Streaming → alerts + HDFS.
Joins the stream with the batch climatology (lambda architecture) so live readings are judged against history.
    spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1 06_spark_streaming.py"""
from pyspark.sql import SparkSession, functions as F
from pyspark.sql.types import StructType, StringType, DoubleType
spark = SparkSession.builder.appName("EarthScape-Streaming").getOrCreate()
schema = StructType().add("station_id", StringType()).add("date", StringType()).add("temperature_c", DoubleType()) \
    .add("precipitation_mm", DoubleType()).add("wind_speed_kmh", DoubleType()).add("pm25_ugm3", DoubleType())
raw = spark.readStream.format("kafka").option("kafka.bootstrap.servers", "localhost:9092").option("subscribe", "climate-readings").load()
s = raw.select(F.from_json(F.col("value").cast("string"), schema).alias("r")).select("r.*") \
       .withColumn("month", F.month(F.to_date("date"))).withColumn("ts", F.current_timestamp())
clim = spark.read.parquet("hdfs:///earthscape/curated/readings_parquet").groupBy("station_id", "month") \
       .agg(F.avg("temperature_c").alias("mu"), F.stddev("temperature_c").alias("sd"))          # batch view
j = s.join(clim, ["station_id", "month"], "left").withColumn("z", (F.col("temperature_c") - F.col("mu")) / F.col("sd"))
alerts = j.filter((F.abs("z") > 3) | (F.col("temperature_c") >= 45) | (F.col("precipitation_mm") >= 100) |
                  (F.col("wind_speed_kmh") >= 70) | (F.col("pm25_ugm3") >= 250))
alerts.selectExpr("station_id AS key", "to_json(struct(*)) AS value").writeStream.format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092").option("topic", "climate-alerts").option("checkpointLocation", "/tmp/chk_alerts").start()
j.writeStream.format("parquet").option("path", "hdfs:///earthscape/stream/readings").option("checkpointLocation", "/tmp/chk_store") \
    .trigger(processingTime="30 seconds").start()
# 10-minute windowed regional stats for the live dashboard
s.withWatermark("ts", "10 minutes").groupBy(F.window("ts", "10 minutes"), "station_id").agg(F.avg("temperature_c").alias("avg_t")) \
    .writeStream.outputMode("update").format("console").start()
spark.streams.awaitAnyTermination()
