# nluTrainer
## A decentralized NLU trainer
The idea behind this small tool is to provide a simple trainer on your Network for Alice to use. Training the NLU is a costly operation and your device running ProjectAlice might get slow at it the more skills you have. In order for Alice to use it, turn on the option `delegateNluTraining`

# Users
To use this, create a Virtual Environment wherever you wish on your main computer, be it Windows, Linux or Mac, on a Synology station, whatever network device that can run python. Make sure this device runs Python 3.7!

`python3.7 -m venv venv`

Activate your virtual environment and install the nlu trainer with pip:

`pip install projectalice-nlu-trainer`

That's all you need to install!

# Devs of this tool
- Clone this repository
- Open a terminal on whatever OS you are
- CD to the path where you cloned this repository
- Create a python 3.7 virtual environment:
  `python -m venv`
- Activate your virtual environment
- Install the package in dev mode:
  `pip install --editable .`


# Usage 
Run the trainer using this command, in your terminal:

`alice-trainer --host ALICE_IP`

You can also define some other options with arguments:

- -h / --host: Define the Mqtt hostname, generally it's Alice's main unit IP address
- -p / --port: Define the Mqtt port, by default 1883
- -u / --user: Define a Mqtt username to connect with
- -s / --password: Define a Mqtt password to connect with
- -f / --tls_file: Define the path to your TLS certificate file to connect with, if you Mqtt server requires it

As you want it to be always running, you might want to automate it to run at computer boot.

# Messages
- projectalice/nlu/doTrain : Send this message to have the trainer train on the data in payload.

Payload structure:

```json
{
    "language": "en",
    "data": "the data to train the NLU on, as a json string"
}
```

- projectalice/nlu/trainerReady : Sent when the trainer has started and connected
- projectalice/nlu/trainerStopped : Sent when the trainer is stopped

- projectalice/nlu/trainingFailed : Sent if the training failed with the reason as payload
- projectalice/nlu/trainingResult/# : Sent when the training is finished with the zipped result as a bytearray in payload. The mqtt topic last level is the file control hash (`hashlib.blake2b(result.read_bytes()).hexdigest()`)

# Nice to know
- The trainer can only train if it's not already training.
- The trainer will download the language pack each time a training is asked
- You can only train Snips NLU on this for now
- You are limited to Snips NLU supported languages
