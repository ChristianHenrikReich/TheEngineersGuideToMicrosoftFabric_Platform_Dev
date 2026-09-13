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
# MAGIC CREATE OR REPLACE TEMP VIEW dim_bike_station AS
# MAGIC 
# MAGIC WITH stations AS (
# MAGIC 
# MAGIC     SELECT
# MAGIC         start_station_id AS station_id,
# MAGIC         start_station_name AS station_name,
# MAGIC         start_lat AS latitude,
# MAGIC         start_lng AS longitude
# MAGIC     FROM citi_bike
# MAGIC 
# MAGIC     UNION ALL
# MAGIC 
# MAGIC     SELECT
# MAGIC         end_station_id,
# MAGIC         end_station_name,
# MAGIC         end_lat,
# MAGIC         end_lng
# MAGIC     FROM citi_bike
# MAGIC ),
# MAGIC 
# MAGIC deduplicated AS (
# MAGIC 
# MAGIC     SELECT
# MAGIC         *,
# MAGIC         ROW_NUMBER() OVER (
# MAGIC             PARTITION BY station_id
# MAGIC             ORDER BY station_name
# MAGIC         ) AS row_number
# MAGIC     FROM stations
# MAGIC     WHERE station_id IS NOT NULL
# MAGIC )
# MAGIC 
# MAGIC SELECT
# MAGIC     ROW_NUMBER() OVER (
# MAGIC         ORDER BY station_id
# MAGIC     ) AS station_sk,
# MAGIC     station_id,
# MAGIC     station_name,
# MAGIC     latitude,
# MAGIC     longitude
# MAGIC 
# MAGIC FROM deduplicated
# MAGIC WHERE row_number = 1;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df = spark.table("dim_bike_station")

(
    df.write
    .mode("overwrite")
    .synapsesql("gold.dbo.dim_bike_station")
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
