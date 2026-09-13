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
# MAGIC CREATE OR REPLACE TEMP VIEW dim_date AS
# MAGIC 
# MAGIC WITH dates AS (
# MAGIC 
# MAGIC     SELECT TO_DATE(tpep_pickup_datetime) AS date
# MAGIC     FROM new_york_taxi
# MAGIC 
# MAGIC     UNION
# MAGIC 
# MAGIC     SELECT TO_DATE(tpep_dropoff_datetime)
# MAGIC     FROM new_york_taxi
# MAGIC 
# MAGIC     UNION
# MAGIC 
# MAGIC     SELECT TO_DATE(started_at)
# MAGIC     FROM citi_bike
# MAGIC 
# MAGIC     UNION
# MAGIC 
# MAGIC     SELECT TO_DATE(ended_at)
# MAGIC     FROM citi_bike
# MAGIC 
# MAGIC     UNION
# MAGIC 
# MAGIC     SELECT TO_DATE(DATE)
# MAGIC     FROM weather
# MAGIC )
# MAGIC 
# MAGIC SELECT
# MAGIC     CAST(DATE_FORMAT(date, 'yyyyMMdd') AS INT) AS date_sk,
# MAGIC     date,
# MAGIC     YEAR(date) AS year,
# MAGIC     QUARTER(date) AS quarter,
# MAGIC     MONTH(date) AS month,
# MAGIC     DATE_FORMAT(date, 'MMMM') AS month_name,
# MAGIC     DAY(date) AS day,
# MAGIC     DAYOFWEEK(date) AS day_of_week,
# MAGIC     DATE_FORMAT(date, 'EEEE') AS day_name,
# MAGIC     CASE
# MAGIC         WHEN DAYOFWEEK(date) IN (1, 7) THEN TRUE
# MAGIC         ELSE FALSE
# MAGIC     END AS is_weekend
# MAGIC 
# MAGIC FROM dates
# MAGIC WHERE date IS NOT NULL

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df = spark.table("dim_date")

(
    df.write
    .mode("overwrite")
    .synapsesql("gold.dbo.dim_date")
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
