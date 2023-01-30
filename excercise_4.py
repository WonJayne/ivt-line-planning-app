from excercise_3 import configure_parameters, load_paths

from openbus_light.manipulate import load_scenario
from openbus_light.manipulate.recorded_trip import enrich_lines_with_measurements


def main():
    paths = load_paths()
    parameters = configure_parameters()
    baseline_scenario = load_scenario(parameters, paths)
    baseline_scenario.check_consistency()
    updated_scenario = baseline_scenario._replace(
        bus_lines=enrich_lines_with_measurements(paths.to_measurements, baseline_scenario.bus_lines)
    )
    # Laden der scenario (Setzt nur_linie auf die Nummer eurer Linie um nur diese scenario zu laden)
    updated_scenario.check_consistency()
    print(updated_scenario)

    # TODO: Eure Analyse folgt hier.


if __name__ == "__main__":
    main()
