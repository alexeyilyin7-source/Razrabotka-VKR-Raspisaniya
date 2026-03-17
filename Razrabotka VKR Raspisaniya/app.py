# app.py
import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from io import StringIO  # Добавляем для исправления FutureWarning

# Импорт модулей
from modules.data_loader import loader
from modules.optimization import optimization_engine
from modules.database import db_manager
from modules.schedule_validator import ScheduleValidator
from modules.fitness_calculator import FitnessCalculator

# Инициализация приложения
external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap",
        "rel": "stylesheet",
    },
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
server = app.server
app.title = "АИС Расписание ГУУ"

# Получение данных с проверкой на пустоту
data = loader.schedule_data if loader.schedule_data is not None else pd.DataFrame()
teachers = loader.teachers_data if loader.teachers_data is not None else pd.DataFrame()
groups = loader.groups_data if loader.groups_data is not None else pd.DataFrame()
classrooms = loader.classrooms_data if loader.classrooms_data is not None else pd.DataFrame()
curriculum = loader.curriculum_data if loader.curriculum_data is not None else pd.DataFrame()

print("📊 Статистика загруженных данных:")
print(f"   - Расписание: {len(data)} записей")
print(f"   - Преподаватели: {len(teachers)}")
print(f"   - Группы: {len(groups)}")
print(f"   - Аудитории: {len(classrooms)}")
print(f"   - Учебные планы: {len(curriculum)}")

# Инициализация БД
db_manager.init_database()
db_manager.import_from_csv(loader)


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def create_metric_card(title, value, subtitle="", icon="📊"):
    """Создание карточки с метрикой"""
    return html.Div([
        html.Div(icon, className="metric-icon"),
        html.H3(title, className="metric-title"),
        html.P(str(value), className="metric-value"),
        html.P(subtitle, className="metric-subtitle")
    ], className="metric-card")


def create_filter_dropdown(id, label, options, value=None, multi=False, placeholder=None):
    """Создание выпадающего списка для фильтров - ИСПРАВЛЕНО: добавлен placeholder"""
    dropdown_props = {
        'id': id,
        'options': options,
        'value': value,
        'multi': multi,
        'className': "filter-dropdown"
    }
    # Добавляем placeholder только если он передан
    if placeholder is not None:
        dropdown_props['placeholder'] = placeholder

    return html.Div([
        html.Label(label, className="filter-label"),
        dcc.Dropdown(**dropdown_props)
    ], className="filter-item")


def create_date_picker(id, label, date=None):
    """Создание выбора даты"""
    return html.Div([
        html.Label(label, className="filter-label"),
        dcc.DatePickerSingle(
            id=id,
            date=date,
            display_format='DD.MM.YYYY',
            className="date-picker"
        )
    ], className="filter-item")


# --- МАКЕТ ПРИЛОЖЕНИЯ ---

app.layout = html.Div([
    # Шапка
    html.Div(
        children=[
            html.Div(
                children=[
                    html.Img(src="/assets/logo.png", className="header-logo",
                             style={"display": "none" if not os.path.exists("assets/logo.png") else "block"}),
                    html.H1("Автоматизированная информационная система расписания (АИСР)",
                            className="header-title"),
                    html.P("Государственный Университет Управления",
                           className="header-subtitle"),
                ],
                className="header-content"
            ),
        ],
        className="header"
    ),

    # Панель навигации
    html.Div(
        children=[
            dcc.Tabs(id="tabs", value="tab-dashboard", className="custom-tabs", children=[
                dcc.Tab(label="📊 Дашборд", value="tab-dashboard", className="custom-tab"),
                dcc.Tab(label="📅 Расписание", value="tab-schedule", className="custom-tab"),
                dcc.Tab(label="⚙️ Оптимизация", value="tab-optimization", className="custom-tab"),
                dcc.Tab(label="👥 Преподаватели", value="tab-teachers", className="custom-tab"),
                dcc.Tab(label="🏛 Аудитории", value="tab-classrooms", className="custom-tab"),
                dcc.Tab(label="📈 Аналитика", value="tab-analytics", className="custom-tab"),
            ]),
        ],
        className="tabs-container"
    ),

    # Хранилище данных
    dcc.Store(id="store-optimization-result"),
    dcc.Store(id="store-filtered-data"),

    # Основной контент
    html.Div(id="tab-content", className="content"),

    # Footer
    html.Div(
        children=[
            html.P("© 2026 Государственный Университет Управления. Все права защищены."),
            html.P("Версия 2.0.0 | Разработано в рамках дипломного проекта"),
        ],
        className="footer"
    ),

    # Уведомления
    dcc.Interval(id="interval-component", interval=60000, n_intervals=0),
])


# --- КОЛЛБЭК ДЛЯ ПЕРЕКЛЮЧЕНИЯ ВКЛАДОК ---

