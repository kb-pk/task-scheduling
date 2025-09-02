from scheduler.ProgramState import ProgramState

class Translations:
    def __init__(self, state: ProgramState):
        self.__state = state

        self.translation = {
            self.__state.lang.State.pl_PL: {
                "Which algorithm would you like to use?": "Jaki algorytm chcesz użyć?",

                "makespan": "makespan (czas wykonania)",
                "energy": "zużyta energia",
                "all": "wszystko",

                "Pitt (direct)": "Pitt (reprezentacja bezpośrednia)",
                "Pitt (permutation-based)": "Pitt (reprezentacja permutowana)",

                "Switch scheduling mode (current mode: ": "Zmień tryb szeregowania (obecnie: ",
                "Switch output mode (current mode: ": "Zmień tryb wyświetlania (obecnie: ",
                "Switch stop criterion (current mode: ": "Zmień warunek stopu (obecnie: ",
                "Exit program": "Wyjdź z programu",
                "Invalid choice": "Nieprawidłowy wybór",

                "Stop criterion": "Warunek stopu",
                "Criterion for stopping the evolution": "Warunek zakończenia ewolucji",
                "Iterations": "Iteracje",
                "Number of iterations (epochs)": "Liczba iteracji (epok)",
                "Fitness function value": "Wartość funkcji przystosowania",
                "The value which the algorithm is optimising (": "Wartość, którą optymalizuje algorytm (",
                "Population size": "Ilość osobników",
                "Must be even": "Musi być parzysta",
                "Crossover points": "Punkty krzyżowania",
                "Number of crossover points": "Liczba punktów krzyżowania",
                "Mutation probability": "Prawdopodobieństwo mutacji",
                "Gene mutation probability": "Prawdopodobieństwo mutacji genu",

                "Inertia": "Bezwładność",
                "Movement inertia": "Bezwładność w ruchu",
                "Separation": "Separacja",
                "Separation between entities": "Separacja pomiędzy osobnikami",
                "Alignment": "Wyrównanie",
                "How closely entity's speed matches that of other entities": "Jak dokładnie prędkość osobnika jest podobna do prędkości reszty osobników",
                "Cohesion": "Spójność",
                "How much the entity is drawn to the center of their neighbourhood": "Jak bardzo centrum sąsiedztwa przyciąga osobnika",
                "Food attraction": "Przyciąganie do jedzenia",
                "How much the entity is drawn to food sources": "Jak bardzo źródła jedzenia przyciągają osobniki",
                "Enemy repulsion": "Odpychanie od wrogów",
                "How much the entity is drawn away from enemy sources": "Jak bardzo źródła wrogów odpychają osobniki",
                "Neighbour radius": "Szerokość sąsiedztwa",

                "Step size": "Rozmiar kroku",
                "Step size in vision phase": "Rozmiar kroku w fazie wizji",

                "Number of tasks exceeds number of machines - machines cannot be without tasks":
                    "Liczba zadań przewyższa liczbę maszyn - maszyny nie mogą być bez zadań",
            }
        }

