# Usage Guide

This repository contains two main exercises that demonstrate how to use the `openbus_light` toolkit.
Each exercise has its own README-style document with detailed instructions.

## Working with `exercise_3.py`

`exercise_3.py` explores the line planning problem. A step-by-step walkthrough is available in [exercise_3.md](exercise_3.md). In short you usually:

1. Ensure the dataset in `data/` is available.
2. Run the helper script which executes several configurations in parallel:
   ```bash
   python solve_exercise_3.py
   ```
   The results, including HTML plots, are written to the `results/` directory.
3. Inspect the generated plots in your web browser and experiment with different parameters.

You can also run a single experiment manually:
```bash
python exercise_3.py --help
```
This command lists all available options such as the planning horizon, solver settings and output paths.

## Working with `exercise_4.py`

`exercise_4.py` analyses recorded trip and dwell times for individual lines. A detailed walkthrough can be found in [exercise_4.md](exercise_4.md). The basic procedure is:

1. Make sure you have completed the environment setup from `setup.md`.
2. Execute the script and optionally select the bus lines to analyse:
   ```bash
   python exercise_4.py --lines 1 2 3
   ```
   Without any arguments the script processes all available lines with recorded measurements.
3. Once you fill in the TODO sections the script will produce HTML visualisations similar to those in Exercise 3.
