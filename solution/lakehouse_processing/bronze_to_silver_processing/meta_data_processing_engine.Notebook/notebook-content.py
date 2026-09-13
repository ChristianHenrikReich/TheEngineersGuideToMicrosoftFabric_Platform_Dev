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

# PARAMETERS CELL ********************

entity = None
metadata_path = "/lakehouse/default/Files/meta/meta-data.json"


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import os
import zipfile
from uuid import uuid4
from functools import reduce

from pyspark.sql import functions as F

def read_new_york_taxi(metadata_entity):
    source = metadata_entity["source"]

    local_source_path = (
        f"/lakehouse/default/{source}"
    )

    override_types = metadata_entity.get(
        "override_column_types",
        {},
    )

    dataframes = []

    for root, _, file_names in os.walk(local_source_path):
        for file_name in file_names:
            if not file_name.lower().endswith(".parquet"):
                continue

            local_file_path = os.path.join(
                root,
                file_name,
            )

            # Convert the local mount path back to a
            # Spark-relative Lakehouse path.
            spark_file_path = local_file_path.replace(
                "/lakehouse/default/",
                "",
                1,
            )

            df = (
                spark.read
                .option("basePath", source)
                .parquet(spark_file_path)
            )

            for column, data_type in override_types.items():
                if column in df.columns:
                    df = df.withColumn(
                        column,
                        F.col(column).cast(data_type),
                    )

            dataframes.append(df)

    if not dataframes:
        raise FileNotFoundError(
            f"No Parquet files found in {source}"
        )

    return reduce(
        lambda left, right: left.unionByName(
            right,
            allowMissingColumns=True,
        ),
        dataframes,
    )

def read_parquet(metadata_entity):
    source = metadata_entity["source"]
    options = metadata_entity.get("options", {})

    return (
        spark.read
        .options(**options)
        .parquet(source)
    )


def read_csv(metadata_entity):
    source = metadata_entity["source"]
    options = metadata_entity.get("options", {})

    return (
        spark.read
        .options(**options)
        .csv(source)
    )


def read_zip_csv(metadata_entity):
    source = metadata_entity["source"]
    options = metadata_entity.get("options", {})

    source_path = f"/lakehouse/default/{source}"
    staging_name = uuid4().hex

    staging_path = (
        "/lakehouse/default/Files/_staging/"
        f"{staging_name}"
    )

    os.makedirs(staging_path, exist_ok=True)

    for root, _, files in os.walk(source_path):
        for file_name in files:
            if not file_name.lower().endswith(".zip"):
                continue

            zip_path = os.path.join(root, file_name)

            # Preserve the Hive partition folders.
            relative_path = os.path.relpath(
                root,
                source_path,
            )

            extract_path = os.path.join(
                staging_path,
                relative_path,
            )

            os.makedirs(
                extract_path,
                exist_ok=True,
            )

            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(extract_path)

    spark_path = (
        f"Files/_staging/{staging_name}"
    )

    return (
        spark.read
        .options(**options)
        .csv(spark_path)
    )


readers = {
    "parquet": read_parquet,
    "csv": read_csv,
    "zip_csv": read_zip_csv,
    "new_york_taxi": read_new_york_taxi,
}


def read_source(metadata_entity):
    source_format = metadata_entity["format"]

    if source_format not in readers:
        raise ValueError(
            f"Unsupported source format: {source_format}"
        )

    return readers[source_format](metadata_entity)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import functions as F
from pyspark.sql.window import Window


PARTITION_COLUMNS = [
    "segment",
    "year",
    "month",
    "day",
    "load",
]


def override_column_types(df, metadata_entity):
    column_types = metadata_entity.get(
        "override_column_types",
        {},
    )

    for column, data_type in column_types.items():
        df = df.withColumn(
            column,
            F.col(column).cast(data_type),
        )

    return df


def deduplicate(df, metadata_entity):
    business_key = metadata_entity.get(
        "business_key",
        [],
    )

    # If a business key exists, use it to identify duplicates.
    # Otherwise, use the complete source row.
    if business_key:
        duplicate_key = business_key
    else:
        duplicate_key = [
            column
            for column in df.columns
            if column not in PARTITION_COLUMNS
        ]

    # The newest Bronze load wins.
    window = (
        Window
        .partitionBy(*duplicate_key)
        .orderBy(
            F.col("year").desc(),
            F.col("month").desc(),
            F.col("day").desc(),
            F.col("load").desc(),
        )
    )

    return (
        df
        .withColumn(
            "_row_number",
            F.row_number().over(window),
        )
        .filter(F.col("_row_number") == 1)
        .drop("_row_number")
    )

