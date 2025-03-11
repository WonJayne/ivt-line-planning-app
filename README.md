# IVT Public Transport Optimization Exercises (PUV, TS Part)

This repository contains exercises developed by the **Institute for Transport Planning and Systems (IVT) at ETH Zurich**. These exercises focus on **public transport optimization**, covering topics like line planning, timetable evaluation, and operational performance analysis.

## Setup:

You can now install `openbus_light` directly from PyPI:

```bash
pip install openbus-light
```

Alternatively, if you prefer using the provided wheel file:

1. Clone the repository to a suitable location on your computer.
2. Create your virtual environment (venv) using Python 3.10 with the command:
   ```bash
   python -m venv venv
   ```
3. Activate your venv:
   - On Windows:
     ```bash
     .\venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
4. Install `openbus_light` using the provided wheel file:
   ```bash
   pip install openbus_light-X.X.X-py3-none-any.whl
   ```
   (Replace `X.X.X` with the actual version number.)
5. Verify the setup by running the unittests:
   ```bash
   python -m unittest
   ```
6. Open your preferred IDE and begin working on `exercise_3.py` and `exercise_4.py`.

## Running the Line Planning Problem Experiments (Exercise 3)

The line planning problem (LPP) experiments are designed to explore the impacts of various parameters on the planning outcomes. `exercise_3.py` serves as the main script for executing these experiments in parallel.

### How to Run Experiments

1. Ensure both `exercise_3.py` and `solve_exercise_3.py` are present in your working directory.
2. Execute the `solve_exercise_3.py` script from your terminal to initiate the experiments:
   ```bash
   python solve_exercise_3.py
   ```
   This script will automatically run multiple configurations of the LPP in parallel, collect results, and generate insightful plots for analysis.
3. Experiment summaries and plots will be saved in the `results` directory. Review these materials to analyze the performance and outcomes of different configurations.

## Analyzing Trip and Dwell Times (Exercise 4)

In `exercise_4.py`, you will analyze the trip and dwell times for bus lines using recorded measurements. This involves calculating and comparing planned versus observed trip times and dwell times for selected bus lines.

### How to Run Analysis

1. Ensure you've completed the setup steps and have access to the necessary data files.
2. Run `exercise_4.py`, optionally specifying the bus line numbers for analysis. This script will load bus lines with recorded measurements, calculate trip and dwell times, and prepare the data for further analysis.

**Note:** The script includes a `NotImplementedError` as a placeholder for where you will need to process and display the analysis results. This is an intentional aspect of the exercise, designed to encourage you to apply what you've learned from Exercise 3, such as plotting techniques, and extend it with additional insights, like plotting data on maps or between stations.

## Adding Result Plotting

Result plotting provides a visual analysis of the experiment outcomes, enhancing understanding through visual means.

- After executing `solve_exercise_3.py`, visit the `results` directory to find the generated HTML files.
- Open these files in a web browser to view the scatter and bar plots, which visualize the experiments' results. The scatter plot displays the number of vehicles versus the objective (CHF per hour), while the bar plot details the objective by activity, offering a breakdown of cost components.

## Student Engagement and Adaptation

Exercise 4 is purposefully left incomplete to challenge you to apply and adapt the learnings from Exercise 3. This includes utilizing plotting capabilities and integrating geographic data visualization to enrich your analysis. You are encouraged to manipulate and extend the provided code to explore creative and insightful ways of representing and analyzing the data.

## Conclusion

These exercises are crafted to provide a comprehensive, hands-on experience with public transport optimization, covering everything from setup and execution of line planning problems to in-depth data analysis and visualization. By following the above instructions and engaging actively with the exercises, you will deepen your understanding of transport planning challenges and solutions.

This project is part of the **Institute for Transport Planning and Systems (IVT) at ETH Zurich** and is used in educational settings for students to gain hands-on experience in public transport optimization.
