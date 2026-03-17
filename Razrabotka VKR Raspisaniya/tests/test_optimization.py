# test_optimization.py
"""
Тестовый скрипт для проверки работы алгоритмов оптимизации
Запуск: python test_optimization.py
"""

import pandas as pd
import numpy as np
import time
import sys
from datetime import datetime, timedelta

# Добавляем путь к модулям
sys.path.append('.')

from modules.data_loader import loader
from modules.optimization import optimization_engine
from modules.database import db_manager
from modules.schedule_validator import ScheduleValidator
from modules.fitness_calculator import FitnessCalculator

# Конфигурация для быстрого тестирования
TEST_CONFIG = {
    'quick_mode': True,  # Быстрый режим (меньше данных, меньше итераций)
    'sample_size': 50,  # Размер выборки для тестов
    'ga_generations': 10,  # Количество поколений для ГА
    'sa_iterations': 100,  # Количество итераций для имитации отжига
    'verbose': False  # Подробный вывод
}


def print_separator(title):
    """Печать разделителя с заголовком"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def get_test_data():
    """Получение тестовых данных (сэмплирование для скорости)"""
    if loader.schedule_data is not None and not loader.schedule_data.empty:
        data = loader.schedule_data.copy()
        # Берем только небольшую выборку для тестов
        if len(data) > TEST_CONFIG['sample_size']:
            data = data.sample(n=TEST_CONFIG['sample_size'], random_state=42)
        return data
    return pd.DataFrame()


def test_data_loading():
    """Тест 1: Загрузка данных (быстрый)"""
    print_separator("ТЕСТ 1: ЗАГРУЗКА ДАННЫХ")

    start = time.time()

    print(f"📊 Данные расписания: {len(loader.schedule_data)} записей")
    print(f"👥 Преподаватели: {len(loader.teachers_data)}")
    print(f"👥 Группы: {len(loader.groups_data)}")
    print(f"🏛 Аудитории: {len(loader.classrooms_data)}")
    print(f"📚 Учебные планы: {len(loader.curriculum_data)}")

    if TEST_CONFIG['verbose'] and loader.schedule_data is not None:
        print("\n📋 Первые 3 записи расписания:")
        print(loader.schedule_data.head(3))

    elapsed = time.time() - start
    print(f"⏱️ Время: {elapsed:.2f} сек")

    return all([
        loader.schedule_data is not None and len(loader.schedule_data) > 0,
        loader.teachers_data is not None and len(loader.teachers_data) > 0,
        loader.groups_data is not None and len(loader.groups_data) > 0,
        loader.classrooms_data is not None and len(loader.classrooms_data) > 0
    ])


def test_database():
    """Тест 2: Работа с базой данных (быстрый)"""
    print_separator("ТЕСТ 2: БАЗА ДАННЫХ")

    start = time.time()

    try:
        # Инициализация БД
        db_manager.init_database()

        # Импорт данных
        db_manager.import_from_csv(loader)

        # Получение статистики
        stats = db_manager.get_statistics()
        print("📊 Статистика БД:")
        for key, value in stats.items():
            print(f"   {key}: {value}")

        elapsed = time.time() - start
        print(f"⏱️ Время: {elapsed:.2f} сек")

        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def test_fitness_calculator():
    """Тест 3: Расчет fitness-функции (быстрый)"""
    print_separator("ТЕСТ 3: FITNESS-ФУНКЦИЯ")

    start = time.time()

    calculator = FitnessCalculator()
    test_data = get_test_data()

    if test_data.empty:
        print("⚠️ Нет данных для тестирования")
        return False

    # Тест на тестовых данных
    result = calculator.calculate_fitness(
        test_data,
        loader.teachers_data,
        loader.classrooms_data
    )

    print("📈 Результат fitness-функции:")
    print(f"   Fitness: {result['fitness']:.4f}")
    print(f"   Общий штраф: {result['total_penalty']:.2f}")
    print("   Компоненты:")
    for comp, value in result['components'].items():
        print(f"     - {comp}: {value:.2f}")

    elapsed = time.time() - start
    print(f"⏱️ Время: {elapsed:.2f} сек")

    return result['fitness'] > 0


def test_validator():
    """Тест 4: Валидация расписания (быстрый)"""
    print_separator("ТЕСТ 4: ВАЛИДАЦИЯ РАСПИСАНИЯ")

    start = time.time()

    validator = ScheduleValidator()
    test_data = get_test_data()

    if test_data.empty:
        print("⚠️ Нет данных для тестирования")
        return False

    # Проверка жестких ограничений
    is_valid, hard_violations = validator.check_hard_constraints(
        test_data,
        loader.teachers_data,
        loader.groups_data,
        loader.classrooms_data
    )

    # Проверка мягких ограничений
    soft_violations = validator.check_soft_constraints(
        test_data,
        loader.teachers_data
    )

    print(f"✅ Жесткие ограничения соблюдены: {is_valid}")
    print(f"⚠️ Нарушений жестких ограничений: {len(hard_violations)}")
    print(f"⚠️ Нарушений мягких ограничений: {len(soft_violations)}")

    if hard_violations and TEST_CONFIG['verbose']:
        print("\n📋 Примеры нарушений:")
        for v in hard_violations[:3]:
            print(f"   - {v['message']}")

    report = validator.get_validation_report()
    print(f"\n📊 Качество расписания: {report['quality']}")

    elapsed = time.time() - start
    print(f"⏱️ Время: {elapsed:.2f} сек")

    return True


def test_greedy_algorithm():
    """Тест 5: Жадный алгоритм (быстрый)"""
    print_separator("ТЕСТ 5: ЖАДНЫЙ АЛГОРИТМ")

    from modules.greedy_algorithm import GreedyAlgorithm

    greedy = GreedyAlgorithm()
    test_data = get_test_data()

    if test_data.empty:
        print("⚠️ Нет данных для тестирования")
        return False

    # Тест только с одним приоритетом для скорости
    print(f"\n📊 Тестирование жадного алгоритма...")

    start = time.time()

    result = greedy.run(
        test_data,
        loader.teachers_data,
        loader.classrooms_data,
        priority='balanced',
        distribute=True
    )

    elapsed = time.time() - start

    print(f"⏱️ Время: {elapsed:.2f} сек")

    # Проверка fitness
    fitness = greedy.fitness_calculator.calculate_fitness(
        result, loader.teachers_data, loader.classrooms_data
    )
    print(f"📈 Fitness: {fitness['fitness']:.4f}")

    return fitness['fitness'] > 0


def test_genetic_algorithm():
    """Тест 6: Генетический алгоритм (быстрый)"""
    print_separator("ТЕСТ 6: ГЕНЕТИЧЕСКИЙ АЛГОРИТМ")

    from modules.genetic_algorithm import GeneticAlgorithm

    test_data = get_test_data()

    if test_data.empty:
        print("⚠️ Нет данных для тестирования")
        return False

    # Используем уменьшенные параметры для скорости
    ga = GeneticAlgorithm(
        population_size=10,  # Маленькая популяция
        generations=TEST_CONFIG['ga_generations'],
        mutation_rate=0.1,
        crossover_rate=0.8
    )

    print(f"🧬 Конфигурация: pop={ga.population_size}, gen={ga.generations}")

    start = time.time()
    result = ga.run(
        test_data,
        loader.teachers_data,
        loader.classrooms_data
    )
    elapsed = time.time() - start

    print(f"⏱️ Время: {elapsed:.2f} сек")

    # Fitness
    fitness = ga.fitness_calculator.calculate_fitness(
        result, loader.teachers_data, loader.classrooms_data
    )
    print(f"📈 Fitness: {fitness['fitness']:.4f}")

    return fitness['fitness'] > 0


def test_simulated_annealing():
    """Тест 7: Имитация отжига (быстрый)"""
    print_separator("ТЕСТ 7: ИМИТАЦИЯ ОТЖИГА")

    from modules.simulated_annealing import SimulatedAnnealing

    test_data = get_test_data()

    if test_data.empty:
        print("⚠️ Нет данных для тестирования")
        return False

    # Используем уменьшенные параметры для скорости
    sa = SimulatedAnnealing(
        initial_temperature=50.0,
        cooling_rate=0.9,
        min_temperature=1.0,
        max_iterations=TEST_CONFIG['sa_iterations']
    )

    print(f"🔥 Конфигурация: T0={sa.initial_temperature}, итераций={sa.max_iterations}")

    start = time.time()
    result = sa.run(
        test_data,
        loader.teachers_data,
        loader.classrooms_data
    )
    elapsed = time.time() - start

    print(f"⏱️ Время: {elapsed:.2f} сек")

    # Fitness
    fitness = sa.fitness_calculator.calculate_fitness(
        result, loader.teachers_data, loader.classrooms_data
    )
    print(f"📈 Fitness: {fitness['fitness']:.4f}")

    return fitness['fitness'] > 0


def test_optimization_engine():
    """Тест 8: Движок оптимизации (быстрый)"""
    print_separator("ТЕСТ 8: ДВИЖОК ОПТИМИЗАЦИИ")

    test_data = get_test_data()

    if test_data.empty:
        print("⚠️ Нет данных для тестирования")
        return False

    # Настраиваем движок на быстрый режим
    optimization_engine.ga.population_size = 10
    optimization_engine.ga.generations = TEST_CONFIG['ga_generations']
    optimization_engine.sa.max_iterations = TEST_CONFIG['sa_iterations']

    # Тест только с одним алгоритмом для скорости
    print(f"\n🔧 Тестирование комбинированного алгоритма...")

    start = time.time()

    result = optimization_engine.optimize(
        test_data,
        loader.teachers_data,
        loader.groups_data,
        loader.classrooms_data,
        algorithm='auto',  # Комбинированный
        validate=True
    )

    elapsed = time.time() - start

    if result and result.get('fitness'):
        print(f"📈 Fitness: {result['fitness']['fitness']:.4f}")
        print(f"⏱️ Время: {result.get('time', elapsed):.2f} сек")

        if result.get('validation'):
            print(f"📊 Качество: {result['validation'].get('quality', 'N/A')}")

    return result is not None and result.get('fitness') is not None


def test_all_algorithms_comparison():
    """Тест 9: Сравнение алгоритмов (быстрый)"""
    print_separator("ТЕСТ 9: СРАВНЕНИЕ АЛГОРИТМОВ")

    test_data = get_test_data()

    if test_data.empty:
        print("⚠️ Нет данных для тестирования")
        return False

    # Настраиваем параметры для быстрого сравнения
    original_ga_pop = optimization_engine.ga.population_size
    original_ga_gen = optimization_engine.ga.generations
    original_sa_iter = optimization_engine.sa.max_iterations

    optimization_engine.ga.population_size = 8
    optimization_engine.ga.generations = 5
    optimization_engine.sa.max_iterations = 50

    start = time.time()

    try:
        results, comparison = optimization_engine.compare_algorithms(
            test_data,
            loader.teachers_data,
            loader.groups_data,
            loader.classrooms_data
        )

        elapsed = time.time() - start

        print("\n📋 Таблица сравнения:")
        if comparison is not None and not comparison.empty:
            print(comparison.to_string(index=False))
        else:
            print("Нет данных для сравнения")

        print(f"\n⏱️ Общее время: {elapsed:.2f} сек")

        # Восстанавливаем параметры
        optimization_engine.ga.population_size = original_ga_pop
        optimization_engine.ga.generations = original_ga_gen
        optimization_engine.sa.max_iterations = original_sa_iter

        return comparison is not None and not comparison.empty

    except Exception as e:
        print(f"❌ Ошибка при сравнении: {e}")

        # Восстанавливаем параметры
        optimization_engine.ga.population_size = original_ga_pop
        optimization_engine.ga.generations = original_ga_gen
        optimization_engine.sa.max_iterations = original_sa_iter

        return False


def run_quick_tests():
    """Запуск только быстрых тестов (без тяжелых алгоритмов)"""
    print("\n" + "⚡" * 35)
    print(" ⚡ ЗАПУСК БЫСТРЫХ ТЕСТОВ")
    print("⚡" * 35 + "\n")

    quick_tests = [
        ("Загрузка данных", test_data_loading),
        ("База данных", test_database),
        ("Fitness-функция", test_fitness_calculator),
        ("Валидация", test_validator),
    ]

    results = []

    for test_name, test_func in quick_tests:
        print(f"\n▶️ Запуск: {test_name}")
        try:
            start = time.time()
            success = test_func()
            elapsed = time.time() - start

            if success:
                print(f"✅ УСПЕШНО (за {elapsed:.2f} сек)")
                results.append((test_name, "✅", elapsed))
            else:
                print(f"❌ ПРОВАЛ")
                results.append((test_name, "❌", elapsed))

        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            results.append((test_name, "❌", 0))

    # Итоговый отчет
    print("\n" + "📊" * 35)
    print(" 📊 ИТОГОВЫЙ ОТЧЕТ (БЫСТРЫЕ ТЕСТЫ)")
    print("📊" * 35 + "\n")

    passed = sum(1 for _, status, _ in results if status == "✅")
    total = len(results)

    print(f"Всего тестов: {total}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {total - passed}")
    print(f"Процент успеха: {passed / total * 100:.1f}%\n")

    print("Детали:")
    for test_name, status, elapsed in results:
        print(f"  {status} {test_name} ({elapsed:.2f} сек)")

    return passed == total


def run_all_tests():
    """Запуск всех тестов"""
    print("\n" + "🎯" * 35)
    print(" 🧪 ЗАПУСК ВСЕХ ТЕСТОВ СИСТЕМЫ")
    print("🎯" * 35 + "\n")

    # Предупреждение о времени выполнения
    if not TEST_CONFIG['quick_mode']:
        print("⚠️  ВНИМАНИЕ: Полное тестирование может занять несколько минут!")
        print("   Нажмите Ctrl+C для отмены или подождите...\n")
        time.sleep(2)

    tests = [
        ("Загрузка данных", test_data_loading),
        ("База данных", test_database),
        ("Fitness-функция", test_fitness_calculator),
        ("Валидация", test_validator),
    ]

    # Добавляем алгоритмы только если не быстрый режим
    if not TEST_CONFIG['quick_mode']:
        tests.extend([
            ("Жадный алгоритм", test_greedy_algorithm),
            ("Генетический алгоритм", test_genetic_algorithm),
            ("Имитация отжига", test_simulated_annealing),
            ("Движок оптимизации", test_optimization_engine),
            ("Сравнение алгоритмов", test_all_algorithms_comparison),
        ])
    else:
        print("\n⚡ Быстрый режим: алгоритмы пропущены")

    results = []

    for test_name, test_func in tests:
        print(f"\n▶️ Запуск: {test_name}")
        try:
            start = time.time()
            success = test_func()
            elapsed = time.time() - start

            if success:
                print(f"✅ УСПЕШНО (за {elapsed:.2f} сек)")
                results.append((test_name, "✅", elapsed))
            else:
                print(f"❌ ПРОВАЛ")
                results.append((test_name, "❌", elapsed))

        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            import traceback
            if TEST_CONFIG['verbose']:
                traceback.print_exc()
            results.append((test_name, "❌", 0))

    # Итоговый отчет
    print("\n" + "📊" * 35)
    print(" 📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ")
    print("📊" * 35 + "\n")

    passed = sum(1 for _, status, _ in results if status == "✅")
    total = len(results)

    print(f"Всего тестов: {total}")
    print(f"Успешно: {passed}")
    print(f"Провалено: {total - passed}")
    print(f"Процент успеха: {passed / total * 100:.1f}%\n")

    print("Детали:")
    for test_name, status, elapsed in results:
        print(f"  {status} {test_name} ({elapsed:.2f} сек)")

    print("\n" + "🎉" * 35)
    if passed == total:
        print(" 🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    else:
        print(" ⚠️ ТЕСТЫ ЗАВЕРШЕНЫ С ОШИБКАМИ")
    print("🎉" * 35 + "\n")

    return passed == total


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Тестирование системы расписания')
    parser.add_argument('--mode', choices=['quick', 'full'], default='quick',
                        help='Режим тестирования: quick (быстрый) или full (полный)')
    parser.add_argument('--verbose', action='store_true',
                        help='Подробный вывод')
    parser.add_argument('--sample-size', type=int, default=50,
                        help='Размер выборки данных для тестов')

    args = parser.parse_args()

    # Обновляем конфигурацию
    TEST_CONFIG['quick_mode'] = (args.mode == 'quick')
    TEST_CONFIG['verbose'] = args.verbose
    TEST_CONFIG['sample_size'] = args.sample_size

    if args.mode == 'quick':
        TEST_CONFIG['ga_generations'] = 5
        TEST_CONFIG['sa_iterations'] = 50
    else:
        TEST_CONFIG['ga_generations'] = 20
        TEST_CONFIG['sa_iterations'] = 200

    if args.mode == 'quick':
        run_quick_tests()
    else:
        run_all_tests()