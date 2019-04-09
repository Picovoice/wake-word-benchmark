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
from enum import Enum

import numpy as np
import soundfile


class Datasets(Enum):
    DEMAND = 'DEMAND'
    KEYWORD = 'Keyword'
    LIBRI_SPEECH = "LibriSpeech"


class Dataset(object):
    def __init__(self):
        self._random = np.random.RandomState(seed=778)

    def get(self, index, dtype=np.int16):
        pcm, sample_rate = soundfile.read(self._paths[index], dtype=dtype)
        assert sample_rate == self.sample_rate()

        return pcm

    def random(self, dtype=np.int16):
        return self.get(self._random.randint(low=0, high=self.size()), dtype=dtype)

    def size(self):
        return len(self._paths)

    @staticmethod
    def sample_rate():
        return 16000

    @classmethod
    def create(cls, dataset, path, **kwargs):
        if dataset is Datasets.DEMAND:
            return DEMANDDataset(path)
        elif dataset is Datasets.KEYWORD:
            return KeywordDataset(path)
        elif dataset is Datasets.LIBRI_SPEECH:
            return LibriSpeechDataset(path, *kwargs)
        else:
            raise ValueError("cannot create dataset of type '%s'", dataset.value)

    @property
    def _paths(self):
        raise NotImplementedError()


class DEMANDDataset(Dataset):
    def __init__(self, path):
        super(DEMANDDataset, self).__init__()

        self.__paths = list()
        for noise_type in os.listdir(path):
            self.__paths.append(os.path.join(path, '%s/ch01.wav' % noise_type))
        self.__paths.sort()

    @property
    def _paths(self):
        return self.__paths


class KeywordDataset(Dataset):
    def __init__(self, path):
        super(KeywordDataset, self).__init__()

        self.__paths = list()
        for x in os.listdir(path):
            self.__paths.append(os.path.join(path, x))
        self.__paths.sort()

    @property
    def _paths(self):
        return self.__paths


class LibriSpeechDataset(Dataset):
    def __init__(self, path, exclude_word):
        super(LibriSpeechDataset, self).__init__()

        self.__paths = list()
        for speaker_id in os.listdir(path):
            speaker_dir = os.path.join(path, speaker_id)
            for chapter_id in os.listdir(speaker_dir):
                chapter_dir = os.path.join(speaker_dir, chapter_id)
                transcript_path = os.path.join(chapter_dir, '%s-%s.trans.txt' % (speaker_id, chapter_id))
                with open(transcript_path) as f:
                    for line in f.readlines():
                        flac_basename, transcript = line.split(' ', maxsplit=1)
                        if exclude_word not in transcript:
                            self.__paths.append(os.path.join(chapter_dir, '%s.flac' % flac_basename))
        self.__paths.sort()

    @property
    def _paths(self):
        return self.__paths
