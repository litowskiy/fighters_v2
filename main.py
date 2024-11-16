from flask import Flask, redirect, url_for, render_template, request, flash, jsonify, get_flashed_messages, session
import sqlite3
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Используем режим "без графического интерфейса"
import matplotlib.pyplot as plt
import io
import base64
from functools import wraps

#TODO: Переписать всю логику по бойцам в id
#TODO: В БД ОСТАЕТСЯ СКИП ФАЙТЕР ДЛЯ КОРРЕКТНОГО ОТОБРАЖЕНИЯ ВО VIEW PROFILE!!

app = Flask(__name__)
app.secret_key = 'your_secret_key'

conn = sqlite3.connect('test.db', check_same_thread=False)
cursor = conn.cursor()

users = {
    'test1': {'password': 'pass1', 'role': 'admin'}, #TODO: ВРЕМЕННЫЙ ЛОГИН, НО ЭТО ВООБЩЕ ПИЗДЕЦ ХАХАХХАХ
}
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']
            flash('Авторизация успешна!', 'success')
            return redirect(url_for('main'))
        else:
            flash('Неправильный логин или пароль', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта', 'success')
    return redirect(url_for('main'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def home():
    return redirect(url_for('main'))

@app.route('/main', methods=['GET', 'POST'])
def main():
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    if request.method == 'POST' and session['role'] == 'admin':
        # Обработка добавления бойца
        if 'name' in request.form and 'save_changes' not in request.form:
            name = request.form['name']
            cursor.execute('SELECT * FROM Fighters WHERE name = ?', (name,))
            fighter_exists = cursor.fetchone()
            if fighter_exists:
                flash('Имя уже существует!', 'error')
            else:
                cursor.execute('INSERT INTO Fighters (name, wins, loses) VALUES (?, ?, ?)', (name, 0, 0))
                conn.commit()
                flash('Боец добавлен успешно!', 'success')

        # Обработка удаления бойца
        elif 'delete' in request.form:
            fighter_id = request.form['delete']
            cursor.execute('DELETE FROM Fighters WHERE id = ?', (fighter_id,))
            conn.commit()
            flash('Боец удален успешно!', 'success')

        # Обработка сохранения изменений (только имена бойцов)
        elif 'save_changes' in request.form:
            cursor.execute('SELECT * FROM Fighters')
            fighters = cursor.fetchall()
            for fighter in fighters:
                fighter_id = fighter[0]
                original_name = request.form.get(f'original_name_{fighter_id}')
                new_name = request.form.get(f'name_{fighter_id}')

                # Проверяем, что новое имя получено
                if new_name and new_name != original_name:
                    # Проверяем, что имя не конфликтует с уже существующим
                    cursor.execute('SELECT * FROM Fighters WHERE name = ? AND id != ?', (new_name, fighter_id))
                    name_exists = cursor.fetchone()
                    if name_exists:
                        flash(f'Имя {new_name} уже существует!', 'error')
                    else:
                        cursor.execute('''
                            UPDATE Fighters
                            SET name = ?
                            WHERE id = ?
                        ''', (new_name, fighter_id))
                        conn.commit()
            flash('Изменения сохранены успешно!', 'success')

    cursor.execute('SELECT * FROM Fighters')
    fighters = cursor.fetchall()
    conn.close()

    return render_template('main_sql.html', fighters=fighters, title='Основная')

@app.route('/mark_presence', methods=['GET', 'POST'])
@login_required
def mark_presence():
    cursor.execute('SELECT * FROM FIGHTERS')
    fighters = cursor.fetchall()
    if request.method == 'POST' and session['role'] == 'admin':
        attended = request.form.getlist('attended')
        full_rounds = int(request.form.getlist('full_rounds')[0])
        today_date = create_training_session(attended, full_rounds)
        return redirect(url_for('training_session', date=today_date, full_rounds=full_rounds))
    return render_template('mark_presence.html', fighters=fighters, title='Присутствющие')

def create_training_session(attended_fighters, full_rounds):
    today_date = f'session_{datetime.now().strftime("%d_%m_%Y_%H_%M_%S")}'
    cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS "{today_date}" (
        ROUND INTEGER,
        FIGHTER_1 TEXT,
        SCORE_1 INTEGER,
        SCORE_2 INTEGER,
        FIGHTER_2 TEXT,
        FOREIGN KEY (FIGHTER_1) REFERENCES FIGHTERS (NAME),
        FOREIGN KEY (FIGHTER_2) REFERENCES FIGHTERS (NAME)
    )
    ''')

    fighters = attended_fighters
    if len(fighters) % 2 != 0:
        fighters.append('skip')

    num_fighters = len(fighters)
    x = fighters[0:num_fighters // 2]
    y = fighters[num_fighters // 2:num_fighters]

    matches = []
    for full_round in range(full_rounds): #TODO: Здесь добавляется колиство кругов!!!!!!
        for round_num in range(num_fighters - 1):
            if round_num != 0:
                x.insert(1, y.pop(0))
                y.append(x.pop())
            round_matches = [(x[i], y[i]) for i in range(len(x))]
            matches.append(round_matches)

    round_num = 0
    for fight in matches:
        round_num += 1
        skip_match = None
        for fighter1, fighter2 in fight:
            if fighter1 == 'skip' or fighter2 == 'skip':
                skip_match = (fighter1, fighter2)
            else:
                cursor.execute(f'''
                        INSERT INTO "{today_date}" (ROUND, FIGHTER_1, SCORE_1, SCORE_2, FIGHTER_2)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (round_num, fighter1, 0, 0, fighter2))

        # Добавляем бой со "скипом" в конец раунда, если он есть
        if skip_match:
            fighter1, fighter2 = skip_match
            cursor.execute(f'''
                    INSERT INTO "{today_date}" (ROUND, FIGHTER_1, SCORE_1, SCORE_2, FIGHTER_2)
                    VALUES (?, ?, ?, ?, ?)
                ''', (round_num, fighter1, 0, 0, fighter2))

    conn.commit()
    return today_date

def get_top_fighter(date):
    # Получаем все матчи из сессии
    cursor.execute(f'SELECT * FROM "{date}"')
    matches = cursor.fetchall()

    # Получаем всех бойцов, участвующих в сессии
    cursor.execute(f'''
        SELECT FIGHTER_1 FROM "{date}" WHERE FIGHTER_1 != "skip"
        UNION
        SELECT FIGHTER_2 FROM "{date}" WHERE FIGHTER_2 != "skip"
    ''')
    fighters = [row[0] for row in cursor.fetchall()]

    # Словарь для подсчета побед и поражений, инициализируем всех бойцов с 0 побед и 0 поражений
    stats = {fighter: {'wins': 0, 'losses': 0} for fighter in fighters}

    for match in matches:
        fighter1, score1, score2, fighter2 = match[1], match[2], match[3], match[4]

        # Пропускаем матчи с 'skip'
        if fighter1 == 'skip' or fighter2 == 'skip':
            continue

        # Подсчитываем победы и поражения
        if score1 > score2:
            stats[fighter1]['wins'] += 1
            stats[fighter2]['losses'] += 1
        elif score2 > score1:
            stats[fighter2]['wins'] += 1
            stats[fighter1]['losses'] += 1

    # Вычисляем КД для каждого бойца
    for fighter in stats:
        wins = stats[fighter]['wins']
        losses = stats[fighter]['losses']
        if losses == 0:
            stats[fighter]['kd'] = wins  # Если поражений нет, КД равен количеству побед
        else:
            stats[fighter]['kd'] = round(wins / losses, 2)

    # Сортируем бойцов по количеству побед в порядке убывания
    sorted_fighters = sorted(stats.items(), key=lambda item: item[1]['wins'], reverse=True)

    return sorted_fighters

def get_cleanness(date):
    # Получаем все матчи из сессии
    cursor.execute(f'SELECT * FROM "{date}"')
    matches = cursor.fetchall()

    # Словарь для подсчета забитых и пропущенных очков
    scores = {}

    for match in matches:
        fighter1, score1, score2, fighter2 = match[1], match[2], match[3], match[4]

        # Пропускаем матчи с 'skip'
        if fighter1 == 'skip' or fighter2 == 'skip':
            continue

        # Добавляем бойцов в словарь, если их там еще нет
        if fighter1 not in scores:
            scores[fighter1] = {'scored': 0, 'conceded': 0}
        if fighter2 not in scores:
            scores[fighter2] = {'scored': 0, 'conceded': 0}

        # Подсчитываем забитые и пропущенные очки
        scores[fighter1]['scored'] += score1
        scores[fighter1]['conceded'] += score2
        scores[fighter2]['scored'] += score2
        scores[fighter2]['conceded'] += score1

    # Вычисляем чистоту боя для каждого бойца
    for fighter in scores:
        scored = scores[fighter]['scored']
        conceded = scores[fighter]['conceded']
        if conceded == 0:
            scores[fighter]['clean_sheet'] = scored  # Если пропущенных очков нет, чистота боя равна забитым очкам
        else:
            scores[fighter]['clean_sheet'] = round(scored / conceded, 2)

    sorted_cleanness = sorted(scores.items(), key=lambda item: item[1]['clean_sheet'], reverse=True)

    return sorted_cleanness

def update_fighter_kd():
    cursor.execute('''
        UPDATE FIGHTERS SET KD = 
            CASE 
                WHEN LOSES = 0 THEN WINS
                ELSE ROUND(WINS * 1.0 / LOSES, 2)
            END
    ''')

@app.route('/session/<date>', methods=['GET', 'POST'])
def training_session(date):
    if request.method == 'POST' and session['role'] == 'admin':
        total_matches = int(request.form['total_matches'])  # Получаем количество матчей

        # Получаем текущие матчи перед обновлением
        cursor.execute(f'SELECT * FROM "{date}"')
        matches = cursor.fetchall()

        scores_updated = False  # Флаг для отслеживания изменений
        equal_scores_found = False

        for i in range(total_matches):
            # Получаем данные из формы для каждого матча
            score1 = request.form.get(f'score1_{i}')
            score2 = request.form.get(f'score2_{i}')

            # Пропуск матчей, где значение 'skip'
            if matches[i][1] == 'skip' or matches[i][4] == 'skip':
                continue

            try:
                score1 = int(score1)
                score2 = int(score2)
            except ValueError:
                continue

            # Получаем существующие счета из базы данных
            existing_score1 = matches[i][2] or 0  # matches[i][2] - SCORE_1
            existing_score2 = matches[i][3] or 0  # matches[i][3] - SCORE_2

            # Если счёты не изменились, пропускаем обновление
            if score1 == existing_score1 and score2 == existing_score2:
                continue

            # Данные для обновления
            round_num, fighter_1, _, _, fighter_2 = matches[i]

            # Обновляем счёты бойцов в базе данных
            cursor.execute(f'''
                    UPDATE "{date}" 
                    SET SCORE_1 = ?, SCORE_2 = ?
                    WHERE ROUND = ? AND FIGHTER_1 = ? AND FIGHTER_2 = ?
                ''', (score1, score2, round_num, fighter_1, fighter_2))

            # Обновляем статистику бойцов в зависимости от того, изменились ли счёты

            update_fighter_stats(fighter_1, existing_score1, score1, fighter_2, existing_score2, score2)

            scores_updated = True  # Отмечаем, что было произведено обновление

            if score1 == score2:
                equal_scores_found = True

        if scores_updated:
            update_fighter_kd()  # Обновляем КД всех бойцов

        conn.commit()

        if equal_scores_found:
            flash('Внимание! Найдены матчи с равными счетами.', 'warning')

        # Перенаправление на ту же страницу после сохранения данных
        return redirect(url_for('training_session', date=date))

    # Для GET-запроса или после перенаправления получаем обновленные данные
    cursor.execute(f'SELECT * FROM "{date}"')
    matches = cursor.fetchall()

    ranked_fighters = get_top_fighter(date)
    ranked_cleanness = get_cleanness(date)

    return render_template('training_session.html', matches=matches, today_date=date, ranked_fighters=ranked_fighters, ranked_cleanness=ranked_cleanness, get_flashed_messages=get_flashed_messages)


def update_fighter_stats(fighter1, old_score1, new_score1, fighter2, old_score2, new_score2):
    """Обновляет статистику бойцов (победы и поражения) на основе изменений в счётах."""
    # Убираем старые результаты
    if old_score1 > old_score2:
        cursor.execute('UPDATE FIGHTERS SET WINS = WINS - 1 WHERE NAME = ?', (fighter1,))
        cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES - 1 WHERE NAME = ?', (fighter2,))
    elif old_score2 > old_score1:
        cursor.execute('UPDATE FIGHTERS SET WINS = WINS - 1 WHERE NAME = ?', (fighter2,))
        cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES - 1 WHERE NAME = ?', (fighter1,))

    # Добавляем новые результаты
    if new_score1 > new_score2:
        cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter1,))
        cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter2,))
    elif new_score2 > new_score1:
        cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter2,))
        cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter1,))


