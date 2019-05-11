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

import argparse
import logging
import multiprocessing

from dataset import *
from engine import *
from mixer import create_test_files

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)


def run_sensitivity(pcm, num_frames, labels, num_keywords, engine_type, sensitivity):
    detector = Engine.create(engine_type, keyword=args.keyword, sensitivity=sensitivity)

    frame_length = Engine.frame_length()

    num_false_alarms = 0
    num_true_detects = 0
    for i in range(num_frames):
        frame = pcm[(i * frame_length):((i + 1) * frame_length)]
        if detector.process(frame):
            if labels[i]:
                num_true_detects += 1
            else:
                num_false_alarms += 1

    detector.release()

    miss_rate = (num_keywords - num_true_detects) / num_keywords
    pcm_length_hour = pcm.size / (Dataset.sample_rate() * 3600)
    false_alarm_per_hour = num_false_alarms / pcm_length_hour

    logging.info(
        '[%s - %.2f] fr: %.2f fa: %.2f' % (engine_type.value, sensitivity, miss_rate, false_alarm_per_hour))

    return miss_rate, false_alarm_per_hour


def run(engine_type):
    pcm, sample_rate = soundfile.read(speech_path, dtype=np.int16)
    assert sample_rate == Dataset.sample_rate()

    keyword_times_sec = list()
    with open(label_path, 'r') as f:
        for line in f.readlines():
            keyword_times_sec.append(tuple(float(x) for x in line.strip('\n').split(', ')))

    frame_length = Engine.frame_length()
    num_frames = pcm.size // frame_length

    labels = np.zeros((num_frames,), dtype=np.bool)
    for start_sec, end_sec in keyword_times_sec:
        start_frame = int(start_sec * Dataset.sample_rate() // frame_length)
        end_frame = int((end_sec * Dataset.sample_rate() + (frame_length - 1)) // frame_length)
        labels[start_frame:(end_frame + 1)] = True

    sensitivity_info = Engine.sensitivity_info(engine_type)

    result = dict()

    sensitivity = (sensitivity_info.min + sensitivity_info.max) / 2

    while sensitivity >= sensitivity_info.min:
        result[sensitivity] = run_sensitivity(pcm, num_frames, labels, len(keyword_times_sec), engine_type, sensitivity)
        if result[sensitivity][1] == 0:
            break
        else:
            sensitivity -= sensitivity_info.step

    sensitivity = (sensitivity_info.min + sensitivity_info.max) / 2 + sensitivity_info.step

    while sensitivity <= sensitivity_info.max:
        result[sensitivity] = run_sensitivity(pcm, num_frames, labels, len(keyword_times_sec), engine_type, sensitivity)
        if result[sensitivity][1] > 1:
            break
        else:
            sensitivity += sensitivity_info.step

    return engine_type, result


def save(results):
    for engine, result in results:
        path = os.path.join(os.path.dirname(__file__), '%s_%s.csv' % (args.keyword, engine.value))
        with open(path, 'w') as f:
            for sensitivity in sorted(result.keys()):
                miss_rate, false_alarms_per_hour = result[sensitivity]
                f.write('%f, %f\n' % (miss_rate, false_alarms_per_hour))


parser = argparse.ArgumentParser()
parser.add_argument('--librispeech_dataset_path', required=True)
parser.add_argument('--demand_dataset_path', required=True)
parser.add_argument('--keyword', required=True)

if __name__ == '__main__':
    args = parser.parse_args()

    keyword_dataset =\
        Dataset.create(Datasets.KEYWORD, os.path.join(os.path.dirname(__file__), 'audio/%s' % args.keyword))
    logging.info('loaded keyword dataset with %d examples' % keyword_dataset.size())

    background_dataset = Dataset.create(Datasets.LIBRI_SPEECH, args.librispeech_dataset_path, exclude_word=args.keyword)
    logging.info('loaded librispeech dataset with %d examples' % background_dataset.size())

    noise_dataset = Dataset.create(Datasets.DEMAND, args.demand_dataset_path)
    logging.info('loaded demand dataset with %d examples' % noise_dataset.size())

    speech_path = os.path.join(os.path.dirname(__file__), '%s_speech.wav' % args.keyword)
    label_path = os.path.join(os.path.dirname(__file__), '%s_label.txt' % args.keyword)
    create_test_files(
        speech_path=speech_path,
        label_path=label_path,
        keyword_dataset=keyword_dataset,
        background_dataset=background_dataset,
        noise_dataset=noise_dataset)

    with multiprocessing.Pool() as pool:
        save(pool.map(run, [x for x in Engines]))
