#!/usr/bin/env python3
import requests
import sys

# Disable SSL warnings for self-signed certificates (Splunk's default)
requests.packages.urllib3.disable_warnings()

url = "https://localhost:8089/servicesNS/nobody/search/saved/searches"
auth = ("admin", "Passw0rd")

payload = {
    "name": "Honeypot Bot Trap Triggered",
    "description": "Tracks malicious automated scripts populating hidden web form elements",
    "search": 'index="main" source="/opt/splunk/s3_data/*" "Bot filled hidden field" | iplocation ip | table _time ip City Country',
    "is_scheduled": "1",
    "cron_schedule": "*/5 * * * *",
    "dispatch.earliest_time": "-15m",
    "dispatch.latest_time": "now",
    "alert_type": "number of events",
    "alert_comparator": "greater than",
    "alert_threshold": "0",
    "alert.digest_mode": "0",
    "alert.suppress": "1",
    "alert.suppress.fields": "ip",
    "alert.suppress.period": "300s",
    "actions": "list",
    "action.list.severity": "5"
}

print("Sending API payload via Python requests...")
try:
    response = requests.post(url, auth=auth, data=payload, verify=False)
    
    if response.status_code in [200, 201]:
        print("Success! Honeypot Alert created successfully via Python.")
        sys.exit(0)
    else:
        print(f"Splunk API Error (Status {response.status_code}):")
        print(response.text)
        sys.exit(1)

except Exception as e:
    print(f"Network Connection Failed: {e}")
    sys.exit(1)
