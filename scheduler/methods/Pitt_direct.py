# -*- coding: utf-8 -*-
"""
Created on Sat Feb  2 12:42:50 2019

@author: ini
"""
import csv
import time
from hmac import new

import pandas as pd
import numpy as np
import random
import csv
from collections import Counter

import scheduler.Common as Common

ITERATIONS_NUMBER = 100
POPULATION_SIZE = 10
NUMBER_OF_CROSSOVER_POINTS = 1
MUTATION_POSSIBILITY = 0.01

"""
Wczytuje dane dotyczace maszyn i zadan z plikow
"""

features = Common.read_security_features()
machines = Common.read_machines(features)
tasks = Common.read_tasks(features)


def map_possible_machines_to_tasks():
    """
    Mapuje zadania i maszyny, które dane zadanie mogą wykonać (na podstawie features).
    :return: Słownik {task_id: [machine_id, machine_id, ...], ...}
    """
    possible_machines_for_tasks = {task_id: [
        machine_id for machine_id in machines.index.values
        if Common.can_execute_task_on_machine(machines.iloc[machine_id], tasks.iloc[task_id], features)
    ] for task_id in tasks.index.values}

    return possible_machines_for_tasks


def generate_individual(possible_machines_for_tasks):
    individual = []

    for task_id, possible_machines in possible_machines_for_tasks.items():
        individual.append(random.choice(possible_machines))

    return individual


def generate_population(population_size):
    population = []
    possible_machines_for_tasks = map_possible_machines_to_tasks()

    for i in range(population_size):
        new_individual = generate_individual(possible_machines_for_tasks)
        population.append(new_individual)

    return population


def select_solutions(population):
    """
    Funkcja selekcji zwracajaca najlepszych osobnikow - u nas zwraca cala populacje
    :param population:
    :return:
    """
    return population


def create_new_generation_from_parents(parents):
    individual_length = len(parents[0])
    crossover_points = random.sample(range(0, individual_length - 1), NUMBER_OF_CROSSOVER_POINTS)
    crossover_points.sort()
    first_new_individual = []
    second_new_individual = []
    for i in range(NUMBER_OF_CROSSOVER_POINTS):
        if i == 0:
            first_new_individual.extend(parents[0][:crossover_points[0]])
            second_new_individual.extend(parents[1][:crossover_points[0]])
        else:
            first_new_individual.extend(parents[i % 2][crossover_points[i - 1]:crossover_points[i]])
            second_new_individual.extend(parents[(i + 1) % 2][crossover_points[i - 1]:crossover_points[i]])
    first_new_individual.extend(
        parents[NUMBER_OF_CROSSOVER_POINTS % 2][crossover_points[NUMBER_OF_CROSSOVER_POINTS - 1]:])
    second_new_individual.extend(
        parents[(NUMBER_OF_CROSSOVER_POINTS + 1) % 2][crossover_points[NUMBER_OF_CROSSOVER_POINTS - 1]:])
    return (first_new_individual, second_new_individual)


def is_individual_valid(individual, machines_size):
    return set(range(machines_size)).issubset(individual)


def create_new_generation_from_parents_with_validation(parents, machines_size):
    children = ()
    while True:
        children = create_new_generation_from_parents(parents)
        if is_individual_valid(children[0], machines_size) and is_individual_valid(children[1], machines_size):
            break
    return children


def crossover_population(population, machines_size):
    """
    Funkcja krzyzujaca - zwraca nowych osobnikow poprzez proces reprodukcji ich przodkow
    :param population:
    :return:
    """
    new_population = []
    for i in range(0, len(population), 2):
        new_generation = create_new_generation_from_parents_with_validation(population[i:i + 2], machines_size)
        new_population.append(new_generation[0])
        new_population.append(new_generation[1])
    return new_population


def is_mutation_possible(machine_id, individual):
    counter = 0
    is_mutation_possible = False
    for genomeValue in individual:
        if genomeValue == machine_id:
            counter += 1
        if counter == 2:
            is_mutation_possible = True
            break
    return is_mutation_possible


def should_mutate():
    mutation_rand_val = random.uniform(0, 1)
    return mutation_rand_val <= MUTATION_POSSIBILITY


def mutate_genome(machines_size, machine_id):
    new_value = 0
    while True:
        new_value = random.randint(0, machines_size - 1)
        if new_value != machine_id:
            break
    return new_value


def mutate_individual(individual, machines_size):
    new_individual = []
    for machine_id in individual:
        if should_mutate() and is_mutation_possible(machine_id, individual):
            new_individual.append(mutate_genome(machines_size, machine_id))
        else:
            new_individual.append(machine_id)
    return new_individual


