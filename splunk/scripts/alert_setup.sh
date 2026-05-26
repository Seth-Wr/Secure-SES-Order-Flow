#!/bin/bash
set -e  # crash on any error

echo "Configuring Honeypot Alert..."

# Build the exact urlencoded payload string explicitly
ALERT_PAYLOAD="name=Honeypot+Bot+Trap+Triggered"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&description=Tracks+malicious+automated+scripts+populating+hidden+web+form+elements"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&search=index%3D%22main%22+source%3D%22%2Fopt%2Fsplunk%2Fs3_data%2F%2A%22+%22Bot+filled+hidden+field%22+%7C+iplocation+ip+%7C+table+_time+ip+City+Country"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&is_scheduled=1"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&cron_schedule=%2A%2F5+%2A+%2A+%2A+%2A"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&dispatch.earliest_time=-15m"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&dispatch.latest_time=now"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&alert_type=number+of+events"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&alert_comparator=greater+than"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&alert_threshold=0"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&alert.digest_mode=0"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&alert.suppress=1"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&alert.suppress.fields=ip"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&alert.suppress.period=300s"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&actions=list"
ALERT_PAYLOAD="${ALERT_PAYLOAD}&action.list.severity=5"

# Send the pre-formatted payload directly to the REST target endpoint
sudo curl -k -u admin:Passw0rd https://localhost:8089/servicesNS/nobody/search/saved/searches \
    -X POST \
    -d "$ALERT_PAYLOAD"

echo "Alert call processed."
