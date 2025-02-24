from datetime import datetime, timedelta

# Current time
now = datetime.utcnow()

# Convert to ISO format
iso_format = now.isoformat() + "Z"  # Adding 'Z' to indicate UTC time

print("ISO Format:", iso_format)
