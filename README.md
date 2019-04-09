# Wake Word Benchmark

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/Picovoice/wakeword-benchmark/blob/master/LICENSE)

Made in Vancouver, Canada by [Picovoice](https://picovoice.ai)

The purpose of this benchmarking framework is to provide a scientific comparison between different wake word detection
engines in terms of accuracy and runtime metrics. Currently, the framework is set up for Alexa as the test wake word.
But it can be configured for any other wake word. While working on [Porcupine](https://github.com/Picovoice/Porcupine)
we noted that there is a need for such a tool to empower customers to make data-driven decisions.

# Data

[LibriSpeech](http://www.openslr.org/12/) (test_clean portion) is used as background dataset. It can be downloaded
from [OpenSLR](http://www.openslr.org/resources/12/test-clean.tar.gz).

Furthermore, 329 recordings of the word Alexa from 89 distinct speakers are used. The recordings are crowd-sourced using an
Android mobile application. The recordings are stored within the repository [here](audio/alexa).

In order to simulate real-world situations, the data is mixed with noise (at 0 dB SNR). For this purpose, we use
[DEMAND](https://asa.scitation.org/doi/abs/10.1121/1.4799597) dataset which has noise recording in 18 different
environments (e.g. kitchen, office, traffic, etc.). It can be downloaded from
[Kaggle](https://www.kaggle.com/aanhari/demand-dataset).

# Wake Word Engines

Three wake-word engines are used. [PocketSphinx](https://github.com/cmusphinx/pocketsphinx) which can
be installed using [PyPI](https://pypi.org/project/pocketsphinx/). [Porcupine](https://github.com/Picovoice/Porcupine)
and [Snowboy](https://github.com/Kitt-AI/snowboy) which are included as submodules in this repository. 

# Metric

We measure the accuracy of the wake word engines using false alarm per hour and miss detection rates. The false alarm
per hour is measured as a number of false positives in an hour. Miss detection is measured as the percentage of wake word
 utterances an engine rejects incorrectly. Using these definitions we compare the engines for a given false alarm rate and
 the engine with a smaller miss detection rate has a better performance.

The measured runtime metric is real time factor. Real time factor is computed by dividing the processing time to the
length of input audio. It can be thought of as average CPU usage. The engine with a lower real time factor is more
computationally efficient (faster).

# Usage

### Prerequisites

The benchmark has been developed on Ubuntu 16.04 with Python 3.5. It should be possible to run it on a Mac machine
or different distributions of Linux but has not been tested. Clone the repository using

```bash
git clone --recurse-submodules git@github.com:Picovoice/wakeword-benchmark.git
```

Make sure the Python packages in the [requirements.txt](/requirements.txt) are properly installed for your Python
version as Python bindings are used for running the engines. The repositories for Porcupine and Snowboy are cloned in
[engines](/engines). Follow the instructions on their repositories to be able to run their Python demo before proceeding
to the next step.

### Running the Accuracy Benchmark

Usage information can be retrieved via

```bash
python benchmark.py -h
```

The benchmark can be run using the following command from the root of the repository

```bash
python benchmark.py --librispeech_dataset_path ${LIBRISPEECH_DATASET_PATH} --demand_dataset_path ${DEMAND_DATASET_PATH}
```

### Running the Runtime Benchmark

Refer to runtime [documentation](/runtime/README.md).

# Results

## Accuracy

Below is the result (ROC curve) of running the benchmark framework.

![](doc/img/benchmark_roc.png)


## Runtime

Below are the runtime measurements on a Raspberry Pi 3.

Engine | Real Time Factor | Average CPU Usage
:---: | :---: | :---:
PocketSphinx | 0.32 | 31.75%
Porcupine | 0.06| 5.67%
Porcupine Compressed | 0.02 | 2.43%
Snowboy | 0.19 | 18.94%
