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

import csv
import os
from collections import namedtuple
from enum import Enum

import numpy as np
import soundfile
import sox


class Datasets(Enum):
    """Different datasets."""

    COMMON_VOICE = 'Mozilla Common Voice'
    ALEXA = 'Alexa'
    DEMAND = 'DEMAND'


AudioMetadata = namedtuple('AudioMetadata', ['path', 'contains_keyword'])

AudioData = namedtuple('AudioData', ['pcm', 'metadata'])


class Dataset(object):
    """Base class for dataset."""

    """
    Audio sample rate required by wake-word engines under test. All datasets need to provide data with this sample rate.
    """
    SAMPLE_RATE = 16000

    def size(self):
        """Number of examples within dataset."""

        return len(self._get_metadatas())

    def get_metadata(self, index):
        """
        Getter for audio metadata.

        :param index: index of metadata.
        :return: metadata.
        """

        return self._get_metadatas()[index]

    def get_data(self, index):
        """
        Getter for audio data.

        :param index: index of data.
        :return: data.
        """

        metadata = self.get_metadata(index)

        # All engines consume 16-bit encoded audio
        pcm, sample_rate = soundfile.read(metadata.path, dtype='int16')
        assert sample_rate == self.SAMPLE_RATE
        assert pcm.ndim == 1

        # Add 0.5 second silence to the end of files containing keyword as occasionally the user stopped recording right
        # after uttering the keyword. If the detector needs some time after seeing the keyword to make a decision
        # (e.g. end-pointing) this is going to artificially increase the miss rates.
        if metadata.contains_keyword:
            pcm = np.append(pcm, np.zeros(self.SAMPLE_RATE // 2, dtype=np.int16))

        return AudioData(pcm=pcm, metadata=metadata)

    @classmethod
    def create(cls, dataset_type, root, **kwargs):
        """
        Factory method.

        :param dataset_type: type of dataset.
        :param root: path to root of dataset.
        :param kwargs: keyword arguments.
        :return: dataset instance.
        """

        if dataset_type is Datasets.COMMON_VOICE:
            return CommonVoiceDataset(root, **kwargs)
        if dataset_type is Datasets.ALEXA:
            return AlexaDataset(root)
        if dataset_type is Datasets.DEMAND:
            return DemandDataset(root)

        raise ValueError('Cannot create dataset of type %s', dataset_type.value)

    def _get_metadatas(self):
        """Getter for all metadata information within dataset."""

        raise NotImplementedError()


class CompositeDataset(Dataset):
    """Wrapper dataset for a collection of datasets."""

    def __init__(self, datasets, shuffle=True, seed=666):
        """
        Constructor.

        :param datasets: collection of datasets.
        :param shuffle: flag to indicate if the datasets examples are to be shuffled.
        :param seed: seed for random number generator used for shuffling.
        """

        self._metadatas = []
        for dataset in datasets:
            for i in range(dataset.size()):
                self._metadatas.append(dataset.get_metadata(i))

        if shuffle:
            random = np.random.RandomState(seed=seed)
            random.shuffle(self._metadatas)

    def _get_metadatas(self):
        return self._metadatas


class CommonVoiceDataset(Dataset):
    """Mozilla Common Voice Dataset (https://voice.mozilla.org)."""

    def __init__(self, root, exclude_words=list()):
        """
        Constructor. It converts MP3 files within original dataset into FLAC and caches them.

        :param root: root of dataset.
        :param exclude_words: files containing these words in their transcript are excluded.
        """

        if isinstance(exclude_words, str):
            exclude_words = [exclude_words]

        self._metadatas = self._load_metadatas(root, exclude_words)

    def _get_metadatas(self):
        return self._metadatas

    @staticmethod
    def _load_metadatas(root, exclude_words):
        metadatas = []

        for part in ['cv-valid-train', 'cv-valid-test', 'cv-valid-dev']:
            metadata_file = os.path.join(root, '%s.csv' % part)

            with open(metadata_file) as f:
                reader = csv.DictReader(f)

                for row in reader:
                    text = row['text'].lower()
                    up_votes = int(row['up_votes'])
                    down_votes = int(row['down_votes'])

                    if up_votes < 2 or down_votes > 0 or not text or any(x.lower() in text for x in exclude_words):
                        continue

                    mp3_path = os.path.join(root, row['filename'])
                    assert mp3_path.endswith('.mp3')

                    flac_path = mp3_path.replace('.mp3', '.flac')
                    if not os.path.exists(flac_path):
                        transformer = sox.Transformer()
                        transformer.convert(samplerate=Dataset.SAMPLE_RATE, bitdepth=16, n_channels=1)
                        transformer.build(mp3_path, flac_path)

                    metadatas.append(AudioMetadata(path=flac_path, contains_keyword=False))

        return metadatas


class AlexaDataset(Dataset):
    """Crowd-sourced utterances of Alexa."""

    def __init__(self, root):
        """
        Constructor.

        :param root: root of dataset.
        """

        self._metadatas = self._load_metadata(root)

    def _get_metadatas(self):
        return self._metadatas

    @staticmethod
    def _load_metadata(root):
        metadatas = []
        for directory, _, filenames in os.walk(root):
            for filename in filenames:
                if filename.endswith('.wav'):
                    metadatas.append(AudioMetadata(path=os.path.join(directory, filename), contains_keyword=True))

        return metadatas


class DemandDataset(Dataset):
    """DEMAND noise dataset (http://parole.loria.fr/DEMAND)"""

    def __init__(self, root):
        """
        Constructor.

        :param root: root of dataset.
        """

        self._metadatas = self._load_metadatas(root)

    def _get_metadatas(self):
        return self._metadatas

    @staticmethod
    def _load_metadatas(root):
        metadatas = []

        for directory, _, filenames in os.walk(root):
            for filename in filenames:
                if filename == 'ch01.wav':
                    metadatas.append(AudioMetadata(path=os.path.join(directory, filename), contains_keyword=False))

        return metadatas
