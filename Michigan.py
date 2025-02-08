import csv
from random import randint

import numpy as np
import pandas as pd
from sklearn.utils import shuffle

import Common

columns = ''


def get_last_task_index(chromosome):
    """
    Chromosom zawiera indeksy zadan oraz wartosci np.nan uzupelniajace tablice do konca.
    Funkcja szuka indeksu ostatniego zadania w chromosomie.

    :param chromosome: tablica indeksow zadan
    :return:
    """
    for task_id in range(0, len(chromosome)):
        if np.isnan(chromosome[task_id]):
            return task_id - 1

    return len(chromosome) - 1


def shuffle_chromosome(chromosome):
    """
    Mieszanie zadan w chromosomie

    :param chromosome: tablica indeksow zadan
    """
    last_index = get_last_task_index(chromosome)  # pobranie indeksu ostatniego zadania w chromosomie
    np.random.shuffle(chromosome[:last_index + 1])  # pomieszanie zadań w chromosomie (w zadanym zakresie)


def calculate_time_on_machine(tasks_ids, machine_id, etc):
    """
    Oblicza czas wykonania wszystkich zadan na okreslonej maszynie

    :param tasks_ids: tablica identyfikatorow zadan
    :param machine_id: identyfikator maszyny
    :param etc: macierz etc
    :return: identyfikator maszyny, czas wykonania wszystkich zadan na maszynie
    """
    time_sum = 0.0
    for task_id in tasks_ids:
        if np.isnan(task_id):
            break
        time_sum += etc[int(task_id)][int(machine_id)]  # sumowanie czasu wykonania zadań dla danej maszyny

    return machine_id, time_sum


def calculate_times(population, etc):
    """
    Oblicza czasy wykonania zadan na maszynach, do ktorych zostaly przypisane

    :param population: maszyny z przypisanymy do nich zadaniami (identyfikatorami zadan)
    :param etc: macierz etc
    :return: tablica czasow wykonania zadan na maszynach, do ktorych zostaly przypisane
    """
    tmp = np.zeros(shape=(len(population), 2), dtype=np.float64)

    for machine_id in population.index.values:  # obliczenie czasu wykonania zadań dla wszystkich maszyn
        tmp[machine_id] = calculate_time_on_machine(population.iloc[machine_id].values, machine_id, etc)

    return tmp


def numpy_arr_to_dataframe(data, ids):
    """
    Zamienia ndarray na dataframe

    :param data: tablica ndarray do zamiany
    :param ids: indeksy wierszy
    :return: dataframe powstaly z tablicy ndarray
    """
    df = pd.DataFrame(data=data, index=ids, columns=columns)
    df.index.name = 'machines'
    return df

def calculate_idle_time(tmp, max_time_running, population_size):
    new_tmp = np.zeros(shape=(population_size, 2), dtype=np.float64)
    for i in range(len(tmp)):
        new_tmp[i][0] = tmp[i][0]
        new_tmp[i][1] = max_time_running - tmp[i][1]
    return new_tmp