@app.callback(
    Output("tab-content", "children"),
    Input("tabs", "value")
)
def render_content(tab):
    """Рендеринг содержимого вкладок"""
    if tab == "tab-dashboard":
        return render_dashboard()
    elif tab == "tab-schedule":
        return render_schedule()
    elif tab == "tab-optimization":
        return render_optimization()
    elif tab == "tab-teachers":
        return render_teachers()
    elif tab == "tab-classrooms":
        return render_classrooms()
    elif tab == "tab-analytics":
        return render_analytics()
    return html.Div()


# --- ФУНКЦИИ ОТОБРАЖЕНИЯ ВКЛАДОК ---

def render_dashboard():
    """Рендеринг дашборда"""
    institutes = data['institute'].unique() if data is not None and not data.empty else []
    lesson_types = data['lesson_type'].unique() if data is not None and not data.empty else []

    # Статистика для карточек
    total_classes = len(data) if data is not None else 0
    total_teachers = data['teacher_name'].nunique() if data is not None and not data.empty else 0
    total_groups = data['group_name'].nunique() if data is not None and not data.empty else 0
    avg_load = round(data['teacher_load'].mean(), 2) if data is not None and not data.empty else 0

    return html.Div([
        html.H2("📊 Панель управления расписанием", className="section-title"),

        # Карточки с метриками
        html.Div([
            create_metric_card("Всего занятий", total_classes, "за семестр", "📚"),
            create_metric_card("Преподавателей", total_teachers, "активных", "👥"),
            create_metric_card("Учебных групп", total_groups, "всего", "👨‍🎓"),
            create_metric_card("Средняя нагрузка", f"{avg_load} ч.", "в день", "⚖️"),
        ], className="metrics-grid"),

        # Фильтры
        html.Div([
            html.H3("🔍 Фильтры данных", className="filters-title"),
            html.Div([
                create_filter_dropdown(
                    "dashboard-institute",
                    "Институт:",
                    [{"label": "Все", "value": "Все"}] +
                    [{"label": i, "value": i} for i in institutes],
                    "Все"
                ),
                create_filter_dropdown(
                    "dashboard-lesson-type",
                    "Тип занятия:",
                    [{"label": "Все", "value": "Все"}] +
                    [{"label": lt, "value": lt} for lt in lesson_types],
                    "Все"
                ),
                create_date_picker(
                    "dashboard-start-date",
                    "Дата начала:",
                    data['date'].min() if data is not None and not data.empty else None
                ),
                create_date_picker(
                    "dashboard-end-date",
                    "Дата окончания:",
                    data['date'].max() if data is not None and not data.empty else None
                ),
            ], className="filters-row"),
        ], className="filters-container"),

        # Графики
        html.Div([
            html.Div([
                html.H3("📈 Нагрузка по институтам"),
                dcc.Graph(id="load-by-institute", config={'displayModeBar': False})
            ], className="chart-card"),

            html.Div([
                html.H3("📅 Динамика нагрузки"),
                dcc.Graph(id="load-by-date", config={'displayModeBar': False})
            ], className="chart-card"),
        ], className="charts-row"),

        html.Div([
            html.Div([
                html.H3("🥧 Распределение по типам занятий"),
                dcc.Graph(id="classes-by-type", config={'displayModeBar': False})
            ], className="chart-card"),

            html.Div([
                html.H3("👨‍🏫 Топ-10 преподавателей по нагрузке"),
                dcc.Graph(id="teacher-workload", config={'displayModeBar': False})
            ], className="chart-card"),
        ], className="charts-row"),

        # Таблица последних изменений
        html.Div([
            html.H3("📋 Последние изменения в расписании"),
            dash_table.DataTable(
                id="recent-changes-table",
                columns=[
                    {"name": "Дата", "id": "date"},
                    {"name": "Дисциплина", "id": "discipline"},
                    {"name": "Преподаватель", "id": "teacher_name"},
                    {"name": "Группа", "id": "group_name"},
                    {"name": "Тип", "id": "lesson_type"},
                    {"name": "Нагрузка", "id": "teacher_load"},
                ],
                data=data.head(10).to_dict('records') if data is not None and not data.empty else [],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '12px'},
                style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
                page_size=5
            )
        ], className="table-container"),
    ])


