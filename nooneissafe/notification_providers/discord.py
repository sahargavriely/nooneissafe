import json
import logging

from ..utils import post_multipart


logger = logging.getLogger(__name__)
DISCORD_WEBHOOK_MAX_FILE_SIZE = 8 * 2**20  # 8 MiB per attachment
DISCORD_USER_AGENT = 'curl/8.6.0'


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

    allowed_paths = []
    for file_path in file_paths:
        if file_path.stat().st_size > DISCORD_WEBHOOK_MAX_FILE_SIZE:
            logger.warning(
                'discord file %s is bigger than webhook limit '
                '(8 MiB), skipping',
                file_path,
            )
            continue
        allowed_paths.append(file_path)
    if not allowed_paths:
        msg = (
            'no files under Discord webhook size limit for '
            f'{img_path}, {vid_path}'
        )
        logger.error(msg)
        raise ValueError(msg)

    text_suffix = discord_config.get(
        'text_suffix',
        'From anonymous with love.',
    )
    base_payload = {'content': f'{message}\n{text_suffix}'}
    if 'username' in discord_config:
        base_payload['username'] = discord_config['username']
    if 'avatar_url' in discord_config:
        base_payload['avatar_url'] = discord_config['avatar_url']

    for index, file_path in enumerate(allowed_paths):
        payload = dict(base_payload)
        if index > 0:
            payload['content'] = None
        status = post_multipart(
            discord_config['webhook_url'],
            {'payload_json': json.dumps(payload)},
            [('files[0]', file_path)],
            timeout,
            headers={
                'User-Agent': DISCORD_USER_AGENT,
                'Accept': 'application/json',
            },
        )
        logger.info('discord file %s delivered with status %s',
                    file_path, status)
