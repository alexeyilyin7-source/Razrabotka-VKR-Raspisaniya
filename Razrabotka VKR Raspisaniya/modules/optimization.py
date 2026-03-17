# modules/optimization.py
from modules.genetic_algorithm import GeneticAlgorithm
from modules.simulated_annealing import SimulatedAnnealing
from modules.greedy_algorithm import GreedyAlgorithm
from modules.fitness_calculator import FitnessCalculator
from modules.schedule_validator import ScheduleValidator
import pandas as pd
import time


class OptimizationEngine:
    """
    Основной движок оптимизации, объединяющий все алгоритмы
    Реализует стратегию выбора и комбинирования алгоритмов
    """

    def __init__(self):
        self.ga = GeneticAlgorithm(
            population_size=30,
            generations=50,
            mutation_rate=0.15,
            crossover_rate=0.8
        )
        self.sa = SimulatedAnnealing(
            initial_temperature=100.0,
            cooling_rate=0.95,
            min_temperature=0.1,
            max_iterations=500
        )
        self.greedy = GreedyAlgorithm()
        self.fitness_calculator = FitnessCalculator()
        self.validator = ScheduleValidator()
        self.optimization_history = []

    def optimize(self, base_data, teachers_df, groups_df, classrooms_df,
                 algorithm='auto', validate=True):
        """
        Запуск оптимизации выбранным алгоритмом

        algorithm:
            'ga' - генетический
            'sa' - имитация отжига
            'greedy' - жадный
            'auto' - комбинированный (по умолчанию)
        """
        print("=" * 60)
        print("🧠 ЗАПУСК ОПТИМИЗАЦИИ РАСПИСАНИЯ")
        print("=" * 60)

        result = None
        algorithm_used = algorithm
        start_time = time.time()

        if base_data.empty:
            print("⚠️ Нет данных для оптимизации")
            return {
                'schedule': base_data,
                'algorithm': algorithm_used,
                'fitness': None,
                'validation': None,
                'time': 0
            }

        try:
            if algorithm == 'greedy':
                # Только жадный алгоритм
                result = self.greedy.run(base_data, teachers_df, classrooms_df)

            elif algorithm == 'ga':
                # Только генетический
                result = self.ga.run(base_data, teachers_df, classrooms_df)

            elif algorithm == 'sa':
                # Только имитация отжига
                result = self.sa.run(base_data, teachers_df, classrooms_df)


            elif algorithm == 'auto':

                print("\n📊 Этап 1: Быстрое построение (жадный алгоритм)")

                greedy_result = self.greedy.run(base_data, teachers_df, classrooms_df)

                if greedy_result is None or greedy_result.empty:
                    print("   Жадный алгоритм не дал результата, используем исходные данные")

                    greedy_result = base_data

                print("\n🧬 Этап 2: Глобальная оптимизация (генетический алгоритм)")

                # Уменьшаем параметры для скорости

                original_pop = self.ga.population_size

                original_gen = self.ga.generations

                self.ga.population_size = min(20, self.ga.population_size)

                self.ga.generations = min(30, self.ga.generations)

                ga_result = self.ga.run(greedy_result, teachers_df, classrooms_df)

                # Восстанавливаем параметры

                self.ga.population_size = original_pop

                self.ga.generations = original_gen

                if ga_result is None or ga_result.empty:
                    print("   Генетический алгоритм не дал результата, используем результат жадного")

                    ga_result = greedy_result

                print("\n🔥 Этап 3: Локальное улучшение (имитация отжига)")

                result = self.sa.run(ga_result, teachers_df, classrooms_df)

                if result is None or result.empty:
                    print("   Имитация отжига не дала результата, используем результат ГА")

                    result = ga_result

                algorithm_used = 'combined (greedy + ga + sa)'

            # Валидация результата
            if validate and result is not None and not result.empty:
                print("\n🔍 Этап 4: Валидация результата")

                is_valid, hard_violations = self.validator.check_hard_constraints(
                    result, teachers_df, groups_df, classrooms_df
                )
                soft_violations = self.validator.check_soft_constraints(
                    result, teachers_df
                )

                if is_valid:
                    print("   ✅ Все жесткие ограничения соблюдены")
                else:
                    print(f"   ⚠️ Нарушений жестких ограничений: {len(hard_violations)}")

                print(f"   ⚠️ Нарушений мягких ограничений: {len(soft_violations)}")

            # Итоговый fitness
            fitness_result = self.fitness_calculator.calculate_fitness(
                result, teachers_df, classrooms_df
            )

            elapsed_time = time.time() - start_time

            print(f"\n📈 Итоговая fitness: {fitness_result['fitness']:.4f}")
            print(f"   Общий штраф: {fitness_result['total_penalty']:.2f}")
            print("   Компоненты штрафа:")
            for comp, value in fitness_result['components'].items():
                print(f"     - {comp}: {value:.2f}")
            print(f"   Время выполнения: {elapsed_time:.2f} сек")

            # Сохраняем в историю
            self.optimization_history.append({
                'timestamp': pd.Timestamp.now(),
                'algorithm': algorithm_used,
                'fitness': fitness_result['fitness'],
                'time': elapsed_time,
                'hard_violations': len(hard_violations) if validate else 0,
                'soft_violations': len(soft_violations) if validate else 0
            })

        except Exception as e:
            print(f"❌ Ошибка при оптимизации: {e}")
            import traceback
            traceback.print_exc()
            result = base_data
            fitness_result = None
            elapsed_time = time.time() - start_time

        print("=" * 60)
        print("✅ ОПТИМИЗАЦИЯ ЗАВЕРШЕНА")
        print("=" * 60)

        return {
            'schedule': result,
            'algorithm': algorithm_used,
            'fitness': fitness_result,
            'validation': self.validator.get_validation_report() if validate else None,
            'time': round(elapsed_time, 2)
        }

    # В методе compare_algorithms добавьте:
    def compare_algorithms(self, base_data, teachers_df, groups_df, classrooms_df):
        """Сравнение всех алгоритмов на одних и тех же данных"""
        print("=" * 60)
        print("📊 СРАВНЕНИЕ АЛГОРИТМОВ")
        print("=" * 60)

        results = {}
        algorithms = {
            'greedy': 'Жадный алгоритм',
            'ga': 'Генетический алгоритм',
            'sa': 'Имитация отжига',
            'auto': 'Комбинированный'
        }

        for alg_key, alg_name in algorithms.items():
            print(f"\n🧪 Тестирование: {alg_name}")
            try:
                result = self.optimize(
                    base_data, teachers_df, groups_df, classrooms_df,
                    algorithm=alg_key, validate=True
                )
                results[alg_key] = result
            except Exception as e:
                print(f"   ⚠️ Ошибка: {e}")
                results[alg_key] = None

        # Создаем сравнительную таблицу
        comparison_data = []
        for alg_key, result in results.items():
            if result and result.get('fitness'):
                comparison_data.append({
                    'Алгоритм': algorithms[alg_key],
                    'Fitness': round(result['fitness']['fitness'], 4),
                    'Штраф': round(result['fitness']['total_penalty'], 2),
                    'Время (сек)': round(result.get('time', 0), 2),
                    'Жестких нарушений': result.get('validation', {}).get('hard_constraints', {}).get('count',
                                                                                                      0) if result.get(
                        'validation') else 0,
                    'Мягких нарушений': result.get('validation', {}).get('soft_constraints', {}).get('count',
                                                                                                     0) if result.get(
                        'validation') else 0
                })

        print("\n" + "=" * 60)
        print("📋 ИТОГОВОЕ СРАВНЕНИЕ")
        if comparison_data:
            comparison_df = pd.DataFrame(comparison_data)
            print(comparison_df.to_string(index=False))
        else:
            print("Нет данных для сравнения")
            comparison_df = pd.DataFrame()
        print("=" * 60)

        return results, comparison_df


# Глобальный экземпляр
optimization_engine = OptimizationEngine()