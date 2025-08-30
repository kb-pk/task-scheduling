import numpy as np 
import pandas as pd
import os
from tabulate import tabulate
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.patches import Patch

MAKESPAN_MODE = 0
ENERGY_MODE = 1
scheduling_modes = {MAKESPAN_MODE:"makespan", ENERGY_MODE:"energy"}
scheduling_mode = 0

MAKESPAN_O_MODE = 0
ENERGY_O_MODE = 1
ALL_O_MODE = 2
output_modes = {MAKESPAN_O_MODE:"makespan", ENERGY_O_MODE:"energy", ALL_O_MODE:"all"}
output_mode = 0

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

def print_schedule(schedule_map, etc, machines, makespan, total_energy):
    """
    Wyświetla wyniki harmonogramu (czas i/lub energię) w czytelnej formie.

    Wyświetla wyniki harmonogramu w czytelnej, pionowej formie,
    idealnej dla małych okien terminala.

    :param schedule_map: Słownik {machine_id: [task_id, ...]}
    :param etc: Macierz ETC.
    :param machines: DataFrame z danymi maszyn.
    :param makespan: Całkowity czas wykonania.
    :param total_energy: Całkowita zużyta energia.
    """
    print("\n" + "="*50)
    print(f"--- WYNIKI KOŃCOWE ---")
    if output_mode in [MAKESPAN_O_MODE, ALL_O_MODE]:
        print(f"Najlepszy Makespan: {makespan:.2f}")
    if output_mode in [ENERGY_O_MODE, ALL_O_MODE]:
        print(f"Całkowita Energia: {total_energy:.2f}")
    print("="*50 + "\n")

    # Wyświetl szczegóły dla każdej maszyny
    for machine_id in sorted(schedule_map.keys()):
        task_ids = schedule_map[machine_id]
        
        # Pomiń maszyny, do których nie przypisano zadań
        if not task_ids:
            continue

        print(f"--- Maszyna {machine_id} ---")
        
        machine_time = sum(etc[t_id][machine_id] for t_id in task_ids)
        busy_energy = machine_time * machines.loc[machine_id, 'P_busy']
        idle_energy = (makespan - machine_time) * machines.loc[machine_id, 'P_idle']
        machine_total_energy = busy_energy + idle_energy

        if output_mode in [MAKESPAN_O_MODE, ALL_O_MODE]:
            print(f"  Czas pracy: {machine_time:.2f}")
        
        if output_mode in [ENERGY_O_MODE, ALL_O_MODE]:
            print(f"  Zużycie energii: {machine_total_energy:.2f} (Praca: {busy_energy:.2f}, Spoczynek: {idle_energy:.2f})")

        print("  Przypisane zadania:")
        for task_id in task_ids:
            task_time = etc[task_id][machine_id]
            task_energy = task_time * machines.loc[machine_id, 'P_busy']
            
            if output_mode == MAKESPAN_O_MODE:
                print(f"    - Zadanie {task_id} (czas: {task_time:.2f})")
            elif output_mode == ENERGY_O_MODE:
                print(f"    - Zadanie {task_id} (energia: {task_energy:.2f})")
            elif output_mode == ALL_O_MODE:
                print(f"    - Zadanie {task_id} (czas: {task_time:.2f}, energia: {task_energy:.2f})")
        print("-" * 20)

def plot_gantt_chart(schedule_map, etc, makespan):
    """
    Generuje i wyświetla czytelny, posortowany wykres Gantta dla harmonogramu.
    """
    
    MAX_WIDTH_INCHES = 100
    fig_width = min(max(15, makespan / 10), MAX_WIDTH_INCHES)
    fig_height = max(8, len(schedule_map) * 0.5)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    num_tasks = len(etc)
    colors = cm.viridis(np.linspace(0, 1, num_tasks))

    machine_labels = []
    for machine_id in sorted(schedule_map.keys()):
        machine_labels.append(f'Maszyna {machine_id}')
        current_time = 0.0
        for task_id in schedule_map[machine_id]:
            duration = etc[task_id][machine_id]
            ax.barh(
                machine_id,
                duration,
                left=current_time,
                height=0.6,
                align='center',
                color=colors[task_id],
                edgecolor='black'
            )
            current_time += duration

    ax.set_yticks(list(sorted(schedule_map.keys())))
    ax.set_yticklabels(machine_labels)
    ax.invert_yaxis()

    ax.set_xlabel('Czas')
    ax.set_title('Harmonogram zadań (Wykres Gantta)')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Pionowa linia makespan (zamiast legendy z zadaniami)
    ax.axvline(makespan, color='red', linestyle='--', linewidth=1.2)
    ax.text(
        makespan, 0.5,
        f'Makespan: {makespan:.2f}',
        rotation=90,
        va='bottom',
        ha='left',
        color='red',
        fontsize=9,
        backgroundcolor='white'
    )

    plt.tight_layout()

    chart_path = "results/gantt_chart.png"
    plt.savefig(chart_path)
    print(f"\nZapisano wykres Gantta w pliku: {chart_path}")
    plt.show()