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

dim_weather_station_df = (
    spark.read
    .synapsesql("gold.dbo.dim_weather_station")
)

dim_weather_station_df.createOrReplaceTempView(
    "dim_weather_station"
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# MAGIC %%sql
# MAGIC USE dbo;
# MAGIC CREATE OR REPLACE TEMP VIEW fact_weather_observation AS
# MAGIC 
# MAGIC SELECT
# MAGIC     weather.weather_sk,
# MAGIC 
# MAGIC     station.station_sk,
# MAGIC 
# MAGIC     CAST(
# MAGIC         DATE_FORMAT(
# MAGIC             weather.DATE,
# MAGIC             'yyyyMMdd'
# MAGIC         ) AS INT
# MAGIC     ) AS date_sk,
# MAGIC 
# MAGIC     HOUR(weather.DATE) * 60
# MAGIC         + MINUTE(weather.DATE)
# MAGIC         AS time_sk,
# MAGIC 
# MAGIC     weather.temperature,
# MAGIC     weather.dew_point_temperature,
# MAGIC     weather.station_level_pressure,
# MAGIC     weather.altimeter
# MAGIC 
# MAGIC FROM weather
# MAGIC 
# MAGIC LEFT JOIN dim_weather_station AS station
# MAGIC     ON weather.STATION = station.station_id;

# METADATA ********************

# META {
# META   "language": "sparksql",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

df = spark.table("fact_weather_observation")

(
    df.write
    .mode("overwrite")
    .synapsesql("gold.dbo.dim_tfact_weather_observationime")
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