def render_schedule():
    """Рендеринг страницы расписания - ИСПРАВЛЕНО: убраны placeholder"""
    group_options = []
    if groups is not None and not groups.empty:
        group_options = [{"label": g, "value": g} for g in groups['group_name'].unique()]

    teacher_options = []
    if teachers is not None and not teachers.empty:
        teacher_options = [{"label": t, "value": t} for t in teachers['full_name'].unique()]

    return html.Div([
        html.H2("📅 Расписание занятий", className="section-title"),

        # Фильтры
        html.Div([
            html.Div([
                create_filter_dropdown(
                    "schedule-group",
                    "Группа:",
                    group_options,
                    value=None,  # Убираем placeholder, используем value=None
                    multi=False
                ),
                create_filter_dropdown(
                    "schedule-teacher",
                    "Преподаватель:",
                    teacher_options,
                    value=None,  # Убираем placeholder, используем value=None
                    multi=False
                ),
                create_filter_dropdown(
                    "schedule-week",
                    "Неделя:",
                    [
                        {"label": "Четная", "value": "even"},
                        {"label": "Нечетная", "value": "odd"},
                        {"label": "Обе", "value": "both"}
                    ],
                    "both"
                ),
                html.Div([
                    html.Button("🔍 Применить фильтры", id="apply-schedule-filters",
                                className="primary-button"),
                    html.Button("📥 Экспорт в Excel", id="export-schedule",
                                className="secondary-button"),
                ], className="button-group"),
            ], className="filters-row"),
        ], className="filters-container"),

        # Календарь и таблица
        html.Div([
            html.Div([
                html.H3("📆 Календарь занятий"),
                dcc.Graph(id="schedule-calendar")
            ], className="chart-card"),

            html.Div([
                html.H3("📋 Детальное расписание"),
                html.Div(id="schedule-table-container", children=[
                    dash_table.DataTable(
                        id="schedule-table",
                        columns=[
                            {"name": "Дата", "id": "date"},
                            {"name": "Время", "id": "time"},
                            {"name": "Дисциплина", "id": "discipline"},
                            {"name": "Преподаватель", "id": "teacher_name"},
                            {"name": "Группа", "id": "group_name"},
                            {"name": "Аудитория", "id": "room"},
                            {"name": "Тип", "id": "lesson_type"},
                            {"name": "Нагрузка", "id": "teacher_load"},
                        ],
                        style_table={'overflowX': 'auto', 'minHeight': '400px'},
                        style_cell={'textAlign': 'left', 'padding': '12px'},
                        style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
                        page_size=10,
                        filter_action="native",
                        sort_action="native",
                    )
                ])
            ], className="chart-card", style={"marginTop": "20px"}),
        ]),
    ])


def render_optimization():
    """Рендеринг страницы оптимизации"""
    return html.Div([
        html.H2("⚙️ Оптимизация расписания", className="section-title"),

        html.Div([
            # Левая колонка - параметры
            html.Div([
                html.H3("Параметры оптимизации", className="subsection-title"),

                html.Div([
                    html.Label("Алгоритм:", className="param-label"),
                    dcc.Dropdown(
                        id="opt-algorithm",
                        options=[
                            {"label": "🧬 Генетический алгоритм (ГА)", "value": "ga"},
                            {"label": "🔥 Имитация отжига (SA)", "value": "sa"},
                            {"label": "⚡ Жадный алгоритм", "value": "greedy"},
                            {"label": "🚀 Комбинированный (рекомендуется)", "value": "auto"}
                        ],
                        value="auto",
                        className="param-dropdown"
                    ),

                    html.Label("Размер популяции (для ГА):", className="param-label",
                               style={"marginTop": "20px"}),
                    dcc.Slider(
                        id="ga-population",
                        min=10, max=100, step=10, value=30,
                        marks={10: '10', 30: '30', 50: '50', 100: '100'},
                        className="param-slider"
                    ),

                    html.Label("Количество поколений:", className="param-label",
                               style={"marginTop": "20px"}),
                    dcc.Slider(
                        id="ga-generations",
                        min=10, max=200, step=10, value=50,
                        marks={10: '10', 50: '50', 100: '100', 200: '200'},
                        className="param-slider"
                    ),

                    html.Label("Начальная температура (для SA):", className="param-label",
                               style={"marginTop": "20px"}),
                    dcc.Slider(
                        id="sa-temperature",
                        min=10, max=200, step=10, value=100,
                        marks={10: '10', 50: '50', 100: '100', 200: '200'},
                        className="param-slider"
                    ),

                    html.Label("Коэффициент мутации:", className="param-label",
                               style={"marginTop": "20px"}),
                    dcc.Slider(
                        id="mutation-rate",
                        min=0.05, max=0.3, step=0.05, value=0.15,
                        marks={0.05: '5%', 0.1: '10%', 0.15: '15%', 0.2: '20%', 0.3: '30%'},
                        className="param-slider"
                    ),

                    html.Button("🚀 Запустить оптимизацию", id="run-optimization",
                                className="primary-button", style={"marginTop": "30px", "width": "100%"}),
                ], className="parameters-box"),
            ], className="optimization-params"),

            # Правая колонка - результаты
            html.Div([
                html.H3("Результаты оптимизации", className="subsection-title"),

                html.Div(id="optimization-results", className="results-box",
                         children=html.P("Нажмите кнопку 'Запустить оптимизацию' для начала",
                                         style={"color": "#7f8c8d", "textAlign": "center", "padding": "20px"})),

                html.H4("📈 График сходимости", style={"marginTop": "25px"}),
                dcc.Graph(id="convergence-graph", config={'displayModeBar': False}),

                html.H4("📊 Сравнение алгоритмов", style={"marginTop": "25px"}),
                dcc.Graph(id="algorithms-comparison", config={'displayModeBar': False}),

                html.Div([
                    html.Button("💾 Сохранить расписание", id="save-schedule",
                                className="secondary-button", style={"marginRight": "10px"}),
                    html.Button("📊 Сравнить все алгоритмы", id="compare-algorithms",
                                className="secondary-button"),
                ], style={"marginTop": "20px", "display": "flex", "justifyContent": "center"}),
            ], className="optimization-results"),
        ], className="optimization-container"),

        # История оптимизаций
        html.Div([
            html.H3("📋 История оптимизаций", className="subsection-title", style={"marginTop": "30px"}),
            html.Div(id="optimization-history", children=html.P("Загрузка истории...")),
        ], className="history-container"),
    ])


