import logging
import smtplib
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


logger = logging.getLogger(__name__)


def send_email(img_path, vid_path, message, smtp_config):
    required_smtp_keys = ['password', 'recipient_email', 'sender_email',
                          'smtp_server', 'ssl_port', 'username']
    for key in required_smtp_keys:
        if key not in smtp_config:
            msg = f'missing {key=!r} in email provider config'
            logger.error(msg)
            raise ValueError(msg)

    password = smtp_config['password']
    recipient_email = smtp_config['recipient_email']
    sender_email = smtp_config['sender_email']
    smtp_server = smtp_config['smtp_server']
    ssl_port = smtp_config['ssl_port']
    username = smtp_config['username']
    text_suffix = smtp_config.get('text_suffix', 'From anonymous with love.')

    logger.info('sending email %r to %r, from %r',
                message, recipient_email, sender_email)
    msg = MIMEMultipart()
    msg['Subject'] = f'nooneissafe - {img_path}'
    msg['From'] = sender_email
    msg['To'] = recipient_email

    text = MIMEText(f'{message}\n{text_suffix}', 'plain')
    msg.attach(text)

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