@app.route('/sessions', methods=['GET', 'POST'])
def list_sessions():
    if request.method == 'POST' and session['role'] == 'admin': #TODO: ВРЕМЕННЫЙ ЛОГИН
        # Получаем имя таблицы для удаления
        table_to_delete = request.form.get('delete_table')
        if table_to_delete:
            # Выполняем SQL-запрос для удаления таблицы
            cursor.execute(f"DROP TABLE IF EXISTS {table_to_delete};")
            conn.commit()
            flash(f"Сессия {table_to_delete} успешно удалена", "success")

    # После удаления обновляем список таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%';")
    tables = [row[0] for row in cursor.fetchall()]

    return render_template('story.html', tables=tables)


@app.route('/sessions/<session_id>/add_fight', methods=['GET', 'POST'])
def add_fight(session_id):
    if request.method == 'POST' and session['role'] == 'admin':
        # Получаем данные из формы
        fighter1 = request.form['fighter1']
        score1 = int(request.form['score1'])
        fighter2 = request.form['fighter2']
        score2 = int(request.form['score2'])

        # Проверяем, что выбраны разные бойцы
        if fighter1 == fighter2:
            flash('Выберите двух разных бойцов.')
            return redirect(url_for('add_fight', session_id=session_id))

        if score1 == score2:
            flash('Ошибка: Счета бойцов не могут быть одинаковыми.', 'error')
            return redirect(url_for('add_fight', session_id=session_id))

        # Обновляем данные в базе данных
        cursor.execute(f'''
            INSERT INTO "{session_id}" (ROUND, FIGHTER_1, SCORE_1, SCORE_2, FIGHTER_2)
            VALUES (?, ?, ?, ?, ?)
        ''', ('additional', fighter1, score1, score2, fighter2))

        # Обновление статистики бойцов
        if score1 > score2:
            cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter1,))
            cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter2,))
        elif score2 > score1:
            cursor.execute('UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?', (fighter2,))
            cursor.execute('UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?', (fighter1,))

        # Обновление KD бойцов
        update_fighter_kd()
        conn.commit()

        # Перенаправляем пользователя на страницу сессии
        return redirect(url_for('training_session', date=session_id))
    else:
        # Получаем список бойцов из текущей сессии
        cursor.execute(f'''
            SELECT FIGHTER_1 FROM "{session_id}" WHERE FIGHTER_1 != 'skip'
            UNION
            SELECT FIGHTER_2 FROM "{session_id}" WHERE FIGHTER_2 != 'skip'
        ''')
        fighters = [row[0] for row in cursor.fetchall()]
        fighters = sorted(set(fighters))  # Убираем дубликаты и сортируем

        return render_template('add_fight.html', session_id=session_id, fighters=fighters)


