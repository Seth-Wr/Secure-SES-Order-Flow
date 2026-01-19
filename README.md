Cloud-Native Serverless Order Fulfillment System
A high-performance, production-ready order fulfillment engine built with a security-first serverless architecture. This system leverages AWS best practices to ensure low latency, high availability, and proactive protection against bots and email reputation damage.

Site Link
https://www.nufjuice.com

🏗️ Architecture Overview
The system is designed to be entirely serverless, minimizing overhead while maximizing security:

Static Hosting: Vanilla JavaScript frontend hosted on Amazon S3, completely locked down from public access using Origin Access Control (OAC).

API Layer: FastAPI (Python) running on AWS Lambda, handling order logic, security verification, and fulfillment.

Global Distribution: Amazon CloudFront acts as the single entry point. It serves the static frontend and proxies API requests to the private Lambda function.

Edge Protection: AWS WAF sits in front of CloudFront to filter malicious traffic and common web exploits.

Encryption: Secured with SSL/TLS certificates via AWS Certificate Manager for all data in transit.

🛡️ Multi-Layer Security & Verification
This project implements a "Defense in Depth" strategy to ensure only legitimate orders are processed.

Bot Mitigation

Cloudflare Managed CAPTCHA: Integrated to verify human interaction before order submission.

Honeypot Logic: A hidden field within the frontend that, if populated, allows the backend to identify and reject automated bot submissions.

Email Reputation Management

Maintaining a high Amazon SES sending reputation is critical. The backend performs the following checks before sending any emails:

MX & NS Lookup: Verifies that the recipient's domain is valid and capable of receiving mail.

Disposable Email Filtering: Cross-references the user's email against a list of known temporary/burner email providers.

CloudWatch Alarms: Real-time monitoring for Bounce Rates and Complaint Rates, with automated alerts to ensure the SES production account remains in good standing.

🚀 Technical Stack
Component	Technology
Backend	Python, FastAPI
Frontend	Vanilla JS, HTML5, CSS3
Compute	AWS Lambda
Content Delivery	Amazon CloudFront (OAC Secured)
Storage	Amazon S3 & LocalStorage (State management)
Email	Amazon SES (Production Mode)
Security	AWS WAF, Cloudflare CAPTCHA, SSL/TLS
📩 Fulfillment Workflow
Validation: The system verifies the Cloudflare token and ensures the honeypot field is empty.

Verification: The backend performs DNS lookups (MX/NS records) and filters out disposable email addresses.

Fulfillment:

Customer Receipt: An automated confirmation is sent to the customer via SES.

Merchant Alert: A second, detailed email is sent to the business owner to trigger the physical fulfillment process.

🛠️ Deployment Notes
This project is deployed using a cloud-native manual configuration:

Origins: Both the S3 bucket and Lambda function are private. Access is granted exclusively to the CloudFront Service Principal.

Environment: All sensitive configurations and credentials are managed internally within the AWS Lambda environment to keep the source code clean and secure.
