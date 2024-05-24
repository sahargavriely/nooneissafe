from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import json
import logging
import pathlib
import smtplib


logger = logging.getLogger(__name__)

smtp_config = pathlib.Path(__file__).parent.parent / 'smtp_config.json'
with smtp_config.open('r') as file:
    config = json.load(file)
    for key in ['message', 'password', 'recipient_email', 'sender_email',
                'smtp_server', 'ssl_port', 'username']:
        if key not in config:
            msg = f'missing {key!r} in smtp config file {smtp_config!r}'
            logger.error(msg)
            raise ValueError(msg)
smtp_server = config['smtp_server']
ssl_port = config['ssl_port']
username = config['username']
password = config['password']
sender_email = config['sender_email']
recipient_email = config['recipient_email']
message = config['message']


def send_email(img_path: pathlib.Path):
    logger.info('sending email %s to %r, from %r',
                img_path, recipient_email, sender_email)
    msg = MIMEMultipart()
    msg['Subject'] = f'nooneissafe - {img_path}'
    msg['From'] = sender_email
    msg['To'] = recipient_email

    text = MIMEText(message, 'plain')
    msg.attach(text)

    if img_path.exists():
        with img_path.open('rb') as f:
            image = MIMEImage(f.read(), name=img_path.name)
            msg.attach(image)
    else:
        logger.warning('image file %s does not exists', img_path)

    with smtplib.SMTP_SSL(smtp_server, ssl_port) as server:
        server.login(username, password)
        server.sendmail(sender_email, recipient_email, msg.as_string())

    logger.info('email %s sent successfully', img_path)
