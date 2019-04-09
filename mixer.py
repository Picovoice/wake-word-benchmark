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
import soundfile

from dataset import Dataset
from engine import Engine

_random = np.random.RandomState(seed=778)


def _pcm_energy(pcm):
    frame_length = Engine.frame_length()
    num_frames = pcm.size // frame_length

    pcm_frames = pcm[:(num_frames * frame_length)].reshape((num_frames, frame_length))
    frames_power = (pcm_frames ** 2).sum(axis=1)

    return frames_power.max()


def _noise_scale(speech, noise, snr_db):
    assert speech.shape[0] == noise.shape[0]

    return np.sqrt(_pcm_energy(speech) / (_pcm_energy(noise) * (10 ** (snr_db / 10))))


def _max_abs(x):
    return max(np.max(x), np.abs(np.min(x)))


def _mix_noise(speech, noise_dataset, snr_db):
    parts = list()
    while sum(x.size for x in parts) < speech.size:
        x = noise_dataset.random(dtype=np.float32)
        parts.append(x / _max_abs(x))

    noise = np.concatenate(parts)[:speech.size]

    noisy_speech = speech + (noise * _noise_scale(speech, noise, snr_db))

    return noisy_speech


def _assemble_background(background_dataset, length_samples, background_probability=0.2):
    parts = list()
    while sum(x.size for x in parts) < length_samples:
        x = background_dataset.random(dtype=np.float32)
        if _random.uniform() < background_probability:
            parts.append(x / _max_abs(x))
        else:
            parts.append(np.zeros((x.size,), dtype=np.float32))

    return parts


def _assemble_speech(keyword_dataset, background_dataset, length_hour):
    num_keywords = keyword_dataset.size()
    keyword_indices = _random.permutation(np.arange(num_keywords))

    background_length_samples = (length_hour * 3600 * Dataset.sample_rate()) // (num_keywords + 1)

    parts = _assemble_background(background_dataset, background_length_samples)
    keyword_times_sec = list()
    for keyword_index in keyword_indices:
        keyword_part = keyword_dataset.get(keyword_index, dtype=np.float32)

        start_time_sec = sum(x.size for x in parts) / Dataset.sample_rate()
        end_time_sec = start_time_sec + (keyword_part.size / Dataset.sample_rate()) + 0.5
        keyword_times_sec.append((start_time_sec, end_time_sec))

        parts.append(keyword_part / _max_abs(keyword_part))
        parts.extend(_assemble_background(background_dataset, background_length_samples))

    return np.concatenate(parts), keyword_times_sec


def create_test_files(
        speech_path,
        label_path,
        keyword_dataset,
        background_dataset,
        noise_dataset,
        length_hour=24,
        snr_db=0):
    speech, keyword_times_sec = _assemble_speech(keyword_dataset, background_dataset, length_hour)
    speech = _mix_noise(speech, noise_dataset, snr_db)
    speech /= (4 * _max_abs(speech))

    soundfile.write(speech_path, speech, samplerate=Dataset.sample_rate())

    with open(label_path, 'w') as f:
        for start_sec, end_sec in keyword_times_sec:
            f.write('%.2f, %.2f\n' % (start_sec, end_sec))
