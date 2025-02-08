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

import Common

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

def generateOneIndividual(machinesNumber, taskNumber):
    inividual = []
    for i in range(machinesNumber):
        inividual.append(i)
    for i in range(machinesNumber, taskNumber):
        inividual.append(random.randint(0, machinesNumber - 1))
    random.shuffle(inividual)
    return inividual


def generateFirstPopulation(machinesNumber, taskNumber, populationSize):
    """
    Generuje pierwsza, losowa populacje
    :param machinesNumber:
    :param taskNumber:
    :return:
    """
    # print(populationSize)
    population = []
    for i in range(populationSize):
        individual = generateOneIndividual(machinesNumber, taskNumber)
        # Generuj nową populację dopóki nie będzie ona odpowiednia
        while not Common.check_task_machine_mapping(machines, tasks, features, individual):
            individual = generateOneIndividual(machinesNumber, taskNumber)
        population.append(individual)
    return population


def selectSolutions(population):
    """
    Funkcja selekcji zwracajaca najlepszych osobnikow - u nas zwraca cala populacje
    :param population:
    :return:
    """
    return population


def createNewGenerationFromParents(parents):
    individualLength = len(parents[0])
    crossoverPoints = random.sample(range(0, individualLength - 1), NUMBER_OF_CROSSOVER_POINTS)
    crossoverPoints.sort()
    firstNewIndividual = []
    secondNewIndividual = []
    # print("First" + str(len(parents[0])))
    # print("Second" + str(len(parents[1])))
    for i in range(NUMBER_OF_CROSSOVER_POINTS):
        if i == 0:
            firstNewIndividual.extend(parents[0][:crossoverPoints[0]])
            secondNewIndividual.extend(parents[1][:crossoverPoints[0]])
        else:
            firstNewIndividual.extend(parents[i % 2][crossoverPoints[i - 1]:crossoverPoints[i]])
            secondNewIndividual.extend(parents[(i + 1) % 2][crossoverPoints[i - 1]:crossoverPoints[i]])
    firstNewIndividual.extend(
        parents[NUMBER_OF_CROSSOVER_POINTS % 2][crossoverPoints[NUMBER_OF_CROSSOVER_POINTS - 1]:])
    secondNewIndividual.extend(
        parents[(NUMBER_OF_CROSSOVER_POINTS + 1) % 2][crossoverPoints[NUMBER_OF_CROSSOVER_POINTS - 1]:])
    # print(crossoverPoints)
    # print(parents[0])
    # print(parents[1])
    # print(firstNewIndividual)
    # print(secondNewIndividual)
    # print("-----------")
    return (firstNewIndividual, secondNewIndividual)


def isIndividualValid(individual, machinesSize):
    return set(range(machinesSize)).issubset(individual)


def createNewGenerationFromParentsWithValidation(parents, machinesSize):
    children = ()
    while True:
        children = createNewGenerationFromParents(parents)
        if isIndividualValid(children[0], machinesSize) and isIndividualValid(children[1], machinesSize):
            break
    return children


def crossoverPopulation(population, machinesSize):
    """
    Funkcja krzyzujaca - zwraca nowych osobnikow poprzez proces reprodukcji ich przodkow
    :param population:
    :return:
    """
    newPopulation = []
    for i in range(0, len(population), 2):
        newGeneration = createNewGenerationFromParentsWithValidation(population[i:i + 2], machinesSize)
        newPopulation.append(newGeneration[0])
        newPopulation.append(newGeneration[1])
    return newPopulation


def isMutationPossible(machineId, individual):
    counter = 0
    isMutationPossible = False
    for genomeValue in individual:
        if genomeValue == machineId:
            counter += 1
        if counter == 2:
            isMutationPossible = True
            break
    return isMutationPossible


def shouldMutate():
    mutationRandVal = random.uniform(0, 1)
    return mutationRandVal <= MUTATION_POSSIBILITY


def mutateGenome(machinesSize, machineId):
    newValue = 0
    while True:
        newValue = random.randint(0, machinesSize - 1)
        if newValue != machineId:
            break
    return newValue


def mutateIndividual(individual, machinesSize):
    newIndividual = []
    for machineId in individual:
        if shouldMutate() and isMutationPossible(machineId, individual):
            newIndividual.append(mutateGenome(machinesSize, machineId))
        else:
            newIndividual.append(machineId)
    return newIndividual


