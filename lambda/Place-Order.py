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
from disposable_email_domains import blocklist

app = FastAPI(root_path="/api",
              docs_url=None,
            redoc_url=None,
            openapi_url=None)


# ============================================
# BUSINESS EMAIL ENV
BUSINESS_EMAIL = os.getenv('BUSINESS_EMAIL')
NO_REPLY_EMAIL = os.getenv('NO_REPLY_EMAIL')
SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL')

# CLOUDFLARE KEY
CLOUDFLARE_KEY = os.getenv('CLOUDFLARE_KEY')

# Initialize AWS SES client
ses_client = boto3.client('ses', region_name='us-east-1')  # Change to your region

# Phone number validation pattern
PHONE_PATTERN = re.compile(r'^(\+?1 *[ -.])?(\d{3}) *[ .-]?(\d{3}) *[ .-]?(\d{4}) *$')

# ============================================
# PYDANTIC MODELS
# ============================================

class CartItem(BaseModel):
    """Individual cart item"""
    qty: int = Field(gt=0, description="Quantity must be greater than 0")
    price: float = Field(ge=0, description="Price must be non-negative")
    pricePerUnit: float = Field(ge=0, description="Price per unit must be non-negative")
    imageUrl: str


class Cart(BaseModel):
    """Cart model with items and totals"""
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
        """Verify that totalPrice matches sum of item prices"""
        if 'items' in values:
            calculated_total = sum(item.price for item in values['items'].values())
            # Allow small floating point differences
            if abs(calculated_total - v) > 0.01:
                raise ValueError("Total price does not match sum of item prices")
        return v
    
    @validator('totalQty')
    def validate_total_qty(cls, v, values):
        """Verify that totalQty matches sum of item quantities"""
        if 'items' in values:
            calculated_qty = sum(item.qty for item in values['items'].values())
            if calculated_qty != v:
                raise ValueError("Total quantity does not match sum of item quantities")
        return v


class OrderRequest(BaseModel):
    """Request model for checkout"""
    phone: str
    email: EmailStr
    verification: str  # honeypot field
    shipping: str
    order: Cart  # Now directly a Cart object, Pydantic handles parsing
    cf_token: str #cloudflare turnstile
    
    @validator('phone')
    def validate_phone_format(cls, v):
        if not PHONE_PATTERN.match(v):
            raise ValueError("Please enter a valid phone number.")
        return v


# ============================================
# VALIDATION FUNCTIONS
# ============================================

def validate_business_hours() -> tuple[bool, str]:
    """
    Check if current time is within business hours
    Returns: (is_valid, error_message)
    """
    # Get current time in Eastern timezone
    eastern = pytz.timezone('America/New_York')
    now = datetime.now(eastern)
    
    current_day = now.strftime('%A')  # Monday, Tuesday, etc.
    current_hour = now.hour
    
    # Check if it's Sunday
    if current_day == 'Sunday':
        return False, 'Our business hours are Mon-Sat 8am-8pm.'
    
    # Check if hour is outside 8am-8pm (8-20 in 24hr format)
    if current_hour < 8 or current_hour >= 20:
        return False, 'Our business hours are Mon-Sat 8am-8pm.'
    
    return True, ''


# ============================================
# EMAIL TEMPLATE FUNCTIONS
# ============================================
def create_product_html(name: str, price: float, image_url: str, qty: int) -> str:
    """Generate HTML for a single product using tables for stability"""
    return f'''
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin: 16px 0; border-bottom: 1px solid #e0e0e0;">
        <tr>
            <td style="width: 80px; padding-bottom: 16px; vertical-align: top;">
                <img src="{image_url}" width="80" height="80" style="display: block; object-fit: contain; border-radius: 4px; border: 1px solid #f0f0f0;" alt="{name}">
            </td>
            
            <td style="padding: 0 12px 16px 12px; vertical-align: top;">
                <h4 style="margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: #333;">{name}</h4>
                <p style="margin: 0; font-size: 14px; font-weight: 600; color: #2e7d32;">${price:.2f}</p>
            </td>
            
            <td style="width: 60px; padding-bottom: 16px; vertical-align: top; text-align: right;">
                <span style="font-size: 14px; color: #666; font-weight: bold;">Qty: {qty}</span>
            </td>
        </tr>
    </table>
    '''


