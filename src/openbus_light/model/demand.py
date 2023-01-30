from dataclasses import dataclass


@dataclass(frozen=True)
class DemandMatrix:
    matrix: dict[str, dict[str, float]]

    def all_origins(self) -> tuple[str, ...]:
        return tuple(self.matrix.keys())

    def between(self, origin: str, destination: str) -> float:
        return self.matrix[origin][destination]

    def starting_from(self, origin: str) -> float:
        return sum(self.matrix[origin].values())

    def arriving_at(self, destination: str) -> float:
        return sum(destinations[destination] for destinations in self.matrix.values() if destination in destinations)