def sort_population(population, etc, machines = None):
    """
    Sortuje liste maszyn ( oraz zadan do nich przypisanych) od maszyny wykonujacej wszystkie swoje zadania najszybciej
    do maszyny wykonuacej swoje zadania najwolniej

    :param population:  maszyny z przypisanymy do nich zadaniami (identyfikatorami zadan)
    :param etc: macierz etc
    :return: posortowana populacja, najwyzszy czas wykonania zadan w populacji
    """
    tmp = calculate_times(population, etc)  # obliczenie czasu wykonania zadań dla populacji
    
    tmp_sorted = tmp[tmp[:, 1].argsort()]  # posortowanie czasów od najmniejszych do największych
    mat_sort_ids = None
    
    best_fitness = tmp_sorted[:, 1][-1]  # wyszukanie największego czasu


    max_time_running = best_fitness
    idle_times_on_mach = calculate_idle_time(tmp, max_time_running, len(population))

    tmp_energy = np.zeros(shape=(len(population), 2), dtype=np.float64)

    for machine_idle_time in idle_times_on_mach:
        tmp_energy[int(machine_idle_time[0])][0] = int(machine_idle_time[0])
        tmp_energy[int(machine_idle_time[0])][1] = machines.values[int(machine_idle_time[0])][3] * machine_idle_time[1]
    
    for machine_busy_time in tmp:
        tmp_energy[int(machine_busy_time[0])][1] = tmp_energy[int(machine_busy_time[0])][1] + machines.values[int(machine_busy_time[0])][2] * machine_busy_time[1]

    tmp_energy_sorted = tmp_energy[tmp_energy[:, 1].argsort()]
    if Common.scheduling_mode == Common.ENERGY_MODE:
        mat_sort_ids = tmp_energy_sorted[:, 0].astype(int)
        other_param = best_fitness
        best_fitness = tmp_energy_sorted[:, 1][-1]
    elif Common.scheduling_mode == Common.MAKESPAN_MODE:
        mat_sort_ids = tmp_sorted[:, 0].astype(int)
        other_param = tmp_energy_sorted[:, 1][-1]

    sorted_population_df = numpy_arr_to_dataframe(population.values[mat_sort_ids], mat_sort_ids)  # konwersja do data frame

    return sorted_population_df, best_fitness, other_param


def split_population(population):
    """
    Dzieli populacje na dwie czesci i miesza maszyny (z ich zadaniami) w obrebie tych czesci
    :param population:
    :return:
    """
    parts = np.array_split(population, 2)  # podział populacji na pół
    top = shuffle(parts[0])  # przemieszanie maszyn w pierwszej czesci
    bottom = shuffle(parts[1])  # przemieszanie maszyn w drugiej czesci

    return top, bottom