def mutatePopulation(population, machinesSize):
    """
    Funkcja mutacji - jej zadaniem jest wprowadzenie do chromosomu losowych zmian
    :param population:
    :return:
    """
    newPopulation = []
    for individual in population:
        newPopulation.append(mutateIndividual(individual, machinesSize))
    return newPopulation


def calculateIndividualMakespan(population, etcMatrix, machinesSize):
    machinesValues = [0.0] * machinesSize
    for i in range(len(population)):
        machinesValues[population[i]] += etcMatrix[i, population[i]]
    return max(machinesValues)

def calculateIndividualPower(population, etcMatrix, machinesSize, machines):
    machinesValues = [0.0] * machinesSize
    for i in range(len(population)):
        machinesValues[population[i]] += etcMatrix[i, population[i]]
    maxTime = max(machinesValues)
    totalPower = 0
    for i in range(len(machinesValues)):
        totalPower = totalPower + machinesValues[i] * machines.values[i][2] + (maxTime - machinesValues[i]) * machines.values[i][3]
    return totalPower

def rateAdaptation(population, etcMatrix, machinesSize, machines = None):
    """
    Ocena przystosowania - ocenia przystosowania nowej populacji - u nas jest to czas makespan
    Zadaniem naszego programu jest uzyskanie jak najmniejszej wartosci
    :param population:
    :return:
    """
    bestIndividual = 0.0
    otherParam = 0.0
    for i in range(len(population)):
        individual = 0.0
        if Common.scheduling_mode == Common.MAKESPAN_MODE:
            individual = calculateIndividualMakespan(population[i], etcMatrix, machinesSize)
            otherParam = calculateIndividualPower(population[i], etcMatrix, machinesSize, machines)
        elif Common.scheduling_mode == Common.ENERGY_MODE:
            individual = calculateIndividualPower(population[i], etcMatrix, machinesSize, machines)
            otherParam = calculateIndividualMakespan(population[i], etcMatrix, machinesSize)
        if individual < bestIndividual or i == 0:
            bestIndividual = individual
            otherForBest = otherParam
    return bestIndividual, otherForBest


def shouldStopIterations():
    """
    Warunek stopu - u nas brana pod uwage tylko liczba iteracji
    :return:
    """
    return False


def iterateNextPopulation(newPopulation, size):
    newPopulation = selectSolutions(newPopulation)
    newPopulation = crossoverPopulation(newPopulation, len(machines))
    newPopulation = mutatePopulation(newPopulation, len(machines))
    # for ind in newPopulation:
    #     print(ind)
    # print("###########")
    return newPopulation


def getBestScheduleFromPopulation(population, etcMatrix, machinesSize):
    bestIndividualMakespan = 0.0
    for i in range(len(population)):
        individualMakespan = calculateIndividualMakespan(population[i], etcMatrix, machinesSize)
        if individualMakespan < bestIndividualMakespan or i == 0:
            bestIndividualMakespan = individualMakespan
            bestIndividual = population[i]
    return bestIndividual


def getTasksOnMachine(machineId, bestSchedule, etcMatrix):
    machineTasks = []
    # print(machineId)
    # print(bestSchedule)
    time = 0.0
    for i in range(len(bestSchedule)):
        if bestSchedule[i] == machineId:
            taskValueOnMachine = etcMatrix[i][machineId]
            time += taskValueOnMachine
            machineTasks.append(str(i) + "(" + "{0:.2f}".format(taskValueOnMachine) + ")")
    machineTasks = ["{0:.2f}".format(time)] + machineTasks
    return machineTasks


def prepareScheduleToSave(schedule, machinesSize, etcMatrix):
    rows = []
    for i in range(machinesSize):
        row = []
        row.append(str(i))
        row.extend(getTasksOnMachine(i, schedule, etcMatrix))
        rows.append(row)
    return rows


def saveResultsToFile(fileName, bestAdaptationRate, bestSchedule, machinesSize, etcMatrix):
    wfile = open(fileName, "w", newline='')
    writer = csv.writer(wfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["Best adaptation rate:", "{0:.2f}".format(bestAdaptationRate)])
    writer.writerow(["MachineID", "Time on machine", "MachineId(time)"])
    saveablePopulation = prepareScheduleToSave(bestSchedule, machinesSize, etcMatrix)
    for row in saveablePopulation:
        writer.writerow(row)
    wfile.close()


