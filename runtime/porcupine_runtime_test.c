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

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>

#include "pv_porcupine.h"

/**
 * Simple utility program to measure the real time factor (RTF) of Porcupine wake-word engine. It processes a WAV file
 * with sampling rate of 16000 and measures duration of file and execution time. Different variants of Porcupine engine
 * (i.e. standard, small, and tiny) can be tested by passing corresponding model/keyword files.
 */
int main(int argc, char *argv[]) {
    if (argc != 5) {
        printf("usage: pv_porcupine_runtime_test wav_path model_file_path keyword_file_path library_path\n");
        return 1;
    }

    const char *wav_path = argv[1];
    const char *model_file_path = argv[2];
    const char *keyword_file_path = argv[3];
    const char *library_path = argv[4];

    void *handle = dlopen(library_path, RTLD_NOW);
    if (!handle) {
        printf("failed to open porcupine's shared library at '%s'\n", library_path);
    }

    pv_status_t (*pv_porcupine_init_func)(const char*, const char*, float, pv_porcupine_object_t**);
    pv_porcupine_init_func = dlsym(handle, "pv_porcupine_init");

    void (*pv_porcupine_delete_func)(pv_porcupine_object_t*);
    pv_porcupine_delete_func = dlsym(handle, "pv_porcupine_delete");

    pv_status_t (*pv_porcupine_process_func)(pv_porcupine_object_t*, const int16_t*, bool*);
    pv_porcupine_process_func = dlsym(handle, "pv_porcupine_process");

    int (*pv_porcupine_frame_length_func)();
    pv_porcupine_frame_length_func = dlsym(handle, "pv_porcupine_frame_length");

    FILE *wav = fopen(wav_path, "rb");
    if (!wav) {
        printf("failed to open wav file located at '%s'\n", wav_path);
        return 1;
    }

    // Assume the input WAV file has sampling rate of 1600 and is 16bit encoded. Skip the WAV header and get to data
    // portion.

    static const int WAV_HEADER_SIZE_BYTES = 44;

    if (fseek(wav, WAV_HEADER_SIZE_BYTES, SEEK_SET) != 0) {
        printf("failed to skip the wav header\n");
        return 1;
    }

    const size_t frame_length = (size_t) pv_porcupine_frame_length_func();

    int16_t *pcm = malloc(sizeof(int16_t) * frame_length);
    if (!pcm) {
        printf("failed to allocate memory for audio buffer\n");
        return 1;
    }

    pv_porcupine_object_t *porcupine;
    pv_status_t status = pv_porcupine_init_func(model_file_path, keyword_file_path, 0.5, &porcupine);
    if (status != PV_STATUS_SUCCESS) {
        printf("failed to initialize porcupine with following arguments:\n");
        printf("model file path: %s", model_file_path);
        printf("keyword file path: %s", keyword_file_path);
        return 1;
    }

    static const int SAMPLE_RATE = 16000;

    double total_cpu_time_usec = 0;
    double total_processed_time_usec = 0;

    while(fread(pcm, sizeof(int16_t), frame_length, wav) == frame_length) {
        struct timeval before, after;
        gettimeofday(&before, NULL);

        bool result;
        status = pv_porcupine_process_func(porcupine, pcm, &result);
        if (status != PV_STATUS_SUCCESS) {
            printf("failed to process audio\n");
            return 1;
        }

        gettimeofday(&after, NULL);

        total_cpu_time_usec += (after.tv_sec - before.tv_sec) * 1e6 + (after.tv_usec - before.tv_usec);
        total_processed_time_usec += (frame_length * 1e6) / SAMPLE_RATE;
    }

    const double real_time_factor = total_cpu_time_usec / total_processed_time_usec;
    printf("real time factor is: %f\n", real_time_factor);

    pv_porcupine_delete_func(porcupine);
    free(pcm);
    fclose(wav);

    return 0;
}
