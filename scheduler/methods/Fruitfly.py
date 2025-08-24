import scheduler.Common as Common
import numpy as np

features = Common.read_security_features()
machines = Common.read_machines(features)
tasks = Common.read_tasks(features)

etc_matrix = Common.generate_etc_matrix(machines, tasks)

tasks_num = len(tasks)
machines_num = len(machines)

POPULATION_SIZE = 30
ITERATIONS_NUMBER = 100
W_VISION_STEP_SIZE = 5.0

# TODO
#   decode, get_entity_fitness, makespan and energy are copy-pasted from Dragonfly.py and should be moved to Common!
#   (ideally using a diff branch, hence all this)


def decode(position_vector):
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
    Inicjuje populację początkową

    :return: wektor populacji początkowej
    """
    return np.random.uniform(0, machines_num - 1, size=(POPULATION_SIZE, tasks_num))


def optimise(init_population):
    """
    Optymalizuje populację początkową

    :param init_population: populacja początkowa

    :return: pozycję i wartość funkcji przystosowania (fitness) najlepszego osobnika
    """
    global_best_pos = None
    global_best_val = np.inf

    for iteration in range(ITERATIONS_NUMBER):
        # smell search
        smell_vals = np.array([get_entity_fitness(x) for x in init_population])
        i_smell = np.argmin(smell_vals)
        X_smell = init_population[i_smell].copy()

        # vision search
        for i in range(POPULATION_SIZE):
            init_population[i] = X_smell + np.random.randn(tasks_num) * W_VISION_STEP_SIZE
            init_population[i] = np.clip(init_population[i], 0, machines_num - 1)

        for i in range(POPULATION_SIZE):
            f_val = get_entity_fitness(init_population[i])

            if f_val < global_best_val:
                global_best_val = f_val
                global_best_pos = init_population[i].copy()

                print(f"New best {Common.scheduling_modes[Common.scheduling_mode]} - {global_best_val}")

    return global_best_pos, global_best_val


def schedule_tasks():
    init_population = initialise()
    _, best_val = optimise(init_population)

    print(f"Final best {Common.scheduling_modes[Common.scheduling_mode]} - {best_val}")


def main():
    schedule_tasks()


if __name__ == "__main__":
    main()