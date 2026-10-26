"""Step 2: unloaded dependent random-access latency on HBM3 and HBM4 (gives T_HBM_access).

Run from the repo root so `tests.utils` is importable:
    cd ~/ramulator2
    PYTHONPATH=python:. python3 mytests/pnm_dependent.py     (adjust path to this file)

Mirrors tests/smoke/runner.py and tests/latency_throughput/utils/runner.py.
A huge nop_counter means almost no background streaming load, so the probe
measures unloaded random-access latency (what one pointer hop costs the DRAM).
HBM3 and HBM4 both use tick_multiplier=2, so 1 controller cycle = half CK.
"""
import ramulator
from tests.utils import extract_dram_layout

CONFIGS = {
    # tck_ps from the timing presets; expected_ck = nRP + nRCDRD + nCL (random row-miss)
    "HBM3": dict(cls="HBM3", org="HBM3_16Gb_8hi", timing="HBM3_6400Mbps",
                 tck_ps=625, expected_ck=26 + 31 + 20, rbuf=128, wbuf=64),
    "HBM4": dict(cls="HBM4", org="HBM4_32Gb_8Hi", timing="HBM4_8000Mbps",
                 tck_ps=500, expected_ck=33 + 39 + 20, rbuf=64, wbuf=64),
}


def run(cfg, nop_counter=40000, num_probes=10000):
    dram = getattr(ramulator.dram, cfg["cls"])(org_preset=cfg["org"], timing_preset=cfg["timing"])
    layout = extract_dram_layout(dram)

    frontend = ramulator.frontend.LatencyThroughputTrace(
        clock_ratio=16,
        nop_counter=nop_counter,
        num_probe_requests=num_probes,
        warmup_cycles=10000,
        seed=12345,
        read_ratio=100,
        stream_cls=32,
        stagger_stream_rows=True,
        **layout,
    )
    ctrl = ramulator.controller.HBM34(
        dram=dram,
        scheduler=ramulator.scheduler.FRFCFSRowHit(),
        row_policy=ramulator.row_policy.Open(),
        addr_mapper=ramulator.addr_mapper.PassThroughAddrMapper(),
        refresh_manager=ramulator.refresh_manager.NoRefresh(),
        read_buffer_size=cfg["rbuf"],
        write_buffer_size=cfg["wbuf"],
    )
    mem = ramulator.memory_system.GenericDRAM(
        clock_ratio=1,
        controllers=[ctrl],
        channel_mapper=ramulator.channel_mapper.PassThroughChannelMapper(),
    )
    sim = ramulator.Simulation(frontend, mem)
    sim.run()
    return sim.stats


if __name__ == "__main__":
    for name, cfg in CONFIGS.items():
        st = run(cfg)
        ticks = st["frontend"]["avg_probe_latency"]
        tick_ns = cfg["tck_ps"] / 2 / 1000.0          # half-CK ticks
        expected_ns = cfg["expected_ck"] * cfg["tck_ps"] / 1000.0
        print(f"\n[{name}] avg probe latency: {ticks:.1f} ticks = {ticks * tick_ns:.1f} ns "
              f"(theory nRP+nRCD+nCL = {expected_ns:.1f} ns, plus ~1 burst)")