@app.route('/profiles')
def list_profiles():
    cursor.execute("SELECT name, id FROM FIGHTERS")
    fighter_info = [row for row in cursor.fetchall()]
    return render_template('profiles.html', fighter_info=fighter_info)

@app.route('/profiles/id_<profile_id>')
def view_profile(profile_id):
    cursor.execute('SELECT * FROM FIGHTERS WHERE id = ?', [profile_id])
    fighter_info = [row for row in cursor.fetchall()]
    name = fighter_info[0][1]
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%'")
    fights = get_all_entries_for_person(fighter_info[0][1])
    records = get_fighter_record(name)
    scores = get_fighter_scores(name)
    plot_url_cleanness = plot_clean_sheet_dynamics(name)
    plot_url_kd = plot_kd_dynamics(name)
    return render_template('view_profile.html', fighter_info=fighter_info, fights=fights, scores=scores, records=records, plot_url_cleanness=plot_url_cleanness, plot_url_kd=plot_url_kd)

def get_all_entries_for_person(person_name):
    # Получаем список таблиц, начинающихся с 'session'
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%'")
    session_tables = cursor.fetchall()

    results = []
    for table in session_tables:
        table_name = table[0]
        cursor.execute(f'''
            SELECT * FROM "{table_name}" WHERE FIGHTER_1 = ? OR FIGHTER_2 = ?
        ''', (person_name, person_name))
        rows = cursor.fetchall()
        results.extend(rows)
    return results

