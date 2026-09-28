# Manycore INstantiation Toolkit

Generates, builds and simulates Memphis-V platforms from YAML descriptions.

## Requirements

- Python 3.8+
- A checkout of the Memphis-V platform sources (`MAestro`, `Phivers`, `libmemphis`, `libmutils`, `management`, `applications`)
- `make` and the RISC-V toolchain (`riscv64-elf-*`)
- A simulator: Verilator (default) or the one set in the testcase's `simulation.simulator`
- Optional: Java for the graphical debugger, GTKWave for waveforms

## Installation

Using a venv is recommended:
```sh
python -m venv ~/memphis-venv
source ~/memphis-venv/bin/activate
```

Then, install the package:
```sh
pip install -e .
```

## Configuration

| Variable                | Description                                                           |
|-------------------------|-----------------------------------------------------------------------|
| `MEMPHIS_PATH`          | Path to the Memphis-V platform sources. Required.                    |
| `MEMPHIS_DEBUGGER_PATH` | Folder containing `Memphis_Debugger.jar`. Required for `simulate`, `all` and `debug` unless `--nogui` is given. |

## Usage

Generated folders are created in the current directory, named after the YAML files.

```sh
mint testcase     TESTCASE_FILE                    [--skipdebug]
mint applications TESTCASE_FOLDER APPLICATIONS_FILE [--repodebug]
mint scenario     TESTCASE_FOLDER SCENARIO_FILE     [--skipdebug] [--repodebug]
mint simulate     SCENARIO_FOLDER                   [--timeout MS] [--nogui] [--wave]
mint all          TESTCASE_FILE APPLICATIONS_FILE SCENARIO_FILE [options]
mint debug        SCENARIO_FOLDER
```

- `testcase`: generates and builds the hardware, kernel and libraries described in the testcase.
- `applications`: builds the applications for a generated testcase.
- `scenario`: generates a scenario (application mapping and start times) for a generated testcase.
- `simulate`: runs a generated scenario, opening the debugger unless `--nogui` is given.
- `all`: runs `testcase`, `applications`, `scenario` and `simulate` in sequence.
- `debug`: opens the debugger on a previously simulated scenario.

Options:

- `--skipdebug`: disables the debugger configuration (implies `--nogui`).
- `--repodebug`: generates repository/appstart debug files.
- `--timeout MS`: simulation timeout in milliseconds. When absent, simulation stops when all applications end.
- `--wave`: opens the waveform in GTKWave after simulation. Requires `simulation.trace` enabled in the testcase.

Example:

```sh
export MEMPHIS_PATH=~/Memphis-V
export MEMPHIS_DEBUGGER_PATH=~/GraphicalDebugger
mint all example.yaml apps.yaml scenario.yaml
```
