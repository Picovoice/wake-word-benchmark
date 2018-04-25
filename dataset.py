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
import logging
import os
import tempfile
from abc import abstractmethod
from enum import Enum

import numpy as np
from soundfile import SoundFile
from sox import Transformer
from sox import file_info


class DatasetInstance(Enum):
    """Supported datasets."""
    CommonVoiceDataset = 'Common Voice Dataset'
    AlexaDataset = 'Alexa Dataset'
    DemandDataset = 'Demand Dataset'


class AudioMetadata(object):
    """Audio metadata data."""
    def __init__(self, path, is_keyword):
        """Initializer.

        :param path: absolute path to the audio file.
        :param is_keyword: boolean flag that shows if this audio file belongs to the keyword dataset.
        """
        self.path = path
        self.is_keyword = is_keyword


class AudioReader(object):
    """Audio reader."""
    def __init__(self, sample_rate, channels, bits_per_sample):
        """Initializer.

        :param sample_rate: sample rate of the audio file.
        :param channels: number of channels in the audio file.
        :param bits_per_sample: bit per sample in the audio file.
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._bits_per_sample = bits_per_sample

    def read(self, audio_metadata):
        """Read an audio file.

        :param audio_metadata: metadata info of an audio
        :return: raw audio data as float32 array and duration in seconds.
        """
        fd = temp_path = None
        # Convert it to a wav file.
        if not audio_metadata.path.endswith('.wav'):
            original_sample_rate = file_info.sample_rate(audio_metadata.path)
            assert self._sample_rate <= original_sample_rate
            transformer = Transformer()
            transformer.convert(samplerate=self._sample_rate, n_channels=self._channels, bitdepth=self._bits_per_sample)
            fd, temp_path = tempfile.mkstemp(suffix='.wav')
            transformer.build(audio_metadata.path, temp_path)

        if temp_path:
            path = temp_path
        else:
            path = audio_metadata.path

        # Read the audio file.
        with SoundFile(path) as soundfile:
            # make sure the audio properties are as expected.
            assert soundfile.samplerate == self._sample_rate
            assert soundfile.channels == self._channels
            duration_sec = len(soundfile) / self._sample_rate
            pcm = soundfile.read(dtype='float32')

            # Add 0.5 second silence to the end of files containing keyword as in occasionally the user stopped
            # recording right after uttering the keyword. If the detector needs some time after seeing the keyword to
            # make a decision (e.g. endpointing) this is going to artificially increase the miss rates.
            if audio_metadata.is_keyword:
                pcm = np.append(pcm, np.zeros(self._sample_rate // 2))

            if temp_path:
                os.close(fd)
                os.remove(temp_path)

            return pcm, duration_sec


class Dataset(object):
    """Base class for dataset."""

    def __init__(self, root):
        """Initializer.

        :param root: root directory of the dataset.
        """
        self._root = root
        if not os.path.exists(root) or not os.path.isdir(root):
            raise ValueError('Check your root directory %s', root)

    @classmethod
    def create(cls, dataset_type, root, **kwargs):
        """Factory method to create a dataset.

        :param dataset_type: type of the dataset.
        :param root: root directory of the dataset.
        :param kwargs: optional arguments passed to the constructor of the dataset.
        :return: dataset instance.
        """
        if dataset_type is DatasetInstance.AlexaDataset:
            return AlexaDataset(root)
        if dataset_type is DatasetInstance.CommonVoiceDataset:
            return CommonVoiceDataset(root, **kwargs)
        if dataset_type is DatasetInstance.DemandDataset:
            return DemandDataset(root)
        raise ValueError('%s is not supported', dataset_type.value)

    @abstractmethod
    def metadata(self):
        """Get the metadata in the dataset."""
        pass


class CommonVoiceDataset(Dataset):
    """Mozilla Common Voice Dataset.

    https://voice.mozilla.org
    """
    def __init__(self,
                 root,
                 exclude_words=None):
        """Initialize.

        :param root: root directory of Common Voice Dataset.
        :param exclude_words: exclude the files that contain any of the these words.
        """
        super().__init__(root)
        if isinstance(exclude_words, str):
            exclude_words = [exclude_words]

        self._exclude_words = exclude_words
        # Only read the data from validated directories
        self._include_dirs = ['cv-valid-train', 'cv-valid-test']

    def metadata(self):
        """Get the metadata.

        :return: list of metadata info for audio files in the dataset.
        """
        logging.info('Exploring Common Voice Dataset...')
        res = []
        for directory, _, filenames in os.walk(self._root):
            filenames = [f for f in filenames if f.endswith('.mp3')]
            dirname = os.path.basename(directory)
            if not filenames or dirname == 'cv-invalid' or dirname not in self._include_dirs:
                continue

            dir_metadata = self._get_directory_metadata(dirname)
            for filename in filenames:
                md = dir_metadata.get(filename)
                # Only take the files that have no down votes and have more than one up votes.
                if (md['up_votes'] < 2 or md['down_votes'] > 0 or not md['text'] or
                        any(x in md['text'] for x in self._exclude_words)):
                    continue

                path = os.path.join(directory, filename)
                res.append(AudioMetadata(path, False))

        logging.info('Found %s valid audio files in Common Voice Dataset', len(res))
        return res

    def _get_directory_metadata(self, dirname):
        """Get a metadata info for audio files in a directory.

        The metadata is a dict from the name of a file to their metadata information. For example, it could be something
        like: {'sample.mp3': {'text': 'GitHub is awesome', 'up_votes': 2, 'down_votes': 0}}

        :param dirname: data directory name.
        :return: dict of file names to their metadata info.
        """
        # The metadata files are in the root folder.
        metadata = {}
        metadata_file = os.path.join(self._root, '%s.csv' % dirname)

        with open(metadata_file) as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                # file names are presented as <dirname/filename> in the csv file.
                filename = row['filename'].split('/', maxsplit=1)[1]
                text = row['text'].lower()
                up_votes = int(row['up_votes'])
                down_votes = int(row['down_votes'])
                metadata[filename] = {'text': text, 'up_votes': up_votes, 'down_votes': down_votes}

        return metadata


class AlexaDataset(Dataset):
    """Alexa dataset collected by Picovoice.

    """
    def __init__(self, root):
        """Initializer.

        :param root: root directory of the dataset.
        """
        super().__init__(root)

    def metadata(self):
        """Get the metadata.

        :return: list of metadata info for audio files in the dataset.
        """
        res = []
        logging.info('Exploring Alexa Dataset...')
        for directory, _, filenames in os.walk(self._root):
            filenames = [f for f in filenames if f.endswith('.wav')]
            for f in filenames:
                path = os.path.join(directory, f)
                res.append(AudioMetadata(path, True))

        logging.info('Found %s audio files in Alexa Dataset', len(res))
        return res


class DemandDataset(Dataset):
    """Demand dataset.

    http://parole.loria.fr/DEMAND/
    """
    def __init__(self, root):
        """Initializer.

        :param root: root directory of the dataset.
        """
        super().__init__(root)

    def metadata(self):
        """Get the metadata.

        :return: list of metadata info for audio files in the dataset.
        """
        res = []
        logging.info('Exploring Demand Dataset...')
        for directory, _, filenames in os.walk(self._root):
            filenames = [f for f in filenames if f == 'ch01.wav']
            for f in filenames:
                path = os.path.join(directory, f)
                res.append(AudioMetadata(path, False))

        logging.info('Found %s audio files in Demand Dataset', len(res))
        return res
