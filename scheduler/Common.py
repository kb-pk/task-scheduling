from enum import Enum

import numpy as np
import pandas as pd
import os

MAKESPAN_MODE = 0
ENERGY_MODE = 1
scheduling_modes = {MAKESPAN_MODE:"makespan", ENERGY_MODE:"energy"}
scheduling_mode = 0


def prepare_results_directory():
    """
    Prepare the results directory for storing output files and clean up old results.
    """
    results_dir = "results"
    os.makedirs("results", exist_ok=True)
    
     # Iterate over all the files in the directory and remove them
    for filename in os.listdir(results_dir):
        file_path = os.path.join(results_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')


def read_machines(features):
    """
    Wczytanie macierzy maszyn z pliku CSV

    :return: macierz maszyn
    """
    machines_filename = "data/M20_security_features.csv"
    skip_rows = [0, 1]
    column_delimiter = ';'
    column_names = ['CC', 'cores', 'P_busy', 'P_idle', 'A', 'B', 'C', 'D', 'E']
    machines = pd.read_csv(machines_filename, skiprows=skip_rows, delimiter=column_delimiter, index_col=False, names=column_names)

    for machine_id in machines.index.values:
        if not are_security_features_correct(machines.iloc[machine_id], features):
            raise Exception("Machine features greater than defined. Machine:\n" + machines.iloc[machine_id].to_string())
    return machines


def read_tasks(features):
    """
    Wczytanie macirzy zadań z pliku CSV

    :return: macierz zadań
    """
    tasks_filename = "data/T200_security_features.csv"
    skip_rows = [0, 1]
    column_delimiter = ';'
    column_names = ['WL_seq', 'WL_par', 'A', 'B', 'C', 'D', 'E']
    tasks = pd.read_csv(tasks_filename, skiprows=skip_rows, delimiter=column_delimiter, index_col=False, names=column_names)
    for task_id in tasks.index.values:
        if not are_security_features_correct(tasks.iloc[task_id], features):
            raise Exception("Task features requirements greater than defined. Task:\n" + tasks.iloc[task_id].to_string())
    return tasks


def generate_etc_matrix(machines, tasks):
    """
    Generowanie mcierzy ETC z uwzględnieniem przetwarzania równoległego i sekwencyjnego
    Macierz ETC - macierz spodziewanego czasu wykonania zadania na maszynie

    ETC[i][j] = wls/cc + wlp/(cn * cc)
        wls - liczba operacji zmiennoprzecinkowych które NIE MOGĄ zostać zrównoleglone
        wlp - liczba operacji zmiennoprzecinkowych które MOGĄ zostać zrównoleglone
        cc - zdolność obliczeniowa jednego rdzenia
        cn - liczba rdzeni

    :param machines: macierz maszych
    :param tasks: macierz zadań
    :return: macierz ETC
    """
    new_etc = np.zeros(shape=(len(tasks), len(machines)), dtype=np.float64)  # utworzenie pustej tablicy

    for task_id in tasks.index.values:  # iteracja po wszystkich zadaniach
        wls = tasks.values[task_id][0]  # liczba operacji których NIE MOŻNA zrównoleglić
        wlp = tasks.values[task_id][1]  # liczba operacji które MOŻNA zrówloleglić
        for machine_id in machines.index.values:  # literacje po wszystkich maszynach
            cc = machines.values[machine_id][0]  # zdolność obliczenniowa maszyny
            cn = machines.values[machine_id][1]  # liczba rdzeni maszyny
            # obliczenie spodziewanego czasu wykonania zadania na maszynie
            new_etc[int(task_id)][int(machine_id)] = wls / cc + wlp / (cn * cc)

    return new_etc


def read_security_features():
    """
    Wczytanie listy cech bezpieczeństwa i ich wag, lista cech może być dowolnie długa

    :return: macierz cecha-waga
    """
    security_features_filename = "data/security_features_list.csv"
    skip_rows = [0]
    column_delimiter = ';'
    column_names = ['security_feature', 'weight']
    feature_matrix = pd.read_csv(security_features_filename, skiprows=skip_rows, delimiter=column_delimiter, index_col=False, names=column_names)
    return feature_matrix


def are_security_features_correct(item, features):
    """
    Sprawdzenie czy cechy bezpieczeństwa na maszynie lub w zadaniu są mniejsze niż definicja
    :param item: wiersz z macierzy maszyn lub zadań
    :param features: macierz cech
    :return: False jeśli dowolna cecha maszyny lub zadania jest większa niż definicja, True w przeciwnym wypadku
    """

    for feature_id in features.index.values:
        feature_name = features.values[feature_id][0]
        feature_value = features.values[feature_id][1]
        if item[feature_name] > feature_value:
            return False

    return True


def can_execute_task_on_machine(machine, task, features):
    """
    Sprawdzenie czy można wykonać zadanie na maszynie,
    czyli czy wszystkie wartości cech wymaganych przez zadanie są mniejsze niż cechy maszyny
    :param machine: wiersz określający maszynę
    :param task: wiersz określający zadaine
    :param features: macierz cech bezpieczenstwa
    :return: True jesli można wykonać zadanie, False w przeciwnym wypadku
    """
    for feature_id in features.index.values:
        feature_name = features.values[feature_id][0]
        if task[feature_name] > machine[feature_name]:
            return False

    return True

def check_task_machine_mapping(machines, tasks, features, mappings):
    """
    Sprawdzenie czy dane przypisanie maszyn do zadań jest prawidłowe.
    :param machines: macierz maszyn
    :param tasks: macierz zadań
    :param mappings: przypisanie poszczegolnych zadań do maszyn w formacie: 
        [machine_id, machine_id, machine_id, ...]
        gdzie indeks w tabeli jest równy id zadania, a każda wartość przedstawia id maszyny
    :return True jesli dopasowanie jest poprawne, False w przeciwnym wypadku
    """
    for task_id, machine_id in enumerate(mappings):
        machine = machines.iloc[machine_id]
        task = tasks.iloc[task_id]
        if not can_execute_task_on_machine(machine, task, features):
            return False

    return True

def decode_position_vector(position_vector, machines_num: int):
    """
    Zaokrąglenie i obcięcie wartości wektora pozycji do zakresu ID maszyn.
    :param position_vector: ndarray float (długość = liczba zadań)
    :param machines_num: liczba maszyn
    :return: ndarray int (przypisanie task -> machine_id)
    """
    assign = np.rint(position_vector).astype(int)
    return np.clip(assign, 0, machines_num - 1)


def compute_schedule_metrics(position_vector, etc_matrix: np.ndarray, machines_df: pd.DataFrame):
    """
    Liczy (makespan, total_energy) dla zakodowanego harmonogramu reprezentowanego przez wektor pozycji.
    :param position_vector: wektor (floats)
    :param etc_matrix: macierz ETC (tasks x machines)
    :param machines_df: DataFrame maszyn z kolumnami P_busy, P_idle
    :return: (makespan, total_energy)
    """
    machines_num = etc_matrix.shape[1]
    assign = decode_position_vector(position_vector, machines_num)
    loads = [etc_matrix[assign == j, j].sum() for j in range(machines_num)]
    makespan = max(loads) if loads else 0.0
    p_busy = machines_df['P_busy'].values
    p_idle = machines_df['P_idle'].values
    loads_arr = np.array(loads, dtype=float)
    total_energy = np.sum(loads_arr * p_busy + (makespan - loads_arr) * p_idle)
    return makespan, total_energy


def vector_fitness(position_vector, etc_matrix: np.ndarray, machines_df: pd.DataFrame, mode: int):
    """
    Zwraca (primary_metric, secondary_metric) zależnie od trybu (makespan / energy).
    :param position_vector: wektor pozycji
    :param etc_matrix: macierz ETC
    :param machines_df: DataFrame maszyn
    :param mode: MAKESPAN_MODE lub ENERGY_MODE
    """
    mk, en = compute_schedule_metrics(position_vector, etc_matrix, machines_df)
    if mode == ENERGY_MODE:
        return en, mk
    return mk, en