from pathlib import Path

import pytest
from pyspark.sql import SparkSession
from notebook_test_utilities import read_fabric_notebook

NOTEBOOK_FOLDER = Path("solution/lakehouse_processing/process_from_bronze_to_silver.Notebook")

# Mock for notebookutils, use this when your notebooks are
# importing notebookutils. You can add extend the mock with 
# more of the notebookutils methods if needed.
class NotebookUtilsMock:
    class credentials:
        @staticmethod
        def getSecret(*_args, **_kwargs):
            return "fake-secret"


# Fixture to create SparkSession and reads the notebook.
# Pytest understands the yield in the function, and evertyhing
# after becomees so-called teardown. 
# The mocks are injected when reading the notebook.
@pytest.fixture(scope="session")
def spark() -> SparkSession:
    s = (
        SparkSession.builder
        .master("local[1]")
        .appName("test_bronze_to_silver_processing")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    s.sparkContext.setLogLevel("ERROR")

    read_fabric_notebook(
        NOTEBOOK_FOLDER,
        injected_mocks={"notebookutils": NotebookUtilsMock()},
    )

    yield s
    s.stop()

# Test to verify that the audit column is added 
# to the DataFrame.
#
# The test is following the Given-When-Then pattern. 
# Expression the Given-When-Then pattern in the 
# test name can make it easier to name the test but
# also gives context in the test overview when a test is
# failing. Inline comments in the test itself is also an 
# option. Using both methods is redundant, and brings a
# little value.
def test_given_dataframe_when_add_audit_columns_then_fields_and_values_are_set(spark):
    # Given: a base DataFrame and an audit value
    base_df = spark.createDataFrame([(1,), (2,), (3,)], ["n"])
    
    # When: we add the audit column
    df = add_audit_columns(base_df, "unit_test")

    # Then: the audit column is present 
    assert "audit_timestamp" in df.columns
    assert "audit_source" in df.columns
    assert df.select("audit_source").distinct().collect()[0][0] == "unit_test"
