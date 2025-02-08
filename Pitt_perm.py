import csv

import numpy as np
from sklearn.utils import shuffle
import random
import math
import Common

ITERATIONS_NUMBER = 100
POPULATION_SIZE = 10
MUTATION_POSSIBILITY_S = 0.01
MUTATION_POSSIBILITY_T = 0.01

features = Common.read_security_features()
machines = Common.read_machines(features)
tasks = Common.read_tasks(features)

def find_machine_ids_for_task(task):
    ids = []
    for machine_id in machines.index.values:
        machine = machines.iloc[machine_id]
        if (Common.can_execute_task_on_machine(machine, task, features)):
            ids.append(machine_id)
    return ids

def map_tasks_to_possible_machines():
    """
    Funkcja przechodzi przez wszystkie taski i sprawdza na jakich maszynach mogą one zostać uruchomione.
    :returns słownik z przypisaniem task_id => [machine_id, machine_id]
    """    
    tasks_to_machines = {}
    for i in tasks.index.values:
        tasks_to_machines[i] = []

    for task_id in tasks.index.values:
        task = tasks.iloc[task_id]
        machine_ids = find_machine_ids_for_task(task)
        tasks_to_machines[task_id] += machine_ids
    return tasks_to_machines

tasks_to_machines = map_tasks_to_possible_machines()


# generowanie jednego osobnika
def generate_individual():
    machines_chromosome = get_machines_chromosome()
    # Słownik z maszynami zmapowanymi na zadania jakie zostały do niej przypisane
    machines_to_tasks = assign_tasks_to_machines(tasks_to_machines, machines_chromosome)

    # osobnik jest reprezentowany przez krotkę:
    # 1. lista z kolejnymi zadaniami (numer zadania)
    # 2. lista z iloscia zadan na maszynę (kolejnosc w liscie - numer maszyny)
    ret_tasks = []
    for tasks_list in machines_to_tasks.values():
        ret_tasks += tasks_list

    return ret_tasks, machines_chromosome


def get_machines_chromosome():
    number_of_tasks = len(tasks)
    number_of_machines = len(machines)
    tasks_per_machine = math.floor(number_of_tasks / number_of_machines)
    # wypelnij macierz iloscia osobnikow na maszyne
    machines_chromosome = [tasks_per_machine] * number_of_machines
    # dodaj po jednym osobniku, jeśli ilość osobników na maszynę nie jest równa dla każdej maszyny
    for i in range(number_of_tasks - (tasks_per_machine * number_of_machines)):
        machines_chromosome[i] += 1
    return machines_chromosome


def assign_tasks_to_machines(tasks_to_machines, machines_chromosome):
    """
    Funkcja przechodzi po wszystkich taskach i przypisuje je do maszyn na których mogą zostać wykonane.
    Działanie funkcji jest następujące:
        - gdy dla danego zadania poprawna jest tylko jedna maszyna, przypisz to zadanie do tej maszyny
        - gdy jest więcej maszyn mogących wykonać dane zadanie, wybierz losowo maszynę i sprawdź czy
          nie ma ona za dużo zadań przypisanych. Jeżeli ma mniej niż max, przypisz zadanie do tej maszyny,
          w przeciwnym wypadku losuj następną maszynę.
    """
    machines_to_tasks = {}
    for i in machines.index.values:
        machines_to_tasks[i] = []

    sorted_tasks_to_machines = sorted(tasks_to_machines.items(), key=lambda item: len(item[1]))
    for task_to_machines in sorted_tasks_to_machines:
        task_id = task_to_machines[0]
        machine_ids = task_to_machines[1]
        if len(machine_ids) == 1:
            machines_to_tasks[machine_ids[0]].append(task_id)
        else:
            random_machine = random.choice(machine_ids)
            while len(machines_to_tasks[random_machine]) >= machines_chromosome[random_machine]:
                random_machine = random.choice(machine_ids)
            machines_to_tasks[random_machine].append(task_id)

    return machines_to_tasks


