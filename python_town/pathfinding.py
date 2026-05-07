from __future__ import annotations

import heapq
from collections.abc import Callable


GridCell = tuple[int, int]


def manhattan(a: GridCell, b: GridCell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar_path(
    start: GridCell,
    goal: GridCell,
    width: int,
    height: int,
    is_walkable: Callable[[int, int], bool],
) -> list[GridCell]:
    if start == goal:
        return [start]
    if not is_walkable(*goal):
        return []

    open_heap: list[tuple[int, int, GridCell]] = []
    sequence = 0
    heapq.heappush(open_heap, (manhattan(start, goal), sequence, start))
    came_from: dict[GridCell, GridCell] = {}
    best_cost = {start: 0}
    closed: set[GridCell] = set()

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            return reconstruct_path(came_from, current)

        closed.add(current)
        current_cost = best_cost[current]
        for neighbor in neighbors4(current, width, height):
            if neighbor != start and not is_walkable(*neighbor):
                continue
            next_cost = current_cost + 1
            if next_cost >= best_cost.get(neighbor, 1_000_000_000):
                continue
            came_from[neighbor] = current
            best_cost[neighbor] = next_cost
            sequence += 1
            priority = next_cost + manhattan(neighbor, goal)
            heapq.heappush(open_heap, (priority, sequence, neighbor))

    return []


def neighbors4(cell: GridCell, width: int, height: int) -> tuple[GridCell, ...]:
    x, y = cell
    cells = []
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if 0 <= nx < width and 0 <= ny < height:
            cells.append((nx, ny))
    return tuple(cells)


def reconstruct_path(came_from: dict[GridCell, GridCell], current: GridCell) -> list[GridCell]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
