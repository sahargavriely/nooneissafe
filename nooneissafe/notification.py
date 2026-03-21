import json
import logging
import mimetypes
import pathlib
import smtplib
import urllib.request
import uuid
from email.encoders import encode_base64
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


logger = logging.getLogger(__name__)

EMAIL_PROVIDER = 'email'
TELEGRAM_PROVIDER = 'telegram'
DISCORD_PROVIDER = 'discord'
_repo_root = pathlib.Path(__file__).parent.parent
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
            if 'bot_token' in config and 'chat_id' in config:
                provider = TELEGRAM_PROVIDER
            elif ('webhook_url' in config and
                  'discord.com/api/webhooks/' in config['webhook_url']):
                provider = DISCORD_PROVIDER
            else:
                provider = EMAIL_PROVIDER
        return provider, config, _notification_config_path
    msg = f'missing notification config file {_notification_config_path!r}'
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


def _encode_multipart_form_data(fields, files):
    boundary = f'----NoOneIsSafeBoundary{uuid.uuid4().hex}'
    body = bytearray()
    for field_name, value in fields.items():
        if value is None:
            continue
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        disposition = f'Content-Disposition: form-data; name="{field_name}"'
        body.extend(f'{disposition}\r\n\r\n'.encode('utf-8'))
        body.extend(str(value).encode('utf-8'))
        body.extend(b'\r\n')
    for field_name, file_path in files:
        mime_type = mimetypes.guess_type(file_path.name)[0]
        if mime_type is None:
            mime_type = 'application/octet-stream'
        with file_path.open('rb') as file_handle:
            payload = file_handle.read()
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        disposition = (
            f'Content-Disposition: form-data; name="{field_name}"; '
            f'filename="{file_path.name}"'
        )
        body.extend(f'{disposition}\r\n'.encode('utf-8'))
        body.extend(f'Content-Type: {mime_type}\r\n\r\n'.encode('utf-8'))
        body.extend(payload)
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    content_type = f'multipart/form-data; boundary={boundary}'
    return bytes(body), content_type


def _post_multipart(url, fields, files, timeout):
    body, content_type = _encode_multipart_form_data(fields, files)
    request = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': content_type},
        method='POST',
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status


def _send_telegram_file(telegram_config, endpoint, field_name, file_path,
                        caption):
    timeout = telegram_config.get('timeout_sec', 10)
    url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/{endpoint}"
    fields = {'chat_id': telegram_config['chat_id'], 'caption': caption}
    if 'parse_mode' in telegram_config:
        fields['parse_mode'] = telegram_config['parse_mode']
    status = _post_multipart(url, fields, [(field_name, file_path)], timeout)
    logger.info('telegram file %s delivered with status %s', file_path, status)


def _send_telegram(img_path, vid_path, message, telegram_config, config_path):
    _validate_keys(telegram_config, ['bot_token', 'chat_id'], config_path)
    sent_any_file = False
    caption = message
    if img_path.exists():
        _send_telegram_file(telegram_config, 'sendPhoto', 'photo', img_path,
                            caption)
        sent_any_file = True
        caption = None
    else:
        logger.warning('image file %s does not exists', img_path)
    if vid_path.exists():
        _send_telegram_file(telegram_config, 'sendDocument', 'document',
                            vid_path, caption)
        sent_any_file = True
    else:
        logger.warning('video file %s does not exists', vid_path)
    if not sent_any_file:
        msg = f'no files to send via telegram for {img_path} and {vid_path}'
        logger.error(msg)
        raise FileNotFoundError(msg)


def _send_discord(img_path, vid_path, message, discord_config, config_path):
    _validate_keys(discord_config, ['webhook_url'], config_path)
    timeout = discord_config.get('timeout_sec', 10)
    file_paths = []
    if img_path.exists():
        file_paths.append(img_path)
    else:
        logger.warning('image file %s does not exists', img_path)
    if vid_path.exists():
        file_paths.append(vid_path)
    else:
        logger.warning('video file %s does not exists', vid_path)
    if not file_paths:
        msg = f'no files to send via discord for {img_path} and {vid_path}'
        logger.error(msg)
        raise FileNotFoundError(msg)
    files = [(f'files[{i}]', path) for i, path in enumerate(file_paths)]
    payload = {'content': message}
    if 'username' in discord_config:
        payload['username'] = discord_config['username']
    if 'avatar_url' in discord_config:
        payload['avatar_url'] = discord_config['avatar_url']
    status = _post_multipart(
        discord_config['webhook_url'],
        {'payload_json': json.dumps(payload)},
        files,
        timeout,
    )
    logger.info('discord notification delivered with status %s', status)


def send_notification(img_path: pathlib.Path, vid_path: pathlib.Path, message):
    provider, config, config_path = _load_provider_config()
    if provider == EMAIL_PROVIDER:
        send_email(img_path, vid_path, message, config, config_path)
        return
    if provider == TELEGRAM_PROVIDER:
        _send_telegram(img_path, vid_path, message, config, config_path)
        return
    if provider == DISCORD_PROVIDER:
        _send_discord(img_path, vid_path, message, config, config_path)
        return
    msg = f'unsupported notification provider {provider!r} in {config_path!r}'
    logger.error(msg)
    raise ValueError(msg)
