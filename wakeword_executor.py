#
# Copyright 2018 Picovoice Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging

from dataset import AudioReader
from engine import Engine
from noise_mixer import NoiseMixer


class WakeWordExecutor(object):
    def __init__(self, engine_type, sensitivity, keyword, dataset, noise_dataset=None):
        """Executor for running different wake-word engines under different environments.

        :param engine_type: type of the wake-word engine.
        :param sensitivity: sensitivity to use in the wake-word engine.
        :param keyword: keyword to use in the wake word engine.
        :param dataset: dataset containing both background and keyword datasets.
        :param noise_dataset: dataset used as a source for mixing noise into clean data.
        """
        self._keyword = keyword
        self._sensitivity = sensitivity
        self._dataset = dataset
        # Initialize the engine.
        self._engine = Engine.create(engine_type, keyword, sensitivity)

        self._audio_reader = AudioReader(self._engine.sample_rate, self._engine.channels, self._engine.bits_per_sample)
        self._noise_mixer = None
        if noise_dataset:
            self._noise_mixer = NoiseMixer(noise_dataset, self._audio_reader, self._engine.frame_length)

    def execute(self):
        """Run the engine on the dataset.

        :return: tuple of false alarm per hour and miss detection rate.
        """
        logging.info('Running %s with sensitivity %s', self._engine.engine_type.value, self._sensitivity)
        fa = 0
        md = 0
        # Duration of the dataset in seconds.
        total_duration_sec = 0
        for data in self._dataset:
            pcm, duration_sec = self._audio_reader.read(data)
            total_duration_sec += duration_sec
            if self._noise_mixer:
                pcm = self._noise_mixer.mix(pcm)
            num_frames = len(pcm) // self._engine.frame_length
            num_detected = 0
            for i in range(num_frames):
                frame = pcm[i * self._engine.frame_length:(i + 1) * self._engine.frame_length]
                if self._engine.process(frame):
                    num_detected += 1

            if data.is_keyword:
                if num_detected == 0:
                    md += 1
            else:
                fa += num_detected

        false_alarm_per_hour = fa * 3600 / total_duration_sec
        keyword_dataset_size = sum(1 for d in self._dataset if d.is_keyword)
        miss_rate = md / keyword_dataset_size
        logging.info('[%s][%s] proceeded %s hours', self._engine.engine_type.value, self._sensitivity,
                     (total_duration_sec / 3600))
        logging.info('[%s][%s] %s keyword files', self._engine.engine_type.value, self._sensitivity,
                     keyword_dataset_size)
        logging.info('[%s][%s] %s false alarms', self._engine.engine_type.value, self._sensitivity, fa)
        logging.info('[%s][%s] %s miss detections', self._engine.engine_type.value, self._sensitivity, md)
        logging.info('[%s][%s] %s false alarms per hour', self._engine.engine_type.value, self._sensitivity,
                     false_alarm_per_hour)
        logging.info('[%s][%s] miss detection rate %s', self._engine.engine_type.value, self._sensitivity, miss_rate)
        return false_alarm_per_hour, miss_rate

    def release(self):
        """Release the resources hold by the engine."""
        self._engine.release()
