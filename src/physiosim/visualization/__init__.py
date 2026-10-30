"""Headless scientific plots of computed arrays; no waveform synthesis."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.integrate import trapezoid


def plot_comparison(results, output):
    output = Path(output)
    fig, axes = plt.subplots(4, 2, figsize=(14, 14), constrained_layout=True)
    colors = ('#1764ab', '#c43b36', '#20855e')
    for (name, r), color in zip(results.items(), colors):
        label = name.replace('_', ' ')
        n = min(3 * r.samples_per_cycle + 1, len(r.time))
        t, v, p, q = r.time[-n:], r.volumes[-n:], r.pressures[-n:], r.flows[-n:]
        axes[0, 0].plot(t, p[:, 1], color=color, label=label)
        axes[0, 1].plot(t, p[:, 0], color=color, label=label)
        axes[1, 0].plot(t, q[:, 0], color=color)
        axes[1, 1].plot(t, v[:, 0], color=color)
        axes[2, 0].plot(t, p[:, 5], color=color)
        axes[2, 1].plot(t, v[:, 3], color=color)
        axes[3, 0].plot(r.volumes[r.final_beat, 0], r.pressures[r.final_beat, 0], color=color)
    labels = [('Systemic arterial pressure', 'mmHg'), ('LV pressure', 'mmHg'),
              ('Aortic valve flow', 'mL/s'), ('LV volume', 'mL'),
              ('Pulmonary venous reservoir pressure', 'mmHg'), ('RV volume', 'mL')]
    for ax, (title, unit) in zip(axes.flat, labels):
        ax.set(title=title, ylabel=unit, xlabel='Time (s)')
        ax.grid(alpha=.2)
    axes[0, 0].legend(fontsize=8)
    axes[3, 0].set(title='Last-beat LV pressure-volume loop', xlabel='Volume (mL)', ylabel='Pressure (mmHg)')
    axes[3, 0].grid(alpha=.2)
    axes[3, 1].axis('off')
    p = next(iter(results.values())).parameters
    axes[3, 1].text(0, .96,
        'EXPERIMENTAL — not for clinical use\n\n'
        'Separate runs from identical initial volumes.\n'
        'Baseline is an exploratory elevated-pressure case.\n'
        'Restoration is a parameter scenario, not a drug.\n\n'
        f'HR = {p.heart_rate:g} /min; total volume = {sum(p.initial_volumes):g} mL\n'
        'LV Emax: baseline 2.5, reduced 1.25, restoration 1.875\n'
        '(mmHg/mL; all values illustrative)\n\n'
        'Selected semantic relations:\n'
        'P_lv → fluid pressure → blood in left ventricle\n'
        'Q_aortic → fluid flow → LV-to-systemic-artery path\n'
        'E_lv → fluid volumetric elastance → LV wall\n\n'
        'Omitted: atria, reflexes, septal interaction,\n'
        'respiration, renal feedback, drug PK/PD.', va='top', fontsize=10)
    fig.suptitle('Experimental cardiovascular simulations — final three cycles', fontsize=15)
    fig.savefig(output / 'comparison.png', dpi=140)
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), constrained_layout=True)
    for (name, r), color in zip(results.items(), colors):
        axes[0].plot(r.time, r.pressures[:, 5], color=color, label=name.replace('_', ' '))
        n = r.samples_per_cycle
        ends, outputs = [], []
        for start in range(0, len(r.time) - n, n):
            s = slice(start, start + n + 1)
            ends.append(r.time[start + n])
            outputs.append(float(trapezoid(r.flows[s, 0], r.time[s]) / r.parameters.period * 60 / 1000))
        axes[1].plot(ends, outputs, color=color)
    axes[0].set(title='Pulmonary venous reservoir pressure — includes initialization transient', ylabel='mmHg')
    axes[1].set(title='Aortic cardiac output integrated over each full cycle', ylabel='L/min', xlabel='Time (s)')
    axes[0].legend(fontsize=8)
    for ax in axes:
        ax.grid(alpha=.2)
    fig.suptitle('EXPERIMENTAL — independently initialized scenarios, not a timed treatment sequence')
    fig.savefig(output / 'transients.png', dpi=140)
    plt.close(fig)
