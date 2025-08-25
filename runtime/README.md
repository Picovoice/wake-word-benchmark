# Runtime Measurements

Below the methodology for measuring the real-time factor of different wake-word engines is explained. The goal is to
measure only the CPU consumed by the engine and not remaining tasks such as audio reading (from file or microphone),
moving data between C and different language bindings, etc. when possible.

For Snowboy a utility program is created [here](../runtime/snowboy_runtime_test.cpp).

For Porcupine, we use the file-based C demo application available within the official repository. These programs read a
WAV file and pass it through the corresponding wake-word engine frame-by-frame as is the case in real time applications.
They only measure the time spent in the corresponding processing/detection method of the engines.

For PocketSphinx the task of creating such a utility program is more involved and hence we opt for an easier method of
measuring the processing time of its commandline interface. This is essentially an upper bound on the actual processing
time of PocketSphinx.

All the measurements are done on Raspberry Pi 5 32bit.

## Real Time Factor

The [real time factor](https://openvoice-tech.net/index.php/Real-time-factor) is the ratio of processing time to 
the length of input audio. It can be thought of as average CPU usage. It is a common metric for measuring the 
performance of speech recognition systems. For example, if it takes an engine 1 seconds to process a 10-second audio 
file it has a real-time factor of 0.1. The lower the real-time factor the more 
computationally-efficient (faster) the engine is.

### Snowboy

First, we need to build the utility program for Snowboy. From the root of the repository execute the following in the
command line

```bash
g++ -o runtime/snowboy_runtime_test -O3 --std=c++11 -D_GLIBCXX_USE_CXX11_ABI=0 -I engines/snowboy/include/ \
runtime/snowboy_runtime_test.cpp engines/snowboy/lib/rpi/libsnowboy-detect.a /usr/lib/arm-linux-gnueabihf/libf77blas.a \
/usr/lib/arm-linux-gnueabihf/libcblas.a /usr/lib/arm-linux-gnueabihf/liblapack_atlas.a \
/usr/lib/arm-linux-gnueabihf/libatlas.a
```

it creates a binary file called `runtime/snowboy_runtime_test`. Next we run the file on a sample audio file to measure
the realtime factor. The file contains speech with background babble noise (same file is used for all measurements)

```bash
./runtime/snowboy_runtime_test audio/multiple_keywords.wav \
engines/snowboy/resources/common.res engines/snowboy/resources/alexa/alexa-avs-sample-app/alexa.umdl alexa
```

### Porcupine
Refer to the documentation of the [C demo](https://github.com/Picovoice/porcupine/tree/master/demo/c) application
within the official repository.

### PocketSphinx

For PocketSphinx we opt for simpler method of measuring the processing time from commandline using the following command

```bash
time  pocketsphinx_continuous -logfn /dev/null -keyphrase alexa -infile audio/multiple_keywords.wav
```

Then divide the output of previous command (i.e. processing time) by the length of WAV file (in seconds). 
