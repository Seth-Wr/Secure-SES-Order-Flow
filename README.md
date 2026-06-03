# Cloud-Native Serverless Order Fulfillment System & Portable Splunk SOC

A high-performance, security-first serverless order fulfillment engine integrated with a **decoupled, portable Splunk SIEM Security Operations Center (SOC)**. 

This project demonstrates a **production-grade** order fulfillment engine deployed in a **live staging environment** to showcase real-world cloud defense and cost-effective architecture. Instead of scouring messy CloudWatch logs manually, this setup transforms log analysis into an automated, visualized pipeline. The entire infrastructure—from the web application to the ephemeral local monitoring environment—is fully automated to prevent running costly cloud resources 24/7.

🔗 **Live Demo Site:** [https://www.nufjuice.com](https://www.nufjuice.com)

---

## 🛠️ SOC & Splunk Monitoring Architecture
The monitoring stack is designed to be completely **stateless, portable, and cost-optimized**, decoupling the SIEM platform from active log storage. 

* **Cost-Optimized Log Pipeline:** To eliminate unnecessary AWS data transfer and edge storage costs, high-volume CloudFront logging is disabled. Instead, the pipeline captures high-fidelity security and telemetry events generated directly by the FastAPI backend on AWS Lambda, routing them to a private Amazon S3 bucket.
* **Ephemeral Splunk Instance:** Splunk Enterprise runs locally inside a Docker container, removing the need for paid cloud licenses or permanent cloud endpoints.
* **Automated Ingestion:** A localized `cron` job runs every 3 minutes, pulling the latest log deltas from the S3 bucket and feeding them directly into Splunk’s monitored input directory.
* **Infrastructure as Code (IaC):** The entire security laboratory infrastructure, environment variables, and Docker configurations are managed via **Terraform**. This allows a defender to spin up the cloud pipeline, execute local initialization bash scripts, and begin live monitoring within 1–2 minutes, completely bypassing the AWS Console and avoiding expensive, always-on `t3.large` cloud instances.

### 📊 Web Overview Dashboard & Alerts
The Splunk environment features a custom-built dashboard that utilizes SPL (Splunk Processing Language) to query traffic trends rapidly, visualizing threats such as:
* **Geographic Traffic Distribution:** Tracking request geolocation data to spot anomalous global traffic spikes hitting the application layer.
* **HTTP Status Code Analytics:** Monitoring API endpoint health and mapping input validation failures on the Lambda backend.
* **Honeypot Trigger Alerts:** Instantly flagging automated bot submissions when the hidden frontend honeypot field is populated, tripping immediate SOC priority alerts.

---

## 🏗️ Core Application Architecture
The application is built completely serverless to eliminate server maintenance overhead while maximizing performance and security.

* **Static Hosting:** Vanilla JavaScript frontend hosted on Amazon S3, completely isolated from public access using **Origin Access Control (OAC)**.
* **API Layer:** FastAPI (Python) running on **AWS Lambda**, executing core order logic, security validation, and fulfillment actions.
* **Global Distribution:** **Amazon CloudFront** serves as the single public entry point, delivering the static frontend globally and securely proxying API requests to the private Lambda backend.
* **Edge Protection:** **AWS WAF** sits directly in front of CloudFront to filter out malicious traffic, layer-7 exploits, and automated scanner activity.
* **Transit Security:** Full end-to-end SSL/TLS encryption managed via AWS Certificate Manager (ACM).

---

## 🛡️ Defense-in-Depth Security & Verification
The backend implements strict verification controls to block automated exploits and safeguard third-party integrations.

### 🤖 Bot Mitigation
* **Cloudflare Managed CAPTCHA:** Mandatory token verification on the client side before an order payload can hit the backend.
* **Honeypot Logic:** A hidden form field invisible to human users. If an automated script populates this field, the payload is immediately dropped, and an event log is routed to Splunk for alerting.

### 📧 Email Reputation Management
To maintain an unblemished sending reputation with Amazon SES, the system performs strict validation before dispatching transaction emails:
* **DNS Verification:** Active MX and NS record lookups to ensure the target domain is legitimate and capable of receiving mail.
* **Disposable Email Filtering:** Algorithmic validation against known temporary/burner email providers.
* **Reputation Alarms:** Real-time CloudWatch metrics tracking Bounce and Complaint rates, ensuring proactive management of the SES production account.

---

## 🚀 Technical Stack

| Component | Technology |
| :--- | :--- |
| **SIEM & Analytics** | Splunk Enterprise (Dockerized), SPL (Splunk Processing Language) |
| **Infrastructure as Code** | Terraform, Bash Scripting |
| **Backend API** | Python, FastAPI, AWS Lambda |
| **Frontend** | Vanilla JS, HTML5, CSS3 |
| **Content Delivery** | Amazon CloudFront (OAC Secured) |
| **Storage & Logging** | Amazon S3, Local Storage (State Management) |
| **Email Delivery** | Amazon SES (Production Mode) |
| **Edge Security** | AWS WAF, Cloudflare CAPTCHA, SSL/TLS (ACM) |

---

## 📩 Fulfillment & Telemetry Workflow

[User Action] ──> [CloudFront / WAF] ──> [FastAPI on Lambda]
│
┌───────────────────────────────┴───────────────────────────────┐
▼                                                               ▼
[Security Verification]                                         [Fulfillment Executed]
Check Cloudflare CAPTCHA Token                               - Send Customer Receipt via SES
Verify Honeypot Field = Empty                                - Send Merchant Notification via SES
Run MX/NS Domain Lookups                                                    │
Filter Disposable Email Lists                                               ▼
│                                                    [Telemetry Log Drop]
└───────────────────────────────┬───────────────────────────────┘
▼
[Private S3 Log Bucket]
│  (Cron Sync / 3 Mins)
▼
[Local Splunk Container]
(Dashboard & Alerts Triggered)


1.  **Validation:** The Lambda backend verifies the incoming payload's Cloudflare token and assesses the honeypot field.
2.  **Verification:** The backend processes DNS validations and scans for disposable email domains.
3.  **Fulfillment & Logging:** 
    * An automated confirmation receipt is sent to the customer via Amazon SES.
    * A fulfillment alert is sent to the merchant to trigger physical shipping workflows.
    * Structured, clean event logs are formatted and written out to the S3 logging pipeline for Splunk ingestion.

---

## 🛠️ Deployment & Environment Notes
* **Access Control:** Both the application S3 bucket and the backend Lambda function are explicitly private. Communication is strictly limited to the CloudFront Service Principal via IAM policies.
* **Secrets Management:** Sensitive API keys, credentials, and environmental variables are injected securely within the AWS Lambda runtime configuration, keeping the codebase zero-trust and clean.
* **Local Lab Lifecycle:** To spin down the monitoring workspace and avoid running costly resources indefinitely, use the included teardown scripts to purge local Docker volumes and execute a clean `terraform destroy`.
