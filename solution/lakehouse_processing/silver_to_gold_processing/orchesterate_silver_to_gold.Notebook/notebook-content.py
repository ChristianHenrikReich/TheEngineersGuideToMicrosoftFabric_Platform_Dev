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

notebooks = [
    ("dim_date", []),
    ("dim_time", []),
    ("dim_bike_station", []),
    ("dim_weather_station", []),
    (
        "fact_taxi_trip",
        ["dim_date", "dim_time"],
    ),
    (
        "fact_bike_trip",
        ["dim_date", "dim_time", "dim_bike_station"],
    ),
    (
        "fact_weather_observation",
        ["dim_date", "dim_time", "dim_weather_station"],
    ),
]


DAG = {
    "activities": [
        {
            "name": notebook,
            "path": notebook,
            "dependencies": dependencies,
            "timeoutPerCellInSeconds": 600,
        }
        for notebook, dependencies in notebooks
    ]
}


notebookutils.notebook.validateDAG(DAG)

results = notebookutils.notebook.runMultiple(DAG)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