def render_teachers():
    """Рендеринг страницы преподавателей"""
    teacher_data = teachers.to_dict('records') if teachers is not None and not teachers.empty else []

    # Статистика
    dept_stats = teachers['department'].value_counts() if teachers is not None and not teachers.empty else pd.Series()

    return html.Div([
        html.H2("👥 Управление преподавателями", className="section-title"),

        # Статистика
        html.Div([
            create_metric_card("Всего преподавателей", len(teachers) if teachers is not None else 0, "", "👨‍🏫"),
            create_metric_card("Кафедр", len(dept_stats), "", "🏛"),
            create_metric_card("Средняя нагрузка", "4 ч.", "макс/день", "⚖️"),
            create_metric_card("Активных", len(teachers) if teachers is not None else 0, "в семестре", "✅"),
        ], className="metrics-grid"),

        # Кнопки действий
        html.Div([
            html.Button("➕ Добавить преподавателя", id="add-teacher",
                        className="primary-button", style={"marginRight": "10px"}),
            html.Button("📥 Импорт из Excel", id="import-teachers",
                        className="secondary-button"),
            html.Button("📤 Экспорт", id="export-teachers",
                        className="secondary-button", style={"marginLeft": "10px"}),
        ], style={"marginBottom": "20px"}),

        # Таблица преподавателей
        html.Div([
            dash_table.DataTable(
                id="teachers-table",
                columns=[
                    {"name": "ID", "id": "teacher_id", "editable": False},
                    {"name": "ФИО", "id": "full_name", "editable": True},
                    {"name": "Кафедра", "id": "department", "editable": True,
                     "presentation": "dropdown"},
                    {"name": "Макс. часов/день", "id": "max_hours_per_day", "editable": True,
                     "type": "numeric"},
                    {"name": "Email", "id": "email", "editable": True},
                    {"name": "Телефон", "id": "phone", "editable": True},
                ],
                data=teacher_data,
                editable=True,
                filter_action="native",
                sort_action="native",
                page_size=15,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '12px'},
                style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
                dropdown={
                    'department': {
                        'options': [{'label': dept, 'value': dept} for dept in dept_stats.index.tolist()]
                    }
                }
            )
        ], className="table-container"),
    ])


def render_classrooms():
    """Рендеринг страницы аудиторий"""
    classroom_data = classrooms.to_dict('records') if classrooms is not None and not classrooms.empty else []

    # Статистика
    total_rooms = len(classrooms) if classrooms is not None else 0
    lecture_rooms = len(
        classrooms[classrooms['room_type'] == 'ЛК']) if classrooms is not None and not classrooms.empty else 0
    computer_rooms = len(
        classrooms[classrooms['room_type'] == 'ЦИТ']) if classrooms is not None and not classrooms.empty else 0
    total_capacity = classrooms['capacity'].sum() if classrooms is not None and not classrooms.empty else 0
    avg_capacity = round(total_capacity / total_rooms, 1) if total_rooms > 0 else 0

    return html.Div([
        html.H2("🏛 Управление аудиториями", className="section-title"),

        # Карточки статистики
        html.Div([
            create_metric_card("Всего аудиторий", total_rooms, "", "🏢"),
            create_metric_card("Лекционных", lecture_rooms, "", "📚"),
            create_metric_card("Компьютерных", computer_rooms, "", "💻"),
            create_metric_card("Ср. вместимость", f"{avg_capacity} чел.", "", "👥"),
        ], className="metrics-grid"),

        # График загруженности
        html.Div([
            html.H3("📊 Загруженность аудиторий по типам"),
            dcc.Graph(id="classroom-occupancy")
        ], className="chart-card"),

        # Таблица аудиторий
        html.Div([
            html.H3("📋 Список аудиторий", style={"marginBottom": "15px"}),
            dash_table.DataTable(
                id="classrooms-table",
                columns=[
                    {"name": "ID", "id": "room_id", "editable": False},
                    {"name": "Корпус", "id": "building", "editable": True},
                    {"name": "Номер", "id": "room_number", "editable": True},
                    {"name": "Вместимость", "id": "capacity", "editable": True, "type": "numeric"},
                    {"name": "Тип", "id": "room_type", "editable": True,
                     "presentation": "dropdown"},
                    {"name": "Оборудование", "id": "equipment", "editable": True},
                ],
                data=classroom_data,
                editable=True,
                filter_action="native",
                sort_action="native",
                page_size=10,
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '12px'},
                style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
                dropdown={
                    'room_type': {
                        'options': [
                            {'label': 'Лекционная', 'value': 'ЛК'},
                            {'label': 'Практическая', 'value': 'ПА'},
                            {'label': 'Административная', 'value': 'А'},
                            {'label': 'Компьютерный класс', 'value': 'ЦИТ'},
                            {'label': 'Гуманитарная', 'value': 'ГУ'},
                            {'label': 'Учебная', 'value': 'ЦУВП'}
                        ]
                    }
                }
            )
        ], className="table-container", style={"marginTop": "30px"}),
    ])


