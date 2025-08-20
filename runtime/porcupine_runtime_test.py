import argparse
import time

import numpy as np
import pvporcupine
import soundfile


def run(audio_path, keyword, access_key):
    pcm, sample_rate = soundfile.read(audio_path, dtype=np.int16)

    porcupine = pvporcupine.create(access_key=access_key, keywords=[keyword.lower()])

    frame_length = 512
    num_frames = pcm.size // frame_length

    processing_time = 0

    for i in range(num_frames):
        frame = pcm[(i * frame_length):((i + 1) * frame_length)]
        start_time = time.process_time()
        _ = porcupine.process(frame)
        end_time = time.process_time()
        processing_time += end_time - start_time

    duration_sec = pcm.size / 16000
    rtf = processing_time / duration_sec

    print(f"Audio duration  : {duration_sec:.5f} s")
    print(f"Processing time : {processing_time:.5f} s")
    print(f"Real-time factor: {rtf:.5f}")

    porcupine.delete()


parser = argparse.ArgumentParser()
parser.add_argument('--audio', required=True)
parser.add_argument('--keyword', required=True)
parser.add_argument('--access-key', required=True)

if __name__ == '__main__':
    args = parser.parse_args()
    run(args.audio, args.keyword, args.access_key)