def mutate_population(population, machines_size):
    """
    Funkcja mutacji - jej zadaniem jest wprowadzenie do chromosomu losowych zmian
    :param population:
    :return:
    """
    new_population = []
    for individual in population:
        new_population.append(mutate_individual(individual, machines_size))
    return new_population


def calculate_individual_makespan(population, etc_matrix, machines_size):
    machines_values = [0.0] * machines_size
    for i in range(len(population)):
        machines_values[population[i]] += etc_matrix[i, population[i]]
    return max(machines_values)

def calculate_individual_power(population, etc_matrix, machines_size, machines):
    machines_values = [0.0] * machines_size
    for i in range(len(population)):
        machines_values[population[i]] += etc_matrix[i, population[i]]
    max_time = max(machines_values)
    total_power = 0
    for i in range(len(machines_values)):
        total_power = total_power + machines_values[i] * machines.values[i][2] + (max_time - machines_values[i]) * machines.values[i][3]
    return total_power

def rate_adaptation(population, etc_matrix, machines_size, machines = None):
    """
    Ocena przystosowania - ocenia przystosowania nowej populacji - u nas jest to czas makespan
    Zadaniem naszego programu jest uzyskanie jak najmniejszej wartosci
    :param population:
    :return:
    """
    best_individual = 0.0
    other_param = 0.0
    for i in range(len(population)):
        individual = 0.0
        if Common.scheduling_mode == Common.MAKESPAN_MODE:
            individual = calculate_individual_makespan(population[i], etc_matrix, machines_size)
            other_param = calculate_individual_power(population[i], etc_matrix, machines_size, machines)
        elif Common.scheduling_mode == Common.ENERGY_MODE:
            individual = calculate_individual_power(population[i], etc_matrix, machines_size, machines)
            other_param = calculate_individual_makespan(population[i], etc_matrix, machines_size)
        if individual < best_individual or i == 0:
            best_individual = individual
            other_for_best = other_param
    return best_individual, other_for_best


def should_stop_iterations():
    """
    Warunek stopu - u nas brana pod uwage tylko liczba iteracji
    :return:
    """
    return False


def iterate_next_population(new_population, size):
    new_population = select_solutions(new_population)
    new_population = crossover_population(new_population, len(machines))
    new_population = mutate_population(new_population, len(machines))
    return new_population


def get_best_schedule_from_population(population, etc_matrix, machines_size):
    best_individual_makespan = 0.0
    for i in range(len(population)):
        individual_makespan = calculate_individual_makespan(population[i], etc_matrix, machines_size)
        if individual_makespan < best_individual_makespan or i == 0:
            best_individual_makespan = individual_makespan
            best_individual = population[i]
    return best_individual


def get_tasks_on_machine(machine_id, best_schedule, etc_matrix):
    machine_tasks = []
    time = 0.0
    for i in range(len(best_schedule)):
        if best_schedule[i] == machine_id:
            task_value_on_machine = etc_matrix[i][machine_id]
            time += task_value_on_machine
            machine_tasks.append(str(i) + "(" + "{0:.2f}".format(task_value_on_machine) + ")")
    machine_tasks = ["{0:.2f}".format(time)] + machine_tasks
    return machine_tasks


def prepare_schedule_to_save(schedule, machines_size, etc_matrix):
    rows = []
    for i in range(machines_size):
        row = []
        row.append(str(i))
        row.extend(get_tasks_on_machine(i, schedule, etc_matrix))
        rows.append(row)
    return rows