def destination_exists(metadata_entity):
    destination = metadata_entity["destination"]

    schema, table = destination.split(".", 1)

    delta_log_path = (
        f"Tables/{schema}/{table}/_delta_log"
    )

    return notebookutils.fs.exists(delta_log_path)

def add_surrogate_key(df, metadata_entity):
    destination = metadata_entity["destination"]
    surrogate_key = metadata_entity["surrogate_key"]

    if destination_exists(metadata_entity):
        max_key = (
            spark.table(destination)
            .agg(F.max(surrogate_key))
            .first()[0]
            or 0
        )
    else:
        max_key = 0

    window = Window.orderBy(
        F.monotonically_increasing_id()
    )

    return df.withColumn(
        surrogate_key,
        F.row_number().over(window) + max_key,
    )

def default_transform(df, metadata_entity):
    df = override_column_types(
        df,
        metadata_entity,
    )

    df = deduplicate(
        df,
        metadata_entity,
    )

    df = add_surrogate_key(
        df,
        metadata_entity,
    )

    return df


# Maps transformation names to functions.
transformations = {
    "default": default_transform,
}


def transform_data(df, metadata_entity):
    transform_name = metadata_entity.get(
        "custom_transform",
        "default",
    )

    if transform_name not in transformations:
        raise ValueError(
            f"Unknown transformation: {transform_name}"
        )

    return transformations[transform_name](
        df,
        metadata_entity,
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import logging

from delta.tables import DeltaTable


logger = logging.getLogger("lakehouse_pipeline")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)


def write_append(df, metadata_entity):
    destination = metadata_entity["destination"]

    logger.info(
        "Appending data to destination: %s",
        destination,
    )

    (
        df.write
        .format("delta")
        .mode("append")
        .saveAsTable(destination)
    )

    logger.info(
        "Append completed: %s",
        destination,
    )


def write_merge(df, metadata_entity):
    destination = metadata_entity["destination"]
    business_key = metadata_entity["business_key"]
    surrogate_key = metadata_entity["surrogate_key"]

    if not destination_exists(metadata_entity):
        logger.info(
            "Destination does not exist. "
            "Performing initial append: %s",
            destination,
        )

        write_append(df, metadata_entity)
        return

    merge_condition = " AND ".join(
        f"target.{column} = source.{column}"
        for column in business_key
    )

    update_values = {
        column: f"source.{column}"
        for column in df.columns
        if column != surrogate_key
    }

    insert_values = {
        column: f"source.{column}"
        for column in df.columns
    }

    logger.info(
        "Merging data into destination: %s",
        destination,
    )

    target = DeltaTable.forName(
        spark,
        destination,
    )

    (
        target.alias("target")
        .merge(
            df.alias("source"),
            merge_condition,
        )
        .whenMatchedUpdate(set=update_values)
        .whenNotMatchedInsert(values=insert_values)
        .execute()
    )

    logger.info(
        "Merge completed: %s",
        destination,
    )

writers = {
    "append": write_append,
    "merge": write_merge,
}


def write_data(df, metadata_entity):
    load_type = metadata_entity["load_type"]
    destination = metadata_entity["destination"]

    if load_type not in writers:
        logger.error(
            "Unsupported load type '%s' for %s",
            load_type,
            destination,
        )

        raise ValueError(
            f"Unsupported load type: {load_type}"
        )

    logger.info(
        "Write strategy for %s: %s",
        destination,
        load_type,
    )

    writers[load_type](
        df,
        metadata_entity,
    )

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import json


# When run standalone, read all metadata from the JSON file.
# When called from runMultiple, process only the supplied entity.
if entity is None:
    with open(metadata_path, "r") as file:
        metadata = json.load(file)
else:
    metadata = [json.loads(entity)]


# Main loop.
for metadata_entity in metadata:
    destination = metadata_entity["destination"]

    logger.info(
        "Starting entity: %s",
        destination,
    )

    try:
        df = read_source(metadata_entity)

        if metadata_entity["projected_columns"]:
            df = df.select(
                *metadata_entity["projected_columns"]
            )

        df = transform_data(
            df,
            metadata_entity,
        )

        write_data(
            df,
            metadata_entity,
        )

        logger.info(
            "Completed entity: %s",
            destination,
        )

    except Exception:
        logger.exception(
            "Failed entity: %s",
            destination,
        )
        raise

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }
