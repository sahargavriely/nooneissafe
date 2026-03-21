import logging

from ..utils import post_multipart


logger = logging.getLogger(__name__)


def _send_telegram_file(telegram_config, endpoint, field_name, file_path,
                        caption):
    timeout = telegram_config.get('timeout_sec', 10)
    url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/{endpoint}"
    fields = {'chat_id': telegram_config['chat_id'], 'caption': caption}
    if 'parse_mode' in telegram_config:
        fields['parse_mode'] = telegram_config['parse_mode']
    status = post_multipart(url, fields, [(field_name, file_path)], timeout)
    logger.info('telegram file %s delivered with status %s', file_path, status)


def send_telegram(img_path, vid_path, message, telegram_config):
    for key in ['bot_token', 'chat_id']:
        if key not in telegram_config:
            msg = f'missing {key=!r} in telegram provider config'
            logger.error(msg)
            raise ValueError(msg)

    sent_any_file = False
    text_suffix = telegram_config.get('text_suffix', 'From anonymous with love.')
    caption = f'{message}\n{text_suffix}'
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