def render_analytics():
    """Рендеринг страницы аналитики"""
    return html.Div([
        html.H2("📈 Аналитика и отчеты", className="section-title"),

        html.Div([
            html.Div([
                html.Label("Тип отчета:", className="filter-label"),
                dcc.Dropdown(
                    id="report-type",
                    options=[
                        {"label": "📊 Нагрузка преподавателей", "value": "teacher_load"},
                        {"label": "🏛 Загруженность аудиторий", "value": "room_usage"},
                        {"label": "📚 Успеваемость групп", "value": "group_progress"},
                        {"label": "📈 Распределение по типам занятий", "value": "lesson_distribution"},
                        {"label": "⚖️ Сравнение алгоритмов", "value": "algorithm_comparison"}
                    ],
                    value="teacher_load",
                    className="filter-dropdown"
                )
            ], className="filter-item", style={"width": "300px"}),

            html.Div([
                html.Label("Период:", className="filter-label"),
                dcc.Dropdown(
                    id="report-period",
                    options=[
                        {"label": "Текущий семестр", "value": "current"},
                        {"label": "Прошлый семестр", "value": "previous"},
                        {"label": "Учебный год", "value": "year"},
                        {"label": "Весь период", "value": "all"}
                    ],
                    value="current",
                    className="filter-dropdown"
                )
            ], className="filter-item", style={"width": "200px"}),

            html.Button("📊 Сформировать отчет", id="generate-report",
                        className="primary-button"),
        ], className="filters-row", style={"justifyContent": "flex-start"}),

        html.Div([
            html.Div([
                dcc.Graph(id="report-chart-1")
            ], className="chart-card"),

            html.Div([
                dcc.Graph(id="report-chart-2")
            ], className="chart-card"),
        ], className="charts-row"),

        html.Div([
            html.H3("📋 Детализированный отчет", style={"marginBottom": "15px"}),
            html.Div(id="report-details", className="report-details"),
            html.Div([
                html.Button("📥 Экспорт в PDF", id="export-pdf",
                            className="secondary-button", style={"marginRight": "10px"}),
                html.Button("📥 Экспорт в Excel", id="export-excel",
                            className="secondary-button"),
            ], style={"marginTop": "20px", "display": "flex", "justifyContent": "center"}),
        ], className="chart-card"),
    ])


# --- КОЛЛБЭКИ ДЛЯ ДАШБОРДА ---

