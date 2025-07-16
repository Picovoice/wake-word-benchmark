#
# Copyright 2018-2025 Picovoice Inc.
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


def _speech_scale(speech, noise, snr_db):
    assert speech.shape[0] == noise.shape[0]

    speech_energy = _pcm_energy(speech)
    if speech_energy == 0:
        return 0

    return np.sqrt((_pcm_energy(noise) * (10 ** (snr_db / 10))) / speech_energy)


def _max_abs(x):
    return max(np.max(x), np.abs(np.min(x)))


def _mix_noise(speech_parts, noise_dataset, snr_db):
    speech_length = sum(len(x) for x in speech_parts)

    parts = list()
    while sum(x.size for x in parts) < speech_length:
        x = noise_dataset.random(dtype=np.float32)
        parts.append(x / _max_abs(x))

    res = np.concatenate(parts)[:speech_length]

    start_index = 0
    for speech_part in speech_parts:
        end_index = start_index + len(speech_part)
        res[start_index:end_index] += speech_part * _speech_scale(speech_part, res[start_index:end_index], snr_db)
        start_index = end_index

    return res


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

    return parts, keyword_times_sec


def create_test_files(
        speech_path,
        label_path,
        keyword_dataset,
        background_dataset,
        noise_dataset,
        length_hour=24,
        snr_db=10):
    speech_parts, keyword_times_sec = _assemble_speech(keyword_dataset, background_dataset, length_hour)
    speech = _mix_noise(speech_parts, noise_dataset, snr_db)
    speech /= _max_abs(speech)

    soundfile.write(speech_path, speech, samplerate=Dataset.sample_rate())

    with open(label_path, 'w') as f:
        for start_sec, end_sec in keyword_times_sec:
            f.write('%.2f, %.2f\n' % (start_sec, end_sec))
