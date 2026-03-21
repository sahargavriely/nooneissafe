import json
import logging
import pathlib
import smtplib
import urllib.parse
import urllib.request
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


logger = logging.getLogger(__name__)

EMAIL_PROVIDER = 'email'
WEBHOOK_PROVIDER = 'webhook'
TELEGRAM_PROVIDER = 'telegram'
_repo_root = pathlib.Path(__file__).parent.parent
_legacy_smtp_config_path = _repo_root / 'smtp_config.json'
_notification_config_path = _repo_root / 'notification_config.json'
_required_smtp_keys = ['password', 'recipient_email', 'sender_email',
                       'smtp_server', 'ssl_port', 'username']


def _load_json(path):
    with path.open('r') as file:
        return json.load(file)


def _validate_keys(config, required_keys, config_path):
    for key in required_keys:
        if key not in config:
            msg = f'missing {key=!r} in config file {config_path!r}'
            logger.error(msg)
            raise ValueError(msg)


def _load_provider_config():
    if _notification_config_path.exists():
        config = _load_json(_notification_config_path)
        provider = config.get('provider')
        if provider is None:
            if 'webhook_url' in config:
                provider = WEBHOOK_PROVIDER
            elif 'bot_token' in config and 'chat_id' in config:
                provider = TELEGRAM_PROVIDER
            else:
                provider = EMAIL_PROVIDER
        return provider, config, _notification_config_path
    if _legacy_smtp_config_path.exists():
        return (EMAIL_PROVIDER, _load_json(_legacy_smtp_config_path),
                _legacy_smtp_config_path)
    msg = ('missing notification config file: expected '
           f'{_notification_config_path!r} or {_legacy_smtp_config_path!r}')
    logger.error(msg)
    raise FileNotFoundError(msg)


def send_email(img_path: pathlib.Path, vid_path: pathlib.Path, message,
               smtp_config: dict, config_path: pathlib.Path):
    _validate_keys(smtp_config, _required_smtp_keys, config_path)
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


def _send_webhook(img_path: pathlib.Path, vid_path: pathlib.Path, message,
                  webhook_config: dict, config_path: pathlib.Path):
    _validate_keys(webhook_config, ['webhook_url'], config_path)
    headers = {'Content-Type': 'application/json'}
    headers.update(webhook_config.get('headers', {}))
    payload = {
        'message': message,
        'image_path': str(img_path),
        'video_path': str(vid_path),
    }
    timeout = webhook_config.get('timeout_sec', 10)
    request = urllib.request.Request(
        webhook_config['webhook_url'],
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        logger.info('webhook notification delivered with status %s',
                    response.status)


def _send_telegram(message, telegram_config, config_path):
    _validate_keys(telegram_config, ['bot_token', 'chat_id'], config_path)
    timeout = telegram_config.get('timeout_sec', 10)
    endpoint = (
        f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
    )
    payload = {
        'chat_id': telegram_config['chat_id'],
        'text': message,
    }
    if 'parse_mode' in telegram_config:
        payload['parse_mode'] = telegram_config['parse_mode']
    data = urllib.parse.urlencode(payload).encode('utf-8')
    request = urllib.request.Request(endpoint, data=data, method='POST')
    with urllib.request.urlopen(request, timeout=timeout) as response:
        logger.info('telegram notification delivered with status %s',
                    response.status)


def send_notification(img_path: pathlib.Path, vid_path: pathlib.Path, message):
    provider, config, config_path = _load_provider_config()
    if provider == EMAIL_PROVIDER:
        send_email(img_path, vid_path, message, config, config_path)
        return
    if provider == WEBHOOK_PROVIDER:
        _send_webhook(img_path, vid_path, message, config, config_path)
        return
    if provider == TELEGRAM_PROVIDER:
        _send_telegram(message, config, config_path)
        return
    msg = f'unsupported notification provider {provider!r} in {config_path!r}'
    logger.error(msg)
    raise ValueError(msg)
