# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "6b44db70-9943-4926-ab1c-e854ad92d358",
# META       "default_lakehouse_name": "silver",
# META       "default_lakehouse_workspace_id": "cd0d796d-7c51-4231-89d7-3fe4238c60c4",
# META       "known_lakehouses": [
# META         {
# META           "id": "6b44db70-9943-4926-ab1c-e854ad92d358"
# META         }
# META       ]
# META     },
# META     "warehouse": {
# META       "known_warehouses": [
# META         {
# META           "id": "6b8b71aa-d9f4-4e2a-8ce2-72be2bbd0597",
# META           "type": "Datawarehouse"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

import com.microsoft.spark.fabric

dim_bike_station_df = (
    spark.read
    .synapsesql("gold.dbo.dim_bike_station")
)

dim_bike_station_df.createOrReplaceTempView(
    "dim_bike_station"
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC USE dbo;
# MAGIC CREATE OR REPLACE TEMP VIEW fact_bike_trip AS
# MAGIC 
# MAGIC SELECT
# MAGIC     bike.ride_sk AS bike_trip_sk,
# MAGIC     bike.ride_id,
# MAGIC 
# MAGIC     CAST(
# MAGIC         DATE_FORMAT(
# MAGIC             bike.started_at,
# MAGIC             'yyyyMMdd'
# MAGIC         ) AS INT
# MAGIC     ) AS start_date_sk,
# MAGIC 
# MAGIC     HOUR(bike.started_at) * 60
# MAGIC         + MINUTE(bike.started_at)
# MAGIC         AS start_time_sk,
# MAGIC 
# MAGIC     CAST(
# MAGIC         DATE_FORMAT(
# MAGIC             bike.ended_at,
# MAGIC             'yyyyMMdd'
# MAGIC         ) AS INT
# MAGIC     ) AS end_date_sk,
# MAGIC 
# MAGIC     HOUR(bike.ended_at) * 60
# MAGIC         + MINUTE(bike.ended_at)
# MAGIC         AS end_time_sk,
# MAGIC 
# MAGIC     start_station.station_sk
# MAGIC         AS start_station_sk,
# MAGIC 
# MAGIC     end_station.station_sk
# MAGIC         AS end_station_sk,
# MAGIC 
# MAGIC     bike.rideable_type,
# MAGIC     bike.member_casual,
# MAGIC 
# MAGIC     UNIX_TIMESTAMP(bike.ended_at)
# MAGIC         - UNIX_TIMESTAMP(bike.started_at)
# MAGIC         AS duration_seconds
# MAGIC 
# MAGIC FROM citi_bike AS bike
# MAGIC 
# MAGIC LEFT JOIN dim_bike_station AS start_station
# MAGIC     ON bike.start_station_id = start_station.station_id
# MAGIC 
# MAGIC LEFT JOIN dim_bike_station AS end_station
# MAGIC     ON bike.end_station_id = end_station.station_id;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df = spark.table("fact_bike_trip")

(
    df.write
    .mode("overwrite")
    .synapsesql("gold.dbo.fact_bike_trip")
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
