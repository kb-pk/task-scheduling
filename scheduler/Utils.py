import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.patches import Patch
import numpy as np
import os
from tabulate import tabulate
from . import Common

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
    
    tasks_in_schedule = set()
    machine_labels = []

    for machine_id in sorted(schedule_map.keys()):
        machine_labels.append(f'Maszyna {machine_id}')
        current_time = 0
        for task_id in schedule_map[machine_id]:
            duration = etc[task_id][machine_id]
            # Rysuj pasek bez etykiety
            ax.barh(machine_id, duration, left=current_time, height=0.6, align='center', 
                    color=colors[task_id], edgecolor='black')
            tasks_in_schedule.add(task_id)
            current_time += duration

    ax.set_yticks(list(sorted(schedule_map.keys())))
    ax.set_yticklabels(machine_labels)
    ax.invert_yaxis()

    ax.set_xlabel('Czas')
    ax.set_title('Harmonogram zadań (Wykres Gantta)')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # --- POCZĄTEK ZMIAN ---
    # Ręczne tworzenie posortowanej legendy
    legend_elements = []
    # Dodaj linię makespan jako pierwszy element
    legend_elements.append(plt.Line2D([0], [0], color='r', linestyle='--', label=f'Makespan: {makespan:.2f}'))
    
    # Dodaj posortowane zadania
    for task_id in sorted(list(tasks_in_schedule)):
        legend_elements.append(Patch(facecolor=colors[task_id], edgecolor='black', label=f'Zadanie {task_id}'))

    # Legenda z posortowanymi elementami, podzielona na kolumny
    ncol = 1 + len(tasks_in_schedule) // 20
    ax.legend(handles=legend_elements, title="Legenda", bbox_to_anchor=(1.02, 1), loc='upper left', ncol=ncol)

    plt.tight_layout(rect=[0, 0, 0.9, 1])
    
    chart_path = "results/gantt_chart.png"
    plt.savefig(chart_path)
    print(f"\nZapisano wykres Gantta w pliku: {chart_path}")

    plt.show()

def display_results(schedule_map, etc, machines, makespan, total_energy):
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
    if Common.output_mode in [Common.MAKESPAN_O_MODE, Common.ALL_O_MODE]:
        print(f"Najlepszy Makespan: {makespan:.2f}")
    if Common.output_mode in [Common.ENERGY_O_MODE, Common.ALL_O_MODE]:
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

        if Common.output_mode in [Common.MAKESPAN_O_MODE, Common.ALL_O_MODE]:
            print(f"  Czas pracy: {machine_time:.2f}")
        
        if Common.output_mode in [Common.ENERGY_O_MODE, Common.ALL_O_MODE]:
            print(f"  Zużycie energii: {machine_total_energy:.2f} (Praca: {busy_energy:.2f}, Spoczynek: {idle_energy:.2f})")

        print("  Przypisane zadania:")
        for task_id in task_ids:
            task_time = etc[task_id][machine_id]
            task_energy = task_time * machines.loc[machine_id, 'P_busy']
            
            if Common.output_mode == Common.MAKESPAN_O_MODE:
                print(f"    - Zadanie {task_id} (czas: {task_time:.2f})")
            elif Common.output_mode == Common.ENERGY_O_MODE:
                print(f"    - Zadanie {task_id} (energia: {task_energy:.2f})")
            elif Common.output_mode == Common.ALL_O_MODE:
                print(f"    - Zadanie {task_id} (czas: {task_time:.2f}, energia: {task_energy:.2f})")
        print("-" * 20)
    plot_gantt_chart(schedule_map, etc, makespan)