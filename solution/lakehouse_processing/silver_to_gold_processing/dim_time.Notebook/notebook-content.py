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
# MAGIC CREATE OR REPLACE TEMP VIEW dim_time AS
# MAGIC 
# MAGIC WITH times AS (
# MAGIC     SELECT EXPLODE(SEQUENCE(0, 1439)) AS minute_of_day
# MAGIC )
# MAGIC 
# MAGIC SELECT
# MAGIC     minute_of_day AS time_sk,
# MAGIC     FLOOR(minute_of_day / 60) AS hour,
# MAGIC     MOD(minute_of_day, 60) AS minute,
# MAGIC 
# MAGIC     CASE
# MAGIC         WHEN FLOOR(minute_of_day / 60) < 6
# MAGIC             THEN 'Night'
# MAGIC         WHEN FLOOR(minute_of_day / 60) < 12
# MAGIC             THEN 'Morning'
# MAGIC         WHEN FLOOR(minute_of_day / 60) < 18
# MAGIC             THEN 'Afternoon'
# MAGIC         ELSE 'Evening'
# MAGIC     END AS part_of_day
# MAGIC 
# MAGIC FROM times;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df = spark.table("dim_time")

(
    df.write
    .mode("overwrite")
    .synapsesql("gold.dbo.dim_time")
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
