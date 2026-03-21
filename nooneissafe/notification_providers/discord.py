import json
import logging

from ..utils import post_multipart


logger = logging.getLogger(__name__)


def send_discord(img_path, vid_path, message, discord_config):
    if 'webhook_url' not in discord_config:
        msg = "missing 'webhook_url' in discord provider config"
        logger.error(msg)
        raise ValueError(msg)

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
    files = [(f'file{i + 1}', path) for i, path in enumerate(file_paths)]

    text_suffix = discord_config.get('text_suffix', 'From anonymous with love.')
    payload = {'content': f'{message}\n{text_suffix}'}
    if 'username' in discord_config:
        payload['username'] = discord_config['username']
    if 'avatar_url' in discord_config:
        payload['avatar_url'] = discord_config['avatar_url']
    status = post_multipart(
        discord_config['webhook_url'],
        {'payload_json': json.dumps(payload)},
        files,
        timeout,
    )
    logger.info('discord notification delivered with status %s', status)