def save_results_to_file(file_name, best_adaptation_rate, best_schedule, machines_size, etc_matrix):
    wfile = open(file_name, "w", newline='')
    writer = csv.writer(wfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Best adaptation rate:", "{0:.2f}".format(best_adaptation_rate)])
    writer.writerow(["MachineID", "Time on machine", "MachineId(time)"])
    saveable_population = prepare_schedule_to_save(best_schedule, machines_size, etc_matrix)
    for row in saveable_population:
        writer.writerow(row)
    wfile.close()


def get_tasks_of_machines(best_schedule):
    tasks_of_machines = [[] for _ in range(len(machines))]

    for i in range(len(best_schedule)):
        for j in range(len(machines)):
            if best_schedule[i] == j:
                tasks_of_machines[j].append(i)

    return tasks_of_machines


def get_max_tasks_number(best_schedule):
    c = Counter(best_schedule)
    max_tasks = max(c.values())

    return max_tasks


def pretty_print(best_schedule, etc, machines, max_time):
    """
    Wypisywanie harmonogramu zadan (populacji) wraz z czasami wykonania zadan.

    :param best_schedule: harmonogram dla najlepszego rozwiazania
    :param etc: macierz etc
    """
    print('-----------------------------------------------------')
    max_tasks = get_max_tasks_number(best_schedule)
    tasks_of_machines = get_tasks_of_machines(best_schedule)

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


def print_no_time(best_schedule):
    """
    Wypisywanie harmonogramu zadan (populacji) bez czasow wykonania zadan.

    :param best_schedule: harmonogram dla najlepszego rozwiazania
    """
    print('-----------------------------------------------------')
    max_tasks = get_max_tasks_number(best_schedule)
    tasks_of_machines = get_tasks_of_machines(best_schedule)

    columns = format('', '8s')
    for i in range(0, max_tasks):
        columns += format(i, '13d')

    print('\t\ttasks')
    print(columns)
    print('machines')

    for machine_id in range(len(machines)):
        row = format(machine_id, '8d')
        for i in range(len(tasks_of_machines[machine_id])):
            row += format(tasks_of_machines[machine_id][i], '13d')

        print(format(row))
    print('-----------------------------------------------------')


def write_to_csv(best_score, best_schedule, etc, machines, max_time):
    """
    Zapisywanie do pliku csv
    :param best_score: najlepszy wynik
    :param best_schedule: harmonogram dla najlepszego rozwiazania
    :param etc: macierz etc
    """
    max_tasks = get_max_tasks_number(best_schedule)
    tasks_of_machines = get_tasks_of_machines(best_schedule)

    with open('results/output_pitt_direct.csv', 'w', newline='') as csvfile:
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
            for i in range(len(tasks_of_machines[machine_id])):
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


def schedule_tasks(number_of_iterations, population_size):
    if population_size % 2 != 0:
        print("Population size should be even")
        return
    random.seed()
    etc_matrix = Common.generate_etc_matrix(machines, tasks)
    first_population = generate_population(population_size)
    best_population = first_population
    best_adaptation_rate, other_for_best = rate_adaptation(first_population, etc_matrix, len(machines), machines)
    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        print("Initial makespan value: " + "{0:.2f}".format(best_adaptation_rate) + " energy usage: " + "{0:.2f}".format(other_for_best))
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        print("Initial energy usage: " + "{0:.2f}".format(best_adaptation_rate) + " makespan: " + "{0:.2f}".format(other_for_best))
    new_population = first_population
    for i in range(number_of_iterations):
        new_population = iterate_next_population(new_population, len(machines))
        adaptation_rate, other_param = rate_adaptation(new_population, etc_matrix, len(machines), machines)
        if adaptation_rate < best_adaptation_rate:
            best_adaptation_rate = adaptation_rate
            best_population = new_population
            other_for_best = other_param
            if Common.scheduling_mode == Common.MAKESPAN_MODE:
                print("New best makespan value(iteration " + str(i) + "): " + "{0:.2f}".format(best_adaptation_rate) + " energy usage: " + "{0:.2f}".format(other_for_best))
            elif Common.scheduling_mode == Common.ENERGY_MODE:
                print("New best energy usage(iteration " + str(i) + "): " + "{0:.2f}".format(best_adaptation_rate) + " makespan: " + "{0:.2f}".format(other_for_best))
        if should_stop_iterations():
            break
    best_schedule = get_best_schedule_from_population(best_population, etc_matrix, len(machines))
    save_results_to_file("results/results_pitt_direct.csv", best_adaptation_rate, best_schedule, len(machines), etc_matrix)
    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        print("Best makespan value: " + "{0:.2f}".format(best_adaptation_rate) + " energy usage: " + "{0:.2f}".format(other_for_best))
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        print("Best energy usage: " + "{0:.2f}".format(best_adaptation_rate) + " makespan: " + "{0:.2f}".format(other_for_best))
    open('results/result_pitt_direct', 'a').write(str(best_adaptation_rate) + "," + str(other_for_best) + "\n")

    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        max_time = best_adaptation_rate
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        max_time = other_for_best
    pretty_print(best_schedule, etc_matrix, machines, max_time)
    write_to_csv(best_adaptation_rate, best_schedule, etc_matrix, machines, max_time)


def main():
    schedule_tasks(ITERATIONS_NUMBER, POPULATION_SIZE)
    security_features = Common.read_security_features()


if __name__ == "__main__":
    main()
