# Runtime Measurements

Below the methodology for measuring runtime (i.e. real-time factor and memory) metrics of different wake-word engines is
explained. The goal is to measure only the CPU and memory consumed by the engine and not remaining tasks such as 
audio reading (from file or microphone), moving data between C and different language bindings, etc when possible.

For Porcupine and Snowboy lean utility programs are created [here](/runtime/porcupine_runtime_test.c) and
[here](/runtime/snowboy_runtime_test.cpp). These programs read a WAV file and pass it through the corresponding wake-word
engine frame-by-frame as is the case in real time applications. They only measure the time spent in the corresponding 
processing/detection method of the engines.

For PocketSphinx the task of creating such utility program is more involved and hence we opt for easier method of
measuring the processing time of its commandline interface. This is essentially an upperbound on actual processing time
of PocketSphinx.

All the measurements are done on **Raspberry Pi 3**. The wake-word for testing is 'Alexa' same as the accuracy benchmark.

## Real Time Factor

The [real time factor](http://enacademic.com/dic.nsf/enwiki/3796485) is ratio of processing time to length of audio input.
It can be thought of as inverse CPU usage. It is a common metric for measuring the performance of speech recognition system. For
example, if it takes an engine 2 seconds to process a 20 second audio file it has a real time factor of 10. The higher
the real time factor the more computationally-efficient (faster) the engine is.

### Snowboy

First, we need to build the utility program for Snowboy. From the root of the repository execute the following in the
command line

```bash
g++ -o runtime/snowboy_runtime_test -O3 --std=c++11 -D_GLIBCXX_USE_CXX11_ABI=0 -I engines/snowboy/include/ \
runtime/snowboy_runtime_test.cpp engines/snowboy/lib/rpi/libsnowboy-detect.a /usr/lib/atlas-base/libf77blas.a \
/usr/lib/atlas-base/libcblas.a /usr/lib/atlas-base/liblapack_atlas.a /usr/lib/atlas-base/libatlas.a
```

it creates a binary file called `runtime/snowboy_runtime_test`. Next we run the file on a sample audio file to measure
the realtime factor. The file contains speech with background babble noise (same file is used for all measurements)

```bash
./runtime/snowboy_runtime_test engines/porcupine/resources/audio_samples/multiple_keywords.wav \
engines/snowboy/resources/common.res engines/snowboy/resources/alexa/alexa-avs-sample-app/alexa.umdl
```

### Porcupine

First, we need to build the utility program for Porcupine. From the root of the repository execute the following in the
command line

```bash
gcc -O3 -o runtime/porcupine_runtime_test -I engines/porcupine/include/ runtime/porcupine_runtime_test.c \
engines/porcupine/lib/raspberry-pi/cortex-a53/libpv_porcupine.a -lm
```

it creates a binary file called `runtime/porcupine_runtime_test`. Next we run the file on a sample audio file to measure
the realtime factor for each variant (standard, small, and tiny) by

```bash
./runtime/porcupine_runtime_test engines/porcupine/resources/audio_samples/multiple_keywords.wav \
engines/porcupine/lib/common/porcupine_params.pv engines/porcupine/resources/keyword_files/alexa_raspberrypi.ppn
```

```bash
./runtime/porcupine_runtime_test engines/porcupine/resources/audio_samples/multiple_keywords.wav \
engines/porcupine/lib/common/porcupine_small_params.pv engines/porcupine/resources/keyword_files/alexa_raspberrypi_small.ppn
```

```bash
./runtime/porcupine_runtime_test engines/porcupine/resources/audio_samples/multiple_keywords.wav \
engines/porcupine/lib/common/porcupine_tiny_params.pv engines/porcupine/resources/keyword_files/alexa_raspberrypi_tiny.ppn
```

### PocketSphinx

For PocketSphinx for opt for simpler method of measuring the processing time from commandline using the following command

```bash
time  pocketsphinx_continuous -logfn /dev/null -keyphrase alexa -infile engines/porcupine/resources/audio_samples/multiple_keywords.wav
```

Then divide the length of WAV file (in seconds) by the output of previous command (i.e. processing time). 

## Memory

We use [valgrind's](http://valgrind.org/) [massif](http://valgrind.org/docs/manual/ms-manual.html) tool for measuring used memory.
Simply run any of the commands above prepended with `valgrind --tool=massif` and then read the generated output file with
`ms_print`. For example:

```bash
valgrind --tool=massif ./runtime/porcupine_runtime_test engines/porcupine/resources/audio_samples/multiple_keywords.wav \
engines/porcupine/lib/common/porcupine_params.pv engines/porcupine/resources/keyword_files/alexa_raspberrypi.ppn
```

and then read out the generated file by

```bash
ms_print massif.out.XXXX
```
