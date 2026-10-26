# PNM base-die pointer-chasing evaluation

Scripts, RTL, logs and model for the EE-295 paper "Processing-Near-Memory
Logic Controllers for Pointer-Chasing Acceleration in HBM Base Dies".

## Requirements
- Ramulator 2.1, commit 72427a1bba3771564c4fb0e494ba02242fd1eaa7
  (https://github.com/CMU-SAFARI/ramulator2), built from source
- Python 3, NumPy, Matplotlib; Icarus Verilog
- Exact versions: results/environment.txt

## Run
Copy ramulator/*.py into the Ramulator checkout (they import its Python
package and tests.utils), then from the checkout root:

    python3 trace.py                                  # HBM3 access patterns
    PYTHONPATH=python:. python3 pnm_dependent.py      # HBM3/HBM4 probe

Analytical model:

    python3 model/pnm_model.py

RTL simulation:

    cd rtl && iverilog -o sim.out pnm_controller.v tb_pnm_controller.v && vvp sim.out

## Expected results
- Row hit/miss/conflict (%): sequential 93.6/2.5/3.9; linked list 0.0/2.7/97.3;
  A[B[i]] 46.2/2.7/51.1
- Dependent access latency: HBM3-6400 49.9 ns, HBM4-8000 47.4 ns
- RTL: 5 hops, null terminated, 29 cycles

## Notes
- HBM3/HBM4 core timings are Ramulator presets marked as estimates in its
  source, not JEDEC-sourced values.
- Host overhead H and base-die setup time are assumed; only T_HBM is measured.
- The access-pattern traces issue independent requests and do not model a
  dependency chain.