# generowanie populacji
def generate_population(p):
    population = []
    for _ in range(p):
        individual = tuple(generate_individual())
        population.append(individual)

    return population


def mutate_population(p):
    # dla każdego osobnika w populacji sprawdzamy czy zachodzi mutacja
    for i in range(int(len(p))):
        for j in range(int(len(p[i][0]))):
            # Sprawdzamy czy ma zajść mutacja typu swap
            if check_swap_mutation():
                p[i] = swap_mutation(p[i], j)
            # sprawdzamy czy ma zajść mutacja typu transposition
            if check_transposition_mutation():
                p[i] = transposition_mutation(p[i], j)
    return p


def check_swap_mutation():
    random_value = np.random.uniform(0.0, 1.0)
    #pms = 0.1
    if random_value <= MUTATION_POSSIBILITY_S:
        return 1
    else:
        return 0


def check_transposition_mutation():
    random_value = np.random.uniform(0.0, 1.0)
    #pms = 0.05
    if random_value <= MUTATION_POSSIBILITY_T:
        return 1
    else:
        return 0


def swap_mutation(individual, i):
    #Losowane są dwie liczby a następnie allele o odpowiadającyhc im numerach zostają ze sobą zamienione
    number_of_tasks = len(individual[0]) - 1
    #i = np.random.randint(0, number_of_tasks)
    j = np.random.randint(0, number_of_tasks)
    machine_id = get_machine_number_for_task(individual, j)
    while i == j or not can_run_task_on_machine(individual[0][i], machine_id):
        j = np.random.randint(0, number_of_tasks)
        machine_id = get_machine_number_for_task(individual, j)

    individual[0][i], individual[0][j] = individual[0][j], individual[0][i]
    return individual


def can_run_task_on_machine(task_id, machine_id):
    return machine_id in tasks_to_machines[task_id]


def transposition_mutation(individual, i):
    # print(individual)
    #Losujemy dwie liczby
    number_of_tasks = len(individual[0]) - 1
    #i = np.random.randint(0, number_of_tasks)
    j = np.random.randint(0, number_of_tasks)
    while i == j:
        j = np.random.randint(0, number_of_tasks)
    #Sprawdzamy czy do jakich maszyn przypisane są wylosowane zadania
    position_to_change = get_machine_number_for_task(individual, i)
    if individual[1][position_to_change] <= 1:
        return individual

    destination_to_change = get_machine_number_for_task(individual, j)
    while not can_run_task_on_machine(individual[0][i], destination_to_change):
        j = np.random.randint(0, number_of_tasks)
        destination_to_change = get_machine_number_for_task(individual, j)    

    #Odpowiednio modyfikujemy liczbę przypisanych wylosowanym maszynom zadań
    individual[1][position_to_change] = individual[1][position_to_change] - 1
    individual[1][destination_to_change] = individual[1][destination_to_change] + 1
    #Zadanie zostaje przeniesione do odpowiedniej maszyny
    #Zadanie przenoszone jest do dalszej maszyny
    if i < j:
        transpositioned_number = individual[0][i]
        for x in range(i, j):
            individual[0][x] = individual[0][x + 1]
        individual[0][j] = transpositioned_number
    #Zadanie przenoszone jest dowcześniejszej maszyny
    else:
        transpositioned_number = individual[0][i]
        # print(transpositioned_number)
        for x in reversed(range(j+1, i + 1)):
            individual[0][x] = individual[0][x - 1]
        individual[0][j] = transpositioned_number
    # print(individual)
    return individual


def get_machine_number_for_task(individual, task_position):
    counter = 0
    position_number = 0
    for machine in individual[1]:
        position_number += machine
        if position_number >= task_position + 1:
            return counter
        else:
            counter = counter + 1
    return None