def create_order_html(products: list, total_qty: int, total_price: float, 
                     email: str, phone: str, shipping: str, order_id: str) -> str:
    """Generate complete HTML email template"""
    products_html = ''.join(products)
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>New Order</title>
    </head>
    <body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background-color: #2e7d32; padding: 30px 20px; text-align: center;">
                <h2 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">New Order Received</h2>
                <p style="margin: 10px 0 0 0; color: #c8e6c9; font-size: 14px;">Order ID: {order_id}</p>
            </div>
            
            <!-- Products Section -->
            <div style="padding: 30px 20px;">
                <h3 style="margin: 0 0 20px 0; font-size: 20px; color: #333; font-weight: 600;">Order Items</h3>
                {products_html}
            </div>
            
            <!-- Total Section -->
            <div style="margin: 20px; padding: 24px; background-color: #f9f9f9; border-radius: 8px; border: 1px solid #e0e0e0;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <p style="margin: 0 0 8px 0; font-size: 18px; color: #666;">{total_qty} Item{"s" if total_qty != 1 else ""}</p>
                    <p style="margin: 0; font-size: 24px; font-weight: 700; color: #2e7d32;">Total: ${total_price:.2f}</p>
                </div>
                
                <!-- Customer Details -->
                <div style="padding-top: 20px; border-top: 1px solid #e0e0e0;">
                    <h4 style="margin: 0 0 16px 0; font-size: 16px; color: #333; font-weight: 600;">Customer Information</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; font-weight: 600; color: #666; font-size: 14px; width: 100px;">Email:</td>
                            <td style="padding: 8px 0; color: #333; font-size: 14px;">{email}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: 600; color: #666; font-size: 14px;">Phone:</td>
                            <td style="padding: 8px 0; color: #333; font-size: 14px;">{phone}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; font-weight: 600; color: #666; font-size: 14px;">Shipping:</td>
                            <td style="padding: 8px 0; color: #333; font-size: 14px;">{shipping}</td>
                        </tr>
                    </table>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="padding: 20px; text-align: center; background-color: #fafafa; border-top: 1px solid #e0e0e0;">
                <p style="margin: 0; color: #999; font-size: 12px;">This is an automated order notification</p>
            </div>
            
        </div>
    </body>
    </html>
    '''


def create_customer_confirmation_html(products: list, total_qty: int, total_price: float, 
                                     order_id: str) -> str:
    """Generate customer confirmation email"""
    products_html = ''.join(products)
    
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Order Confirmation</title>
    </head>
    <body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #2e7d32 0%, #43a047 100%); padding: 40px 20px; text-align: center;">
                <h2 style="margin: 0; font-size: 28px; color: #ffffff; font-weight: 600;">Thank You for Your Order! 🎉</h2>
                <p style="margin: 12px 0 0 0; color: #c8e6c9; font-size: 14px;">Order ID: {order_id}</p>
            </div>
            
            <!-- Products Section -->
            <div style="padding: 30px 20px;">
                <h3 style="margin: 0 0 20px 0; font-size: 20px; color: #333; font-weight: 600; text-align: center;">Your Order Summary</h3>
                {products_html}
            </div>
            
            <!-- Total Section -->
            <div style="margin: 20px; padding: 24px; background-color: #f9f9f9; border-radius: 8px; border: 2px solid #2e7d32; text-align: center;">
                <p style="margin: 0 0 8px 0; font-size: 18px; color: #666;">{total_qty} Item{"s" if total_qty != 1 else ""}</p>
                <p style="margin: 0; font-size: 28px; font-weight: 700; color: #2e7d32;">Total: ${total_price:.2f}</p>
            </div>
            
            <!-- Confirmation Message -->
            <div style="margin: 20px; padding: 24px; background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-radius: 8px; text-align: center;">
                <p style="margin: 0; color: #1b5e20; font-weight: 600; font-size: 16px; line-height: 1.5;">
                    We've received your order and will contact you soon to confirm delivery details!
                </p>
            </div>
            
            <!-- Footer -->
            <div style="padding: 24px 20px; text-align: center; background-color: #fafafa; border-top: 1px solid #e0e0e0;">
                <p style="margin: 0 0 8px 0; color: #666; font-size: 14px;">Questions about your order?</p>
                <p style="margin: 0; color: #2e7d32; font-size: 14px; font-weight: 600;">Contact us at ${SUPPORT_EMAIL}</p>
            </div>
            
        </div>
    </body>
    </html>
    '''


# ============================================
# EMAIL SENDING FUNCTION
# ============================================