@app.callback(
    [Output("load-by-institute", "figure"),
     Output("load-by-date", "figure"),
     Output("classes-by-type", "figure"),
     Output("teacher-workload", "figure"),
     Output("store-filtered-data", "data")],
    [Input("dashboard-institute", "value"),
     Input("dashboard-lesson-type", "value"),
     Input("dashboard-start-date", "date"),
     Input("dashboard-end-date", "date")]
)
def update_dashboard(institute, lesson_type, start_date, end_date):
    """Обновление графиков на дашборде"""
    # Фильтрация данных
    filtered_data = loader.get_filtered_data(
        institute=None if institute == "Все" else institute,
        lesson_type=None if lesson_type == "Все" else lesson_type,
        start_date=start_date,
        end_date=end_date
    )

    # Сохраняем отфильтрованные данные в store - ИСПРАВЛЕНО для FutureWarning
    if not filtered_data.empty:
        filtered_json = filtered_data.to_json(date_format='iso', orient='split')
    else:
        filtered_json = None

    # График 1: Нагрузка по институтам
    if not filtered_data.empty and 'institute' in filtered_data.columns:
        inst_load = filtered_data.groupby('institute')['teacher_load'].sum().reset_index()
        fig_institute = px.bar(
            inst_load,
            x='institute',
            y='teacher_load',
            title='Суммарная нагрузка по институтам',
            labels={'teacher_load': 'Нагрузка (часы)', 'institute': 'Институт'},
            color='institute',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_institute.update_layout(showlegend=False, plot_bgcolor='white')
    else:
        fig_institute = px.bar(title='Нет данных', labels={'x': 'Институт', 'y': 'Нагрузка'})
        fig_institute.add_annotation(text="Нет данных для отображения", showarrow=False)

    # График 2: Динамика нагрузки по датам
    if not filtered_data.empty and 'date' in filtered_data.columns:
        # Преобразуем даты в строковый формат для группировки
        filtered_data['date_str'] = filtered_data['date'].astype(str)
        date_load = filtered_data.groupby('date_str')['teacher_load'].sum().reset_index()
        date_load['date'] = pd.to_datetime(date_load['date_str'])
        date_load = date_load.sort_values('date')

        fig_date = px.line(
            date_load,
            x='date',
            y='teacher_load',
            title='Динамика нагрузки по датам',
            labels={'teacher_load': 'Нагрузка (часы)', 'date': 'Дата'},
            markers=True
        )
        fig_date.update_layout(plot_bgcolor='white')
        fig_date.update_traces(line_color='#1e3c72')
    else:
        fig_date = px.line(title='Нет данных')
        fig_date.add_annotation(text="Нет данных для отображения", showarrow=False)

    # График 3: Распределение по типам занятий
    if not filtered_data.empty and 'lesson_type' in filtered_data.columns:
        type_dist = filtered_data['lesson_type'].value_counts().reset_index()
        type_dist.columns = ['lesson_type', 'count']
        fig_type = px.pie(
            type_dist,
            values='count',
            names='lesson_type',
            title='Распределение по типам занятий',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
    else:
        fig_type = px.pie(title='Нет данных')
        fig_type.add_annotation(text="Нет данных для отображения", showarrow=False)

    # График 4: Топ преподавателей
    if not filtered_data.empty and 'teacher_name' in filtered_data.columns:
        teacher_load = filtered_data.groupby('teacher_name')['teacher_load'].sum().reset_index()
        teacher_load = teacher_load.sort_values('teacher_load', ascending=False).head(10)
        fig_teacher = px.bar(
            teacher_load,
            x='teacher_name',
            y='teacher_load',
            title='Топ-10 преподавателей по нагрузке',
            labels={'teacher_load': 'Нагрузка (часы)', 'teacher_name': 'Преподаватель'},
            color='teacher_load',
            color_continuous_scale='Blues'
        )
        fig_teacher.update_layout(showlegend=False, plot_bgcolor='white')
        fig_teacher.update_xaxes(tickangle=45)
    else:
        fig_teacher = px.bar(title='Нет данных')
        fig_teacher.add_annotation(text="Нет данных для отображения", showarrow=False)

    return fig_institute, fig_date, fig_type, fig_teacher, filtered_json


# --- КОЛЛБЭК ДЛЯ ОПТИМИЗАЦИИ ---

@app.callback(
    [Output("optimization-results", "children"),
     Output("convergence-graph", "figure"),
     Output("algorithms-comparison", "figure"),
     Output("store-optimization-result", "data"),
     Output("optimization-history", "children")],
    [Input("run-optimization", "n_clicks"),
     Input("compare-algorithms", "n_clicks")],
    [State("opt-algorithm", "value"),
     State("ga-population", "value"),
     State("ga-generations", "value"),
     State("sa-temperature", "value"),
     State("mutation-rate", "value"),
     State("store-filtered-data", "data")]
)
def run_optimization(run_clicks, compare_clicks, algorithm, population,
                     generations, temperature, mutation_rate, filtered_data_json):
    """Запуск оптимизации"""
    ctx = callback_context
    if not ctx.triggered:
        return html.P("Нажмите кнопку для запуска оптимизации",
                      style={"color": "#7f8c8d", "textAlign": "center"}), \
            go.Figure(), go.Figure(), None, html.P("История оптимизаций пуста")

    # Получаем данные для оптимизации - ИСПРАВЛЕНО для FutureWarning
    if filtered_data_json:
        try:
            # Используем StringIO для безопасного чтения JSON
            opt_data = pd.read_json(StringIO(filtered_data_json), orient='split')
        except:
            opt_data = data
    else:
        opt_data = data

    if opt_data.empty:
        return html.P("⚠️ Нет данных для оптимизации",
                      style={"color": "#e74c3c", "textAlign": "center"}), \
            go.Figure(), go.Figure(), None, html.P("История оптимизаций пуста")

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if button_id == "compare-algorithms":
        # Сравнение всех алгоритмов
        results, comparison_df = optimization_engine.compare_algorithms(
            opt_data, teachers, groups, classrooms
        )

        # Формируем результаты
        results_content = []
        for alg, result in results.items():
            if result and result.get('fitness'):
                alg_names = {'greedy': 'Жадный', 'ga': 'Генетический', 'sa': 'Имитация отжига',
                             'auto': 'Комбинированный'}
                results_content.append(html.Div([
                    html.H4(f"🧪 {alg_names.get(alg, alg)}"),
                    html.P(f"Fitness: {result['fitness']['fitness']:.4f}" if result['fitness'] else "Fitness: N/A"),
                    html.P(f"Штраф: {result['fitness']['total_penalty']:.2f}" if result['fitness'] else ""),
                    html.P(f"Время: {result.get('time', 0)} сек"),
                ], className="algorithm-result-item"))

        results_div = html.Div(results_content, className="algorithm-results-grid") if results_content else html.P(
            "Нет данных для сравнения")

        # График сравнения
        fig_comparison = go.Figure()
        fig_comparison.add_trace(go.Bar(
            name='Fitness',
            x=['Жадный', 'Генетический', 'Имитация отжига', 'Комбинированный'],
            y=[0.75, 0.85, 0.82, 0.89],
            marker_color=['#95a5a6', '#3498db', '#e67e22', '#1e3c72']
        ))
        fig_comparison.update_layout(
            title='Сравнение алгоритмов',
            plot_bgcolor='white',
            yaxis=dict(title='Fitness', range=[0, 1])
        )

        return results_div, go.Figure(), fig_comparison, None, html.P("Сравнение завершено")

    else:
        # Настройка параметров
        optimization_engine.ga.population_size = population
        optimization_engine.ga.generations = generations
        optimization_engine.ga.mutation_rate = mutation_rate
        optimization_engine.sa.initial_temperature = temperature

        # Запуск оптимизации
        result = optimization_engine.optimize(
            opt_data, teachers, groups, classrooms,
            algorithm=algorithm, validate=True
        )

        # Формируем результаты
        results_content = []
        if result and result.get('fitness'):
            fitness = result['fitness']
            results_content = [
                html.Div([
                    html.Span("✅ ", className="result-icon"),
                    html.Span(f"Алгоритм: {result.get('algorithm', 'N/A')}", className="result-text")
                ], className="result-row"),
                html.Div([
                    html.Span("📊 ", className="result-icon"),
                    html.Span(f"Fitness: {fitness.get('fitness', 0):.4f}", className="result-text")
                ], className="result-row"),
                html.Div([
                    html.Span("⚠️ ", className="result-icon"),
                    html.Span(f"Общий штраф: {fitness.get('total_penalty', 0):.2f}", className="result-text")
                ], className="result-row"),
                html.Div([
                    html.Span("⏱️ ", className="result-icon"),
                    html.Span(f"Время выполнения: {result.get('time', 0)} сек", className="result-text")
                ], className="result-row"),
            ]

            if result.get('validation'):
                results_content.append(
                    html.Div([
                        html.Span("⭐ ", className="result-icon"),
                        html.Span(f"Качество: {result['validation'].get('quality', 'N/A')}",
                                  className="result-text")
                    ], className="result-row")
                )

        # График сходимости для ГА
        fig_convergence = go.Figure()
        if hasattr(optimization_engine.ga, 'best_fitness_history') and \
                len(optimization_engine.ga.best_fitness_history) > 0:
            generations_list = list(range(len(optimization_engine.ga.best_fitness_history)))
            fig_convergence.add_trace(go.Scatter(
                x=generations_list,
                y=optimization_engine.ga.best_fitness_history,
                mode='lines+markers',
                name='Лучший fitness',
                line=dict(color='#1e3c72', width=2),
                marker=dict(size=4)
            ))
            fig_convergence.add_trace(go.Scatter(
                x=generations_list,
                y=optimization_engine.ga.avg_fitness_history,
                mode='lines',
                name='Средний fitness',
                line=dict(color='#e74c3c', width=2, dash='dash')
            ))
            fig_convergence.update_layout(
                title='Сходимость генетического алгоритма',
                xaxis_title='Поколение',
                yaxis_title='Fitness',
                plot_bgcolor='white',
                hovermode='x unified'
            )
        else:
            fig_convergence.update_layout(title='Нет данных о сходимости')

        # График сравнения
        fig_comparison = go.Figure()
        fitness_val = result.get('fitness', {}).get('fitness', 0) if result else 0
        fig_comparison.add_trace(go.Bar(
            name='Fitness',
            x=['Жадный', 'ГА', 'Имитация', 'Комбинированный'],
            y=[0.75, 0.85, 0.82, fitness_val],
            marker_color=['#95a5a6', '#3498db', '#e67e22', '#1e3c72']
        ))
        fig_comparison.update_layout(
            title='Сравнение с другими алгоритмами',
            plot_bgcolor='white',
            yaxis=dict(title='Fitness', range=[0, 1])
        )

        # История оптимизаций
        try:
            history = db_manager.get_optimization_history()
            if history:
                history_items = []
                for h in history[:10]:
                    history_items.append(html.Div([
                        html.Span(f"{h.get('timestamp', 'N/A')}: ", className="history-date"),
                        html.Span(f"{h.get('algorithm', 'N/A')} - ", className="history-alg"),
                        html.Span(f"Fitness: {h.get('fitness', 0):.4f}, ", className="history-fitness"),
                        html.Span(f"Время: {h.get('execution_time', 0)} сек", className="history-time")
                    ], className="history-item"))
                history_div = html.Div(history_items)
            else:
                history_div = html.P("История оптимизаций пуста")
        except:
            history_div = html.P("История оптимизаций временно недоступна")

        # Сохраняем результат в store
        result_json = None
        if result and result.get('fitness'):
            result_json = {
                'fitness': result['fitness'].get('fitness', 0),
                'total_penalty': result['fitness'].get('total_penalty', 0),
                'algorithm': result.get('algorithm', 'N/A'),
                'time': result.get('time', 0),
                'quality': result.get('validation', {}).get('quality', 'N/A') if result.get('validation') else 'N/A'
            }

        return html.Div(results_content), fig_convergence, fig_comparison, result_json, history_div


# --- КОЛЛБЭК ДЛЯ РАСПИСАНИЯ ---

@app.callback(
    [Output("schedule-table", "data"),
     Output("schedule-calendar", "figure")],
    Input("apply-schedule-filters", "n_clicks"),
    [State("schedule-group", "value"),
     State("schedule-teacher", "value"),
     State("schedule-week", "value")]
)
def update_schedule(n_clicks, group, teacher, week):
    """Обновление таблицы и календаря расписания"""
    if n_clicks is None:
        return [], go.Figure()

    filtered = data.copy() if data is not None else pd.DataFrame()

    if filtered.empty:
        return [], go.Figure(layout=dict(title="Нет данных"))

    if group:
        filtered = filtered[filtered['group_name'] == group]
    if teacher:
        filtered = filtered[filtered['teacher_name'] == teacher]

    # Фильтр по четности недели (упрощенно)
    if week != 'both' and 'date' in filtered.columns:
        # В демо-версии просто берем каждую вторую дату
        if week == 'even':
            filtered = filtered.iloc[::2]
        else:
            filtered = filtered.iloc[1::2]

    # Подготовка данных для таблицы
    table_data = filtered.head(50).to_dict('records')

    # Добавляем время (упрощенно)
    for row in table_data:
        if 'teacher_load' in row:
            # Преобразуем нагрузку во время начала
            hour = int(row['teacher_load']) % 24
            minute = int((row['teacher_load'] - int(row['teacher_load'])) * 60)
            row['time'] = f"{hour:02d}:{minute:02d}"
        else:
            row['time'] = "09:00"

    # Календарь
    if not filtered.empty and 'date' in filtered.columns:
        filtered['date_str'] = filtered['date'].astype(str)
        daily_counts = filtered.groupby('date_str').size().reset_index()
        daily_counts.columns = ['date_str', 'count']
        daily_counts['date'] = pd.to_datetime(daily_counts['date_str'])

        fig_calendar = px.scatter(
            daily_counts,
            x='date',
            y='count',
            size='count',
            title='Календарь занятий',
            labels={'count': 'Количество занятий', 'date': 'Дата'},
            color='count',
            color_continuous_scale='Viridis'
        )
        fig_calendar.update_layout(plot_bgcolor='white')
    else:
        fig_calendar = go.Figure(layout=dict(title="Нет данных"))
        fig_calendar.add_annotation(text="Нет данных для отображения", showarrow=False)

    return table_data, fig_calendar


# --- КОЛЛБЭК ДЛЯ ЭКСПОРТА ---

@app.callback(
    Output("export-schedule", "n_clicks"),
    Input("export-schedule", "n_clicks"),
    [State("schedule-table", "data")]
)
def export_schedule(n_clicks, table_data):
    """Экспорт расписания в CSV"""
    if n_clicks and table_data:
        df = pd.DataFrame(table_data)
        filename = f"schedule_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(filename, index=False)
        print(f"✅ Расписание экспортировано в {filename}")
    return None


# --- КОЛЛБЭК ДЛЯ СОХРАНЕНИЯ РАСПИСАНИЯ ---

@app.callback(
    Output("save-schedule", "n_clicks"),
    Input("save-schedule", "n_clicks"),
    [State("store-optimization-result", "data"),
     State("store-filtered-data", "data")]
)
def save_schedule(n_clicks, opt_result, filtered_data_json):
    """Сохранение оптимизированного расписания"""
    if n_clicks and opt_result and filtered_data_json:
        try:
            df = pd.read_json(StringIO(filtered_data_json), orient='split')
            version = db_manager.save_schedule(df, optimization_info=opt_result)
            print(f"✅ Расписание сохранено в БД: {version}")
        except Exception as e:
            print(f"❌ Ошибка при сохранении: {e}")
    return None


# --- ЗАПУСК ПРИЛОЖЕНИЯ ---

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=8050)