# krzyżowanie populacji
def crossover(population):
    # przemieszaj populację, tak aby brać losowe osobniki do krzyżowania, a nie kolejne
    shuffled_population = shuffle(population)
    new_population = []
    # bierz kolejno po dwa osobniki z populacji i krzyżuj ze sobą
    for i in range(int(len(shuffled_population) / 2)):
        element = i * 2
        new_task_chromosome_a, new_task_chromosome_b = ordered_crossover(shuffled_population[element][0],
                                                                         shuffled_population[element + 1][0])

        new_population.append((new_task_chromosome_a, shuffled_population[element][1]))
        new_population.append((new_task_chromosome_b, shuffled_population[element + 1][1]))
    return new_population


# krzyżowanie dwóch osobników
def ordered_crossover(dad, mom):
    # długość osobnika (ilość zadań)
    size = len(mom)

    # wybierz losową pozycje początku / końca krzyżowania
    daughter, son = [-1] * size, [-1] * size
    start, end = sorted([random.randrange(size) for _ in range(2)])

    # replikuj sekwencję matki dla córki i ojca dla syna
    daughter_inherited = []
    son_inherited = []
    for i in range(start, end + 1):
        daughter[i] = mom[i]
        son[i] = dad[i]
        daughter_inherited.append(mom[i])
        son_inherited.append(dad[i])

    # wypełnij pozostałe pozycje pozostałymi danymi z rodziców
    current_dad_position, current_mom_position = 0, 0

    fixed_pos = list(range(start, end + 1))
    i = 0
    while i < size:
        # pomiń już skrzyzowany fragment
        if i in fixed_pos:
            i += 1
            continue

        # wypełniaj pozostałe fragmenty
        if daughter[i] == -1:  # wymaga wypelnienia
            dad_trait = dad[current_dad_position]
            while dad_trait in daughter_inherited:
                current_dad_position += 1
                dad_trait = dad[current_dad_position]
            daughter[i] = dad_trait
            daughter_inherited.append(dad_trait)

        if son[i] == -1:  # wymaga wypelnienia
            mom_trait = mom[current_mom_position]
            while mom_trait in son_inherited:
                current_mom_position += 1
                mom_trait = mom[current_mom_position]
            son[i] = mom_trait
            son_inherited.append(mom_trait)
        i += 1

    return daughter, son


def population_makespan(etc, population, machines = None):
    individuals_score = []
    individuals_other = []
    for i in range(len(population)):
        one, two = get_highest_makespan_for_individual(etc, population[i], machines)
        individuals_score.append(one)
        individuals_other.append(two)
    min_population_score = min(individuals_score)
    best_individual_from_population = population[individuals_score.index(min_population_score)]
    other = individuals_other[individuals_score.index(min_population_score)]
    return min_population_score, best_individual_from_population, other


def get_highest_makespan_for_individual(etc, individual, machines = None):
    tasks_arr, machine_arr = individual
    offset = 0
    max_makespan = 0
    machines_makespan  = [0] * len(machine_arr)
    for m in range(len(machine_arr)):  # m to id maszyny
        num_of_tasks = machine_arr[m]  # na pozycji m jest liczba zadan
        for t in range(num_of_tasks):
            index = t + offset
            machines_makespan[m] += etc[tasks_arr[index]][m]  # dodajemy czas dla zadan dla maszyny m
        if machines_makespan[m] > max_makespan:
            max_makespan = machines_makespan[m]
        offset += machine_arr[m]  # offset aby brac dalsze elementy tablicy z zadaniami
    
    total_power = 0
    for i in range(len(machines_makespan)):
        total_power += machines_makespan[i] * machines.values[i][2] + (max_makespan - machines_makespan[i]) * machines.values[i][3]
    if Common.scheduling_mode == Common.ENERGY_MODE:
        main_score = total_power
        other_score = max_makespan
    elif Common.scheduling_mode == Common.MAKESPAN_MODE:
        main_score = max_makespan
        other_score = total_power
    return main_score, other_score

def get_max_tasks_number(individual):
    _, machine_arr = individual
    max_tasks = 0
    for m in range(len(machine_arr)):
        if max_tasks < machine_arr[m]:
            max_tasks = machine_arr[m]
    return max_tasks


