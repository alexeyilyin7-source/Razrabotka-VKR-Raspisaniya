# modules/database.py
import sqlite3
import pandas as pd
import os
from datetime import datetime
import json


class DatabaseManager:
    """Класс для работы с базой данных (SQLite для прототипа)"""

    def __init__(self, db_path='schedule.db'):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """Подключение к БД"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def disconnect(self):
        """Отключение от БД"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def init_database(self):
        """Инициализация структуры БД"""
        conn = self.connect()
        cursor = conn.cursor()

        # Таблица институтов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS institutes (
                institute_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                abbreviation TEXT
            )
        ''')

        # Таблица кафедр
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS departments (
                department_id TEXT PRIMARY KEY,
                institute_id TEXT,
                name TEXT NOT NULL,
                head_name TEXT,
                FOREIGN KEY (institute_id) REFERENCES institutes(institute_id)
            )
        ''')

        # Таблица преподавателей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teachers (
                teacher_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                department_id TEXT,
                max_hours_per_day INTEGER,
                email TEXT,
                phone TEXT,
                preferences TEXT,
                FOREIGN KEY (department_id) REFERENCES departments(department_id)
            )
        ''')

        # Таблица групп
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id TEXT PRIMARY KEY,
                group_name TEXT NOT NULL,
                institute_id TEXT,
                course INTEGER,
                student_count INTEGER,
                level TEXT,
                FOREIGN KEY (institute_id) REFERENCES institutes(institute_id)
            )
        ''')

        # Таблица дисциплин
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS disciplines (
                discipline_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT
            )
        ''')

        # Таблица аудиторий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classrooms (
                classroom_id TEXT PRIMARY KEY,
                building TEXT,
                room_number TEXT,
                capacity INTEGER,
                room_type TEXT,
                equipment TEXT
            )
        ''')

        # Таблица учебных планов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS curriculum (
                curriculum_id TEXT PRIMARY KEY,
                group_id TEXT,
                discipline_id TEXT,
                teacher_id TEXT,
                hours_per_semester INTEGER,
                semester TEXT,
                lesson_type TEXT,
                weeks_parity TEXT,
                FOREIGN KEY (group_id) REFERENCES groups(group_id),
                FOREIGN KEY (discipline_id) REFERENCES disciplines(discipline_id),
                FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
            )
        ''')

        # Таблица расписания
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule (
                schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                curriculum_id TEXT,
                classroom_id TEXT,
                date DATE,
                time_slot TEXT,
                is_cancelled BOOLEAN DEFAULT 0,
                cancel_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (curriculum_id) REFERENCES curriculum(curriculum_id),
                FOREIGN KEY (classroom_id) REFERENCES classrooms(classroom_id)
            )
        ''')

        # Таблица истории оптимизаций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS optimization_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                algorithm TEXT,
                fitness REAL,
                total_penalty REAL,
                execution_time REAL,
                hard_violations INTEGER,
                soft_violations INTEGER,
                schedule_version TEXT
            )
        ''')

        conn.commit()
        print("✅ База данных инициализирована")

    def import_from_csv(self, data_loader):
        """Импорт данных из CSV в БД"""
        conn = self.connect()

        # Импорт институтов
        if data_loader.schedule_data is not None and 'institute' in data_loader.schedule_data.columns:
            institutes = data_loader.schedule_data['institute'].unique()
            for inst in institutes:
                conn.execute(
                    "INSERT OR IGNORE INTO institutes (institute_id, name) VALUES (?, ?)",
                    (inst, inst)
                )

        # Импорт преподавателей
        if data_loader.teachers_data is not None:
            data_loader.teachers_data.to_sql('teachers', conn, if_exists='replace', index=False)

        # Импорт групп
        if data_loader.groups_data is not None:
            data_loader.groups_data.to_sql('groups', conn, if_exists='replace', index=False)

        # Импорт аудиторий
        if data_loader.classrooms_data is not None:
            data_loader.classrooms_data.to_sql('classrooms', conn, if_exists='replace', index=False)

        # Импорт учебных планов
        if data_loader.curriculum_data is not None:
            data_loader.curriculum_data.to_sql('curriculum', conn, if_exists='replace', index=False)

        conn.commit()
        print("✅ Данные импортированы в БД")

    def save_schedule(self, schedule_df, version_name=None, optimization_info=None):
        """
        Сохранение расписания в БД и CSV
        """
        conn = self.connect()

        if version_name is None:
            version_name = f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Сохраняем как CSV
        csv_path = f"data/{version_name}.csv"
        schedule_df.to_csv(csv_path, index=False)

        # Сохраняем информацию об оптимизации в БД
        if optimization_info:
            conn.execute('''
                INSERT INTO optimization_history 
                (algorithm, fitness, total_penalty, execution_time, hard_violations, soft_violations, schedule_version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                optimization_info.get('algorithm', 'unknown'),
                optimization_info.get('fitness', {}).get('fitness', 0) if optimization_info.get('fitness') else 0,
                optimization_info.get('fitness', {}).get('total_penalty', 0) if optimization_info.get('fitness') else 0,
                optimization_info.get('time', 0),
                optimization_info.get('validation', {}).get('hard_constraints', {}).get('count',
                                                                                        0) if optimization_info.get(
                    'validation') else 0,
                optimization_info.get('validation', {}).get('soft_constraints', {}).get('count',
                                                                                        0) if optimization_info.get(
                    'validation') else 0,
                version_name
            ))
            conn.commit()

        print(f"✅ Расписание сохранено как {version_name}.csv")
        return version_name

    def load_schedule(self, version_name):
        """Загрузка расписания из CSV файла"""
        try:
            file_path = f"data/{version_name}.csv"
            if not version_name.endswith('.csv'):
                file_path = f"data/{version_name}.csv"

            df = pd.read_csv(file_path,
                             parse_dates=['date'] if 'date' in pd.read_csv(file_path, nrows=0).columns else None)
            print(f"✅ Расписание {version_name} загружено")
            return df
        except FileNotFoundError:
            print(f"❌ Файл {version_name}.csv не найден")
            return None
        except Exception as e:
            print(f"❌ Ошибка при загрузке: {e}")
            return None

    def get_optimization_history(self):
        """Получение истории оптимизаций"""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM optimization_history 
            ORDER BY timestamp DESC 
            LIMIT 50
        ''')

        rows = cursor.fetchall()
        history = []

        for row in rows:
            history.append({
                'id': row[0],
                'timestamp': row[1],
                'algorithm': row[2],
                'fitness': row[3],
                'total_penalty': row[4],
                'execution_time': row[5],
                'hard_violations': row[6],
                'soft_violations': row[7],
                'schedule_version': row[8]
            })

        return history

    def get_statistics(self):
        """Получение статистики из БД"""
        conn = self.connect()
        cursor = conn.cursor()

        stats = {}

        # Количество преподавателей
        cursor.execute("SELECT COUNT(*) FROM teachers")
        stats['teachers_count'] = cursor.fetchone()[0]

        # Количество групп
        cursor.execute("SELECT COUNT(*) FROM groups")
        stats['groups_count'] = cursor.fetchone()[0]

        # Количество аудиторий
        cursor.execute("SELECT COUNT(*) FROM classrooms")
        stats['classrooms_count'] = cursor.fetchone()[0]

        # Количество сохраненных расписаний
        cursor.execute("SELECT COUNT(DISTINCT schedule_version) FROM optimization_history")
        stats['saved_schedules'] = cursor.fetchone()[0]

        # Средний fitness
        cursor.execute("SELECT AVG(fitness) FROM optimization_history WHERE fitness > 0")
        avg_fitness = cursor.fetchone()[0]
        stats['avg_fitness'] = round(avg_fitness, 4) if avg_fitness else 0

        return stats


# Глобальный экземпляр
db_manager = DatabaseManager()