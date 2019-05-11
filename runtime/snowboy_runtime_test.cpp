/*
    Copyright 2018 Picovoice Inc.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

            http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
*/

#include <iostream>
#include <sys/time.h>

#include "snowboy-detect.h"

/**
 * Simple utility program to measure the real time factor (RTF) of Snowboy engine. It processes a WAV file
 * with sampling rate of 16000 and measures duration of file and execution time.
 */
int main(int argc, char *argv[]) {
    if (argc != 5) {
        std::cout << "usage: pv_snowboy_speed_test wav_path resource_path model_path keyword" << std::endl;
        return 1;
    }

    const char *wav_path = argv[1];
    std::string resource_path = argv[2];
    std::string model_path = argv[3];
    std::string keyword = argv[4];

    FILE *wav = fopen(wav_path, "rb");
    if (!wav) {
        std::cout << "failed to open wav file located at " << argv[1] << std::endl;
        return 1;
    }

    static const int WAV_HEADER_SIZE_BYTES = 44;

    if (fseek(wav, WAV_HEADER_SIZE_BYTES, SEEK_SET) != 0) {
        std::cout << "failed to skip the wav header";
        return 1;
    }

    const size_t frame_length = 512;

    auto *pcm = (int16_t*) malloc(sizeof(int16_t) * frame_length);
    if (!pcm) {
        std::cout << "failed to allocate memory for audio buffer" << std::endl;
        return 1;
    }

    // https://github.com/Kitt-AI/snowboy#pretrained-universal-models

    snowboy::SnowboyDetect detector(resource_path, model_path);
    if (keyword == "jarvis") {
        detector.SetSensitivity(std::string("0.5,0.5"));
    } else {
        detector.SetSensitivity(std::string("0.5"));
    }

    detector.SetAudioGain(1.0);

    if (keyword == "alexa" || keyword == "computer" || keyword == "jarvis" || keyword == "view glass") {
        detector.ApplyFrontend(true);
    } else {
        detector.ApplyFrontend(true);
    }

    static const int SAMPLE_RATE = 16000;

    double total_cpu_time_usec = 0;
    double total_processed_time_usec = 0;


    while(fread(pcm, sizeof(int16_t), frame_length, wav) == frame_length) {
        struct timeval before, after;
        gettimeofday(&before, NULL);

        detector.RunDetection(pcm, frame_length);

        gettimeofday(&after, NULL);

        total_cpu_time_usec += (after.tv_sec - before.tv_sec) * 1e6 + (after.tv_usec - before.tv_usec);
        total_processed_time_usec += (frame_length * 1e6) / SAMPLE_RATE;
    }

    const double real_time_factor = total_cpu_time_usec / total_processed_time_usec;
    printf("real time factor is: %f\n", real_time_factor);

    fclose(wav);

    return 0;
}