def is_domain_real(email):
    try:
        # Extract domain from email (e.g., "user@gmail.com" -> "gmail.com")
        domain = email.split('@')[-1]

        
        if domain in blocklist:
            print(f"BLOCKLIST: Caught disposable email domain: {domain}")
            return False

        # Check for MX Records (The most important check for SES)
        mx_records = dns.resolver.resolve(domain, 'MX')
        if not mx_records:
            return False
            
        #  Check for Nameservers (Optional "Strict" check)
        ns_records = dns.resolver.resolve(domain, 'NS')
        if not ns_records:
            return False

        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, Exception):
        # NXDOMAIN means the domain doesn't even exist
        return False


async def send_order_emails(order_data: OrderRequest, order_id: str) -> bool:
    """
    Send order confirmation emails via AWS SES
    Returns: True if successful, False otherwise
    """
    try:
        # Build product HTML list
        product_html_list = []
        for item_name, item_data in order_data.order.items.items():
            product_html = create_product_html(
                name=item_name,
                price=item_data.price,
                image_url=item_data.imageUrl,
                qty=item_data.qty
            )
            product_html_list.append(product_html)
        
        # Create email HTML for business owner
        owner_email_html = create_order_html(
            products=product_html_list,
            total_qty=order_data.order.totalQty,
            total_price=order_data.order.totalPrice,
            email=order_data.email,
            phone=order_data.phone,
            shipping=order_data.shipping,
            order_id=order_id
        )
        
        # Create email HTML for customer
        customer_email_html = create_customer_confirmation_html(
            products=product_html_list,
            total_qty=order_data.order.totalQty,
            total_price=order_data.order.totalPrice,
            order_id=order_id
        )
        
        # Send email to business owner
        ses_client.send_email(
            Source=NO_REPLY_EMAIL,  # Must be verified in SES
            Destination={
                'ToAddresses': [BUSINESS_EMAIL]  # Your business email
            },
            Message={
                'Subject': {
                    'Data': f'New Order Received - {order_id}',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': owner_email_html,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        # Send confirmation email to customer
        ses_client.send_email(
            Source=NO_REPLY_EMAIL,  # Must be verified in SES
            Destination={
                'ToAddresses': [order_data.email.lower()]
            },
            Message={
                'Subject': {
                    'Data': f'Order Confirmation - {order_id}',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': customer_email_html,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        return True
        
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

# ============================================
# CLOUDFLARE VALIDATION
# ============================================
async def verify_turnstile_token(token: str):
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    
    # Use an async client
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data={
            "secret": CLOUDFLARE_KEY,
            "response": token,
        })
        
        result = response.json()
        return result.get("success", False)



# ============================================
# API ENDPOINTS
# ============================================

@app.post("/order")
async def process_order(order_request: OrderRequest,request: Request):
    """
    Process order submission
    Validates data, sends emails, and returns order ID
    """
    
    try:
        client_ip = request.client.host
        # Validate business hours
        is_valid_hours, hours_error = validate_business_hours()
        if not is_valid_hours:
            raise HTTPException(status_code=400, detail=hours_error)
        
        # Generate unique order ID
        order_id = str(uuid.uuid4())[:8].upper()
        
        # Check Honeypot field verification
        if order_request.verification:
            print(f"HONEYPOT TRIGGERED: Bot at {client_ip} sent '{order_request.verification}'")
            return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "orderId": order_id,
                "message": "Order placed successfully"
            }
        )
        # Now you can use 'await' properly
        is_human = await verify_turnstile_token(order_request.cf_token)
        
        if not is_human:
            raise HTTPException(status_code=400, detail="Security check failed")
        
        # Name server and Mail ecahnge check and SES will check the final email
        if not is_domain_real(order_request.email.lower()):
            print(f"SECURITY: Blocked invalid email domain: {order_request.email}")
            raise HTTPException(status_code=400, detail="Please provide a valid email address.")
        
        # Send emails
        email_sent = await send_order_emails(
            order_data=order_request,
            order_id=order_id
        )
        
        if not email_sent:
            raise HTTPException(
                status_code=500,
                detail="Failed to send order confirmation. Please try again."
            )
        
        # Return success with order ID
        # Frontend will use this to redirect to success page
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "orderId": order_id,
                "message": "Order placed successfully"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing order: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Network error. Please try again."
        )


# ============================================
# LAMBDA HANDLER
# ============================================

# Mangum adapter for AWS Lambda
lambda_handler = Mangum(app)
