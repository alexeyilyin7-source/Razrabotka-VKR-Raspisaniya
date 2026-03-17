# modules/schedule_validator.py
import pandas as pd
import numpy as np
from datetime import datetime


class ScheduleValidator:
    """
    Класс для проверки соблюдения ограничений в расписании
    Проверяет как жесткие (обязательные), так и мягкие (желательные) ограничения
    """

    def __init__(self):
        self.hard_constraints_violations = []
        self.soft_constraints_violations = []

    def check_hard_constraints(self, schedule_df, teachers_df, groups_df, classrooms_df):
        """
        Проверка жестких ограничений (должны выполняться всегда)
        Возвращает (is_valid, list_of_violations)
        """
        violations = []

        if schedule_df.empty:
            self.hard_constraints_violations = violations
            return False, violations

        # 1. Преподаватель не может вести два занятия одновременно
        if 'teacher_name' in schedule_df.columns and 'date' in schedule_df.columns:
            # Группировка по преподавателю и дате
            teacher_date_counts = schedule_df.groupby(['teacher_name', 'date']).size()
            conflicts = teacher_date_counts[teacher_date_counts > 1]

            for (teacher, date), count in conflicts.items():
                violations.append({
                    'type': 'teacher_overlap',
                    'teacher': teacher,
                    'date': str(date),
                    'count': int(count),
                    'message': f"Преподаватель {teacher} имеет {count} занятий {date}"
                })

        # 2. Группа не может быть в двух местах одновременно
        if 'group_name' in schedule_df.columns and 'date' in schedule_df.columns:
            group_date_counts = schedule_df.groupby(['group_name', 'date']).size()
            conflicts = group_date_counts[group_date_counts > 1]

            for (group, date), count in conflicts.items():
                violations.append({
                    'type': 'group_overlap',
                    'group': group,
                    'date': str(date),
                    'count': int(count),
                    'message': f"Группа {group} имеет {count} занятий {date}"
                })

        # 3. Аудитория не может использоваться одновременно для разных занятий
        # Упрощенно: в демо-версии нет реального распределения аудиторий

        # 4. Проверка вместимости аудиторий
        if classrooms_df is not None and 'group_name' in schedule_df.columns and groups_df is not None:
            for _, row in schedule_df.iterrows():
                group_name = row.get('group_name')
                if group_name is None:
                    continue

                group_data = groups_df[groups_df['group_name'] == group_name]

                if len(group_data) > 0:
                    student_count = group_data.iloc[0].get('student_count', 30)

                    # В демо-версии считаем, что максимальная вместимость 50
                    if student_count > 50:
                        violations.append({
                            'type': 'capacity',
                            'group': group_name,
                            'students': int(student_count),
                            'message': f"Группа {group_name} ({student_count} чел.) может превышать вместимость"
                        })

        # 5. Проверка максимальной нагрузки преподавателя
        if teachers_df is not None and 'teacher_name' in schedule_df.columns and 'teacher_load' in schedule_df.columns:
            for _, row in schedule_df.iterrows():
                teacher_name = row.get('teacher_name')
                teacher_load = row.get('teacher_load', 0)

                if teacher_name is None:
                    continue

                teacher_data = teachers_df[teachers_df['full_name'] == teacher_name]

                if len(teacher_data) > 0:
                    max_load = teacher_data.iloc[0].get('max_hours_per_day', 4)

                    if teacher_load > max_load:
                        violations.append({
                            'type': 'teacher_overload',
                            'teacher': teacher_name,
                            'load': float(teacher_load),
                            'max': int(max_load),
                            'message': f"Преподаватель {teacher_name}: нагрузка {teacher_load} > {max_load}"
                        })

        self.hard_constraints_violations = violations
        is_valid = len(violations) == 0

        return is_valid, violations

    def check_soft_constraints(self, schedule_df, teachers_df):
        """
        Проверка мягких ограничений (желательные, но не обязательные)
        Возвращает список нарушений с весами
        """
        violations = []

        if schedule_df.empty:
            self.soft_constraints_violations = violations
            return violations

        # 1. Проверка пожеланий преподавателей
        if teachers_df is not None and 'teacher_name' in schedule_df.columns:
            for _, row in schedule_df.iterrows():
                teacher_name = row.get('teacher_name')
                if teacher_name is None:
                    continue

                teacher_data = teachers_df[teachers_df['full_name'] == teacher_name]

                if len(teacher_data) > 0:
                    teacher = teacher_data.iloc[0]
                    preferences = teacher.get('preferences', '{}')

                    # Проверка JSON-поля
                    if pd.notna(preferences) and preferences != '{}' and preferences != '':
                        try:
                            import json
                            pref_dict = json.loads(preferences) if isinstance(preferences, str) else preferences

                            # Проверка нежелательных дней
                            if 'avoid_days' in pref_dict:
                                date = row.get('date')
                                if date is not None:
                                    day_of_week = pd.to_datetime(date).dayofweek
                                    if day_of_week in pref_dict['avoid_days']:
                                        violations.append({
                                            'type': 'preference_day',
                                            'teacher': teacher_name,
                                            'weight': 0.7,
                                            'message': f"Нарушено пожелание преподавателя {teacher_name} по дню недели"
                                        })

                            # Проверка предпочтительного времени
                            if 'preferred_start' in pref_dict and 'preferred_end' in pref_dict:
                                # Упрощенная проверка
                                pass

                        except:
                            pass

        # 2. Проверка на "окна" в расписании
        if 'teacher_name' in schedule_df.columns and 'date' in schedule_df.columns:
            for teacher in schedule_df['teacher_name'].unique():
                teacher_schedule = schedule_df[schedule_df['teacher_name'] == teacher]

                for date in teacher_schedule['date'].unique():
                    day_classes = teacher_schedule[teacher_schedule['date'] == date]

                    if len(day_classes) > 1 and 'teacher_load' in day_classes.columns:
                        # Сортируем по нагрузке (время начала)
                        sorted_classes = day_classes.sort_values('teacher_load')

                        # Ищем окна (разрывы между занятиями)
                        prev_end = 0
                        windows_count = 0

                        for _, class_row in sorted_classes.iterrows():
                            start_time = class_row.get('teacher_load', 0)
                            # Предполагаем, что занятие длится 1.5 часа
                            end_time = start_time + 1.5

                            if start_time > prev_end + 0.1:  # Если есть разрыв
                                windows_count += 1

                            prev_end = end_time

                        if windows_count > 0:
                            violations.append({
                                'type': 'windows',
                                'teacher': teacher,
                                'date': str(date),
                                'weight': 0.3 * windows_count,
                                'message': f"У преподавателя {teacher} {windows_count} окон {date}"
                            })

        # 3. Неравномерное распределение нагрузки
        if 'teacher_name' in schedule_df.columns:
            for teacher in schedule_df['teacher_name'].unique():
                teacher_schedule = schedule_df[schedule_df['teacher_name'] == teacher]

                if len(teacher_schedule) > 1 and 'teacher_load' in teacher_schedule.columns:
                    daily_load = teacher_schedule.groupby('date')['teacher_load'].sum()

                    if len(daily_load) > 1:
                        std_dev = daily_load.std()

                        if std_dev > 2.0:  # Если стандартное отклонение больше 2 часов
                            violations.append({
                                'type': 'load_imbalance',
                                'teacher': teacher,
                                'weight': 0.2 * std_dev,
                                'message': f"Неравномерная нагрузка преподавателя {teacher}"
                            })

        self.soft_constraints_violations = violations
        return violations

    def get_validation_report(self):
        """
        Получение отчета по валидации
        """
        report = {
            'hard_constraints': {
                'count': len(self.hard_constraints_violations),
                'violations': self.hard_constraints_violations
            },
            'soft_constraints': {
                'count': len(self.soft_constraints_violations),
                'violations': self.soft_constraints_violations
            }
        }

        # Добавляем общую оценку
        total_violations = len(self.hard_constraints_violations) + len(self.soft_constraints_violations)

        if total_violations == 0:
            quality = "Отлично"
        elif total_violations < 5:
            quality = "Хорошо"
        elif total_violations < 10:
            quality = "Удовлетворительно"
        else:
            quality = "Требует улучшения"

        report['quality'] = quality
        report['total_violations'] = total_violations

        return report