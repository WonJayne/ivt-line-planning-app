from excercise_3 import configure_parameters, load_paths

from openbus_light.manipulate import load_scenario
from openbus_light.manipulate.recorded_trip import enrich_lines_with_recorded_trips


def main() -> None:
    paths = load_paths()
    parameters = configure_parameters()
    baseline_scenario = load_scenario(parameters, paths)
    baseline_scenario.check_consistency()
    lines_with_recordings = enrich_lines_with_recorded_trips(paths.to_measurements, baseline_scenario.bus_lines)
    print(lines_with_recordings)


if __name__ == "__main__":
    main()