def get_tasks_of_machines(bestSchedule):
    tasks_of_machines = [[] for _ in range(len(machines))]

    for i in range(len(bestSchedule)):
        for j in range(len(machines)):
            if bestSchedule[i] == j:
                tasks_of_machines[j].append(i)

    return tasks_of_machines


def get_max_tasks_number(bestSchedule):
    c = Counter(bestSchedule)
    max_tasks = max(c.values())

    return max_tasks


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


def print_no_time(bestSchedule):
    """
    Wypisywanie harmonogramu zadan (populacji) bez czasow wykonania zadan.

    :param bestSchedule: harmonogram dla najlepszego rozwiazania
    """
    print('-----------------------------------------------------')
    max_tasks = get_max_tasks_number(bestSchedule)
    tasks_of_machines = get_tasks_of_machines(bestSchedule)

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


def write_to_csv(best_score, bestSchedule, etc, machines, max_time):
    """
    Zapisywanie do pliku csv
    :param best_score: najlepszy wynik
    :param bestSchedule: harmonogram dla najlepszego rozwiazania
    :param etc: macierz etc
    """
    max_tasks = get_max_tasks_number(bestSchedule)
    tasks_of_machines = get_tasks_of_machines(bestSchedule)

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


def scheduleTasks(numberOfIterations, populationSize):
    if populationSize % 2 != 0:
        print("Population size should be even")
        return
    random.seed()
    etcMatrix = Common.generate_etc_matrix(machines, tasks)
    firstPopulation = generateFirstPopulation(len(machines), len(tasks), populationSize)
    bestPopulation = firstPopulation
    bestAdaptationRate, otherForBest = rateAdaptation(firstPopulation, etcMatrix, len(machines), machines)
    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        print("Initial makespan value: " + "{0:.2f}".format(bestAdaptationRate) + " energy usage: " + "{0:.2f}".format(otherForBest))
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        print("Initial energy usage: " + "{0:.2f}".format(bestAdaptationRate) + " makespan: " + "{0:.2f}".format(otherForBest))
    newPopulation = firstPopulation
    for i in range(numberOfIterations):
        newPopulation = iterateNextPopulation(newPopulation, len(machines))
        adaptationRate, otherParam = rateAdaptation(newPopulation, etcMatrix, len(machines), machines)
        if adaptationRate < bestAdaptationRate:
            bestAdaptationRate = adaptationRate
            bestPopulation = newPopulation
            otherForBest = otherParam
            if Common.scheduling_mode == Common.MAKESPAN_MODE:
                print("New best makespan value(iteration " + str(i) + "): " + "{0:.2f}".format(bestAdaptationRate) + " energy usage: " + "{0:.2f}".format(otherForBest))
            elif Common.scheduling_mode == Common.ENERGY_MODE:
                print("New best energy usage(iteration " + str(i) + "): " + "{0:.2f}".format(bestAdaptationRate) + " makespan: " + "{0:.2f}".format(otherForBest))
        if shouldStopIterations():
            break
    bestSchedule = getBestScheduleFromPopulation(bestPopulation, etcMatrix, len(machines))
    saveResultsToFile("results/results_pitt_direct.csv", bestAdaptationRate, bestSchedule, len(machines), etcMatrix)
    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        print("Best makespan value: " + "{0:.2f}".format(bestAdaptationRate) + " energy usage: " + "{0:.2f}".format(otherForBest))
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        print("Best energy usage: " + "{0:.2f}".format(bestAdaptationRate) + " makespan: " + "{0:.2f}".format(otherForBest))
    open('results/result_pitt_direct', 'a').write(str(bestAdaptationRate) + "," + str(otherForBest) + "\n")

    if Common.scheduling_mode == Common.MAKESPAN_MODE:
        maxTime = bestAdaptationRate
    elif Common.scheduling_mode == Common.ENERGY_MODE:
        maxTime = otherForBest
    pretty_print(bestSchedule, etcMatrix, machines, maxTime)
    write_to_csv(bestAdaptationRate, bestSchedule, etcMatrix, machines, maxTime)


def main():
    # scheduleTasks(ITERATIONS_NUMBER, POPULATION_SIZE)
    security_features = Common.read_security_features()


if __name__ == "__main__":
    main()
