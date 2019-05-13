import os

import matplotlib.pyplot as plt
import numpy as np

from engine import Engines

KEYWORDS = {'alexa', 'computer', 'jarvis', 'smart mirror', 'snowboy', 'view glass'}

ENGINE_COLORS = {
    Engines.POCKET_SPHINX.value: 'b',
    Engines.PORCUPINE.value: 'm',
    Engines.PORCUPINE_COMPRESSED.value: 'r',
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


def plot_roc(keyword):
    engines_roc = dict()

    for engine in Engines:
        engine = engine.value

        engines_roc[engine] = list()
        with open(os.path.join(os.path.dirname(__file__), '%s_%s.csv' % (keyword, engine)), 'r') as f:
            miss_rates = list()
            false_alarms_per_hour = list()
            for line in f.readlines():
                miss_rate, false_alarm = [float(x) for x in line.strip('\n').split(', ')]
                miss_rates.append(miss_rate)
                false_alarms_per_hour.append(false_alarm)
            engines_roc[engine].append((miss_rates, false_alarms_per_hour))

    for engine in Engines:
        engine = engine.value

        plt.plot(
            engines_roc[engine][0][1],
            engines_roc[engine][0][0],
            color=ENGINE_COLORS[engine],
            label=engine,
            marker='o')

    plt.legend()
    plt.xlim(0, 1)
    plt.xlabel('false alarm per hour')
    plt.ylim(0, 1)
    plt.ylabel('miss probability')
    plt.grid(linestyle='--')
    plt.title(keyword)
    plt.show()


def plot_engine_roc(engine):
    keywords_roc = dict()

    for keyword in KEYWORDS:
        keywords_roc[keyword] = list()
        with open(os.path.join(os.path.dirname(__file__), '%s_%s.csv' % (keyword, engine)), 'r') as f:
            miss_rates = list()
            false_alarms_per_hour = list()
            for line in f.readlines():
                miss_rate, false_alarm = [float(x) for x in line.strip('\n').split(', ')]
                miss_rates.append(miss_rate)
                false_alarms_per_hour.append(false_alarm)
            keywords_roc[keyword].append((miss_rates, false_alarms_per_hour))

    for keyword in KEYWORDS:
        plt.plot(
            keywords_roc[keyword][0][1],
            keywords_roc[keyword][0][0],
            color=KEYWORD_COLORS[keyword],
            label=keyword,
            marker='o')

    plt.legend()
    plt.xlim(0, 1)
    plt.xlabel('false alarm per hour')
    plt.ylim(0, 1)
    plt.ylabel('miss probability')
    plt.grid(linestyle='--')
    plt.title(engine)
    plt.show()


def plot_bar_chart(target_false_alarm_per_hour=0.1):
    engine_miss_rates = dict([(x.value, 0) for x in Engines])

    for keyword in KEYWORDS:
        for engine in Engines:
            engine = engine.value

            with open(os.path.join(os.path.dirname(__file__), '%s_%s.csv' % (keyword, engine)), 'r') as f:
                miss_rates = list()
                false_alarms_per_hour = list()
                for line in f.readlines():
                    miss_rate, false_alarm = [float(x) for x in line.strip('\n').split(', ')]
                    miss_rates.append(miss_rate)
                    false_alarms_per_hour.append(false_alarm)
                engine_miss_rates[engine] +=\
                    np.interp(target_false_alarm_per_hour, false_alarms_per_hour, miss_rates) / len(KEYWORDS)

    fig, ax = plt.subplots()

    engine_miss_rates = sorted(engine_miss_rates.items(), key=lambda x: x[1], reverse=True)
    engines = [x[0] for x in engine_miss_rates]
    miss_rates = [x[1] for x in engine_miss_rates]

    index = np.arange(len(engine_miss_rates))

    ax.bar(index, miss_rates, 0.4, color='b')

    for i in index:
        ax.text(i - 0.1, engine_miss_rates[i][1] + 0.05, '%.2f' % engine_miss_rates[i][1], color='b')

    ax.set_xlabel('engines')
    ax.set_ylabel('miss probability')
    ax.set_ylim(0, 1)
    ax.set_title('miss rates (at 1 false alarm per 10 hours)')
    ax.set_xticks(index)
    ax.set_xticklabels(engines)

    fig.tight_layout()
    plt.show()


def plot_cpu_chart():
    fig, ax = plt.subplots()

    engine_cpu_usage = [
        (Engines.POCKET_SPHINX.value, 31.75),
        (Engines.SNOWBOY.value, 24.82),
        (Engines.PORCUPINE.value, 5.67),
        (Engines.PORCUPINE_COMPRESSED.value, 2.43)
    ]

    engines = [x[0] for x in engine_cpu_usage]
    cpu_usages = [x[1] for x in engine_cpu_usage]

    index = np.arange(len(engine_cpu_usage))

    ax.bar(index, cpu_usages, 0.4, color='g')

    for i in index:
        ax.text(i - 0.1, engine_cpu_usage[i][1] + 1, '%.2f' % engine_cpu_usage[i][1], color='g')

    ax.set_xlabel('engines')
    ax.set_ylabel('CPU usage %')
    ax.set_ylim(0, 40)
    ax.set_title('average CPU usage on Raspberry Pi 3')
    ax.set_xticks(index)
    ax.set_xticklabels(engines)

    fig.tight_layout()
    plt.show()


if __name__ == '__main__':
    for k in KEYWORDS:
        plot_roc(k)

    for e in Engines:
        plot_engine_roc(e.value)

    plot_bar_chart()

    plot_cpu_chart()
