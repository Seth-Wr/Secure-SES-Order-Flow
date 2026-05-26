#!/bin/bash
set -e  # crash on any error

# Update system
sudo apt update

# Install Docker
sudo apt install -y docker.io

# Enable Docker
sudo systemctl enable --now docker

# Make folders
mkdir -p ~/splunk_data
mkdir -p ~/s3_sync_dir

# Download only the splunk directory from your GitHub repo
sudo apt install -y git
git clone --no-checkout https://github.com/Seth-Wr/Serverless_Splunk_Lab.git /tmp/seth-wr
cd /tmp/seth-wr
git sparse-checkout init --cone
git sparse-checkout set splunk
git checkout main
cd ~

# Run Splunk container
sudo docker run -d \
  --name splunk_server \
  --restart unless-stopped \
  -m 4g \
  -p 8000:8000 \
  -p 8089:8089 \
  -v /home/ubuntu/splunk_data:/opt/splunk/var \
  -v /home/ubuntu/s3_sync_dir:/opt/splunk/s3_data \
  -e "SPLUNK_START_ARGS=--accept-license" \
  -e "SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com" \
  -e "SPLUNK_PASSWORD=Passw0rd" \
  splunk/splunk:latest

# Install AWS CLI
sudo apt install -y awscli

# Create s3 sync script
sudo tee /usr/local/bin/s3_sync.sh << 'EOF'
#!/bin/bash
shopt -s globstar
/usr/bin/aws s3 sync s3://nufjuice-logs/ /home/ubuntu/s3_sync_dir
EOF

# Make it executable
sudo chmod +x /usr/local/bin/s3_sync.sh

# Setup cronjob as root
echo "*/3 * * * * /usr/local/bin/s3_sync.sh >> /home/ubuntu/s3_cron.log 2>&1" > /tmp/root_cron
sudo crontab /tmp/root_cron
rm /tmp/root_cron

# Set permissions
sudo chown -R 41812:41812 /home/ubuntu/splunk_data
sudo chmod -R 755 /home/ubuntu/splunk_data
sudo chown -R 41812:41812 /home/ubuntu/s3_sync_dir
sudo chmod -R 755 /home/ubuntu/s3_sync_dir
sudo chmod 755 /home/ubuntu

# Wait for Splunk to be ready before doing anything else
echo "Waiting for Splunk to start..."
until curl -sk https://localhost:8089/services/server/info -u admin:Passw0rd > /dev/null 2>&1; do
  sleep 5
done
echo "Splunk is up"

# Copy lookup files into container
sudo docker cp /tmp/seth-wr/splunk/lookups/GeoIP2-City.mmdb splunk_server:/opt/splunk/etc/apps/search/lookups/
echo "Copied lookup file"

# Copy inputs config into container
sudo docker exec -u 0 -it splunk_server mkdir -p /opt/splunk/etc/apps/search/local
sudo docker cp /tmp/seth-wr/splunk/configs/inputs.conf splunk_server:/opt/splunk/etc/apps/search/local/inputs.conf
echo "copied inputs.conf"

# Alert setup
sudo bash /tmp/seth-wr/splunk/scripts/alert_setup.sh

sudo bash /tmp/seth-wr/splunk/scripts/dashboard_setup.sh
echo "Dashboard created"


# Dark mode 
echo "Setting system theme preference to Dark Mode..."
curl -k -s -o /dev/null -w "Status: %{http_code}\n" \
    -u "admin":"Passw0rd" \
    -X POST "https://localhost:8089/servicesNS/admin/user-prefs/configs/conf-user-prefs/general?output_mode=json" \
    --data "theme=dark"

# Restart so all configs take effect
sudo docker restart splunk_server

echo "Lab setup complete"
