from ..plan import LPPData, LPPResult


def create_summary(planning_data: LPPData, result: LPPResult) -> str:
    demand_matrix = planning_data.scenario.demand_matrix
    total_demand = sum(demand_matrix.starting_from(origins) for origins in demand_matrix.all_origins())
    number_of_demand_relations = sum(
        sum(demand > 0 for demand in demand_matrix.matrix[origins].values()) for origins in demand_matrix.all_origins()
    )
    stars = "******************"
    solution = result.solution
    summary = f"{stars}\n{stars}\nused parameters:\n"
    summary += "\t" + "\n\t".join(f"{key}:{value}" for key, value in sorted(planning_data.parameters._asdict().items()))
    summary += f"{stars}\n\ttotal passengers transported [n] \n\t{total_demand} "
    summary += f" \n\ton {number_of_demand_relations} relations"
    summary += f"\n{stars}\n\tweighted time per activity [hours]:\n"
    summary += "\n".join(
        f"{activity.name}\t:{dt.total_seconds() // 3600}" for activity, dt in solution.weighted_travel_time.items()
    )
    summary += f"\n{stars}\n\tactive lines:\n"
    summary += "\n".join(
        f"\t{line.number=} \tat {line.permitted_frequencies[0]}"
        for line in sorted(solution.active_lines, key=lambda x: x.number)
    )
    summary += f"\n{stars}\n\tused vehicles: \t {solution.used_vehicles}\n{stars}"
    return summary
