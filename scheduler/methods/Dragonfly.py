import scheduler.Common as Common
import numpy as np

features = Common.read_security_features()
machines = Common.read_machines(features)
tasks = Common.read_tasks(features)

etc_matrix = Common.generate_etc_matrix(machines, tasks)

tasks_num = len(tasks)
machines_num = len(machines)

DRAGONFLY_NUMBER = 30
ITERATIONS_NUMBER = 100
# weights
W_INERTIA = 0.9
W_SEPARATION = 0.1
W_ALIGNMENT = 0.1
W_COHESION = 0.1
W_FOOD_ATTRACT = 2.0
W_ENEMY_REPULSE = 1.0
# threshold for being considered a neighbor
NEIGHBOUR_RADIUS_THRESH = (len(machines) - 1) / 2

description = {
    "pl": """
    Algorytm optymalizacyjny Dragonfly. Rodzaj algorytmu optymalizacyjnego particle swarm.

    Algorytm polega na zdefiniowaniu w przestrzeni poszukiwań miejsc z jedzeniem (najlepszym rozwiązaniem z poprzedniej epoki) i z wrogami (najgorszym rozwiązaniem z poprzedniej epoki).
    Poziom przyciągania do źródeł jedzenia i odpychania od wrogów jest dyktowany parametrami.

    Osobniki w pobliżu (próg określony parametrem) tworzą sąsiedztwo danego osobnika.

    Dodatkowo zdefiniowane są parametry (wagi) w postaci:
    1. Bezwładności osobników (inertia)
    2. Separacji osobników od siebie (separation),
    3. Poruszania się z podobną prędkością co reszta osobników (alignment),
    4. Poruszania się w stronę centrum swojego sąsiedztwa (cohesion).

    Przestrzeń poszukiwań można sobie wyobrazić jako N-wymiarową (M = liczba zadań) przestrzeń z osobnikami "latającymi" wewnątrz niej zgodnie z ustalonymi parametrami.
    Pozycja (koordynaty) osobników wyrażają harmonogram w postaci [machine_id, machine_id, ...], gdzie indeks to numer zadania wykonywanego przez maszynę.

    Przykładowo, dla 3 zadań osobniki "latają" po 3-wymiarowej przestrzeni, gdzie ich koordynaty to harmonogram wszystkich maszyn.
    """,

    "en": """
    Dragonfly optimisation algorithm. A type of particle swarm optimisation algorithm.

    Algorithm defines places with food (best solution from last epoch) and enemies (worst solution from last epoch) in the search space.
    Levels of attraction toward food sources and repulsion from enemies are defined with parameters.

    Entities close (threshold is defined with a parameter) to the specific entity are considered its neighbourhood.

    Additionally, the following parameters (weights) are defined:
    1. Inertia of entities,
    2. Separation of entities from each other,
    3. Alignment of the entity in terms of speed with the rest of entities,
    4. Cohesion of entities in terms of being drawn to the center of their neighbourhood.

    The search space can be visualised as a N-dimensional (N = task number) space with the entities "flying" inside of it according to the defined parameters.
    Entity's position (its coordinates) represent a schedule in the form of [machine_id, machine_id, ...], where the index denotes the task number assigned to the machine.

    For example, for 3 machines the entities "fly" through a 3-dimensional space, where each entity's coordinates are a schedule for all the machines.
    """
}


def decode(position_vector):
    """
    Dekoduje chromosom position_vector na przypisanie zadań do maszyn

    :param position_vector: chromosom (wektor pozycji)
    :return: tablica przypisania maszyn do zadań w postaci [machine_id, machine_id, ...], gdzie indeks w tablicy = task_id
    """
    assign = np.rint(position_vector).astype(int)
    return np.clip(assign, 0, machines_num - 1)


def get_entity_fitness(position_vector):
    match Common.scheduling_mode:
        case Common.MAKESPAN_MODE:
            return makespan(position_vector)
        case Common.ENERGY_MODE:
            return energy(position_vector)

    return None


