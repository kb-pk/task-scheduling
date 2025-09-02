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