"""PySpark batch pipeline: clean → climatology → anomaly z-scores → trends → write Parquet + Tableau extracts.
    spark-submit 05_spark_batch.py hdfs:///earthscape/raw  hdfs:///earthscape/curated"""
import sys
from pyspark.sql import SparkSession, functions as F, Window
src = sys.argv[1] if len(sys.argv) > 1 else "../data/sample_dataset.csv"; dst = sys.argv[2] if len(sys.argv) > 2 else "../dashboard/spark_out"
spark = SparkSession.builder.appName("EarthScape-Batch").getOrCreate()
df = spark.read.csv(src, header=True, inferSchema=True).withColumn("date", F.to_date("date")) \
    .withColumn("year", F.year("date")).withColumn("month", F.month("date"))
# missing values: impute with station/month mean
w = Window.partitionBy("station_id", "month")
for c in ["humidity_pct", "wind_speed_kmh", "pm25_ugm3", "ndvi", "land_surface_temp_c", "soil_moisture_pct"]:
    df = df.withColumn(c, F.coalesce(F.col(c), F.avg(c).over(w)))
df = df.withColumn("temp_z", (F.col("temperature_c") - F.avg("temperature_c").over(w)) / F.stddev("temperature_c").over(w)) \
       .withColumn("anomaly", (F.abs("temp_z") > 3).cast("int"))
df.repartition("year").write.mode("overwrite").partitionBy("year", "month").parquet(f"{dst}/readings_parquet")
annual = df.groupBy("station_id", "region", "year").agg(F.avg("temperature_c").alias("t"), F.avg("co2_ppm").alias("co2"))
from pyspark.ml.regression import LinearRegression
from pyspark.ml.feature import VectorAssembler
trends = []
for s in [r.station_id for r in annual.select("station_id").distinct().collect()]:
    d = VectorAssembler(inputCols=["year"], outputCol="f").transform(annual.filter(F.col("station_id") == s))
    m = LinearRegression(featuresCol="f", labelCol="t").fit(d); trends.append((s, float(m.coefficients[0]) * 10))
spark.createDataFrame(trends, ["station_id", "c_per_decade"]).coalesce(1).write.mode("overwrite").csv(f"{dst}/trends", header=True)
df.groupBy("region", "year", "month").agg(F.avg("temperature_c").alias("mean_temp"), F.sum("precipitation_mm").alias("rain"),
    F.sum("anomaly").alias("anomalies")).coalesce(1).write.mode("overwrite").csv(f"{dst}/monthly_region", header=True)
print("batch complete"); spark.stop()
