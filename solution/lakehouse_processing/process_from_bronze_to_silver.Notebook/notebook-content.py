# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.12"
# META   },
# META   "dependencies": {}
# META }

# CELL ********************

%pip install --upgrade "PyJWT>=2.6.0"
%pip install mssql_python --quiet

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

import notebookutils
from pyspark.sql.functions import current_timestamp, lit

def add_audit_columns(df, source):
    from datetime import datetime
    return df.withColumn("audit_timestamp", current_timestamp()) \
             .withColumn("audit_source", lit(source))