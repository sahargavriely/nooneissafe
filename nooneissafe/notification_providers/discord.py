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
    user_agent = discord_config.get('user_agent', 'curl/8.6.0')
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
    text_suffix = discord_config.get('text_suffix', 'From anonymous with love.')
    base_payload = {'content': f'{message}\n{text_suffix}'}
    if 'username' in discord_config:
        base_payload['username'] = discord_config['username']
    if 'avatar_url' in discord_config:
        base_payload['avatar_url'] = discord_config['avatar_url']

    for index, file_path in enumerate(file_paths):
        payload = dict(base_payload)
        if index > 0:
            payload['content'] = None
        status = post_multipart(
            discord_config['webhook_url'],
            {'payload_json': json.dumps(payload)},
            [('files[0]', file_path)],
            timeout,
            headers={
                'User-Agent': user_agent,
                'Accept': 'application/json',
            },
        )
        logger.info('discord file %s delivered with status %s',
                    file_path, status)

