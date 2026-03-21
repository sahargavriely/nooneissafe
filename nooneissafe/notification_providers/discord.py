import json
import logging

from ..utils import post_multipart


logger = logging.getLogger(__name__)
DEFAULT_MAX_FILE_MB = 8


def send_discord(img_path, vid_path, message, discord_config):
    if 'webhook_url' not in discord_config:
        msg = "missing 'webhook_url' in discord provider config"
        logger.error(msg)
        raise ValueError(msg)

    timeout = discord_config.get('timeout_sec', 10)
    max_file_mb = discord_config.get('max_file_mb', DEFAULT_MAX_FILE_MB)
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
    max_file_size = max_file_mb * 2**20
    filtered_paths = []
    for file_path in file_paths:
        if file_path.stat().st_size > max_file_size:
            logger.warning(
                'discord file %s is bigger than %s MB, skipping',
                file_path,
                max_file_mb,
            )
            continue
        filtered_paths.append(file_path)
    if not filtered_paths:
        msg = (f'no files small enough to send via discord for '
               f'{img_path} and {vid_path}')
        logger.error(msg)
        raise ValueError(msg)

    text_suffix = discord_config.get('text_suffix', 'From anonymous with love.')
    base_payload = {'content': f'{message}\n{text_suffix}'}
    if 'username' in discord_config:
        base_payload['username'] = discord_config['username']
    if 'avatar_url' in discord_config:
        base_payload['avatar_url'] = discord_config['avatar_url']

    for index, file_path in enumerate(filtered_paths):
        payload = dict(base_payload)
        if index > 0:
            payload['content'] = None
        status = post_multipart(
            discord_config['webhook_url'],
            {'payload_json': json.dumps(payload)},
            [('files[0]', file_path)],
            timeout,
        )
        logger.info('discord file %s delivered with status %s',
                    file_path, status)

