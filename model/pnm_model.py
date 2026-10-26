"""Analytical baseline-vs-PNM pointer-chasing model (Eqs. 1 and 2 of the paper).

  T_baseline(N) = N * (H + T_HBM)                    H = T_interconnect + T_host_decode
  T_PNM(N)      = (H + T_SETUP) + N * T_HBM_LOCAL    one offload+return round trip, then N local hops

T_HBM comes from Ramulator2 (dependent random-probe, unloaded). H is NOT measured here:
it is swept over a range (sensitivity analysis) until a literature/gem5 value is available.

Run:  python3 pnm_model.py                      (writes PNG+PDF figures and a CSV next to this file)
      python3 pnm_model.py --cited-h 120        (adds a highlighted curve for a sourced H value)
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Measured with Ramulator 2.1 (pnm_dependent_probe.py): ns per dependent random access
T_HBM = {"HBM3-6400": 49.9, "HBM4-8000": 47.4}

H_SWEEP = [25, 50, 100, 150, 200]       # ns, host+interconnect cost per hop (ASSUMED range)
N_POINTS = (10, 100, 1000)              # hop counts reported in the paper table
OUT = os.path.dirname(os.path.abspath(__file__))


def t_baseline(n, h, t_hbm):
    return n * (h + t_hbm)


def t_pnm(n, h, t_hbm, t_setup, local_factor):
    # one command out + one result back costs about one host round trip (H), plus base-die setup
    return (h + t_setup) + n * t_hbm * local_factor


def speedup(n, h, t_hbm, t_setup, local_factor):
    return t_baseline(n, h, t_hbm) / t_pnm(n, h, t_hbm, t_setup, local_factor)


def break_even_n(h, t_hbm, t_setup, local_factor):
    denom = h + t_hbm - t_hbm * local_factor
    return (h + t_setup) / denom


def asymptotic_speedup(h, t_hbm, local_factor):
    return (h + t_hbm) / (t_hbm * local_factor)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t-setup", type=float, default=20.0,
                    help="ns of fixed base-die command decode/setup (ASSUMED)")
    ap.add_argument("--local-factor", type=float, default=1.0,
                    help="T_HBM_local / T_HBM; 1.0 = no latency gain from being on the base die (conservative)")
    ap.add_argument("--cited-h", type=float, default=None,
                    help="a literature-sourced or gem5-measured H (ns) to highlight")
    args = ap.parse_args()

    hs = sorted(set(H_SWEEP + ([args.cited_h] if args.cited_h else [])))
    ns = np.logspace(0, 3, 200)

    plt.rcParams.update({"font.size": 8, "axes.linewidth": 0.6})
    mem = "HBM3-6400"

    # ---- Figure 1: speedup vs N, one curve per H ----
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for h in hs:
        cited = args.cited_h is not None and h == args.cited_h
        ax.plot(ns, speedup(ns, h, T_HBM[mem], args.t_setup, args.local_factor),
                lw=1.8 if cited else 1.0, ls="-" if cited else "--" if h not in H_SWEEP else "-",
                label=f"H = {h:g} ns" + (" (cited)" if cited else ""))
    ax.axhline(1.0, color="k", lw=0.6)
    ax.set_xscale("log")
    ax.set_xlabel("Pointer hops $N$")
    ax.set_ylabel("Speedup  $T_{baseline}/T_{PNM}$")
    ax.set_title(f"{mem}, $T_{{HBM}}$={T_HBM[mem]} ns", fontsize=8)
    ax.legend(fontsize=6, frameon=False)
    ax.grid(alpha=0.3, lw=0.4)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"fig_speedup_vs_N.{ext}"), dpi=300)
    plt.close(fig)

    # ---- Figure 2: absolute latency vs N for one illustrative H ----
    h_ill = args.cited_h if args.cited_h else 100
    fig, ax = plt.subplots(figsize=(3.4, 2.6))
    for name, t in T_HBM.items():
        ax.plot(ns, t_baseline(ns, h_ill, t) / 1000, label=f"Baseline {name}")
        ax.plot(ns, t_pnm(ns, h_ill, t, args.t_setup, args.local_factor) / 1000, ls="--",
                label=f"PNM {name}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Pointer hops $N$")
    ax.set_ylabel("Traversal latency ($\\mu$s)")
    ax.set_title(f"H = {h_ill:g} ns" + ("" if args.cited_h else " (illustrative)"), fontsize=8)
    ax.legend(fontsize=6, frameon=False)
    ax.grid(alpha=0.3, lw=0.4)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"fig_latency_vs_N.{ext}"), dpi=300)
    plt.close(fig)

    # ---- Table: speedup at N in N_POINTS, break-even N, asymptotic cap ----
    rows = []
    for name, t in T_HBM.items():
        for h in hs:
            row = {"memory": name, "T_HBM_ns": t, "H_ns": h,
                   "break_even_N": round(break_even_n(h, t, args.t_setup, args.local_factor), 2),
                   "asymptotic_speedup": round(asymptotic_speedup(h, t, args.local_factor), 2)}
            for n in N_POINTS:
                row[f"speedup_N{n}"] = round(speedup(n, h, t, args.t_setup, args.local_factor), 2)
            rows.append(row)
    with open(os.path.join(OUT, "model_results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"t_setup={args.t_setup} ns, local_factor={args.local_factor}")
    hdr = ["memory", "H_ns", "break_even_N"] + [f"speedup_N{n}" for n in N_POINTS] + ["asymptotic_speedup"]
    print("  ".join(f"{k:>18}" for k in hdr))
    for r in rows:
        print("  ".join(f"{r[k]:>18}" for k in hdr))


if __name__ == "__main__":
    main()