def cross(population):
    """
    Krzyzowanie osobnikow w populacji

    :param population:  maszyny z przypisanymy do nich zadaniami (identyfikatorami zadan)
    :return: populacja po krzyzowaniu
    """
    # pobranie zbioru maszyn o najmniejszych czasach wykonania zadan (top)
    # oraz o najwiekszych czasach wykonania zadan bottom
    top, bottom = split_population(population)

    for i in range((len(population) + 1) // 2):  # krzyzowanie par
        cross_pair(top.values[i], bottom.values[i])  # krzyżowanie danej pary

    data = np.concatenate((top, bottom), axis=0)  # łączenie dwoch zbiorow maszyn (top,bottom) po krzyzowaniu

    # wyznaczenie indeksow kolumn do trasformacji na dataframe
    indexes = np.concatenate((top.index.values, bottom.index.values), axis=0)
    res = numpy_arr_to_dataframe(data, indexes)  # transformacja danych do dataframe

    return res


def cross_pair(first, second):
    """
    Krzyzowanie pary chromosomow (dwoch maszyn)

    :param first: pierwsza maszyna (zestaw indeksow zadan dla maszyny)
    :param second: druga maszyna (zestaw indeksow zadan dla maszyny)
    """
    # pobranie rozmiarow chromosomow
    size_first = get_last_task_index(first) + 1
    size_second = get_last_task_index(second) + 1

    # wylosowanie punktów podziału
    cross_point_first = randint(1, size_first)
    cross_point_second = randint(1, size_second)

    # krzyżowanie według punktów podziału
    tmp_first = np.concatenate((first[:cross_point_first], second[cross_point_second:size_second]), axis=0)
    tmp_second = np.concatenate((second[:cross_point_second], first[cross_point_first:size_first]), axis=0)

    # nadpisanie skrzyżowanych osobników
    first[:len(tmp_first)] = tmp_first
    first[len(tmp_first): len(first)] = np.NaN

    # nadpisanie skrzyżowanych osobników
    second[:len(tmp_second)] = tmp_second
    second[len(tmp_second): len(second)] = np.NaN


def generate_population(machines, tasks):
    """
    Populacja sklada sie z chromosomow.
    Jeden chromosom to jedna maszyna.
    Kazdy chromosom to lista indeksow zadan, ktore maja byc wykonane na maszynie.
    Funkcja generuje populacje poczatkowa.

    :param machines: tablica maszyn
    :param tasks: tablica zadan
    :return: populacja -> maszyny z przypisanymy do nich zadaniami (identyfikatorami zadan)
    """

    if len(machines) > len(tasks):
        raise Exception('Each machine have to have at least one task')

    tasks_cpy = tasks.copy()
    np.random.shuffle(tasks_cpy)  # wymieszanie zadań

    tasks_arr = np.zeros((len(machines), len(tasks_cpy)))  # utworzenie pustej tablicy
    tasks_arr.fill(np.nan)  # wypelnienie tablicy wartosciami np.nan

    j = -1
    for i in range(0, len(tasks_cpy)):
        machine = i % len(machines)
        if machine == 0:
            j += 1

        tasks_arr[machine][j] = tasks_cpy[i]

    tasks_arr = numpy_arr_to_dataframe(tasks_arr, machines)  # konwersja na typ data frame

    return tasks_arr


def selection(population):
    """
    Operacja selekcji

    :param population: populacja przed selekcja
    :return: populacja po selekcji
    """
    return population


def mutation(population, pm):
    """
    Mutacja - przemieszanie kolejnosci zadan w obrebie maszyny

    :param population: populacja -> maszyny z przypisanymy do nich zadaniami (identyfikatorami zadan)
    :param pm: szansa na mutacje
    :return: populacja po mutacji
    """
    for machine_id in population.index:  # iteracja po maszynach
        if np.random.uniform(0.0, 1.0) <= pm:  # wykonanie mutacji z okreslonym prawdopodobienstwem
            shuffle_chromosome(population.loc[machine_id].values)  # zamiana kolejności zadań dla maszyny

    return population


def alg(machines, tasks, epochs, pm, etc):
    """
    Algorytm genetyczny
    :param machines: tablica maszyn
    :param tasks: tablica zadan
    :param epochs: liczba epok
    :param pm: prawdopodobienstwo mutacji
    :param etc: macierz etc
    :return: najlepsza populacja i osiagniety dla niej czas
    """
    # generacja populacji poczatkowej
    pop = generate_population(machines=machines.index.values, tasks=tasks.index.values)
    # mutacja
    # mutated = mutation(pop, pm)
    # sortowanie populacji i wyznaczanie czasu jej wykonania
    sorted_pop, current_score, other_param = sort_population(pop, etc, machines)

    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        print("Makespan beginning: ", current_score, "energy use:", other_param)
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        print("Energy beginning: ", current_score, "makespan:", other_param)
    best_score = current_score
    other_param_for_best = other_param
    best_pop = sorted_pop
    best_iter = 0

    for i in range(epochs):
        cros = cross(sorted_pop)  # krzyzowanie
        mutated = mutation(cros, pm)  # mutacja
        # sortowanie populacji i wyznaczanie czasu jej wykonania
        sorted_pop, current_score, other_param = sort_population(mutated, etc, machines)
        if current_score < best_score:  # sprawdzenie czy uzyskano lepsze rozwiazanie
            best_pop = sorted_pop
            best_score = current_score
            best_iter = i
            other_param_for_best = other_param
            if Common.scheduling_mode == Common.MAKESPAN_MODE:
                print("[", i, "] Current best makespan: ", best_score, "energy use:", other_param_for_best)
            elif Common.scheduling_mode == Common.ENERGY_MODE:
                print("[", i, "] Current best energy: ", best_score, "makespan:", other_param_for_best)
        sorted_pop = selection(sorted_pop)  # selekcja

    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        print("Makespan optimized: ", best_score, " in iter nb. ", best_iter, "energy use:", other_param_for_best)
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        print("Makespan optimized: ", best_score, " in iter nb. ", best_iter, "energy use:", other_param_for_best)
    return (best_pop, best_score, other_param_for_best)


def pretty_print(population, etc, machines, max_time):
    """
    Wypisywanie harmonogramu zadan (populacji) wraz z czasami wykonania zadan.

    :param population:
    :param etc:
    """
    print('-----------------------------------------------------')
    max_tasks = 0
    for i in range(0, len(population)):  # pobieranie maksymalnej liczby zadan przypisanych do maszyn
        max_tasks = max(get_last_task_index(population.values[i]), max_tasks)

    columns = format('', '8s')  # formatowanie nazw kolumn
    for i in range(0, max_tasks + 1):
        columns += format(i, '13d')

    if Common.output_mode == Common.ENERGY_O_MODE or Common.output_mode == Common.ALL_O_MODE:
        columns += " IDLE "

    print('\t\ttasks')
    print(columns)
    print('machines')

    sorted_pop = population.sort_index()

    for machine_id in sorted_pop.index.values:  # iteracja po maszynach
        row = format(machine_id, '8d')

        time_sum = 0.0
        energy_sum = 0.0
        for task_id in sorted_pop.loc[machine_id].values:  # iteracja po zadaniach przypisanych do maszyn
            if np.isnan(task_id):
                break
            time_sum += etc[int(task_id)][int(machine_id)]  # obliczanie sumy czasow wykonania zadan dla maszyny
            energy = etc[int(task_id)][int(machine_id)] * machines.values[machine_id][2]
            energy_sum += energy
            # formatowanie wyjscia
            if Common.output_mode == Common.MAKESPAN_O_MODE:
                row += format(format(int(task_id), '5') + ' (' + format(round(etc[int(task_id)][int(machine_id)], 1), '5.1f') + ')','12s')
            elif Common.output_mode == Common.ENERGY_O_MODE:
                row += format(format(int(task_id), '5') + ' (' + format(round(energy, 1), '5.1f') + ')','12s')
            elif Common.output_mode == Common.ALL_O_MODE:
                row += format(format(int(task_id), '5') + ' (' + format(round(energy, 1), '5.1f') + ';' + format(round(etc[int(task_id)][int(machine_id)], 1), '5.1f') + ')','12s')
            
        idle_energy = (max_time - time_sum) * machines.values[machine_id][3]
        if Common.output_mode == Common.MAKESPAN_O_MODE:
            print(format(row, str((max_tasks + 1) * 14) + 's') + ' | ' + str(round(time_sum, 2)))
        elif Common.output_mode == Common.ENERGY_O_MODE:
            print(format(row, str((max_tasks + 1) * 14) + 's') + '(' + str(idle_energy) + ') | ' + str(round(energy_sum + idle_energy, 2)))
        elif Common.output_mode == Common.ALL_O_MODE:
            print(format(row, str((max_tasks + 1) * 14) + 's') + '(' + str(idle_energy) + ') | MAKESPAN: ' + str(round(time_sum, 2)) + ' | ENERGY: ' + str(round(energy_sum + idle_energy, 2)))
    print('-----------------------------------------------------')


def print_no_time(population, etc):
    """
    Wypisywanie harmonogramu zadan (populacji) bez czasow wykonania zadan.

    :param population:
    :param etc:
    """
    print('-----------------------------------------------------')
    max_tasks = 0
    for i in range(0, len(population)):  # pobieranie maksymalnej liczby zadan przypisanych do maszyn
        max_tasks = max(get_last_task_index(population.values[i]), max_tasks)

    columns = format('', '8s')  # formatowanie nazw kolumn
    for i in range(0, max_tasks + 1):
        columns += format(i, '13d')

    print('\t\ttasks')
    print(columns)
    print('machines')

    sorted_pop = population.sort_index()

    for machine_id in sorted_pop.index.values:  # iteracja po maszynach
        row = format(machine_id, '8d')

        time_sum = 0.0
        for task_id in sorted_pop.loc[machine_id].values:  # iteracja po zadaniach przypisanych do maszyn
            if np.isnan(task_id):
                break
            time_sum += etc[int(task_id)][int(machine_id)]  # obliczanie sumy czasow wykonania zadan dla maszyny

            # formatowanie wyjscia
            row += format(
                format(int(task_id), '13d'))

        print(row)
    print('-----------------------------------------------------')


def write_to_csv(best_score, population, etc, machines, max_time):
    """
    Zapisywanie do pliku csv
    :param best_score: najlepszy wynik
    :param population: population
    :param etc: macierz etc
    """
    with open('results/output_michigan.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(['{} optimized'.format(Common.scheduling_modes[Common.scheduling_mode]), ('%f' % best_score).replace('.', ',')])
        
        first_row = ['Machines / Tasks']

        max_tasks = 0
        for i in range(0, len(population)):
            max_tasks = max(get_last_task_index(population.values[i]), max_tasks)

        for i in range(0, max_tasks + 1):
            first_row.append(str(i))

        if Common.output_mode == Common.ENERGY_O_MODE or Common.output_mode == Common.ALL_O_MODE:
            first_row.append('IDLE')

        writer.writerow(first_row)

        for machine_id in population.index.values:  # iteracja po maszynach
            row = [str(machine_id)]  # dodanie do wiersza id maszyny
            time = 0.0
            for task_id in population.loc[machine_id].values:  # iteracja po zadaniach przypisanych do maszyn
                if np.isnan(task_id):
                    break
                if Common.output_mode == Common.MAKESPAN_O_MODE:
                    row.append(str(str(int(task_id)) + ' (' + ('%.1f' % etc[int(task_id)][int(machine_id)]).replace('.', ',') + ')'))  # dodanie do wiersza task id i czasu wykonywania
                elif Common.output_mode == Common.ENERGY_O_MODE:
                    time += etc[int(task_id)][int(machine_id)]
                    row.append(str(str(int(task_id)) + ' (' + (('%.1f' % (etc[int(task_id)][int(machine_id)] * machines.values[machine_id][2]))).replace('.', ',') + ')'))  
                elif Common.output_mode == Common.ALL_O_MODE:
                    time += etc[int(task_id)][int(machine_id)]
                    row.append(str(str(int(task_id)) + ' (' + ('%.1f' % etc[int(task_id)][int(machine_id)]).replace('.', ',') + '|' + (('%.1f' % (etc[int(task_id)][int(machine_id)] * machines.values[machine_id][2]))).replace('.', ',') + ')'))

            if Common.output_mode == Common.ENERGY_O_MODE or Common.output_mode == Common.ALL_O_MODE:
                time = max_time - time
                row.append(('%.1f' % time).replace('.', ',') + '|' + ('%.1f' % (time * machines.values[machine_id][3])).replace('.', ','))
            writer.writerow(row)  # zapisanie calego wiesza


def main():
    np.random.seed(0)  # ustawienie ziarna

    # wczytanie cech bezpieczeństwa
    features = Common.read_security_features()

    # wczytanie danych z plikow
    machines = Common.read_machines(features)
    tasks = Common.read_tasks(features)

    # wyznaczenie nazw kolumn w harmonogramie zadan
    global columns
    columns = ['task_' + str(i) for i in range(0, len(tasks))]

    # machines = pd.DataFrame(data=[[0, 1], [1, 1], [2, 1], [3, 1]])
    # print(machines)
    # tasks = pd.DataFrame(data=[[0, 1], [1, 2], [2, 3], [3, 4],
    #                            [4, 5], [5, 6], [6, 7], [7, 8],
    # [8, 9], [9, 10], [10, 11], [11, 12]])

    # generacja macierzy etc
    etc = Common.generate_etc_matrix(machines, tasks)

    # wykonanie algorytmu genetycznego
    pop, best_score, other_param = alg(machines, tasks, 100, 0.01, etc)  # 1% mutation chance

    # wypisanie wyniku
    # print_no_time(pop, etc)

    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        max_time = best_score
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        max_time = other_param
    # wypisanie wyniku
    pretty_print(pop, etc, machines, max_time)

    # zapis wyniku do pliku csv
    write_to_csv(best_score, pop.sort_index(), etc, machines, max_time)

    open('results/result_michigan', 'a').write(str(best_score) + "," + str(other_param) + "\n")


if __name__ == "__main__":
    main()
