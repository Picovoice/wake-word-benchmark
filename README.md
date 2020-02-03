# Wake Word Benchmark

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/Picovoice/wakeword-benchmark/blob/master/LICENSE)

Made in Vancouver, Canada by [Picovoice](https://picovoice.ai)

The purpose of this benchmarking framework is to provide a scientific comparison between different wake word detection
engines in terms of accuracy and runtime metrics. While working on [Porcupine](https://github.com/Picovoice/Porcupine)
we noted that there is a need for such a tool to empower customers to make data-driven decisions.

# Data

[LibriSpeech](http://www.openslr.org/12/) (test_clean portion) is used as background dataset. It can be downloaded
from [OpenSLR](http://www.openslr.org/resources/12/test-clean.tar.gz).

Furthermore, more than 300 recordings of six keywords (alexa, computer, jarvis, smart mirror, snowboy, and view glass)
from more than 50 distinct speakers are used. The recordings are crowd-sourced. The recordings are stored within the
repository [here](audio/).

In order to simulate real-world situations, the data is mixed with noise (at 10 dB SNR). For this purpose, we use
[DEMAND](https://asa.scitation.org/doi/abs/10.1121/1.4799597) dataset which has noise recording in 18 different
environments (e.g. kitchen, office, traffic, etc.). It can be downloaded from
[Kaggle](https://www.kaggle.com/aanhari/demand-dataset).

# Wake Word Engines

Three wake-word engines are used. [PocketSphinx](https://github.com/cmusphinx/pocketsphinx) which can
be installed using [PyPI](https://pypi.org/project/pocketsphinx/). [Porcupine](https://github.com/Picovoice/Porcupine)
and [Snowboy](https://github.com/Kitt-AI/snowboy) which are included as submodules in this repository. The Snowboy engine
has a audio frontend component which is not normally a part of wake word engines and is considered a  separate part of
audio processing chain. The other two engines have not such component in them. We enabled this component in Snowboy engine
for this benchmark as this is the optimal way of running it. 

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

The benchmark has been developed on Ubuntu 18.04 with Python 3.6. Clone the repository using

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
python benchmark.py --librispeech_dataset_path ${LIBRISPEECH_DATASET_PATH} --demand_dataset_path ${DEMAND_DATASET_PATH} --keyword ${KEYWORD}
```

### Running the Runtime Benchmark

Refer to runtime [documentation](/runtime/README.md).

# Results

## Accuracy

Below is the result of running the benchmark framework averaged on six different keywords. The plot below shows the miss
rate of different engines at 1 false alarm per 10 hours. The lower the miss rate the more accurate the engine is.

![](doc/img/summary.png)


## Runtime

Below is the runtime measurements on a Raspberry Pi 3. For Snowboy the runtime highly-depends on the keyword. Therefore
we measured the CPU usage for each keyword and used the average.

![](doc/img/cpu.png)
