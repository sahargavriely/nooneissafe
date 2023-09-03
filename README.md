# No one is safe

A python package with the sol purpose of monitoring your connected camera's view.

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
    $ source .env/bin/activate
    (nooneissafe) $ # rock and roll
    ```

## Usage

1. Before we go ahead and start the pogram there some configuration you can play with.
   In the `nooneissafe/__main__.py` file, there is a single function call which receives 3 arguments:

    1.1. `show` - If is sets to `True`, displays the camera work on screen, otherwise, is sets to `False` does not display. Default setting is `False`.

    1.2. `min_rec_time` - The minimum recording time once a movment was discoverd, in seconds. Default setting is `10`s.

    1.3. `time_between_frames` - The frequency of sampling in seconds. Default setting is `3`s. The program will sample a frame every `time_between_frame` seconds and compare the two last frames.

2. Let the program run and do its magic:

    ```sh
    (nooneissafe) $ python -m nooneissafe
    ...
    ```

3. Stop the program with `ctrl` + `C` and view results. after activation a `database/` directory will be created and in it you will be able to find all the movment detections videos.
