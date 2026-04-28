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

key_vault_name = "https://mugatomasterkv87234.vault.azure.net/"
connection_secret_name = "FabricReader"


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

!pip install mssql_python --quiet

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import notebookutils
import mssql_python
import struct

#connection.close()
# Retrieve connection string securely from Key Vault via notebookutils
connection_string = notebookutils.credentials.getSecret(key_vault_name, connection_secret_name)
#connection_string = "Server=tcp:srv-mugatomaster.database.windows.net,1433;Database=MasterCoreDB;UID=FabricReader;PWD=Z/iNGXDbsdjNvgpAZH7ozN2fJ1ehlmy8UOOvOwSAMI4=;"
connection = mssql_python.connect(connection_string)

print("Connected to SQL Server successfully!")
cursor = connection.cursor()
cursor.execute("SELECT ClientGUID, RandomUniqueId FROM [dbo].[Client]")

# Example: {1: "Alice", 2: "Bob"}
customers = {row[0]: row[1] for row in cursor.fetchall()}

print(customers)


connection.close()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
