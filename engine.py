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

import os
import platform
from abc import abstractmethod
from enum import Enum

import numpy as np
from pocketsphinx import get_model_path
from pocketsphinx.pocketsphinx import Decoder

from engines import Porcupine
from engines import snowboydetect


class EngineInstance(Enum):
    """Supported engines."""
    Pocketsphinx = 'Pocketsphinx'
    Porcupine = 'Porcupine'
    Snowboy = 'Snowboy'


def prepare_pcm(method):
    """Decorator to prepare the PCM data for engines.

    :param method: input method.
    :return: wrapped method which passes the modified PCM data to the engine.
    """
    def wrapper(self, pcm, *args, **kwargs):
        res = np.multiply(np.iinfo(np.int16).max, pcm).astype(np.int16)
        if self.engine_type is EngineInstance.Snowboy or self.engine_type is EngineInstance.Pocketsphinx:
            res = res.tobytes()
        elif self.engine_type is not EngineInstance.Porcupine:
            raise ValueError('%s is not supported', self.engine_type.value)

        return method(self, res, *args, **kwargs)
    return wrapper


class Engine(object):
    """Wake-word engine abstract class."""
    def __init__(self, engine_type, keyword, sensitivity):
        """Initializer.

        :param engine_type: type of the engine.
        :param keyword: keyword used in the engine.
        :param sensitivity: sensitivity of the engine.
        """
        self.engine_type = engine_type
        self._keyword = keyword
        self._sensitivity = sensitivity

    @property
    def sample_rate(self):
        """Audio sample rate expected by the engine."""
        return 16000

    @property
    def frame_length(self):
        """Number of audio samples per frame expected by the engine."""
        return 512

    @property
    def channels(self):
        """Number of channels expected by the engine.."""
        return 1

    @property
    def bits_per_sample(self):
        """Number of bits per sample expected by the engine."""
        return 16

    @abstractmethod
    @prepare_pcm
    def process(self, pcm):
        """Process the PCM data for the keyword."""
        pass

    @abstractmethod
    def release(self):
        """Release the resources hold by the engine."""
        pass

    @classmethod
    def sensitivity_range(cls, engine_type):
        """Return sensitivity range of the engine to use in the benchmark."""
        if engine_type is EngineInstance.Porcupine:
            return np.linspace(0.0, 1.0, 10)
        if engine_type is EngineInstance.Pocketsphinx:
            return np.logspace(-10, 20, 10)
        if engine_type is EngineInstance.Snowboy:
            return np.linspace(0.4, 0.6, 10)
        raise ValueError('No sensitivity range for %s', engine_type.value)

    @classmethod
    def create(cls, engine_type, keyword, sensitivity):
        """Factory method to create wake-word detection engine.
        :param engine_type: type of the engine.
        :param keyword: keyword that the engine needs to detect.
        :param sensitivity: sensitivity of the engine. It changes the number of false alarms versus miss detections.
        :return: engine instance.
        """
        if engine_type is EngineInstance.Porcupine:
            return PorcupineEngine(engine_type, keyword, sensitivity)
        if engine_type is EngineInstance.Pocketsphinx:
            return PocketSphinxEngine(engine_type, keyword, sensitivity)
        if engine_type is EngineInstance.Snowboy:
            return SnowboyEngine(engine_type, keyword, sensitivity)
        return ValueError('%s is not supported', engine_type.value)


class PocketSphinxEngine(Engine):
    """Pocketsphinx engine."""
    def __init__(self, engine_type, keyword, sensitivity):
        """Initializer.

        :param engine_type: type of the engine.
        :param keyword: keyword being used for detection.
        :param sensitivity: sensitivity passed to the engine.
        """

        super().__init__(engine_type, keyword, sensitivity)
        # Set the configuration.
        config = Decoder.default_config()
        config.set_string('-logfn', '/dev/null')
        # Set recognition model to US
        config.set_string('-hmm', os.path.join(get_model_path(), 'en-us'))
        config.set_string('-dict', os.path.join(get_model_path(), 'cmudict-en-us.dict'))
        config.set_string('-keyphrase', keyword)
        config.set_float('-kws_threshold', sensitivity)
        self._decoder = Decoder(config)
        self._decoder.start_utt()

    @prepare_pcm
    def process(self, pcm):
        """Process the PCM data for the keyword."""
        self._decoder.process_raw(pcm, False, False)
        detected = self._decoder.hyp()
        if detected:
            self._decoder.end_utt()
            self._decoder.start_utt()
        return detected

    def release(self):
        """Release the resources hold by the engine."""
        self._decoder.end_utt()


class PorcupineEngine(Engine):
    """Porcupine engine."""

    def __init__(self, engine_type, keyword, sensitivity):
        """Initializer.

        :param engine_type: type of the engine.
        :param keyword: keyword being used for detection.
        :param sensitivity: sensitivity passed to the engine.
        """
        super().__init__(engine_type, keyword, sensitivity)
        library_path = os.path.join(
            os.path.dirname(__file__),
            'engines/porcupine/lib/linux/%s/libpv_porcupine.so' % platform.machine())
        model_file_path = os.path.join(os.path.dirname(__file__),
                                       'engines/porcupine/lib/common/porcupine_params.pv')
        keyword_file_path = os.path.join(os.path.dirname(__file__),
                                         'engines/porcupine/resources/keyword_files/%s_linux.ppn' % keyword.lower())
        self._porcupine = Porcupine(
            library_path=library_path,
            model_file_path=model_file_path,
            keyword_file_path=keyword_file_path,
            sensitivity=sensitivity)

    @prepare_pcm
    def process(self, pcm):
        """Process the PCM data for the keyword."""
        return self._porcupine.process(pcm)

    def release(self):
        """Release the resources hold by the engine."""
        self._porcupine.delete()


class SnowboyEngine(Engine):
    """Snowboy engine."""
    def __init__(self, engine_type, keyword, sensitivity):
        """Initializer.

        :param engine_type: type of the engine.
        :param keyword: keyword being used for detection.
        :param sensitivity: sensitivity passed to the engine.
        """
        super().__init__(engine_type, keyword, sensitivity)
        keyword = keyword.lower()
        if keyword == 'alexa':
            model_relative_path = 'engines/snowboy/resources/alexa/alexa-avs-sample-app/alexa.umdl'
        else:
            model_relative_path = 'engines/snowboy/resources/models/%s.umdl' % keyword

        model_str = os.path.join(os.path.dirname(__file__), model_relative_path).encode()
        resource_filename = os.path.join(os.path.dirname(__file__), 'engines/snowboy/resources/common.res').encode()
        self._snowboy = snowboydetect.SnowboyDetect(resource_filename=resource_filename,
                                                    model_str=model_str)
        self._snowboy.SetSensitivity(str(sensitivity).encode())

    @prepare_pcm
    def process(self, pcm):
        """Process the PCM data for the keyword."""
        return self._snowboy.RunDetection(pcm) == 1

    def release(self):
        """Release the resources hold by the engine."""
        pass
