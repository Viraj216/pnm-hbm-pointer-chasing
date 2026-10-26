"""Step 1: run random-access traces on HBM3 in Ramulator 2.1 (LoadStoreTrace).

Run from ~/ramulator2:   python3 pnm_trace_run.py
NOTE: LoadStoreTrace sends a request every cycle with NO dependency between
requests, so this measures independent random access (row hit/miss/conflict
behavior), NOT dependent pointer-chasing latency. Use pnm_dependent_probe.py
for per-hop latency.
"""
import random
import ramulator

SPACE = 1 << 29          # 512 MiB, safely below one HBM3_16Gb_8hi channel (1 GiB)
TCK_NS = 0.3125  # tick_multiplier=2: 1 cycle = half CK


def gen_linked_list(path, n, seed=1):
    random.seed(seed)
    with open(path, "w") as f:
        for _ in range(n):
            f.write(f"LD 0x{random.randrange(0, SPACE, 64):x}\n")


def gen_indirect(path, n, seed=1):
    """A[B[i]]: B read sequentially, A read at a random location."""
    random.seed(seed)
    a_base = SPACE // 2
    with open(path, "w") as f:
        for i in range(n // 2):
            f.write(f"LD 0x{64 * i:x}\n")
            f.write(f"LD 0x{a_base + random.randrange(0, SPACE // 2, 64):x}\n")


def gen_sequential(path, n):
    """Reference: streaming access, should show mostly row hits."""
    with open(path, "w") as f:
        for i in range(n):
            f.write(f"LD 0x{64 * i:x}\n")


def run(trace):
    frontend = ramulator.frontend.LoadStoreTrace(clock_ratio=1, path=trace)
    dram = ramulator.dram.HBM3(org_preset="HBM3_16Gb_8hi", timing_preset="HBM3_6400Mbps")
    ctrl = ramulator.controller.HBM34(
        dram=dram,
        scheduler=ramulator.scheduler.FRFCFS(),
        refresh_manager=ramulator.refresh_manager.AllBank(),
        row_policy=ramulator.row_policy.Open(),
        addr_mapper=ramulator.addr_mapper.RoBaRaCoCh(),
    )
    mem = ramulator.memory_system.GenericDRAM(
        clock_ratio=1,
        controllers=[ctrl],
        channel_mapper=ramulator.channel_mapper.CacheLineInterleave(),
    )
    sim = ramulator.Simulation(frontend, mem)
    sim.run()
    s = sim.stats["memory_system"]["controller"]
    return s[0] if isinstance(s, list) else s


if __name__ == "__main__":
    N = 20000
    gen_linked_list("ll.trace", N)
    gen_indirect("ind.trace", N)
    gen_sequential("seq.trace", N)
    for name in ("seq", "ll", "ind"):
        s = run(f"{name}.trace")
        total = s["row_hits"] + s["row_misses"] + s["row_conflicts"]
        print(f"\n[{name}] cycles={s['cycles']}  reads={s['num_read_reqs']}")
        print(f"  avg read latency: {s['avg_read_latency']:.1f} cycles "
              f"= {s['avg_read_latency'] * TCK_NS:.1f} ns")
        print(f"  row hit/miss/conflict: "
              f"{100 * s['row_hits'] / total:.1f}% / "
              f"{100 * s['row_misses'] / total:.1f}% / "
              f"{100 * s['row_conflicts'] / total:.1f}%")
