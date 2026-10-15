import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class EmailManager:
    def __init__(self, sender_email, sender_password, smtp_server="smtp.gmail.com", port=587):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.smtp_server = smtp_server
        self.port = port

    def send_email(self, subject, body, recipient_email):
        message = MIMEMultipart()
        message["From"] = self.sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(self.smtp_server, self.port) as server:
            server.starttls()
            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, recipient_email, message.as_string())
            server.quit()

    # def read_email(): function could be added here.
    def read_emails(self, subject_filter):
        """Read emails from the inbox with a specific subject filter."""
        mail = imaplib.IMAP4_SSL(self.imap_server)
        mail.login(self.sender_email, self.sender_password)
        mail.select('inbox')  

        status, messages = mail.search(None, f'(SUBJECT "{subject_filter}")')
        if status != 'OK':
            print("No emails found!")
            return []

        emails = []
        for mail_id in messages[0].split():
            status, data = mail.fetch(mail_id, '(RFC822)')
            if status != 'OK':
                print("Error fetching the email")
                continue

            msg = email.message_from_bytes(data[0][1])
            subject, encoding = decode_header(msg["Subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8')

            from_ = msg.get("From")
            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and part.get("Content-Disposition") is None:
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                if msg.get_content_type() == "text/plain":
                    body = msg.get_payload(decode=True).decode()

            emails.append({
                'subject': subject,
                'from': from_,
                'body': body
            })

        mail.close()
        mail.logout()
        return emails