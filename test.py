"""def create_fights_history(fighter_id):
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS "fights_{fighter_id}" (
            ROUND INTEGER,
            FIGHTER_1 TEXT,
            SCORE_1 INTEGER,
            SCORE_2 INTEGER,
            FIGHTER_2 TEXT,
            FOREIGN KEY (FIGHTER_1) REFERENCES FIGHTERS (NAME),
            FOREIGN KEY (FIGHTER_2) REFERENCES FIGHTERS (NAME)
        )
        ''')

def check_scores(fighter1, score1, score2, fighter2):
    if score1 > score2:
        cursor.execute('''
                    UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?
                ''', (fighter1, ))
        cursor.execute('''
                    UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?
                ''', (fighter2,))
    elif score2 > score1:
        cursor.execute('''
                    UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?
                ''', (fighter2,))
        cursor.execute('''
                    UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?
                ''', (fighter1,))

    return jsonify(success=True)"""

city_map_list = [
    [1, 1, 0, 0, 1],
    [1, 1, 0, 0, 1],
    [1, 1, 1, 1, 1],
    [0, 0, 0, 0, 1],
    [0, 0, 0, 0, 1]
]

courier_location = (2, 2)  # стартовая позиция курьера
orders_location = [(4, 0), (0, 2), (4, 3)]  # координаты для доставки товаров

# Основной список для маршрута
route = []


# Функция для перемещения курьера к цели
def move_courier(start, end, city_map):
    path = []
    x, y = start  # Текущие координаты курьера
    target_x, target_y = end  # Координаты цели

    # Перемещаемся по оси X
    while x != target_x:
        if x < target_x:  # Движемся вниз
            if city_map[x + 1][y] == 1:
                x += 1
        elif x > target_x:  # Движемся вверх
            if city_map[x - 1][y] == 1:
                x -= 1
        path.append((x, y))  # Сохраняем текущую позицию

    # Перемещаемся по оси Y
    while y != target_y:
        if y < target_y:  # Движемся вправо
            if city_map[x][y + 1] == 1:
                y += 1
        elif y > target_y:  # Движемся влево
            if city_map[x][y - 1] == 1:
                y -= 1
        path.append((x, y))  # Сохраняем текущую позицию

    return path


# Основной цикл: проходим по всем заказам
current_location = courier_location
for order in orders_location:
    route += move_courier(current_location, order, city_map_list)
    current_location = order  # Обновляем текущее положение курьера после доставки

# Выводим результат
print("Маршрут курьера:", route)
