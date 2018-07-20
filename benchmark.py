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
import time

from dataset import *
from engine import *
from wakeword_executor import WakeWordExecutor

# Filter out logs from sox.
logging.getLogger('sox').setLevel(logging.ERROR)
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)

parser = argparse.ArgumentParser(description='Benchmark for different wake-word engines')

parser.add_argument(
    '--common_voice_directory',
    type=str,
    help='root directory of Common Voice dataset',
    required=True)

parser.add_argument(
    '--alexa_directory',
    type=str,
    help='root directory of Alexa dataset',
    required=True)

parser.add_argument(
    '--demand_directory',
    type=str,
    help='root directory of Demand dataset',
    required=True)

parser.add_argument(
    '--output_directory',
    type=str,
    help='output directory to save the results')

parser.add_argument(
    '--add_noise',
    action='store_true',
    default=False,
    help='add noise to the datasets')


def run_detection(engine_type):
    """
    Run wake-word detection for a given engine.

    :param engine_type: type of the engine.
    :return: tuple of engine and list of accuracy information for different detection sensitivities.
    """

    res = []
    for sensitivity in Engine.sensitivity_range(engine_type):
        start_time = time.process_time()

        executor = WakeWordExecutor(engine_type, sensitivity, keyword, dataset, noise_dataset=noise_dataset)
        false_alarm_per_hour, miss_rate = executor.execute()
        executor.release()

        end_time = time.process_time()

        logging.info('[%s][%s] took %s minutes to finish', engine_type.value, sensitivity, (end_time - start_time) / 60)

        res.append(dict(sensitivity=sensitivity, false_alarm_per_hour=false_alarm_per_hour, miss_rate=miss_rate))

    return engine_type.value, res


if __name__ == '__main__':
    keyword = 'alexa'

    args = parser.parse_args()

    background_dataset = Dataset.create(Datasets.COMMON_VOICE, args.common_voice_directory, exclude_words=keyword)
    logging.info('loaded background speech dataset with %d examples' % background_dataset.size())

    keyword_dataset = Dataset.create(Datasets.ALEXA, args.alexa_directory)
    logging.info('loaded keyword dataset with %d examples' % keyword_dataset.size())

    if args.add_noise:
        noise_dataset = Dataset.create(Datasets.DEMAND, args.demand_directory)
        logging.info('loaded noise dataset with %d examples' % noise_dataset.size())
    else:
        noise_dataset = None

    # Interleave the keyword dataset with background dataset to simulate the real-world conditions.
    dataset = CompositeDataset(datasets=(background_dataset, keyword_dataset), shuffle=True)

    # Run the benchmark for each engine in it's own process.
    with multiprocessing.Pool() as pool:
        results = pool.map(run_detection, [e for e in Engines])

    # Save the results.
    if args.output_directory:
        if not os.path.exists(args.output_directory):
            os.makedirs(args.output_directory)

        for engine, result in results:
            with open(os.path.join(args.output_directory, '%s.csv' % engine), 'w') as f:
                writer = csv.DictWriter(f, ['sensitivity', 'false_alarm_per_hour', 'miss_rate'])
                writer.writeheader()
                writer.writerows(result)
