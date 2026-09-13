# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# CELL ********************

import logging
import os
import random
from datetime import datetime, timezone

import requests


logger = logging.getLogger("weather_bronze")
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

topic = "weather"
segment = "incremental"

max_retries = 5

station_id = "USW00094728"

source_year_min = 2020
source_year_max = 2025

source_base_url = (
    "https://www.ncei.noaa.gov/oa/"
    "global-historical-climatology-network/"
    "hourly/access/by-year"
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

def generate_source():
    source_year = random.randint(
        source_year_min,
        source_year_max
    )

    source_file = (
        f"GHCNh_{station_id}_{source_year}.psv"
    )

    return source_year, source_file

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

def download_batch(target_dir):
    attempted = set()

    for attempt in range(1, max_retries + 1):
        source_year, source_file = generate_source()

        while source_file in attempted:
            source_year, source_file = generate_source()

        attempted.add(source_file)

        source_url = (
            f"{source_base_url}/"
            f"{source_year}/psv/"
            f"{source_file}"
        )

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
        "Weather Bronze ingestion completed: %s",
        target_path
    )

except Exception:
    logger.exception(
        "Weather Bronze ingestion failed."
    )
    raise

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
