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

import numpy as np


class NoiseMixer(object):
    """Mixes noise with speech."""

    def __init__(self, noise_dataset, window_length=512, snr_db=10):
        """
        Constructor.

        :param noise_dataset: noise dataset.
        :param window_length: length of window used to compute power statistics.
        :param snr_db: SNR in dB.
        """

        self._noise_dataset = noise_dataset
        self._window_length = window_length
        self._snr_dB = snr_db

        self._random = np.random.RandomState(seed=666)

    def mix(self, pcm):
        """
        Mixes a randomly chosen noise with clean speech.

        :param pcm: clean speech.
        :return: noisy speech.
        """

        noise_sample = self._noise(pcm.shape[0])
        noise_scale = self._noise_scale(pcm, noise_sample)
        res = pcm + noise_sample * noise_scale
        # Make sure that we are not clipping.
        res = (np.iinfo(np.int16).max * res / (np.abs(res).max() * 2)).astype(np.int16)

        return res

    def _noise(self, length):
        noise_data = None
        noise_data_length = 0
        while noise_data_length < length:
            index = self._random.randint(low=0, high=self._noise_dataset.size())
            noise_data = self._noise_dataset.get_data(index).pcm
            noise_data_length = noise_data.shape[0]

        start_sample = self._random.randint(low=0, high=(noise_data_length - length + 1))
        end_sample = start_sample + length

        return noise_data[start_sample:end_sample]

    def _noise_scale(self, pcm, noise):
        assert pcm.shape[0] == noise.shape[0]

        # HINT: snr = 10 * log10( pcm_energy / (noise_energy * (noise_scale ** 2)) )
        noise_scale = np.sqrt(self._pcm_energy(pcm) / (self._noise_energy(noise) * (10 ** (self._snr_dB / 10.))))

        return noise_scale

    def _pcm_energy(self, pcm):
        num_frames = pcm.size // self._window_length

        pcm_windows = pcm[:num_frames * self._window_length].reshape((num_frames, self._window_length))
        pcm_powers = (pcm_windows ** 2).sum(axis=1)

        return pcm_powers.max()

    def _noise_energy(self, noise):
        num_frames = noise.size // self._window_length

        noise_windows = noise[:num_frames * self._window_length].reshape((num_frames, self._window_length))
        noise_powers = (noise_windows ** 2).sum(axis=1)

        return noise_powers.max()
