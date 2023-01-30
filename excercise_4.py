from excercise_3 import configure_parameters, load_paths

from openbus_light.manipulate import load_scenario
from openbus_light.manipulate.recorded_trip import enrich_lines_with_measurements


def main() -> None:
    paths = load_paths()
    parameters = configure_parameters()
    baseline_scenario = load_scenario(parameters, paths)
    baseline_scenario.check_consistency()
    line_with_measurement = enrich_lines_with_measurements(paths.to_measurements, (baseline_scenario.bus_lines[-1],))
    line_with_measurement


if __name__ == "__main__":
    main()
