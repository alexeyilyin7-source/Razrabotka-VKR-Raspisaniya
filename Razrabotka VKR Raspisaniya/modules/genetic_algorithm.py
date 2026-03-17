# modules/genetic_algorithm.py
import numpy as np
import pandas as pd
import random
import copy
from modules.fitness_calculator import FitnessCalculator


class GeneticAlgorithm:
    """
    Реализация генетического алгоритма для оптимизации расписания
    Особь - DataFrame с расписанием
    Популяция - список таких DataFrame
    """

    def __init__(self, population_size=30, generations=50, mutation_rate=0.15, crossover_rate=0.8):
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.fitness_calculator = FitnessCalculator()
        self.best_fitness_history = []
        self.avg_fitness_history = []

    def initialize_population(self, base_data, teachers_df, classrooms_df):
        """
        Создание начальной популяции из случайных вариаций базовых данных
        """
        population = []

        if base_data.empty:
            return population

        for _ in range(self.population_size):
            # Создаем копию базовых данных
            individual = base_data.copy()

            if len(individual) > 0:
                # Добавляем случайные вариации
                # Мутируем от 10% до 30% записей
                n_mutations = max(1, int(len(individual) * random.uniform(0.1, 0.3)))

                # Выбираем случайные индексы для мутации
                indices = random.sample(range(len(individual)),
                                        min(n_mutations, len(individual)))

                for idx in indices:
                    # Случайный тип мутации
                    mutation_type = random.choice(['load', 'time', 'type', 'full'])

                    try:
                        if mutation_type == 'load' and 'teacher_load' in individual.columns:
                            # Изменяем нагрузку на ±20%
                            individual.loc[idx, 'teacher_load'] *= random.uniform(0.8, 1.2)

                        elif mutation_type == 'time' and 'date' in individual.columns:
                            # Сдвигаем дату на 1-3 дня
                            days_shift = random.randint(1, 3)
                            current_date = pd.to_datetime(individual.loc[idx, 'date'])
                            new_date = current_date + pd.Timedelta(days=days_shift)
                            individual.loc[idx, 'date'] = new_date

                        elif mutation_type == 'type' and 'lesson_type' in individual.columns:
                            # Меняем тип занятия
                            types = ['Лекция', 'Семинар', 'Лабораторная']
                            current_type = individual.loc[idx, 'lesson_type']
                            other_types = [t for t in types if t != current_type]
                            if other_types:
                                individual.loc[idx, 'lesson_type'] = random.choice(other_types)

                        elif mutation_type == 'full' and 'teacher_name' in individual.columns:
                            # Полная мутация - меняем преподавателя
                            if teachers_df is not None and not teachers_df.empty:
                                teachers_list = teachers_df['full_name'].tolist()
                                current_teacher = individual.loc[idx, 'teacher_name']
                                other_teachers = [t for t in teachers_list if t != current_teacher]
                                if other_teachers:
                                    individual.loc[idx, 'teacher_name'] = random.choice(other_teachers)
                    except Exception as e:
                        # Игнорируем ошибки при мутации
                        pass

            population.append(individual)

        return population

    def calculate_individual_fitness(self, individual, teachers_df, classrooms_df):
        """
        Расчет fitness для одной особи
        """
        result = self.fitness_calculator.calculate_fitness(individual, teachers_df, classrooms_df)
        return result['fitness']

    def selection(self, population, fitness_scores):
        """
        Турнирная селекция - выбираем лучших особей
        """
        selected = []
        population_size = len(population)

        if population_size == 0:
            return selected

        for _ in range(population_size):
            # Турнир из 3 случайных особей
            tournament_size = min(3, population_size)
            tournament_indices = random.sample(range(population_size), tournament_size)

            # Находим победителя (с максимальным fitness)
            winner_idx = tournament_indices[0]
            max_fitness = fitness_scores[winner_idx]

            for idx in tournament_indices[1:]:
                if fitness_scores[idx] > max_fitness:
                    max_fitness = fitness_scores[idx]
                    winner_idx = idx

            # Добавляем победителя в новое поколение
            selected.append(population[winner_idx].copy())

        return selected

    def crossover(self, parent1, parent2):
        """
        Одноточечный кроссинговер для двух родителей
        """
        # Если вероятность кроссовера не сработала, возвращаем родителей
        if random.random() > self.crossover_rate:
            return parent1.copy(), parent2.copy()

        # Проверяем, что есть что скрещивать
        if len(parent1) < 2 or len(parent2) < 2:
            return parent1.copy(), parent2.copy()

        try:
            child1 = parent1.copy()
            child2 = parent2.copy()

            # Выбираем точку кроссовера
            crossover_point = random.randint(1, min(len(parent1), len(parent2)) - 1)

            # Создаем потомков путем обмена частями
            # Часть 1: от начала до точки кроссовера
            child1_part1 = parent1.iloc[:crossover_point].copy()
            child1_part2 = parent2.iloc[crossover_point:].copy()

            child2_part1 = parent2.iloc[:crossover_point].copy()
            child2_part2 = parent1.iloc[crossover_point:].copy()

            # Собираем потомков
            child1 = pd.concat([child1_part1, child1_part2], ignore_index=True)
            child2 = pd.concat([child2_part1, child2_part2], ignore_index=True)

            return child1, child2

        except Exception as e:
            # В случае ошибки возвращаем родителей
            return parent1.copy(), parent2.copy()

    def mutation(self, individual):
        """
        Мутация особи с заданной вероятностью
        """
        if random.random() > self.mutation_rate:
            return individual

        mutated = individual.copy()

        if len(mutated) > 0:
            # Количество мутаций (от 1 до 3)
            n_mutations = random.randint(1, 3)

            for _ in range(n_mutations):
                idx = random.randint(0, len(mutated) - 1)

                # Случайный тип мутации
                mutation_type = random.choice(['load', 'swap', 'date'])

                try:
                    if mutation_type == 'load' and 'teacher_load' in mutated.columns:
                        # Мутация нагрузки
                        mutated.loc[idx, 'teacher_load'] *= random.uniform(0.7, 1.3)

                    elif mutation_type == 'swap' and len(mutated) > 1:
                        # Обмен двух записей
                        idx2 = random.randint(0, len(mutated) - 1)
                        if idx != idx2:
                            # Создаем копии строк
                            row1 = mutated.iloc[idx].copy()
                            row2 = mutated.iloc[idx2].copy()

                            # Меняем местами, используя имена колонок
                            for col in mutated.columns:
                                temp = mutated.loc[idx, col]
                                mutated.loc[idx, col] = mutated.loc[idx2, col]
                                mutated.loc[idx2, col] = temp

                    elif mutation_type == 'date' and 'date' in mutated.columns:
                        # Сдвиг даты на ±1 день
                        current_date = pd.to_datetime(mutated.loc[idx, 'date'])
                        days_shift = random.choice([-1, 1])
                        new_date = current_date + pd.Timedelta(days=days_shift)
                        mutated.loc[idx, 'date'] = new_date

                except Exception as e:
                    # Игнорируем ошибки при мутации
                    pass

        return mutated

    def run(self, base_data, teachers_df, classrooms_df):
        """
        Запуск генетического алгоритма
        """
        print(f"🚀 Запуск генетического алгоритма:")
        print(f"   Популяция: {self.population_size}")
        print(f"   Поколений: {self.generations}")
        print(f"   Мутация: {self.mutation_rate}")

        if base_data.empty:
            print("   Нет данных для оптимизации")
            return base_data

        # Инициализация
        population = self.initialize_population(base_data, teachers_df, classrooms_df)

        # Проверка, что популяция создана
        if not population:
            print("   Не удалось создать популяцию")
            return base_data

        for generation in range(self.generations):
            # Расчет fitness для всех особей
            fitness_scores = []
            valid_population = []

            for ind in population:
                if ind is not None and not ind.empty:
                    fitness = self.calculate_individual_fitness(ind, teachers_df, classrooms_df)
                    fitness_scores.append(fitness)
                    valid_population.append(ind)

            if not valid_population:
                print(f"   Предупреждение: нет валидных особей в поколении {generation}")
                break

            population = valid_population
            pop_size = len(population)

            # Сохранение статистики
            self.best_fitness_history.append(max(fitness_scores))
            self.avg_fitness_history.append(np.mean(fitness_scores))

            # Селекция
            selected = self.selection(population, fitness_scores)

            if not selected:
                print(f"   Предупреждение: селекция не дала результатов")
                break

            # Скрещивание и мутация
            next_population = []

            # Исправление: безопасное создание следующего поколения
            for i in range(0, len(selected), 2):
                if i + 1 < len(selected):
                    # Скрещивание двух родителей
                    child1, child2 = self.crossover(selected[i], selected[i + 1])

                    # Мутация потомков
                    child1 = self.mutation(child1)
                    child2 = self.mutation(child2)

                    next_population.append(child1)
                    next_population.append(child2)
                else:
                    # Если нечетное количество, добавляем родителя
                    next_population.append(selected[i].copy())

            # Обновляем популяцию (обрезаем до нужного размера)
            if len(next_population) > self.population_size:
                population = next_population[:self.population_size]
            else:
                population = next_population

            # Логирование
            if generation % 10 == 0:
                print(f"   Поколение {generation}: "
                      f"Best = {self.best_fitness_history[-1]:.4f}, "
                      f"Avg = {self.avg_fitness_history[-1]:.4f}, "
                      f"Pop = {len(population)}")

        # Находим лучшее решение
        if not population:
            print("   Предупреждение: популяция пуста, возвращаем исходные данные")
            return base_data

        final_fitness = []
        for ind in population:
            if ind is not None and not ind.empty:
                fitness = self.calculate_individual_fitness(ind, teachers_df, classrooms_df)
                final_fitness.append(fitness)
            else:
                final_fitness.append(0)

        if not final_fitness:
            print("   Предупреждение: нет fitness значений, возвращаем исходные данные")
            return base_data

        best_idx = np.argmax(final_fitness)
        best_solution = population[best_idx]

        print(f"✅ Генетический алгоритм завершен")
        print(f"   Лучший Fitness: {final_fitness[best_idx]:.4f}")
        print(f"   Размер популяции: {len(population)}")

        return best_solution