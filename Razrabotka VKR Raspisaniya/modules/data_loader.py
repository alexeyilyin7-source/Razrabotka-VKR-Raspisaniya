# modules/data_loader.py
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta


class DataLoader:
    """Класс для загрузки и валидации всех данных системы"""

    def __init__(self, data_path='data/'):
        self.data_path = data_path
        self.schedule_data = None
        self.teachers_data = None
        self.groups_data = None
        self.classrooms_data = None
        self.curriculum_data = None

        # Создаем папку data если её нет
        if not os.path.exists(data_path):
            os.makedirs(data_path)
            print(f"📁 Создана папка {data_path}")

    def load_all_data(self):
        """Загрузка всех данных из CSV файлов"""
        try:
            # Пробуем загрузить существующие файлы
            self.schedule_data = pd.read_csv(os.path.join(self.data_path, 'schedule_data.csv'))
            self.teachers_data = pd.read_csv(os.path.join(self.data_path, 'teachers.csv'))
            self.groups_data = pd.read_csv(os.path.join(self.data_path, 'groups.csv'))
            self.classrooms_data = pd.read_csv(os.path.join(self.data_path, 'classrooms.csv'))
            self.curriculum_data = pd.read_csv(os.path.join(self.data_path, 'curriculum.csv'))

            # Предобработка данных
            self._preprocess_data()
            print("✅ Все данные успешно загружены из CSV файлов")
            return True

        except FileNotFoundError as e:
            print(f"⚠️ Файлы не найдены. Генерация демонстрационных данных...")
            self._generate_mock_data()
            # Сохраняем сгенерированные данные в CSV для будущих запусков
            self._save_mock_data_to_csv()
            return True

        except Exception as e:
            print(f"❌ Непредвиденная ошибка: {e}")
            print("Генерация демонстрационных данных...")
            self._generate_mock_data()
            return True

    def _preprocess_data(self):
        """Предобработка данных"""
        if self.schedule_data is not None and 'date' in self.schedule_data.columns:
            self.schedule_data['date'] = pd.to_datetime(self.schedule_data['date'])
            self.schedule_data.sort_values('date', inplace=True)

    def _generate_mock_data(self):
        """Генерация демонстрационных данных"""
        print("🔄 Генерация тестовых данных...")

        # Создаем даты для семестра
        start_date = datetime(2025, 9, 1)
        dates = [start_date + timedelta(days=i * 7) for i in range(16)]  # 16 недель

        institutes = ['ИИС', 'ИОМ', 'ИЭФ', 'ИУПСиБК', 'ИМ', 'ИГУиП', 'ИЗО']
        lesson_types = ['Лекция', 'Семинар', 'Лабораторная']

        # Списки для хранения данных
        schedule_data = []
        teachers_list = []
        groups_list = []
        classrooms_list = []
        curriculum_list = []

        # Генерация преподавателей
        teacher_names = [
            "Иванов И.И.", "Петров П.П.", "Сидорова А.А.", "Соколов В.В.", "Козлова Е.Е.",
            "Морозов Д.Д.", "Новикова М.М.", "Волков А.А.", "Павлова О.О.", "Федоров И.И.",
            "Григорьев С.С.", "Дмитриева Т.Т.", "Алексеева Н.Н.", "Васильев В.В.", "Михайлова Е.С.",
            "Андреев А.А.", "Николаева Н.Н.", "Сергеев С.С.", "Александрова А.А.", "Кузнецов К.К."
        ]

        for i, name in enumerate(teacher_names[:15]):  # Берем первых 15
            inst = np.random.choice(institutes)
            teachers_list.append({
                'teacher_id': f"T{i + 1:03d}",
                'full_name': name,
                'department': inst,
                'max_hours_per_day': np.random.choice([3, 4, 6]),
                'email': f"{name.lower().replace(' ', '.')}@guu.ru",
                'phone': f"+7(495){np.random.randint(100, 999)}-{np.random.randint(10, 99)}-{np.random.randint(10, 99)}",
                'preferences': '{}'
            })

        # Генерация групп
        group_names = []
        for inst in institutes:
            for course in range(1, 5):
                for num in range(1, 4):
                    group_name = f"{inst}-{course}{num}"
                    group_names.append(group_name)
                    groups_list.append({
                        'group_id': f"G{len(groups_list) + 1:03d}",
                        'group_name': group_name,
                        'institute': inst,
                        'course': course,
                        'student_count': np.random.randint(15, 35),
                        'level': np.random.choice(['Бакалавр', 'Магистр', 'Аспирант'], p=[0.7, 0.2, 0.1])
                    })

        # Генерация аудиторий
        buildings = ['Главный корпус', 'Административный корпус', 'Лабораторный корпус',
                     'Поточный корпус', 'Учебный корпус', 'Спортивный комплекс', 'Центр информационных технологий']
        room_types = ['ЛК', 'ПА', 'А', 'ЦИТ', 'ГУ', 'ЦУВП']

        for i in range(20):
            classrooms_list.append({
                'room_id': f"R{i + 1:03d}",
                'building': np.random.choice(buildings),
                'room_number': str(100 + i),
                'capacity': np.random.choice([20, 30, 40, 50, 80, 100, 150, 200, 400, 800]),
                'room_type': np.random.choice(room_types),
                'equipment': np.random.choice(['Проектор, доска', 'Компьютеры, проектор', 'Спортивное оборудование',
                                               'Лабораторное оборудование', 'Стандартное оснащение',
                                               'Интерактивная доска'])
            })

        # Генерация данных расписания
        disciplines = [
            "Математический анализ", "Дискретная математика", "Программирование", "Базы данных",
            "Экономика", "Менеджмент", "Финансы", "Бухгалтерский учет", "Статистика",
            "Информационные системы", "Web-технологии", "Алгоритмы", "Компьютерные сети",
            "Операционные системы", "Иностранный язык", "Философия", "История", "Право"
        ]

        for i, date in enumerate(dates[:10]):  # Первые 10 недель
            for j in range(30):  # 30 записей на дату
                inst = np.random.choice(institutes)
                teacher = np.random.choice(teacher_names[:10])
                group = np.random.choice(group_names)
                disc = np.random.choice(disciplines)
                l_type = np.random.choice(lesson_types)

                schedule_data.append({
                    'institute': inst,
                    'lesson_type': l_type,
                    'date': date.strftime('%Y-%m-%d'),
                    'teacher_load': round(np.random.uniform(1.5, 4.5), 1),
                    'total_classes': np.random.randint(5, 20),
                    'teacher_name': teacher,
                    'group_name': group,
                    'discipline': disc
                })

        # Генерация учебных планов
        for i in range(30):
            curriculum_list.append({
                'plan_id': f"P{i + 1:03d}",
                'group_id': np.random.choice(groups_list)['group_id'] if groups_list else f"G001",
                'discipline': np.random.choice(disciplines),
                'teacher_id': np.random.choice(teachers_list)['teacher_id'] if teachers_list else f"T001",
                'hours_per_semester': np.random.choice([36, 72, 108]),
                'semester': np.random.choice(['Осенний-Зимний', 'Весенний']),
                'lesson_type': np.random.choice(lesson_types),
                'weeks_parity': np.random.choice(['Оба', 'Четные', 'Нечетные'])
            })

        # Преобразуем в DataFrame
        self.schedule_data = pd.DataFrame(schedule_data)
        self.teachers_data = pd.DataFrame(teachers_list)
        self.groups_data = pd.DataFrame(groups_list)
        self.classrooms_data = pd.DataFrame(classrooms_list)
        self.curriculum_data = pd.DataFrame(curriculum_list)

        # Предобработка
        self._preprocess_data()

        print(f"✅ Сгенерировано:")
        print(f"   - {len(self.schedule_data)} записей расписания")
        print(f"   - {len(self.teachers_data)} преподавателей")
        print(f"   - {len(self.groups_data)} групп")
        print(f"   - {len(self.classrooms_data)} аудиторий")
        print(f"   - {len(self.curriculum_data)} учебных планов")

    def _save_mock_data_to_csv(self):
        """Сохранение сгенерированных данных в CSV файлы"""
        try:
            self.schedule_data.to_csv(os.path.join(self.data_path, 'schedule_data.csv'), index=False)
            self.teachers_data.to_csv(os.path.join(self.data_path, 'teachers.csv'), index=False)
            self.groups_data.to_csv(os.path.join(self.data_path, 'groups.csv'), index=False)
            self.classrooms_data.to_csv(os.path.join(self.data_path, 'classrooms.csv'), index=False)
            self.curriculum_data.to_csv(os.path.join(self.data_path, 'curriculum.csv'), index=False)
            print(f"💾 Сгенерированные данные сохранены в папку {self.data_path}")
        except Exception as e:
            print(f"⚠️ Не удалось сохранить данные: {e}")

    def get_filtered_data(self, institute=None, lesson_type=None, start_date=None, end_date=None):
        """Получение отфильтрованных данных"""
        if self.schedule_data is None or self.schedule_data.empty:
            return pd.DataFrame()

        data = self.schedule_data.copy()

        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])

        if institute and institute != 'Все':
            data = data[data['institute'] == institute]

        if lesson_type and lesson_type != 'Все':
            data = data[data['lesson_type'] == lesson_type]

        if start_date:
            data = data[data['date'] >= pd.to_datetime(start_date)]

        if end_date:
            data = data[data['date'] <= pd.to_datetime(end_date)]

        return data

    def get_statistics(self):
        """Получение статистики по данным"""
        stats = {
            'total_classes': len(self.schedule_data) if self.schedule_data is not None else 0,
            'total_teachers': len(self.teachers_data) if self.teachers_data is not None else 0,
            'total_groups': len(self.groups_data) if self.groups_data is not None else 0,
            'total_classrooms': len(self.classrooms_data) if self.classrooms_data is not None else 0,
            'total_curriculum': len(self.curriculum_data) if self.curriculum_data is not None else 0,
        }

        if self.schedule_data is not None and not self.schedule_data.empty:
            stats['avg_load'] = round(self.schedule_data['teacher_load'].mean(), 2)
            stats['institutes'] = self.schedule_data['institute'].nunique()
        else:
            stats['avg_load'] = 0
            stats['institutes'] = 0

        return stats


# Глобальный экземпляр для использования в приложении
loader = DataLoader()
loader.load_all_data()