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
# MAGIC CREATE OR REPLACE TEMP VIEW dim_weather_station AS
# MAGIC 
# MAGIC WITH stations AS (
# MAGIC 
# MAGIC     SELECT DISTINCT
# MAGIC         STATION AS station_id,
# MAGIC         Station_name AS station_name,
# MAGIC         LATITUDE AS latitude,
# MAGIC         LONGITUDE AS longitude,
# MAGIC         ELEVATION AS elevation
# MAGIC 
# MAGIC     FROM weather
# MAGIC     WHERE STATION IS NOT NULL
# MAGIC )
# MAGIC 
# MAGIC SELECT
# MAGIC     ROW_NUMBER() OVER (
# MAGIC         ORDER BY station_id
# MAGIC     ) AS station_sk,
# MAGIC     station_id,
# MAGIC     station_name,
# MAGIC     latitude,
# MAGIC     longitude,
# MAGIC     elevation
# MAGIC 
# MAGIC FROM stations;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df = spark.table("dim_weather_station")

(
    df.write
    .mode("overwrite")
    .synapsesql("gold.dbo.dim_weather_station")
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
