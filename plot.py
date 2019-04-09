import os

import matplotlib.pyplot as plt

from engine import Engines

if __name__ == '__main__':
    engine_colors = {
        Engines.POCKET_SPHINX.value: 'b',
        Engines.PORCUPINE.value: 'm',
        Engines.PORCUPINE_COMPRESSED.value: 'r',
        Engines.SNOWBOY.value: 'g'
    }

    engines_roc = dict()

    for engine in Engines:
        engine = engine.value

        engines_roc[engine] = list()
        with open(os.path.join(os.path.dirname(__file__), '%s.csv' % engine), 'r') as f:
            miss_rates = list()
            false_alarms_per_hour = list()
            for line in f.readlines():
                miss_rate, false_alarm = [float(x) for x in line.strip('\n').split(', ')]
                miss_rates.append(miss_rate)
                false_alarms_per_hour.append(false_alarm)
            engines_roc[engine].append((miss_rates, false_alarms_per_hour))

    for engine in Engines:
        engine = engine.value

        plt.plot(engines_roc[engine][0][1], engines_roc[engine][0][0], color=engine_colors[engine], label=engine, marker='o')

    plt.legend()
    plt.xlim(0, 0.8)
    plt.xlabel('false alarm per hour')
    plt.ylim(0, 0.6)
    plt.ylabel('miss probability')
    plt.grid(linestyle='--')
    plt.show()
