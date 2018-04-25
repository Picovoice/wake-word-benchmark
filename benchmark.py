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
import csv
import logging
import multiprocessing
import os
import time

import matplotlib.pyplot as plt
import numpy as np

from dataset import Dataset
from dataset import DatasetInstance
from engine import Engine
from engine import EngineInstance
from wakeword_executor import WakeWordExecutor

# Filter out logs from sox.
logging.getLogger('sox').setLevel(logging.ERROR)
logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.INFO)

# Parse arguments.
parser = argparse.ArgumentParser(description='Benchmark for different wake-word engines')
parser.add_argument('--common_voice_directory',
                    type=str,
                    help='root directory of Common Voice dataset',
                    required=True)
parser.add_argument('--alexa_directory',
                    type=str,
                    help='root directory of Alexa dataset',
                    required=True)

parser.add_argument('--demand_directory',
                    type=str,
                    help='root directory of Demand dataset',
                    required=True)

parser.add_argument('--output_directory',
                    type=str,
                    help='output directory to save the results')

parser.add_argument('--add_noise',
                    action='store_true',
                    default=False,
                    help='add noise to the datasets')


def run_detection(engine_type):
    """Run wake-word detection for a given engine.

    :param engine_type: type of the engine.
    :return: dictionary of false alarms and miss-detections.
    """

    res = []
    for sensitivity in Engine.sensitivity_range(engine_type):
        executor = WakeWordExecutor(engine_type, sensitivity, keyword, dataset, noise_dataset=noise_dataset)
        # Measure the execution time.
        start_time = time.process_time()
        fa, md = executor.execute()
        end_time = time.process_time()
        logging.info('[%s][%s] took %s minutes to finish', engine_type.value, sensitivity, (end_time - start_time) / 60)
        res.append({'engine': engine_type.value, 'sensitivity': sensitivity, 'false_alarm': fa, 'miss_detection': md})
        executor.release()

    return res


if __name__ == '__main__':
    # Keyword for this test.
    keyword = 'alexa'
    args = parser.parse_args()
    # Read the datasets once to mitigate IO operations.
    background_dataset = Dataset.create(DatasetInstance.CommonVoiceDataset, args.common_voice_directory,
                                        exclude_words=keyword).metadata()
    keyword_dataset = Dataset.create(DatasetInstance.AlexaDataset, args.alexa_directory).metadata()
    noise_dataset = None
    if args.add_noise:
        logging.info('Running benchmark by adding noise to the datasets')
        noise_dataset = Dataset.create(DatasetInstance.DemandDataset, args.demand_directory).metadata()

    # Interleave the keyword dataset with background dataset to simulate the real-world conditions.
    dataset = background_dataset
    dataset.extend(keyword_dataset)
    random = np.random.RandomState(seed=666)
    random.shuffle(dataset)

    # Run the benchmark for each engine in it's own process.
    with multiprocessing.Pool() as pool:
        results = pool.map(run_detection, [e for e in EngineInstance])

    # Plot the ROC curves.
    fig = plt.figure()
    plt.xlabel('False alarm per hour')
    plt.ylabel('Miss detection rate')
    for result, marker, color, legend_location in zip(results, ['o', '*', '^'], ['b', 'r', 'g'], [1, 3, 2]):
        false_alarms = [r['false_alarm'] for r in result]
        miss_detections = [r['miss_detection'] for r in result]
        roc, = plt.plot(false_alarms, miss_detections, c=color, marker=marker,
                        label=result[0]['engine'])
        legend = plt.legend(handles=[roc], loc=legend_location)
        plt.gca().add_artist(legend)

    plt.show()

    # Save the results.
    if args.output_directory:
        if not os.path.exists(args.output_directory):
            os.makedirs(args.output_directory)
        for result in results:
            with open(os.path.join(args.output_directory, '%s.csv' % result[0]['engine']), 'w') as f:
                writer = csv.DictWriter(f, ['engine', 'sensitivity', 'false_alarm', 'miss_detection'])
                writer.writeheader()
                writer.writerows(result)
