# modules/greedy_algorithm.py
import pandas as pd
import numpy as np
from modules.fitness_calculator import FitnessCalculator


class GreedyAlgorithm:
    """
    Жадный алгоритм для быстрого построения расписания
    Используется как начальное приближение или резервный метод
    """

    def __init__(self):
        self.fitness_calculator = FitnessCalculator()

    def schedule_by_priority(self, base_data, teachers_df, classrooms_df, priority='load'):
        """
        Построение расписания на основе приоритетов
        priority: 'load' - по нагрузке (сначала самые загруженные)
                 'classes' - по количеству занятий
                 'balanced' - сбалансированный подход
        """
        if base_data.empty:
            return base_data

        schedule = base_data.copy()

        if priority == 'load' and 'teacher_load' in schedule.columns:
            # Сортировка по убыванию нагрузки
            schedule = schedule.sort_values('teacher_load', ascending=False)

        elif priority == 'classes' and 'total_classes' in schedule.columns:
            # Сортировка по убыванию количества занятий
            schedule = schedule.sort_values('total_classes', ascending=False)

        elif priority == 'balanced':
            # Комбинированный подход
            if 'teacher_load' in schedule.columns and 'total_classes' in schedule.columns:
                # Нормализация значений
                load_min = schedule['teacher_load'].min()
                load_max = schedule['teacher_load'].max()
                classes_min = schedule['total_classes'].min()
                classes_max = schedule['total_classes'].max()

                # Избегаем деления на ноль
                load_range = load_max - load_min if load_max > load_min else 1
                classes_range = classes_max - classes_min if classes_max > classes_min else 1

                schedule['load_norm'] = (schedule['teacher_load'] - load_min) / load_range
                schedule['classes_norm'] = (schedule['total_classes'] - classes_min) / classes_range

                # Приоритет: 60% нагрузка, 40% количество занятий
                schedule['priority_score'] = schedule['load_norm'] * 0.6 + schedule['classes_norm'] * 0.4
                schedule = schedule.sort_values('priority_score', ascending=False)

                # Удаляем временные колонки
                schedule = schedule.drop(['load_norm', 'classes_norm', 'priority_score'], axis=1)

        # Добавляем информацию об аудиториях (упрощенно)
        if 'room' not in schedule.columns and classrooms_df is not None:
            # Для демо - назначаем случайные аудитории
            rooms = classrooms_df['room_id'].tolist() if not classrooms_df.empty else ['R001']
            schedule['room'] = [np.random.choice(rooms) for _ in range(len(schedule))]

        return schedule

    def distribute_evenly(self, base_data):
        """
        Равномерное распределение нагрузки по дням недели
        """
        if base_data.empty or 'date' not in base_data.columns:
            return base_data

        # Копируем данные
        distributed = base_data.copy()

        # Добавляем день недели
        distributed['day_of_week'] = pd.to_datetime(distributed['date']).dt.dayofweek

        # Группировка по преподавателям и дням
        if 'teacher_name' in distributed.columns:
            for teacher in distributed['teacher_name'].unique():
                teacher_mask = distributed['teacher_name'] == teacher
                teacher_data = distributed[teacher_mask]

                # Если у преподавателя много занятий в один день
                day_counts = teacher_data.groupby('day_of_week').size()
                max_per_day = day_counts.max() if not day_counts.empty else 1

                if max_per_day > 3:  # Если больше 3 пар в день
                    # Перераспределяем
                    for day, count in day_counts.items():
                        if count > 3:
                            # Переносим часть занятий на другие дни
                            n_to_move = count - 3
                            # В демо-версии просто логируем
                            print(f"     Преподаватель {teacher}: нужно перенести {n_to_move} занятий")

        return distributed

    def run(self, base_data, teachers_df, classrooms_df, priority='balanced', distribute=True):
        """
        Запуск жадного алгоритма
        """
        print(f"🔄 Запуск жадного алгоритма:")
        print(f"   Приоритет: {priority}")
        print(f"   Равномерное распределение: {distribute}")

        if base_data.empty:
            print("   Нет данных для построения")
            return base_data

        # Построение по приоритетам
        result = self.schedule_by_priority(base_data, teachers_df, classrooms_df, priority)

        # Равномерное распределение
        if distribute:
            result = self.distribute_evenly(result)

        # Расчет fitness
        fitness_result = self.fitness_calculator.calculate_fitness(result, teachers_df, classrooms_df)

        print(f"✅ Жадный алгоритм завершен")
        print(f"   Fitness: {fitness_result['fitness']:.4f}")
        print(f"   Штраф: {fitness_result['total_penalty']:.2f}")

        return result