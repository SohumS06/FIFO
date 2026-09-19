#!/usr/bin/env python3
"""Render waveform PNGs for a handful of isolated FIFO test scenarios.

Runs a single cocotb test at a time (via COCOTB_TEST_FILTER) so each FST
dump starts clean at t=0 with exactly one scenario in it, converts the FST
to VCD with gtkwave's fst2vcd, then plots the interesting signals with
matplotlib.
"""
import os
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import vcdvcd

SIM_DIR = os.path.dirname(os.path.abspath(__file__))
SIM_BUILD = os.path.join(SIM_DIR, "sim_build")
DOCS_DIR = os.path.join(SIM_DIR, "..", "docs", "waveforms")

TOP = "FIFO"

# (cocotb testcase, output png stem, human title)
SCENARIOS = [
    ("test_back_to_back_streaming", "fill_then_drain", "Fill then drain (full/empty toggling)"),
    ("test_simultaneous_read_write", "simultaneous_read_write", "Simultaneous read + write"),
    ("test_pointer_wraparound", "pointer_wraparound", "Pointer wraparound across three fill/drain rounds"),
]

BIT_SIGNALS = ["reset", "wr_en", "rd_en", "full", "empty"]
BUS_SIGNALS = ["wr_data", "rd_data", "wr_ptr", "rd_ptr"]


def run_scenario(testcase):
    subprocess.run(["make", "-C", SIM_DIR, "clean"], check=True, stdout=subprocess.DEVNULL)
    env = dict(os.environ, COCOTB_TEST_FILTER=testcase)
    subprocess.run(
        ["make", "-C", SIM_DIR, "WAVES=1"],
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
    )

    fst_path = os.path.join(SIM_BUILD, f"{TOP}.fst")
    vcd_path = os.path.join(SIM_BUILD, f"{testcase}.vcd")
    subprocess.run(["fst2vcd", fst_path, "-o", vcd_path], check=True, stdout=subprocess.DEVNULL)
    return vcd_path


def load_signal(vcd, base_name):
    """Find a (possibly bussed) signal by its base name and return (time_ns, values)."""
    match = None
    for name in vcd.get_signals():
        short = name.split(".")[-1].split("[")[0]
        if short == base_name:
            match = name
            break
    if match is None:
        return None

    sig = vcd[match]
    times_ns = [t / 1000.0 for t, _ in sig.tv]
    values = [v for _, v in sig.tv]
    return times_ns, values


def to_int(value_str):
    if "x" in value_str or "z" in value_str:
        return None
    return int(value_str, 2)


def plot_bit(ax, name, times, values, end_time):
    times = times + [end_time]
    ivals = [int(v) if v in ("0", "1") else 0 for v in values]
    ivals = ivals + [ivals[-1]]
    ax.fill_between(times, ivals, step="post", alpha=0.3, color="tab:blue")
    ax.step(times, ivals, where="post", color="tab:blue", linewidth=1.5)
    ax.set_ylim(-0.2, 1.2)
    ax.set_yticks([0, 1])
    ax.set_ylabel(name, rotation=0, ha="right", va="center")
    ax.margins(x=0)


def plot_bus(ax, name, times, values, end_time):
    times = times + [end_time]
    ints = [to_int(v) for v in values]
    ints = ints + [ints[-1]]
    plot_vals = [v if v is not None else 0 for v in ints]
    ax.step(times, plot_vals, where="post", color="tab:orange", linewidth=1.5)
    ax.set_ylabel(name, rotation=0, ha="right", va="center")
    ax.margins(x=0)

    total_span = end_time - times[0] if end_time > times[0] else 1
    min_label_width = total_span * 0.02

    for i in range(len(times) - 1):
        seg_start, seg_end = times[i], times[i + 1]
        if seg_end - seg_start < min_label_width:
            continue
        if ints[i] is None:
            continue
        mid = (seg_start + seg_end) / 2
        ax.annotate(
            f"0x{ints[i]:02x}",
            xy=(mid, ints[i]),
            xytext=(0, 6),
            textcoords="offset points",
            ha="center",
            fontsize=7,
        )
    if plot_vals:
        pad = max(plot_vals) * 0.25 + 1
        ax.set_ylim(min(plot_vals) - pad * 0.3, max(plot_vals) + pad)


def render(testcase, stem, title):
    vcd_path = run_scenario(testcase)
    vcd = vcdvcd.VCDVCD(vcd_path)
    end_time = vcd.endtime / 1000.0

    rows = []
    for name in BIT_SIGNALS:
        loaded = load_signal(vcd, name)
        if loaded:
            rows.append(("bit", name, loaded))
    for name in BUS_SIGNALS:
        loaded = load_signal(vcd, name)
        if loaded:
            rows.append(("bus", name, loaded))

    fig, axes = plt.subplots(
        len(rows), 1, figsize=(12, 1.1 * len(rows)), sharex=True, constrained_layout=True
    )
    if len(rows) == 1:
        axes = [axes]

    for ax, (kind, name, (times, values)) in zip(axes, rows):
        if kind == "bit":
            plot_bit(ax, name, times, values, end_time)
        else:
            plot_bus(ax, name, times, values, end_time)

    axes[-1].set_xlabel("time (ns)")
    fig.suptitle(title)

    os.makedirs(DOCS_DIR, exist_ok=True)
    out_path = os.path.join(DOCS_DIR, f"{stem}.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"wrote {out_path}")


def main():
    for testcase, stem, title in SCENARIOS:
        render(testcase, stem, title)


if __name__ == "__main__":
    sys.exit(main())