def get_tasks_of_machines(best_individual):
    tasks_of_machines = []

    stop = 0
    for i in range(len(machines)):
        start = stop
        stop += best_individual[1][i]
        m = []

        for j in range(start, stop):
            m.append(best_individual[0][j])
        tasks_of_machines.append(m)

    return tasks_of_machines


def pretty_print(bestSchedule, etc, machines, max_time):
    """
    Wypisywanie harmonogramu zadan (populacji) wraz z czasami wykonania zadan.

    :param bestSchedule: harmonogram dla najlepszego rozwiazania
    :param etc: macierz etc
    """
    print('-----------------------------------------------------')
    max_tasks = get_max_tasks_number(bestSchedule)
    tasks_of_machines = get_tasks_of_machines(bestSchedule)

    columns = format('', '8s')
    for i in range(0, max_tasks):
        columns += format(i, '13d')

    if Common.output_mode == Common.ENERGY_O_MODE or Common.output_mode == Common.ALL_O_MODE:
        columns += " IDLE "

    print('\t\ttasks')
    print(columns)
    print('machines')

    for machine_id in range(len(machines)):
        row = format(machine_id, '8d')
        time_sum = 0.0
        energy_sum = 0.0
        for i in range(len(tasks_of_machines[machine_id])):
            if np.isnan(i):
                break
            time_sum += etc[int(tasks_of_machines[machine_id][i])][int(machine_id)]
            energy = etc[int(i)][int(machine_id)] * machines.values[machine_id][2]
            energy_sum += energy
            if Common.output_mode == Common.MAKESPAN_O_MODE:
                row += format(format(tasks_of_machines[machine_id][i], '5') + ' (' + format(round(etc[int(tasks_of_machines[machine_id][i])][int(machine_id)], 1),'5.1f') + ')', '12s')
            elif Common.output_mode == Common.ENERGY_O_MODE:
                row += format(format(tasks_of_machines[machine_id][i], '5') + ' (' + format(round(energy, 1), '5.1f') + ')','12s')
            elif Common.output_mode == Common.ALL_O_MODE:
                row += format(format(tasks_of_machines[machine_id][i], '5') + ' (' + format(round(energy, 1), '5.1f') + ';' + format(round(etc[tasks_of_machines[machine_id][i]][int(machine_id)], 1), '5.1f') + ')','12s')

        idle_energy = (max_time - time_sum) * machines.values[machine_id][3]
        if Common.output_mode == Common.MAKESPAN_O_MODE:
            print(format(row, str((max_tasks) * 14) + 's') + ' | ' + str(round(time_sum, 2)))
        elif Common.output_mode == Common.ENERGY_O_MODE:
            print(format(row, str((max_tasks) * 14) + 's') + '(' + str(idle_energy) + ') | ' + str(round(energy_sum + idle_energy, 2)))
        elif Common.output_mode == Common.ALL_O_MODE:
            print(format(row, str((max_tasks) * 14) + 's') + '(' + str(idle_energy) + ') | MAKESPAN: ' + str(round(time_sum, 2)) + ' | ENERGY: ' + str(round(energy_sum + idle_energy, 2)))
    print('-----------------------------------------------------')


def print_no_time(best_individual):
    """
    Wypisywanie harmonogramu zadan (populacji) bez czasow wykonania zadan.

    :param best_individual: harmonogram dla najlepszego rozwiazania
    """
    print('-----------------------------------------------------')
    max_tasks = get_max_tasks_number(best_individual)
    tasks_of_machines = get_tasks_of_machines(best_individual)

    columns = format('', '8s')
    for i in range(0, max_tasks):
        columns += format(i, '13d')

    print(len(tasks_of_machines[0]))

    print('\t\ttasks')
    print(columns)
    print('machines')

    for machine_id in range(len(machines)):
        row = format(machine_id, '8d')
        j = len(tasks_of_machines[machine_id])
        for i in range(j):
            row += format(tasks_of_machines[machine_id][i], '13d')

        print(row)
    print('-----------------------------------------------------')


