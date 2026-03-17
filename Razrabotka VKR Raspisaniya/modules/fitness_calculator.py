# modules/fitness_calculator.py
import numpy as np
import pandas as pd
from datetime import time


class FitnessCalculator:
    """Класс для расчета fitness-функции расписания"""

    def __init__(self):
        # Веса для мягких ограничений (можно настраивать через интерфейс)
        self.weights = {
            'windows_penalty': 0.35,  # Штраф за окна
            'load_imbalance': 0.25,  # Неравномерность нагрузки
            'preferences_violation': 0.25,  # Нарушение пожеланий
            'room_usage': 0.15  # Использование аудиторий
        }

    def calculate_windows_penalty(self, schedule_df):
        """
        Расчет штрафа за окна в расписании у студентов и преподавателей
        Чем больше окон, тем выше штраф
        """
        if schedule_df.empty or 'teacher_name' not in schedule_df.columns or 'date' not in schedule_df.columns:
            return 0

        total_penalty = 0

        # Анализ окон для преподавателей
        for teacher in schedule_df['teacher_name'].unique():
            teacher_schedule = schedule_df[schedule_df['teacher_name'] == teacher]

            for date in teacher_schedule['date'].unique():
                day_classes = teacher_schedule[teacher_schedule['date'] == date]

                if len(day_classes) > 1:
                    # Сортируем по времени (предполагаем, что время указано в teacher_load)
                    # В реальности здесь должен быть анализ временных слотов
                    # Для демо используем упрощенный подход
                    time_slots = sorted(day_classes['teacher_load'].tolist())

                    # Считаем количество окон (разрывов между парами)
                    windows = 0
                    for i in range(len(time_slots) - 1):
                        # Если разрыв больше 1.5 часов (2 академических часа)
                        if time_slots[i + 1] - time_slots[i] > 1.5:
                            windows += 1

                    # Штраф: 1 за каждое окно + дополнительный штраф за большие разрывы
                    total_penalty += windows * 2

        # Анализ окон для групп (аналогично)
        if 'group_name' in schedule_df.columns:
            for group in schedule_df['group_name'].unique():
                group_schedule = schedule_df[schedule_df['group_name'] == group]

                for date in group_schedule['date'].unique():
                    day_classes = group_schedule[group_schedule['date'] == date]

                    if len(day_classes) > 1:
                        windows = len(day_classes) - 1  # Упрощенно
                        total_penalty += windows

        return total_penalty * self.weights['windows_penalty']

    def calculate_load_imbalance(self, schedule_df):
        """
        Расчет неравномерности нагрузки преподавателей
        Штраф за отклонение от среднего
        """
        if schedule_df.empty or 'teacher_name' not in schedule_df.columns:
            return 0

        total_penalty = 0

        for teacher in schedule_df['teacher_name'].unique():
            teacher_schedule = schedule_df[schedule_df['teacher_name'] == teacher]

            if 'teacher_load' in teacher_schedule.columns:
                # Нагрузка преподавателя в разные дни
                daily_load = teacher_schedule.groupby('date')['teacher_load'].sum()

                if len(daily_load) > 1:
                    # Средняя нагрузка
                    avg_load = daily_load.mean()

                    # Штраф за отклонение от среднего (стандартное отклонение)
                    deviations = (daily_load - avg_load) ** 2
                    penalty = np.sqrt(deviations.mean())
                    total_penalty += penalty

        return total_penalty * self.weights['load_imbalance']

    def calculate_preferences_violation(self, schedule_df, teachers_df):
        """
        Расчет нарушений пожеланий преподавателей
        """
        if schedule_df.empty or teachers_df is None or teachers_df.empty:
            return 0

        total_penalty = 0

        for _, row in schedule_df.iterrows():
            teacher_name = row.get('teacher_name')
            if teacher_name is None:
                continue

            teacher_data = teachers_df[teachers_df['full_name'] == teacher_name]

            if len(teacher_data) > 0:
                teacher = teacher_data.iloc[0]

                # 1. Проверка максимальной дневной нагрузки
                max_hours = teacher.get('max_hours_per_day', 4)
                current_load = row.get('teacher_load', 0)

                if current_load > max_hours:
                    # Штраф за превышение нагрузки
                    overload = current_load - max_hours
                    total_penalty += overload * 3

                # 2. Анализ JSON-поля с пожеланиями
                preferences = teacher.get('preferences', '{}')
                if pd.notna(preferences) and preferences != '{}':
                    try:
                        import json
                        pref_dict = json.loads(preferences) if isinstance(preferences, str) else preferences

                        # Проверка нежелательных дней (если указаны)
                        if 'avoid_days' in pref_dict:
                            day_of_week = pd.to_datetime(row.get('date')).dayofweek
                            # 0 = понедельник, 6 = воскресенье
                            if day_of_week in pref_dict['avoid_days']:
                                total_penalty += 5

                        # Проверка предпочтительного времени
                        if 'preferred_time_start' in pref_dict and 'preferred_time_end' in pref_dict:
                            # Упрощенная проверка
                            pass

                    except:
                        pass

        return total_penalty * self.weights['preferences_violation']

    def calculate_room_usage(self, schedule_df, classrooms_df):
        """
        Расчет эффективности использования аудиторий
        """
        if schedule_df.empty or 'total_classes' not in schedule_df.columns:
            return 0

        total_penalty = 0

        # 1. Штраф за недогрузку аудиторий
        avg_classes = schedule_df['total_classes'].mean() if len(schedule_df) > 0 else 10
        for _, row in schedule_df.iterrows():
            classes = row.get('total_classes', 0)
            if classes < avg_classes * 0.5:  # Меньше половины от среднего
                total_penalty += 2

        # 2. Штраф за несоответствие типа аудитории (упрощенно)
        if 'lesson_type' in schedule_df.columns and classrooms_df is not None:
            # В реальной системе здесь была бы проверка соответствия
            lecture_count = len(schedule_df[schedule_df['lesson_type'] == 'Лекция'])
            if lecture_count > 0 and not classrooms_df.empty:
                # Штраф, если мало лекционных аудиторий
                lecture_rooms = len(classrooms_df[classrooms_df['room_type'] == 'ЛК'])
                if lecture_rooms < lecture_count / 10:  # Упрощенно
                    total_penalty += 5

        # Инвертируем: чем больше занятий, тем меньше штраф
        total_classes = len(schedule_df)
        if total_classes > 0:
            occupancy_bonus = 50 / total_classes
            total_penalty = max(0, total_penalty - occupancy_bonus)

        return total_penalty * self.weights['room_usage']

    def calculate_fitness(self, schedule_df, teachers_df=None, classrooms_df=None):
        """
        Расчет общей fitness-функции
        Формула: F(X) = Σ(wi * Ci) → min
        Возвращает словарь с результатами
        """
        if schedule_df.empty:
            return {
                'total_penalty': 1000.0,
                'fitness': 0.001,
                'components': {
                    'windows': 0,
                    'load': 0,
                    'preferences': 0,
                    'room': 0
                }
            }

        # Расчет компонентов
        windows_penalty = self.calculate_windows_penalty(schedule_df)
        load_penalty = self.calculate_load_imbalance(schedule_df)
        preferences_penalty = self.calculate_preferences_violation(schedule_df, teachers_df)
        room_penalty = self.calculate_room_usage(schedule_df, classrooms_df)

        # Общий штраф
        total_penalty = (windows_penalty + load_penalty +
                         preferences_penalty + room_penalty)

        # Fitness (чем выше, тем лучше особь)
        fitness = 1 / (1 + total_penalty) if total_penalty >= 0 else 0

        return {
            'total_penalty': round(total_penalty, 2),
            'fitness': round(fitness, 4),
            'components': {
                'windows': round(
                    windows_penalty / self.weights['windows_penalty'] if self.weights['windows_penalty'] > 0 else 0, 2),
                'load': round(
                    load_penalty / self.weights['load_imbalance'] if self.weights['load_imbalance'] > 0 else 0, 2),
                'preferences': round(preferences_penalty / self.weights['preferences_violation'] if self.weights[
                                                                                                        'preferences_violation'] > 0 else 0,
                                     2),
                'room': round(room_penalty / self.weights['room_usage'] if self.weights['room_usage'] > 0 else 0, 2)
            }
        }