#!/bin/bash
set -e

# Wait for Splunk to be ready before doing anything else
echo "Waiting for Splunk to start..."
until curl -sk https://localhost:8089/services/server/info -u admin:Passw0rd > /dev/null 2>&1; do
  sleep 5
done
echo "Splunk is up"

sudo curl -k -u admin:Passw0rd https://localhost:8089/servicesNS/nobody/search/saved/searches \
    -d name="Honeypot Bot Trap Triggered" \
    -d description="Tracks malicious automated scripts populating hidden web form elements" \
    -d search='index="main" source="/opt/splunk/s3_data/*" "Bot filled hidden field" | iplocation ip | table _time ip City Country' \
    -d is_scheduled=1 \
    -d cron_schedule="*/5 * * * *" \
    -d dispatch.earliest_time="-15m" \
    -d dispatch.latest_time="now" \
    -d alert_type="number of events" \
    -d alert_comparator="greater than" \
    -d alert_threshold=0 \
    -d alert.digest_mode=0 \
    -d alert.suppress=1 \
    -d alert.suppress.fields="ip" \
    -d alert.suppress.period="300s" \
    -d actions="list" \
    -d action.list.severity=5

sudo docker restart splunk_server
echo "Alert Configured"
