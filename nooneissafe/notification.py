import json
import logging
import pathlib

from .notification_providers.discord import send_discord
from .notification_providers.email import send_email
from .notification_providers.telegram import send_telegram


logger = logging.getLogger(__name__)

EMAIL_PROVIDER = 'email'
TELEGRAM_PROVIDER = 'telegram'
DISCORD_PROVIDER = 'discord'
_notification_config_path = (
    pathlib.Path(__file__).parent.parent / 'notification_config.json'
)
_provider_config = None


def _load_json(path):
    with path.open('r') as file:
        return json.load(file)


def _validate_keys(config, required_keys):
    for key in required_keys:
        if key not in config:
            msg = f'missing {key=!r} in config file {_notification_config_path!r}'
            logger.error(msg)
            raise ValueError(msg)


def _load_provider_config():
    if not _notification_config_path.exists():
        msg = f'missing notification config file {_notification_config_path!r}'
        logger.error(msg)
        raise FileNotFoundError(msg)
    config = _load_json(_notification_config_path)
    _validate_keys(config, ['provider'])
    return config['provider'], config


def _get_provider_config():
    global _provider_config
    if _provider_config is None:
        _provider_config = _load_provider_config()
    return _provider_config


def send_notification(img_path: pathlib.Path, vid_path: pathlib.Path, message):
    provider, config = _get_provider_config()
    if provider == EMAIL_PROVIDER:
        send_email(img_path, vid_path, message, config)
        return
    if provider == TELEGRAM_PROVIDER:
        send_telegram(img_path, vid_path, message, config)
        return
    if provider == DISCORD_PROVIDER:
        send_discord(img_path, vid_path, message, config)
        return
    msg = f'unsupported notification provider {provider!r}'
    logger.error(msg)
    raise ValueError(msg)
