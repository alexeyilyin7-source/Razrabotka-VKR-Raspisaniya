# modules/simulated_annealing.py
import numpy as np
import random
import math
import pandas as pd
from modules.fitness_calculator import FitnessCalculator


class SimulatedAnnealing:
    """
    Алгоритм имитации отжига для улучшения расписания
    Позволяет выходить из локальных оптимумов
    """

    def __init__(self, initial_temperature=100.0, cooling_rate=0.95,
                 min_temperature=0.1, max_iterations=1000):
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.min_temperature = min_temperature
        self.max_iterations = max_iterations
        self.fitness_calculator = FitnessCalculator()
        self.temperature_history = []
        self.fitness_history = []

    def generate_neighbor(self, solution, teachers_df, classrooms_df):
        """
        Генерация соседнего решения (небольшая мутация)
        """
        if solution is None or solution.empty:
            return solution

        neighbor = solution.copy()

        if len(neighbor) == 0:
            return neighbor

        # Выбираем случайную операцию мутации
        mutation_type = random.choice(['swap', 'load', 'date', 'teacher'])

        try:
            if mutation_type == 'swap' and len(neighbor) > 1:
                # Обмен двух записей
                idx1 = random.randint(0, len(neighbor) - 1)
                idx2 = random.randint(0, len(neighbor) - 1)

                if idx1 != idx2:
                    # Меняем все колонки местами
                    for col in neighbor.columns:
                        temp = neighbor.loc[idx1, col]
                        neighbor.loc[idx1, col] = neighbor.loc[idx2, col]
                        neighbor.loc[idx2, col] = temp

            elif mutation_type == 'load' and 'teacher_load' in neighbor.columns:
                # Небольшое изменение нагрузки
                idx = random.randint(0, len(neighbor) - 1)
                change = random.uniform(-0.5, 0.5)
                neighbor.loc[idx, 'teacher_load'] = max(1, neighbor.loc[idx, 'teacher_load'] + change)

            elif mutation_type == 'date' and 'date' in neighbor.columns:
                # Небольшой сдвиг даты
                idx = random.randint(0, len(neighbor) - 1)
                current_date = pd.to_datetime(neighbor.loc[idx, 'date'])
                # Сдвиг на 1-3 дня
                days_shift = random.choice([-3, -2, -1, 1, 2, 3])
                new_date = current_date + pd.Timedelta(days=days_shift)
                neighbor.loc[idx, 'date'] = new_date

            elif mutation_type == 'teacher' and 'teacher_name' in neighbor.columns and teachers_df is not None:
                # Смена преподавателя
                idx = random.randint(0, len(neighbor) - 1)
                if not teachers_df.empty:
                    teachers_list = teachers_df['full_name'].tolist()
                    current_teacher = neighbor.loc[idx, 'teacher_name']
                    # Выбираем другого преподавателя из того же института/кафедры
                    other_teachers = [t for t in teachers_list if t != current_teacher]
                    if other_teachers:
                        neighbor.loc[idx, 'teacher_name'] = random.choice(other_teachers)

        except Exception as e:
            # В случае ошибки возвращаем исходное решение
            return solution

        return neighbor

    def calculate_fitness(self, solution, teachers_df, classrooms_df):
        """
        Расчет fitness для решения
        """
        result = self.fitness_calculator.calculate_fitness(solution, teachers_df, classrooms_df)
        return result['fitness']

    def acceptance_probability(self, delta_fitness, temperature):
        """
        Вероятность принятия худшего решения по формуле Больцмана
        """
        if delta_fitness >= 0:
            return 1.0
        if temperature <= 0:
            return 0

        try:
            # delta_fitness отрицательный, так что exp будет меньше 1
            return math.exp(delta_fitness / temperature)
        except:
            return 0

    def run(self, initial_solution, teachers_df, classrooms_df):
        """
        Запуск алгоритма имитации отжига
        """
        print(f"🔥 Запуск алгоритма имитации отжига:")
        print(f"   Начальная температура: {self.initial_temperature}")
        print(f"   Коэффициент охлаждения: {self.cooling_rate}")

        if initial_solution is None or initial_solution.empty:
            print("   ⚠️ Нет данных для оптимизации")
            return initial_solution

        try:
            current_solution = initial_solution.copy()
            current_fitness = self.calculate_fitness(current_solution, teachers_df, classrooms_df)

            best_solution = current_solution.copy()
            best_fitness = current_fitness

            temperature = self.initial_temperature
            iteration = 0

            while temperature > self.min_temperature and iteration < self.max_iterations:
                self.temperature_history.append(temperature)
                self.fitness_history.append(best_fitness)

                # Генерация соседнего решения
                neighbor = self.generate_neighbor(current_solution, teachers_df, classrooms_df)

                if neighbor is not None and not neighbor.empty:
                    neighbor_fitness = self.calculate_fitness(neighbor, teachers_df, classrooms_df)

                    # Расчет изменения fitness
                    delta_fitness = neighbor_fitness - current_fitness

                    # Решение о принятии нового решения
                    if delta_fitness > 0:
                        # Лучшее решение - принимаем всегда
                        current_solution = neighbor
                        current_fitness = neighbor_fitness

                        if current_fitness > best_fitness:
                            best_solution = current_solution.copy()
                            best_fitness = current_fitness
                    else:
                        # Худшее решение - принимаем с вероятностью
                        prob = self.acceptance_probability(delta_fitness, temperature)
                        if random.random() < prob:
                            current_solution = neighbor
                            current_fitness = neighbor_fitness

                # Охлаждение
                temperature *= self.cooling_rate
                iteration += 1

                # Логирование
                if iteration % 200 == 0:
                    print(f"   Итерация {iteration}: "
                          f"T = {temperature:.2f}, "
                          f"Best Fitness = {best_fitness:.4f}")

            print(f"✅ Алгоритм имитации отжига завершен")
            print(f"   Лучший Fitness: {best_fitness:.4f}")
            print(f"   Итераций: {iteration}")

            return best_solution

        except Exception as e:
            print(f"   ⚠️ Ошибка в алгоритме: {e}")
            return initial_solution