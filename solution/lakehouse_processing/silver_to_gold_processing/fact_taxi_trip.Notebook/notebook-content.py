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

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC USE dbo;
# MAGIC CREATE OR REPLACE TEMP VIEW fact_taxi_trip AS
# MAGIC 
# MAGIC SELECT
# MAGIC     trip_sk,
# MAGIC 
# MAGIC     CAST(
# MAGIC         DATE_FORMAT(
# MAGIC             tpep_pickup_datetime,
# MAGIC             'yyyyMMdd'
# MAGIC         ) AS INT
# MAGIC     ) AS pickup_date_sk,
# MAGIC 
# MAGIC     HOUR(tpep_pickup_datetime) * 60
# MAGIC         + MINUTE(tpep_pickup_datetime)
# MAGIC         AS pickup_time_sk,
# MAGIC 
# MAGIC     CAST(
# MAGIC         DATE_FORMAT(
# MAGIC             tpep_dropoff_datetime,
# MAGIC             'yyyyMMdd'
# MAGIC         ) AS INT
# MAGIC     ) AS dropoff_date_sk,
# MAGIC 
# MAGIC     HOUR(tpep_dropoff_datetime) * 60
# MAGIC         + MINUTE(tpep_dropoff_datetime)
# MAGIC         AS dropoff_time_sk,
# MAGIC 
# MAGIC     PULocationID AS pickup_location_id,
# MAGIC     DOLocationID AS dropoff_location_id,
# MAGIC 
# MAGIC     VendorID AS vendor_id,
# MAGIC     passenger_count,
# MAGIC     trip_distance,
# MAGIC     fare_amount,
# MAGIC     tip_amount,
# MAGIC     tolls_amount,
# MAGIC     total_amount,
# MAGIC     payment_type,
# MAGIC 
# MAGIC     UNIX_TIMESTAMP(tpep_dropoff_datetime)
# MAGIC         - UNIX_TIMESTAMP(tpep_pickup_datetime)
# MAGIC         AS trip_duration_seconds
# MAGIC 
# MAGIC FROM new_york_taxi;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df = spark.table("fact_taxi_trip")

(
    df.write
    .mode("overwrite")
    .synapsesql("gold.dbo.fact_taxi_trip")
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
