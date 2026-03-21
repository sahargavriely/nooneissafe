import contextlib
import json
import logging
import pathlib
import subprocess
import tempfile

from ..utils import post_multipart


logger = logging.getLogger(__name__)
DISCORD_WEBHOOK_MAX_FILE_SIZE = 8 * 2**20  # 8 MiB per attachment
DISCORD_USER_AGENT = 'curl/8.6.0'


def _prepare_discord_video_file(vid_path, timeout):
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
        output_path = pathlib.Path(tmp.name)
    ffmpeg_timeout = max(timeout, 60)
    ffmpeg_cmd = [
        'ffmpeg',
        '-y',
        '-i',
        str(vid_path),
        '-an',
        '-c:v',
        'libx264',
        '-profile:v',
        'baseline',
        '-level',
        '3.1',
        '-pix_fmt',
        'yuv420p',
        '-preset',
        'veryfast',
        '-crf',
        '27',
        '-movflags',
        '+faststart',
        '-vf',
        'scale=trunc(iw/2)*2:trunc(ih/2)*2',
        str(output_path),
    ]
    try:
        subprocess.run(
            ffmpeg_cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=ffmpeg_timeout,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        logger.warning('failed to prepare discord-compatible video for %s: %s',
                       vid_path, error)
        with contextlib.suppress(FileNotFoundError):
            output_path.unlink()
        return vid_path, None
    except FileNotFoundError:
        logger.warning('ffmpeg is not available, sending original video %s',
                       vid_path)
        with contextlib.suppress(FileNotFoundError):
            output_path.unlink()
        return vid_path, None
    logger.info('prepared discord-compatible video %s', output_path)
    return output_path, output_path


def send_discord(img_path, vid_path, message, discord_config):
    if 'webhook_url' not in discord_config:
        msg = "missing 'webhook_url' in discord provider config"
        logger.error(msg)
        raise ValueError(msg)

    timeout = discord_config.get('timeout_sec', 10)
    cleanup_paths = []
    try:
        file_paths = []
        if img_path.exists():
            file_paths.append(img_path)
        else:
            logger.warning('image file %s does not exists', img_path)
        if vid_path.exists():
            prepared_vid_path, cleanup_path = _prepare_discord_video_file(
                vid_path,
                timeout,
            )
            file_paths.append(prepared_vid_path)
            if cleanup_path is not None:
                cleanup_paths.append(cleanup_path)
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
                    'discord file %s is bigger than webhook limit (8 MiB), '
                    'skipping',
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

        text_suffix = discord_config.get('text_suffix',
                                         'From anonymous with love.')
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
    finally:
        for cleanup_path in cleanup_paths:
            with contextlib.suppress(FileNotFoundError):
                cleanup_path.unlink()
