import smtplib
from email.utils import formataddr


SMTP_NOTIFICATIONS = True
# Email configuration
SMTP_SERVER = None #"smtp.example.com"
SMTP_PORT = None #587
EMAIL_USER = None #"your-email@example.com"
EMAIL_PASS = None #"your-email-password" Depending on your environment it could be good practive to put this in a secrets-file
RECIPIENTS = None #["recipient1@example.com", "recipient2@example.com"]

def send_email(subject, message):
    """
    Sends a plain-text email using smtplib.
    
    Args:
        subject (str): The subject of the email.
        message (str): The plain-text message body.
    """
    try:
        # Set up the SMTP server and start TLS encryption

        # Initialize SMTP connection
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            #server.starttls()  # Upgrade connection to secure # OBS disable this if needed

            # Log in to the SMTP server
            server.login(EMAIL_USER, EMAIL_PASS)

            # Formatted sender
            formatted_sender = formataddr(('Lumiere Archiver', EMAIL_USER))
            # Construct email header
            header = f'To: {RECIPIENTS}\nFrom: {formatted_sender}\n'

            # Construct the email
            email_body = f"Subject: {subject}\n\n{message}"

            # Send the email
            server.sendmail(from_addr=EMAIL_USER, to_addrs=RECIPIENTS, msg=header+email_body) 
            print(f"Email sent successfully to {RECIPIENTS}")

    except Exception as e:
        print(f"Failed to send email: {e}")


send_email("New mail!", "New mail!")