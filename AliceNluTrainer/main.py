#  Copyright (c) 2022
#
#  This file, main.py, is part of Project Alice.
#
#  Project Alice is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <https://www.gnu.org/licenses/>
#
#  Last modified: 2022.01.17 at 14:36:59 CET
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from subprocess import CompletedProcess
from threading import Thread
from typing import Dict, Optional

import paho.mqtt.client as mqtt


class NLUTrainer(object):

	TOPIC_READY = 'projectalice/nlu/trainerReady'
	TOPIC_STOPPED = 'projectalice/nlu/trainerStopped'

	TOPIC_TRAIN = 'projectalice/nlu/doTrain'
	TOPIC_REFUSE_FAILED = 'projectalice/nlu/trainingFailed'
	TOPIC_TRAINING_RESULT = 'projectalice/nlu/trainingResult/{}'

	DATASET_FILE = Path('snipsNluDataset.json')
	DEBUG_DATA_FILE = Path('debugDataset.json')

	def __init__(self):
		self._mqttClient = mqtt.Client()
		self._training = False
		self._trainingThread: Optional[Thread] = None
		self._mqttClient.on_message = self.onMqttMessage
		self._mqttClient.on_log = self.onLog
		self._mqttClient.on_connect = self.onConnect


	def connect(self):
		self._mqttClient.connect(host='localhost')
		self._mqttClient.loop_start()


	def disconnect(self):
		self._mqttClient.publish(topic=self.TOPIC_STOPPED)
		self._mqttClient.disconnect()
		self._mqttClient.loop_stop()


	def onMqttMessage(self, _client, _userdata, message: mqtt.MQTTMessage):
		if message.topic == self.TOPIC_TRAIN:
			try:
				print('Received training task')

				if not message.payload:
					raise Exception('No payload in message')

				payload = json.loads(message.payload.decode())
				data = json.loads(payload.get('data', '{}'))
				language = payload.get('language', None)

				if not data:
					if self.DEBUG_DATA_FILE.exists():
						print('Using debug data')
						data = json.loads(self.DEBUG_DATA_FILE.read_text())
					else:
						raise Exception('No training data received')

				if not language:
					raise Exception('Language not specified')

				self.train(language=language, trainingData=data)

			except Exception as e:
				print(f'Failed training NLU: {e}')
				self.failedTraining(reason=str(e))


	def failedTraining(self, reason: str):
		self._mqttClient.publish(
			topic=self.TOPIC_REFUSE_FAILED,
			payload=reason
		)


	def train(self, language: str, trainingData: Dict):
		print('Received training request')

		if self._training:
			reason = "Already training, can't train now"
			print(reason)
			self.failedTraining(reason=reason)
			return

		try:
			self._training = True
			dataset = {
				'entities': dict(),
				'intents' : dict(),
				'language': language
			}

			dataset['entities'].update(trainingData['entities'])
			dataset['intents'].update(trainingData['intents'])

			self.DATASET_FILE.write_text(data=json.dumps(dataset, ensure_ascii=False, indent='\t'))
			print('Generated dataset for training')
			self._trainingThread = Thread(name='NLUTraining', target=self.trainingThread, daemon=True, kwargs={'language': language})
			self._trainingThread.start()
		except Exception as e:
			reason = f'Something went wrong preparing NLU training: {e}'
			self._training = False
			print(reason)
			self.failedTraining(reason=reason)


	def trainingThread(self, language: str):
		try:
			startTime = time.time()

			print(f'Download language support for {language}')
			download: CompletedProcess = subprocess.run([f'snips-nlu', 'download', language], shell=True, check=True)
			if download.returncode != 0 :
				raise Exception(download.stderr.decode())

			print('Begin training...')

			trainedNLU = Path('trainedNLU')
			if trainedNLU.exists():
				shutil.rmtree(trainedNLU, ignore_errors=True)

			training: CompletedProcess = subprocess.run([f'snips-nlu', 'train', str(self.DATASET_FILE), str(trainedNLU)], shell=True, check=True)
			if training.returncode != 0 or not trainedNLU.exists():
				raise Exception(training.stderr.decode())

			trainedNLU = Path('trainedNLU.zip')
			if trainedNLU.exists():
				trainedNLU.unlink()

			shutil.make_archive('trainedNLU', 'zip', 'trainedNLU')

			print(f'Sending results')
			self._mqttClient.publish(
				topic=self.TOPIC_TRAINING_RESULT.format(hashlib.blake2b(trainedNLU.read_bytes()).hexdigest()),
				payload=trainedNLU.read_bytes(),
				qos=0
			)
			timer = round(time.time() - startTime, ndigits=2)
			print(f'Training done! It took {timer} seconds to train.')
		except Exception as e:
			reason = f'Training failed: {e}'
			print(reason)
			self.failedTraining(reason=reason)
		finally:
			self._training = False


	def onConnect(self, _client, _userdata, _flags, _rc):
		print('Mqtt connected, listening for training tasks...')
		self._mqttClient.subscribe(self.TOPIC_TRAIN)
		self._mqttClient.publish(topic=self.TOPIC_READY)


	@staticmethod
	def onLog(_client, _userdata, level, buf):
		if level != 16:
			print(buf)


def start():
	trainer = NLUTrainer()
	trainer.connect()
	try:
		print('Starting Project Alice decentralized NLU trainer')
		while True:
			time.sleep(0.1)
	except KeyboardInterrupt:
		print('Stopping')
		trainer.disconnect()
