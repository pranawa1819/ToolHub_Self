import sqlite3
import pandas as pd
from datetime import datetime

# Path to your Django SQLite database
db_path = 'db.sqlite3'  # Make sure this file exists in your project root

# Connect to the database
conn = sqlite3.connect(db_path)

# Get all table names
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

# Generate filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"django_export_{timestamp}.xlsx"

# Export each table to a separate sheet in Excel
with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
    for table_name in tables:
        table_name = table_name[0]
        try:
            # Read table into DataFrame
            df = pd.read_sql_query(f"SELECT * FROM {table_name};", conn)
            # Write to Excel (sheet name limited to 31 chars)
            sheet_name = table_name[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"✅ Exported: {table_name} ({len(df)} rows)")
        except Exception as e:
            print(f"❌ Failed to export {table_name}: {e}")

print(f"\n All tables exported to '{output_file}'")