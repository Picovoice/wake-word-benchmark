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
from collections import namedtuple
from enum import Enum

import numpy as np
from pocketsphinx import get_model_path
from pocketsphinx.pocketsphinx import Decoder

from engines import Porcupine
from engines import snowboydetect


class Engines(Enum):
    POCKET_SPHINX = 'PocketSphinx'
    PORCUPINE = 'Porcupine'
    SNOWBOY = 'Snowboy'


SensitivityInfo = namedtuple('SensitivityInfo', 'min, max, step')


class Engine(object):
    def process(self, pcm):
        raise NotImplementedError()

    def release(self):
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()

    @staticmethod
    def frame_length():
        return 512

    @staticmethod
    def sensitivity_info(engine_type):
        if engine_type is Engines.POCKET_SPHINX:
            return SensitivityInfo(-21, 15, 3)
        elif engine_type is Engines.PORCUPINE:
            return SensitivityInfo(0, 1, 0.1)
        elif engine_type is Engines.SNOWBOY:
            return SensitivityInfo(0, 1, 0.05)
        else:
            raise ValueError("no sensitivity range for '%s'", engine_type.value)

    @staticmethod
    def create(engine, keyword, sensitivity, **kwargs):
        if engine is Engines.POCKET_SPHINX:
            return PocketSphinxEngine(keyword, sensitivity)
        elif engine is Engines.PORCUPINE:
            return PorcupineEngine(keyword, sensitivity, **kwargs)
        elif engine is Engines.SNOWBOY:
            return SnowboyEngine(keyword, sensitivity)
        else:
            ValueError("cannot create engine of type '%s'", engine.value)


class PocketSphinxEngine(Engine):
    def __init__(self, keyword, sensitivity):
        config = Decoder.default_config()
        config.set_string('-logfn', '/dev/null')
        config.set_string('-hmm', os.path.join(get_model_path(), 'en-us'))
        config.set_string('-dict', os.path.join(get_model_path(), 'cmudict-en-us.dict'))
        config.set_string('-keyphrase', keyword if keyword != 'snowboy' else 'snow boy')
        config.set_float('-kws_threshold', 10 ** -sensitivity)

        self._decoder = Decoder(config)
        self._decoder.start_utt()

    def process(self, pcm):
        assert pcm.dtype == np.int16

        self._decoder.process_raw(pcm.tobytes(), False, False)

        detected = self._decoder.hyp()
        if detected:
            self._decoder.end_utt()
            self._decoder.start_utt()

        return detected

    def release(self):
        self._decoder.end_utt()

    def __str__(self):
        return 'PocketSphinx'


class PorcupineEngine(Engine):
    def __init__(self, keyword, sensitivity, access_key):
        self._porcupine = Porcupine(
            access_key=access_key,
            library_path=os.path.join(self._repo_path, 'lib/linux/x86_64/libpv_porcupine.so'),
            model_path=os.path.join(self._repo_path, 'lib/common/porcupine_params.pv'),
            keyword_paths=[os.path.join(self._repo_path, 'resources/keyword_files/linux/%s_linux.ppn' % keyword.lower())],
            sensitivities=[sensitivity])

    def process(self, pcm):
        assert pcm.dtype == np.int16

        return self._porcupine.process(pcm) == 0

    def release(self):
        self._porcupine.delete()

    def __str__(self):
        return 'Porcupine'

    @property
    def _repo_path(self):
        return os.path.join(os.path.dirname(__file__), 'engines/porcupine')


class SnowboyEngine(Engine):
    def __init__(self, keyword, sensitivity):
        keyword = keyword.lower()
        if keyword == 'alexa':
            model_relative_path = 'engines/snowboy/resources/alexa/alexa-avs-sample-app/alexa.umdl'
        else:
            model_relative_path = 'engines/snowboy/resources/models/%s.umdl' % keyword.replace(' ', '_')

        model_str = os.path.join(os.path.dirname(__file__), model_relative_path).encode()
        resource_filename = os.path.join(os.path.dirname(__file__), 'engines/snowboy/resources/common.res').encode()
        self._snowboy = snowboydetect.SnowboyDetect(resource_filename=resource_filename, model_str=model_str)

        # https://github.com/Kitt-AI/snowboy#pretrained-universal-models

        if keyword == 'jarvis':
            self._snowboy.SetSensitivity(('%f,%f' % (sensitivity, sensitivity)).encode())
        else:
            self._snowboy.SetSensitivity(str(sensitivity).encode())

        if keyword in {'alexa', 'computer', 'jarvis', 'view glass'}:
            self._snowboy.ApplyFrontend(True)
        else:
            self._snowboy.ApplyFrontend(False)

    def process(self, pcm):
        assert pcm.dtype == np.int16

        return self._snowboy.RunDetection(pcm.tobytes()) == 1

    def release(self):
        pass

    def __str__(self):
        return 'Snowboy'
