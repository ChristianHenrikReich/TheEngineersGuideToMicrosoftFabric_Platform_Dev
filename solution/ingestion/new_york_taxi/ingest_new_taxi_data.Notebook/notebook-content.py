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


logger = logging.getLogger("bronze_ingestion")
logger.setLevel(logging.INFO)

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

topic = "new_york_taxi"
segment = "incremental"

max_retries = 5

source_base_url = (
    "https://d37ci6vzurychx.cloudfront.net/trip-data"
)

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

def generate_source_name():
    year = random.randint(2022, 2025)
    month = random.randint(1, 12)

    return f"yellow_tripdata_{year}-{month:02d}.parquet"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def download_batch(target_dir):
    attempted = set()

    for attempt in range(1, max_retries + 1):
        source_file = generate_source_name()

        while source_file in attempted:
            source_file = generate_source_name()

        attempted.add(source_file)

        source_url = f"{source_base_url}/{source_file}"
        target_path = os.path.join(target_dir, source_file)

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

                with open(target_path, "wb") as file:
                    for chunk in response.iter_content(
                        chunk_size=1024 * 1024
                    ):
                        if chunk:
                            file.write(chunk)

            logger.info(
                "Download completed: %s",
                source_file
            )

            return target_path

        except requests.RequestException:
            logger.exception(
                "Download failed for %s",
                source_file
            )

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
        "Bronze ingestion completed: %s",
        target_path
    )

except Exception:
    logger.exception("Bronze ingestion failed.")
    raise

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
