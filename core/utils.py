
import random
import threading
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
import datetime

def generate_otp_code(length=6):
    """Generate a numeric OTP of given length."""
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])


class EmailThread(threading.Thread):
    def __init__(self, email):
        super().__init__()
        self.email = email

    def run(self):
        self.email.send(fail_silently=False)


def send_otp_email(verification_code, to_email, fullname):
    subject = 'Verification Code For Simtech Auctions'
    from_email = 'gift200161@gmail.com'  # Update if you have a new sender email

    # Render HTML content from template
    html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Email OTP</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f4;
                }}
                .container {{
                    width: 100%;
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.1);
                }}
                .header {{
                    background-color: #003366;
                    color: #ffffff;
                    padding: 20px;
                    text-align: center;
                    font-size: 28px;
                    font-weight: bold;
                    letter-spacing: 1px;
                }}
                .content {{
                    padding: 30px;
                    text-align: center;
                }}
                .otp-code {{
                    font-size: 36px;
                    font-weight: bold;
                    color: #003366;
                    margin: 20px 0;
                    letter-spacing: 2px;
                }}
                .message {{
                    font-size: 16px;
                    color: #333333;
                    margin-bottom: 30px;
                    line-height: 1.5;
                }}
                .footer {{
                    background-color: #003366;
                    padding: 15px;
                    text-align: center;
                    color: #ffffff;
                    font-size: 14px;
                }}
                .footer a {{
                    color: #ffffff;
                    text-decoration: none;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    Simtech Auctions
                </div>
                <div class="content">
                    <p class="message">Hello, {fullname}</p>
                    <p class="message">
                        Please use the verification code below to complete your registration 
                        on Simtech Auctions:
                    </p>
                    <div class="otp-code">{verification_code}</div>
                    <p class="message">
                        This code is valid for the next 30 minutes. 
                        Please do not share this code with anyone for security reasons.
                    </p>
                </div>
                <div class="footer">
                    <p>&copy; {datetime.date.today().year} Simtech Auctions. All rights reserved.</p>
                    <p>If you did not request this code, please <a href="#">contact support</a>.</p>
                </div>
            </div>
        </body>
        </html>
    """
    text_content = strip_tags(html_content)  # Fallback for email clients that don't support HTML

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")

    # Send the email in a separate thread
    EmailThread(email).start()