def makespan(position_vector):
    """
    Funkcja przystosowania, liczy makespan przyjmując position_vector

    :param position_vector: chromosom (wektor pozycji)
    :return: makespan (skalar)
    """
    """Compute makespan of a schedule given by 'position_vector'."""
    assign = decode(position_vector)
    loads = [etc_matrix[assign == j, j].sum() for j in range(machines_num)]
    return max(loads)


def energy(position_vector):
    """
    Funkcja przystosowania, liczy zużytą energię danego mapowania maszyn i zadań

    :param position_vector: chromosom (wektor pozycji)
    :return: energy (skalar)
    """
    assign = decode(position_vector)
    loads = [etc_matrix[assign == j, j].sum() for j in range(machines_num)]
    makespan_val = max(loads)

    p_busy = machines['P_busy'].values
    p_idle = machines['P_idle'].values

    # Energy = (BusyTime * P_busy) + (IdleTime * P_idle)
    # where IdleTime = Makespan - BusyTime (load)
    total_energy = np.sum(loads * p_busy + (makespan_val - loads) * p_idle)

    return total_energy


def initialise():
    """
    Inicjalizuje populację początkową

    :return: wektor prędkości, wektor pozycji, najlepszy osobnik z początkowej populacji, najgorszy, wartość funkcji przystosowania najlepszego osobnika
    """
    X = np.random.uniform(0, machines_num - 1, size=(DRAGONFLY_NUMBER, tasks_num))
    V = np.zeros_like(X)
    fitness = np.array([get_entity_fitness(x) for x in X])
    best_idx = np.argmin(fitness)
    worst_idx = np.argmax(fitness)
    best_X = X[best_idx].copy()
    worst_X = X[worst_idx].copy()
    best_val = fitness[best_idx]

    return X, V, best_X, worst_X, best_val


def optimise(X, V, best_X, worst_X, best_val):
    """
    Optymalizuje początkową populację

    :param X: initial position
    :param V: initial velocity
    :param best_X: najlepszy osobnik z początkowej populacji
    :param worst_X: najgorszy osobnik z początkowej populacji
    :param best_val: wartość funkcji przystosowania najlepszego osobnika
    """
    for iteration in range(ITERATIONS_NUMBER):
        # Compute pairwise distances
        dist = np.linalg.norm(X[:, None, :] - X[None, :, :], axis=2)
        for i in range(DRAGONFLY_NUMBER):
            neighbors = np.where((dist[i] < NEIGHBOUR_RADIUS_THRESH) & (dist[i] > 0))[0]
            if len(neighbors) > 0:
                # Separation
                S = -np.sum(X[neighbors] - X[i], axis=0)
                # Alignment
                A = np.mean(V[neighbors], axis=0)
                # Cohesion
                C = np.sum(np.mean(X[neighbors], axis=0) - X[i], axis=0)
                # Attraction to food (best solution)
                F = best_X - X[i]
                # Distraction from enemy (worst solution)
                Rv = worst_X + X[i]
                # Velocity and position update
                V[i] = W_INERTIA * V[i] + W_SEPARATION * S + W_ALIGNMENT * A + W_COHESION * C + W_FOOD_ATTRACT * F + W_ENEMY_REPULSE * Rv
                X[i] += V[i]
            else:
                # Random walk (Levy-like)
                X[i] += np.random.randn(tasks_num) * (X[i] - worst_X)
            # Enforce bounds
            X[i] = np.clip(X[i], 0, machines_num - 1)
        # Re-evaluate fitness
        fitness = np.array([get_entity_fitness(x) for x in X])
        current_best = np.min(fitness)
        current_worst = np.max(fitness)
        # Update global best/worst
        if current_best < best_val:
            best_val = current_best
            best_X = X[np.argmin(fitness)].copy()
            print(f"New best {Common.scheduling_modes[Common.scheduling_mode]} - {best_val}")
        if current_worst > get_entity_fitness(worst_X):
            worst_X = X[np.argmax(fitness)].copy()

    return best_X, best_val


def schedule_tasks():
    X, V, best_X, worst_X, best_val = initialise()
    best_X, best_val = optimise(X, V, best_X, worst_X, best_val)
    print(f"Final best {Common.scheduling_modes[Common.scheduling_mode]} - {best_val}")


def main():
    schedule_tasks()


if __name__ == "__main__":
    main()
