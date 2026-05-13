"""
AWS Lambda handler for processing orders
Uses FastAPI with Mangum adapter and AWS SES for email
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from mangum import Mangum
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Dict
import boto3
import re
from datetime import datetime
import pytz
import uuid
import os
import httpx
import dns.resolver
import logging 
from disposable_email_domains import blocklist


# LOGGING CONFIGURATION

logger = logging.getLogger()
logger.setLevel(logging.INFO)

app = FastAPI(root_path="/api",
            docs_url=None,
            redoc_url=None,
            openapi_url=None)



# BUSINESS EMAIL ENV
BUSINESS_EMAIL = os.getenv('BUSINESS_EMAIL')
NO_REPLY_EMAIL = os.getenv('NO_REPLY_EMAIL')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL')

# CLOUDFLARE KEY
CLOUDFLARE_KEY = os.getenv('CLOUDFLARE_KEY')

# Initialize AWS SES client
ses_client = boto3.client('ses', region_name='us-east-1')

# Phone number validation pattern
PHONE_PATTERN = re.compile(r'^(\+?1 *[ -.])?(\d{3}) *[ .-]?(\d{3}) *[ .-]?(\d{4}) *$')

class CartItem(BaseModel):
    qty: int = Field(gt=0)
    price: float = Field(ge=0)
    pricePerUnit: float = Field(ge=0)
    imageUrl: str

class Cart(BaseModel):
    items: Dict[str, CartItem]
    totalQty: int = Field(ge=0)
    totalPrice: float = Field(ge=0)
    
    @validator('totalQty')
    def validate_min_quantity(cls, v):
        if v < 3:
            raise ValueError("Our minimum order size for delivery is 3 items.")
        return v
    
    @validator('totalPrice')
    def validate_total_price(cls, v, values):
        if 'items' in values:
            calculated_total = sum(item.price for item in values['items'].values())
            if abs(calculated_total - v) > 0.01:
                raise ValueError("Total price does not match sum of item prices")
        return v
    
    @validator('totalQty')
    def validate_total_qty(cls, v, values):
        if 'items' in values:
            calculated_qty = sum(item.qty for item in values['items'].values())
            if calculated_qty != v:
                raise ValueError("Total quantity does not match sum of item quantities")
        return v

class OrderRequest(BaseModel):
    phone: str
    email: EmailStr
    verification: str
    shipping: str
    order: Cart
    cf_token: str
    
    @validator('phone')
    def validate_phone_format(cls, v):
        if not PHONE_PATTERN.match(v):
            raise ValueError("Please enter a valid phone number.")
        return v


# VALIDATION FUNCTIONS


def validate_business_hours() -> tuple[bool, str]:
    try:
        eastern = pytz.timezone('America/New_York')
        now = datetime.now(eastern)
        current_day = now.strftime('%A')
        current_hour = now.hour
        
        logger.info(f"Business hours check: {current_day} at {current_hour}:00")
        
        if current_day == 'Sunday':
            return False, 'Our business hours are Mon-Sat 8am-8pm.'
        
        if current_hour < 8 or current_hour >= 20:
            return False, 'Our business hours are Mon-Sat 8am-8pm.'
        
        return True, ''
    except Exception as e:
        logger.error("Error in validate_business_hours", exc_info=True)
        return False, "Validation error"



def is_domain_real(email):
    domain = email.split('@')[-1]
    try:
        if domain in blocklist:
            logger.warning(f"BLOCKLIST: Caught disposable email domain: {domain}")
            return False

        mx_records = dns.resolver.resolve(domain, 'MX')
        if not mx_records:
            logger.warning(f"MX RECORDS: No MX records found for: {domain}")
            return False
            
        ns_records = dns.resolver.resolve(domain, 'NS')
        if not ns_records:
            logger.warning(f"NAMESERVERS: No nameservers found for: {domain}")
            return False

        return True
    except Exception as e:
        logger.error(f"DNS ERROR: Could not resolve domain: {domain} - {str(e)}")
        return False


async def send_order_emails(order_data: OrderRequest, order_id: str) -> bool:
    try:
        # Build product HTML list
        product_html_list = []
        for item_name, item_data in order_data.order.items.items():
            product_html = create_product_html(
                name=item_name, price=item_data.price,
                image_url=item_data.imageUrl, qty=item_data.qty
            )
            product_html_list.append(product_html)
        
        owner_email_html = create_order_html(
            products=product_html_list, total_qty=order_data.order.totalQty,
            total_price=order_data.order.totalPrice, email=order_data.email,
            phone=order_data.phone, shipping=order_data.shipping, order_id=order_id
        )
        
        customer_email_html = create_customer_confirmation_html(
            products=product_html_list, total_qty=order_data.order.totalQty,
            total_price=order_data.order.totalPrice, order_id=order_id
        )
        
        # Send to Owner
        ses_client.send_email(
            Source=NO_REPLY_EMAIL,
            Destination={'ToAddresses': [BUSINESS_EMAIL]},
            Message={
                'Subject': {'Data': f'New Order Received - {order_id}', 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': owner_email_html, 'Charset': 'UTF-8'}}
            }
        )
        
        # Send to Customer
        ses_client.send_email(
            Source=NO_REPLY_EMAIL,
            Destination={'ToAddresses': [order_data.email.lower()]},
            Message={
                'Subject': {'Data': f'Order Confirmation - {order_id}', 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': customer_email_html, 'Charset': 'UTF-8'}}
            }
        )
        logger.info(f"Emails sent successfully for order {order_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email for {order_id}", exc_info=True)
        return False

# ============================================
# CLOUDFLARE VALIDATION
# ============================================
async def verify_turnstile_token(token: str):
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data={
                "secret": CLOUDFLARE_KEY,
                "response": token,
            })
            result = response.json()
            success = result.get("success", False)
            if not success:
                logger.warning(f"Turnstile validation failed: {result.get('error-codes')}")
            return success
    except Exception as e:
        logger.error("Turnstile API error", exc_info=True)
        return False


# API ENDPOINTS


@app.post("/order")
async def process_order(order_request: OrderRequest, request: Request):
    client_ip = request.client.host
    logger.info(f"Processing order request from IP: {client_ip}")

    try:
        # Validate business hours
        is_valid_hours, hours_error = validate_business_hours()
        if not is_valid_hours:
            logger.info(f"Access denied for {client_ip}: Outside business hours")
            raise HTTPException(status_code=400, detail=hours_error)
        
        order_id = str(uuid.uuid4())[:8].upper()
        
        # Honeypot check
        if order_request.verification:
            logger.warning(f"HONEYPOT TRIGGERED: Bot at {client_ip} filled hidden field.")
            # Return fake success to bots
            return {"success": True, "orderId": order_id, "message": "Order placed successfully"}

        # Cloudflare check
        is_human = await verify_turnstile_token(order_request.cf_token)
        if not is_human:
            logger.info(f"Security check failed for IP: {client_ip}")
            raise HTTPException(status_code=400, detail="Security check failed")
        
        # Email domain check
        if not is_domain_real(order_request.email.lower()):
            logger.info(f"Invalid email domain blocked: {order_request.email}")
            raise HTTPException(status_code=400, detail="Please provide a valid email address.")
        
        # Send emails
        email_sent = await send_order_emails(order_data=order_request, order_id=order_id)
        
        if not email_sent:
            raise HTTPException(status_code=500, detail="Failed to send confirmation. Please try again.")
        
        logger.info(f"Order {order_id} completed successfully for {order_request.email}")
        return {"success": True, "orderId": order_id, "message": "Order placed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing order for IP {client_ip}", exc_info=True)
        raise HTTPException(status_code=500, detail="Network error. Please try again.")

lambda_handler = Mangum(app)
