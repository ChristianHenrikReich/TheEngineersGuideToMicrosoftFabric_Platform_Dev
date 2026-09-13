# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "d114437e-b12b-423e-8f73-43624cd88282",
# META       "default_lakehouse_name": "bronze",
# META       "default_lakehouse_workspace_id": "cd0d796d-7c51-4231-89d7-3fe4238c60c4",
# META       "known_lakehouses": [
# META         {
# META           "id": "d114437e-b12b-423e-8f73-43624cd88282"
# META         },
# META         {
# META           "id": "6b44db70-9943-4926-ab1c-e854ad92d358"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

import json
import logging


logger = logging.getLogger("lakehouse_orchestration")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)


metadata_path = (
    "/lakehouse/default/Files/meta/meta-data.json"
)

with open(metadata_path, "r") as file:
    metadata = json.load(file)


DAG = {
    "activities": [
        {
            "name": (
                f"Process_{metadata_entity['destination']}"
                .replace(".", "_")
            ),
            "path": "meta_data_processing_engine",
            "timeoutPerCellInSeconds": 600,
            "args": {
                "entity": json.dumps(metadata_entity),
            },
        }
        for metadata_entity in metadata
    ]
}


logger.info(
    "Starting processing of %s entities",
    len(metadata),
)

notebookutils.notebook.validateDAG(DAG)

results = notebookutils.notebook.runMultiple(DAG)

logger.info(
    "Entity processing completed"
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
