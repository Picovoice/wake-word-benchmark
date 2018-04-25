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
    """Mix noise with audio."""
    def __init__(self, noise_dataset, audio_reader, window_length):
        """Initializer.

        :param noise_dataset: noise dataset to mix with the clean dataset.
        :param audio_reader: audio reader to read audio files.
        :param window_length: number of samples in each frame of audio data.
        """
        self._noise_dataset = noise_dataset
        self._window_length = window_length
        self._audio_reader = audio_reader
        # Use 10dB SNR for adding moderate noise to the data.
        self._snr = 10
        self._random = np.random.RandomState(seed=666)

    def mix(self, pcm):
        """Mix a randomly chosen noise with the clean audio data.

        :param pcm: raw clean audio data.
        :return: mixed audio data with noise.
        """
        noise_sample = self._noise(pcm.shape[0])
        noise_scale = self._noise_scale(pcm, noise_sample)
        res = pcm + noise_sample * noise_scale
        # Make sure that we are not clipping.
        res = res / (np.abs(res).max() * 2)
        return res

    def _noise(self, length):
        """Get a random noise sample with a given length.

        :param length: length of the noise.
        :return: noise sample.
        """
        noise_data = None
        noise_data_length = 0
        while noise_data_length < length:
            index = self._random.randint(low=0, high=len(self._noise_dataset))
            noise_data, _ = self._audio_reader.read(self._noise_dataset[index])
            noise_data_length = noise_data.shape[0]

        start_sample = self._random.randint(low=0, high=(noise_data_length - length + 1))
        end_sample = start_sample + length

        return noise_data[start_sample:end_sample]

    def _noise_scale(self, pcm, noise):
        """Get the scale by which noise is mixed into clean audio data.

        :param pcm: raw audio data.
        :param noise: noise sample.
        :return: scale to use for mixing noise with audio data.
        """
        assert pcm.shape[0] == noise.shape[0]

        # HINT: snr = 10 * log10( pcm_energy / (noise_energy * (noise_scale ** 2)) )
        noise_scale = np.sqrt(
            self._pcm_energy(pcm) / (self._noise_energy(noise) * (10 ** (self._snr / 10.))))

        return noise_scale

    def _pcm_energy(self, pcm):
        """Calculate energy in the PCM data.

        :param pcm: PCM audio data.
        :return: energy of the PCM data.
        """
        num_frames = pcm.size // self._window_length

        pcm_windows = pcm[:num_frames * self._window_length].reshape(
            (num_frames, self._window_length))
        pcm_powers = (pcm_windows ** 2).sum(axis=1)
        return pcm_powers.max()

    def _noise_energy(self, noise):
        """Calculate noise energy.

        :param noise: noise data
        :return: energy of the noise.
        """
        num_frames = noise.size // self._window_length

        noise_windows = noise[:num_frames * self._window_length].reshape(
            (num_frames, self._window_length))
        noise_powers = (noise_windows ** 2).sum(axis=1)
        return noise_powers.max()