def write_to_csv(best_score, best_individual, etc, machines, max_time):
    """
    Zapisywanie do pliku csv
    :param best_score: najlepszy wynik
    :param best_individual: harmonogram dla najlepszego rozwiazania
    :param etc: macierz etc
    """
    max_tasks = get_max_tasks_number(best_individual)
    tasks_of_machines = get_tasks_of_machines(best_individual)

    with open('results/output_pitt_perm.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(['{} optimized'.format(Common.scheduling_modes[Common.scheduling_mode]), ('%f' % best_score).replace('.', ',')])

        first_row = ['Machines / Tasks']

        for i in range(0, max_tasks):
            first_row.append(str(i))

        if Common.output_mode == Common.ENERGY_O_MODE or Common.output_mode == Common.ALL_O_MODE:
            first_row.append('IDLE')

        writer.writerow(first_row)

        for machine_id in range(len(machines)):
            row = [str(machine_id)]
            time = 0.0
            j = len(tasks_of_machines[machine_id])
            for i in range(j):
                if np.isnan(i):
                    break
                if Common.output_mode == Common.MAKESPAN_O_MODE:
                    row.append(str(str(int(tasks_of_machines[machine_id][i])) + ' (' + ('%.1f' % etc[int(i)][int(machine_id)]).replace('.', ',') + ')'))
                elif Common.output_mode == Common.ENERGY_O_MODE:
                    time += etc[int(i)][int(machine_id)]
                    row.append(str(str(int(tasks_of_machines[machine_id][i])) + ' (' + (('%.1f' % (etc[int(i)][int(machine_id)] * machines.values[machine_id][2]))).replace('.', ',') + ')'))
                elif Common.output_mode == Common.ALL_O_MODE:
                    time += etc[int(i)][int(machine_id)]
                    row.append(str(str(int(tasks_of_machines[machine_id][i])) + ' (' + ('%.1f' % etc[int(i)][int(machine_id)]).replace('.', ',') + '|' + (('%.1f' % (etc[int(i)][int(machine_id)] * machines.values[machine_id][2]))).replace('.', ',') + ')'))

            if Common.output_mode == Common.ENERGY_O_MODE or Common.output_mode == Common.ALL_O_MODE:
                time = max_time - time
                row.append(('%.1f' % time).replace('.', ',') + '|' + ('%.1f' % (time * machines.values[machine_id][3])).replace('.', ','))
            writer.writerow(row)


def main():
    try:
        etc = Common.generate_etc_matrix(machines, tasks)
        population = generate_population(POPULATION_SIZE) #pierwszy parametr to liczba osobników
        best_score, other_param = get_highest_makespan_for_individual(etc, population[0], machines)  # makespan dla pierwszego osobnika
        print("Initial best {}: {} | {}: {}"
              .format(Common.scheduling_modes[Common.scheduling_mode], str(best_score), Common.scheduling_modes[(Common.scheduling_mode+1)%2], str(other_param)))
        for i in range(ITERATIONS_NUMBER): # liczba epok
            population = crossover(population)
            population = mutate_population(population)
            # print(population)
            current, best_individual, current_other = population_makespan(etc, population, machines)
            if best_score > current:
                best_score = current
                other_param = current_other
                print("[",i,"] Current best {}: {} | {}: {}"
                      .format(Common.scheduling_modes[Common.scheduling_mode], str(best_score), Common.scheduling_modes[(Common.scheduling_mode+1)%2], str(other_param)))
                
        print("Best {}: {} | {}: {}"
              .format(Common.scheduling_modes[Common.scheduling_mode], str(best_score), Common.scheduling_modes[(Common.scheduling_mode+1)%2], str(other_param)))
        open('results/result_pitt_perm', 'a').write(str(best_score) + "," + str(other_param) + "\n")
    except KeyboardInterrupt:
        # niszczenie obiektow itp
        # (bezpieczne zamkniecie)
        pass

    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        max_time = best_score
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        max_time = other_param
    pretty_print(best_individual, etc, machines, max_time)
    write_to_csv(best_score, best_individual, etc, machines, max_time)


if __name__ == '__main__':
    main()
