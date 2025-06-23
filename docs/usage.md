# Usage Guide

This repository contains two main exercises that demonstrate how to use the `openbus_light` toolkit.

## Working with `exercise_3.py`

`exercise_3.py` explores the line planning problem. The typical workflow is:

1. Ensure the dataset in `data/` is available.
2. Run the helper script which executes several configurations in parallel:
   ```bash
   python solve_exercise_3.py
   ```
   The results, including HTML plots, are written to the `results/` directory.
3. Inspect the generated plots in your web browser to analyse the impact of different parameters.

You can also run a single experiment manually:
```bash
python exercise_3.py --help
```
This shows the available command line options such as the planning horizon, solver settings and output paths.

## Working with `exercise_4.py`

`exercise_4.py` analyses recorded trip and dwell times for individual lines. The typical steps are:

1. Make sure you have completed the environment setup from `docs/setup.md`.
2. Execute the script and optionally select the bus lines to analyse:
   ```bash
   python exercise_4.py --lines 1 2 3
   ```
   Without any arguments the script processes all available lines with recorded measurements.
3. The script will compute the statistics and, once you complete the TODO sections, produce visualisations similar to those in Exercise 3.