def get_fighter_record(fighter_name):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%'")
    session_tables = cursor.fetchall()

    records = {}

    for table in session_tables:
        table_name = table[0]

        # Победы и поражения, когда боец выступал как FIGHTER_1
        cursor.execute(f'''
            SELECT FIGHTER_2, 
                   SUM(CASE WHEN SCORE_1 > SCORE_2 THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN SCORE_1 < SCORE_2 THEN 1 ELSE 0 END) AS loses
            FROM {table_name}
            WHERE FIGHTER_1 = ?
            GROUP BY FIGHTER_2
        ''', (fighter_name,))
        result_1 = cursor.fetchall()

        # Победы и поражения, когда боец выступал как FIGHTER_2
        cursor.execute(f'''
            SELECT FIGHTER_1, 
                   SUM(CASE WHEN SCORE_2 > SCORE_1 THEN 1 ELSE 0 END) AS wins,
                   SUM(CASE WHEN SCORE_2 < SCORE_1 THEN 1 ELSE 0 END) AS loses
            FROM {table_name}
            WHERE FIGHTER_2 = ?
            GROUP BY FIGHTER_1
        ''', (fighter_name,))
        result_2 = cursor.fetchall()

        for opponent, wins, loses in result_1:
            if opponent not in records:
                records[opponent] = {'wins': 0, 'loses': 0}
            records[opponent]['wins'] += wins
            records[opponent]['loses'] += loses

        for opponent, wins, loses in result_2:
            if opponent not in records:
                records[opponent] = {'wins': 0, 'loses': 0}
            records[opponent]['wins'] += wins
            records[opponent]['loses'] += loses

    return records

