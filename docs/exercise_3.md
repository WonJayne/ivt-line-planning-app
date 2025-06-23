# Exercise 3: Line Planning

This exercise introduces the line planning problem using the `openbus_light` toolkit. You will learn how to run optimisation scenarios and inspect the results.

## Objective

Run the provided scripts to explore how different frequencies and capacities affect the bus network. You do not need to modify the optimisation algorithms themselves, but you are encouraged to experiment with the parameters.

## Step-by-Step Guide

1. Complete the setup in [setup.md](setup.md).
2. Ensure the `data/` folder is present (it is part of this repository).
3. Open a terminal and navigate to the project root. Activate your virtual environment if you created one.
4. Execute the helper script:
   ```bash
   python solve_exercise_3.py
   ```
   This runs several scenarios and writes the results to `results/`.
5. After the command finishes, open the generated HTML files from the `results/` directory in your web browser. They contain interactive plots of the network usage.
6. To try your own settings, either edit `solve_exercise_3.py` or run `exercise_3.py` directly. Use
   ```bash
   python exercise_3.py --help
   ```
   to see all available options, such as planning horizon or solver choice.

## What to Look For

Compare the resulting plots for different parameter sets. Observe how vehicle allocation changes and how demand is served. Consider questions like:

- Which settings reduce the number of vehicles required?
- How does increasing the permitted frequency affect passenger wait times?

Write down your observations—they will help you discuss the results in the tutorial.

