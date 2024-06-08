from email.encoders import encode_base64
from email.mime.base import MIMEBase
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
for key in ['password', 'recipient_email', 'sender_email', 'smtp_server',
            'ssl_port', 'username']:
    if key not in config:
        msg = f'missing {key=!r} in smtp config file {smtp_config!r}'
        logger.error(msg)
        raise ValueError(msg)
password = config['password']
recipient_email = config['recipient_email']
sender_email = config['sender_email']
smtp_server = config['smtp_server']
ssl_port = config['ssl_port']
text_suffix = config.get('text_suffix', 'From anonymous with love.')
username = config['username']


def send_email(img_path: pathlib.Path, vid_path: pathlib.Path, message):
    logger.info('sending email %r to %r, from %r',
                message, recipient_email, sender_email)
    msg = MIMEMultipart()
    msg['Subject'] = f'nooneissafe - {img_path}'
    msg['From'] = sender_email
    msg['To'] = recipient_email

    text = MIMEText(message, 'plain')
    msg.attach(f'{text}\n{text_suffix}')

    if not img_path.exists():
        logger.warning('image file %s does not exists', img_path)
    elif img_path.stat().st_size > 2**20:
        warn = f'image file {img_path} size is greater than 1MB, skipping'
        text = MIMEText(f'\n{warn}', 'plain')
        msg.attach(text)
        logger.warning(warn)
    else:
        with img_path.open('rb') as f:
            image = MIMEImage(f.read(), name=img_path.name)
            msg.attach(image)

    if not vid_path.exists():
        logger.warning('video file %s does not exists', vid_path)
    elif vid_path.stat().st_size > 15 * 2**20:
        warn = f'video file {vid_path} size is greater than 15MB, skipping'
        text = MIMEText(f'\n{warn}', 'plain')
        msg.attach(text)
        logger.warning(warn)
    else:
        video = MIMEBase('application', 'octet-stream')
        with vid_path.open('rb') as f:
            video.set_payload(f.read())
        encode_base64(video)
        video.add_header('Content-Disposition',
                         f'attachment; filename="{vid_path.name}"')
        msg.attach(video)

    with smtplib.SMTP_SSL(smtp_server, ssl_port) as server:
        server.login(username, password)
        server.sendmail(sender_email, recipient_email, msg.as_string())

    logger.info('email %r sent successfully', message)