def get_fighter_scores(fighter_name):
    # Получаем список всех таблиц, соответствующих шаблону 'session_%'
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'session_%'")
    session_tables = cursor.fetchall()

    scores = {}

    for table in session_tables:
        table_name = table[0]

        # Забитые и пропущенные очки, когда боец выступал как FIGHTER_1
        cursor.execute(f'''
            SELECT FIGHTER_2, 
                   SUM(SCORE_1) AS scored,
                   SUM(SCORE_2) AS conceded
            FROM {table_name}
            WHERE FIGHTER_1 = ?
            GROUP BY FIGHTER_2
        ''', (fighter_name,))
        result_1 = cursor.fetchall()

        # Забитые и пропущенные очки, когда боец выступал как FIGHTER_2
        cursor.execute(f'''
            SELECT FIGHTER_1, 
                   SUM(SCORE_2) AS scored,
                   SUM(SCORE_1) AS conceded
            FROM {table_name}
            WHERE FIGHTER_2 = ?
            GROUP BY FIGHTER_1
        ''', (fighter_name,))
        result_2 = cursor.fetchall()

        # Объединяем результаты из двух запросов
        for opponent, scored, conceded in result_1:
            if opponent not in scores:
                scores[opponent] = {'scored': 0, 'conceded': 0}
            scores[opponent]['scored'] += scored
            scores[opponent]['conceded'] += conceded

        for opponent, scored, conceded in result_2:
            if opponent not in scores:
                scores[opponent] = {'scored': 0, 'conceded': 0}
            scores[opponent]['scored'] += scored
            scores[opponent]['conceded'] += conceded

    return scores

def plot_clean_sheet_dynamics(fighter_name):
    # Получаем все тренировочные сессии
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name LIKE "session_%"')
    sessions = [row[0] for row in cursor.fetchall()]

    clean_sheets = []
    dates = []

    for session in sessions:
        # Получаем чистоту боев для текущей сессии
        cleanness = get_cleanness(session)

        # Ищем бойца в списке чистоты боев
        for fighter, stats in cleanness:
            if fighter == fighter_name:
                clean_sheets.append(stats['clean_sheet'])
                dates.append(session.split('_')[5])  # TODO:Извлекаем дату из имени сессии
                break

    # Построение графика
    plt.figure(figsize=(10, 5))
    plt.plot(dates, clean_sheets, marker='o')
    plt.title(f'Динамика чистоты боев для {fighter_name}')
    plt.xlabel('Дата сессии')
    plt.ylabel('Чистота боя')
    plt.xticks(rotation=45)
    plt.grid(True)

    # Сохранение графика в байтовый поток
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    # Кодирование изображения в base64
    plot_url_cleanness = base64.b64encode(img.getvalue()).decode()

    return plot_url_cleanness

def plot_kd_dynamics(fighter_name): #TODO: Исрпавить функцию для подсчета КД
    # Получаем все тренировочные сессии
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name LIKE "session_%"')
    sessions = [row[0] for row in cursor.fetchall()]

    kds = []
    dates = []

    for session in sessions:
        # Получаем КД для текущей сессии
        top_fighters = get_top_fighter(session)

        # Ищем бойца в списке КД
        for fighter, stats in top_fighters:
            if fighter == fighter_name:
                kds.append(stats['kd'])
                dates.append(session.split('_')[5])  # TODO:Извлекаем дату из имени сессии!!!!!!!!!!!
                break

    # Построение графика
    plt.figure(figsize=(10, 5))
    plt.plot(dates, kds, marker='o')
    plt.title(f'Динамика КД для {fighter_name}')
    plt.xlabel('Дата сессии')
    plt.ylabel('КД')
    plt.xticks(rotation=45)
    plt.grid(True)

    # Сохранение графика в байтовый поток
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()

    # Кодирование изображения в base64
    plot_url_kd = base64.b64encode(img.getvalue()).decode()

    return plot_url_kd

if __name__ == '__main__':
    app.run(debug=True)