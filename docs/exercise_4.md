# Exercise 4: Recorded Trip Analysis

In this task you analyse recorded trip and dwell times for the Winterthur bus network. The provided script already loads the data and computes basic statistics.

## Objective

Fill in the missing plotting code and inspect the resulting distributions of observed trip and dwell times.

## Step-by-Step Guide

1. Complete the installation steps from [setup.md](setup.md) if you have not done so already.
2. Verify that `data/scenario/Messungen.zip` exists in this repository. It contains the measurement data used for this exercise.
3. Run the script once to generate the intermediate files:
   ```bash
   python exercise_4.py
   ```
   By default all lines with available measurements are processed. Use `--lines` to restrict the analysis to specific line numbers.
4. Open `exercise_4.py` in your editor and locate the TODO comments. Implement the sections that create violin plots for trip times and dwell times. You can take inspiration from the plotting code in `exercise_3.py`.
5. Execute the script again. HTML files will be written under `results/Analysis/`. Open them with a web browser to view the interactive plots.

## Troubleshooting Tips

- If you are unsure what a variable contains, add a `print()` statement and run the script again.
- Read error messages carefully—they usually tell you the line number where something went wrong.
- Use short iteration cycles: modify the code a little, run the script, check the output.

## Expected Result

Once the TODO sections are complete you will obtain violin plots that show the distribution of observed travel and dwell times for each line direction. Use these plots to discuss possible sources of delay and variability.

