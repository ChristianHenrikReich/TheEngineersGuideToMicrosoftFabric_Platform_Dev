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

# CELL ********************

key_vault_name = "https://mugatokvdev2xdvgsdb4sxne.vault.azure.net/"
connection_secret_name = "FabricReader"


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

import notebookutils
import mssql_python

connection_string = notebookutils.credentials.getSecret(key_vault_name, connection_secret_name)
connection = mssql_python.connect(connection_string)

print("Connected to SQL Server successfully!")
cursor = connection.cursor()
cursor.execute("SELECT ClientGUID, RandomUniqueId FROM [dbo].[Client]")

customers = {row[0]: row[1] for row in cursor.fetchall()}

print(customers)


connection.close()

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }

# CELL ********************

for client_guid, random_unique_id in customers.items():
    print(f"ClientGUID: {client_guid}, RandomUniqueId: {random_unique_id}")

    client_key_vault_name = f"https://portal{random_unique_id}.vault.azure.net/"

    try:
        client_connection_string = notebookutils.credentials.getSecret(client_key_vault_name, "FrontendConnectionString")
        client_connection = mssql_python.connect(connection_string)

        print(f"Successfully connected to client database for ClientGUID: {client_guid}")

        client_connection.close()

    except Exception as e:
        print(f"Failed to get secret for client {client_guid}: {e}")
        continue

    break

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "jupyter_python"
# META }
