# No one is safe

A python package with the sole purpose of monitoring your connected camera's
view and notifying upon movement.

## Installtion

1. Clone the repo and enter the dir:

    ```sh
    $ git clone git@github.com:sahargavriely/nooneissafe.git
    ...
    $ cd nooneissafe/
    ```

2. Install and activate virtual environment:

    ```sh
    $ ./scripts/install.sh
    ...
    $ source venv/bin/activate
    (nooneissafe) $ # rock and roll
    ```

## Usage

1. Before we go ahead and start the program there are some configuration you can play with.
   In the `nooneissafe/__main__.py` file, there is a function call (`record_loop`) which receives 4 arguments:

    1.1. `source` - The source of the camera - camera index if you would like. If you have only one camera connected, ignore it. Otherwise and if you want the program to use more than one camera, then change `amount_of_cameras` variable in the `__main__` module to the amount you want.

    1.2. `show` - If is sets to `True`, displays the camera work on screen, otherwise, is sets to `False` does not display. Default setting is `False`.

    1.3. `min_rec_time` - The minimum recording time once a movement was discoverd, in seconds. Default setting is `10`s.

    1.4. `time_between_sample` - The frequency of sampling in seconds. Default setting is `1`s. The program will sample a frame every `time_between_frame` seconds and compare the two last frames.

2. Configure your notification provider:

    2.1. Create `notification_config.json` at the root directory.

    2.2. For SMTP email notifications, use:

        {
          "provider": "email",
          "password": "password used to connect to SMTP",
          "recipient_email": "recipient email address",
          "sender_email": "sender email address",
          "smtp_server": "SMTP server host",
          "ssl_port": 465,
          "username": "SMTP username",
          "text_suffix": "From anonymous with love."
        }

    2.3. For free Telegram notifications, use:

        {
          "provider": "telegram",
          "bot_token": "<telegram bot token from @BotFather>",
          "chat_id": "<your chat id>",
          "parse_mode": "Markdown",
          "text_suffix": "From anonymous with love.",
          "timeout_sec": 10
        }

    2.4. For free Discord notifications, use:

        {
          "provider": "discord",
          "webhook_url": "https://discord.com/api/webhooks/<id>/<token>",
          "username": "NoOneIsSafe",
          "text_suffix": "From anonymous with love.",
          "max_file_mb": 8,
          "user_agent": "curl/8.6.0",
          "timeout_sec": 10
        }

    Telegram and Discord providers upload actual media files when present.

4. Let the program run and do its magic:

    ```sh
    (nooneissafe) $ python -m nooneissafe
    ...
    ```

5. Stop the program by pressing `Enter` key or with `ctrl` + `C` and view results. after activation a `database/` directory will be created and in it you will be able to find all the movement detections videos.
