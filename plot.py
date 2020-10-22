import os

import matplotlib.pyplot as plt
import numpy as np

from engine import Engines

KEYWORDS = {'alexa', 'computer', 'jarvis', 'smart mirror', 'snowboy', 'view glass'}

ENGINE_COLORS = {
    Engines.POCKET_SPHINX.value: 'b',
    Engines.PORCUPINE.value: 'm',
    Engines.SNOWBOY.value: 'g'
}

KEYWORD_COLORS = {
    'alexa': 'b',
    'computer': 'm',
    'jarvis': 'r',
    'smart mirror': 'g',
    'snowboy': 'c',
    'view glass': 'y'
}

COLOR = (119 / 255, 131 / 255, 143 / 255)
PV_COLOR = (55 / 255, 125 / 255, 255 / 255)


def plot_accuracy_chart(target_false_alarm_per_hour=0.1):
    engine_miss_rates = dict([(x.value, 0) for x in Engines])

    for keyword in KEYWORDS:
        for engine in Engines:
            engine = engine.value

            with open(os.path.join(os.path.dirname(__file__), '%s_%s.csv' % (keyword, engine)), 'r') as f:
                miss_rates = list()
                false_alarms_per_hour = list()
                for line in f.readlines():
                    miss_rate, false_alarm = [float(x) for x in line.strip('\n').split(', ')]
                    if len(false_alarms_per_hour) > 0 and false_alarms_per_hour[-1] == false_alarm:
                        miss_rates[-1] = miss_rate
                    else:
                        miss_rates.append(miss_rate)
                        false_alarms_per_hour.append(false_alarm)
                engine_miss_rates[engine] += \
                    np.interp(target_false_alarm_per_hour, false_alarms_per_hour, miss_rates) / len(KEYWORDS)

    engine_miss_rates = sorted(engine_miss_rates.items(), key=lambda x: x[1], reverse=True)
    engines = [x[0] for x in engine_miss_rates]
    miss_rates = [x[1] * 100 for x in engine_miss_rates]
    indices = np.arange(len(engine_miss_rates))

    fig, ax = plt.subplots()

    for spine in plt.gca().spines.values():
        if spine.spine_type != 'bottom':
            spine.set_visible(False)

    for i in indices:
        ax.bar(
            indices[i],
            miss_rates[i],
            0.4,
            color=PV_COLOR if engines[i] == Engines.PORCUPINE.value else COLOR)

    for i in indices:
        ax.text(
            i - 0.075,
            miss_rates[i] + 2,
            '%.1f%%' % miss_rates[i],
            color=PV_COLOR if engines[i] == Engines.PORCUPINE.value else COLOR)

    ax.set_title('Wake Word Miss Rate\n(1 false alarm per %d hours)' % int(1 / target_false_alarm_per_hour))
    ax.set_ylim(0, max(miss_rates) + 10)
    ax.set_xticks(indices)
    ax.set_xticklabels(engines)
    plt.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)

    fig.tight_layout()
    plt.show()


def plot_cpu_chart():
    fig, ax = plt.subplots()

    for spine in plt.gca().spines.values():
        if spine.spine_type != 'bottom':
            spine.set_visible(False)

    engine_cpu_usage = [
        (Engines.POCKET_SPHINX.value, 31.75),
        (Engines.SNOWBOY.value, 24.82),
        (Engines.PORCUPINE.value, 3.80)
    ]

    engines = [x[0] for x in engine_cpu_usage]
    cpu_usages = [x[1] for x in engine_cpu_usage]
    indices = np.arange(len(engine_cpu_usage))

    for i in indices:
        ax.bar(
            indices[i],
            cpu_usages[i],
            0.4,
            color=PV_COLOR if engines[i] == Engines.PORCUPINE.value else COLOR)

    for i in indices:
        ax.text(
            i - 0.075,
            cpu_usages[i] + 1,
            '%.1f%%' % cpu_usages[i],
            color=PV_COLOR if engines[i] == Engines.PORCUPINE.value else COLOR)

    ax.set_ylim(0, max(cpu_usages) + 10)
    ax.set_title('CPU usage on Raspberry Pi 3')
    ax.set_xticks(indices)
    ax.set_xticklabels(engines)
    plt.tick_params(axis='y', which='both', left=False, right=False, labelleft=False)

    fig.tight_layout()
    plt.show()


if __name__ == '__main__':
    plot_accuracy_chart()

    plot_cpu_chart()
