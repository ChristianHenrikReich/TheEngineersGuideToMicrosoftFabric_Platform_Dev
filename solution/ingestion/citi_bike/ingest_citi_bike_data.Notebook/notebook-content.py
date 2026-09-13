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
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

import logging
import os
import random
from datetime import datetime, timezone

import requests


logger = logging.getLogger("citi_bike_bronze")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

topic = "citi_bike"
segment = "incremental"

max_retries = 5

source_base_url = "https://s3.amazonaws.com/tripdata"

source_year_min = 2022
source_year_max = 2025

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

run_timestamp = datetime.now(timezone.utc)

year = run_timestamp.strftime("%Y")
month = run_timestamp.strftime("%m")
day = run_timestamp.strftime("%d")
load = run_timestamp.strftime("%H%M%S%f")

target_dir = (
    f"/lakehouse/default/Files/{topic}/"
    f"segment={segment}/"
    f"year={year}/"
    f"month={month}/"
    f"day={day}/"
    f"load={load}"
)

os.makedirs(target_dir, exist_ok=True)

logger.info("Bronze target path: %s", target_dir)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def generate_source_names():
    year = 2024
    month = random.randint(1, 12)

    prefix = f"{year}{month:02d}-citibike-tripdata"

    return [
        f"{prefix}.zip",
        f"{prefix}.csv.zip",
    ]

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def download_batch(target_dir):
    attempted = set()

    for attempt in range(1, max_retries + 1):
        source_files = generate_source_names()

        for source_file in source_files:
            if source_file in attempted:
                continue

            attempted.add(source_file)

            source_url = f"{source_base_url}/{source_file}"
            target_path = os.path.join(
                target_dir,
                source_file
            )

            temp_path = f"{target_path}.part"

            logger.info(
                "Attempt %s: downloading %s",
                attempt,
                source_file
            )

            try:
                with requests.get(
                    source_url,
                    stream=True,
                    timeout=120
                ) as response:
                    response.raise_for_status()

                    with open(temp_path, "wb") as file:
                        for chunk in response.iter_content(
                            chunk_size=8 * 1024 * 1024
                        ):
                            if chunk:
                                file.write(chunk)

                os.replace(temp_path, target_path)

                logger.info(
                    "Download completed: %s",
                    source_file
                )

                return target_path

            except requests.RequestException as error:
                logger.warning(
                    "Download failed for %s: %s",
                    source_file,
                    error
                )

                if os.path.exists(temp_path):
                    os.remove(temp_path)

    raise RuntimeError(
        f"Download failed after {max_retries} attempts."
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

try:
    target_path = download_batch(target_dir)

    logger.info(
        "Citi Bike Bronze ingestion completed: %s",
        target_path
    )

except Exception:
    logger.exception(
        "Citi Bike Bronze ingestion failed."
    )
    raise

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
