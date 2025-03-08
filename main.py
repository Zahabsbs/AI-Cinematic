import logging
import sqlite3
import json
import aiohttp
import asyncio
import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
API_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'  # Замените на свой токен
DEEPSEEK_API_KEY = 'YOUR_DEEPSEEK_API_KEY'  # Замените на свой API-ключ DeepSeek
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'  # URL для API DeepSeek

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Определение состояний для конечного автомата
class FilmDialog(StatesGroup):
    waiting_for_genre = State()
    waiting_for_depth = State()
    waiting_for_features = State()
    waiting_for_feedback = State()

# Подключение к базе данных SQLite
def init_db():
    conn = sqlite3.connect('movie_bot.db')
    cursor = conn.cursor()
    
    # Создание таблицы пользователей, если она не существует
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        preferences TEXT,
        history TEXT,
        interaction_count INTEGER DEFAULT 0,
        last_interaction TIMESTAMP
    )
    ''')
    
    # Создание таблицы фильмов/аниме, если она не существует
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY,
        title TEXT,
        genre TEXT,
        depth TEXT,
        features TEXT,
        type TEXT,
        description TEXT,
        rating REAL DEFAULT 0,
        likes INTEGER DEFAULT 0,
        dislikes INTEGER DEFAULT 0,
        year INTEGER
    )
    ''')
    
    # Создание таблицы для хранения взаимодействий пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_interactions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        content_id INTEGER,
        interaction_type TEXT,
        timestamp TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id),
        FOREIGN KEY (content_id) REFERENCES content (id)
    )
    ''')
    
    # Добавим несколько фильмов и аниме для примера (расширенная информация)
    sample_content = [
        (1, 'Начало', 'sci-fi,thriller', 'deep', 'action,mystery', 'movie', 
         'Фильм о воре, который крадет корпоративные секреты через использование технологии совместного сна.', 8.8, 0, 0, 2010),
        (2, 'Ла-Ла Ленд', 'romance,drama', 'light', 'music,romance', 'movie', 
         'Музыкальная история любви джазового пианиста и начинающей актрисы в Лос-Анджелесе.', 8.0, 0, 0, 2016),
        (3, 'Атака титанов', 'action,fantasy', 'deep', 'action,drama', 'anime', 
         'Аниме-сериал о борьбе человечества против гигантских людоедов в постапокалиптическом мире.', 9.0, 0, 0, 2013),
        (4, 'Твоё имя', 'romance,fantasy', 'medium', 'romance,drama', 'anime', 
         'История о двух подростках, которые обнаруживают, что таинственным образом меняются телами.', 8.4, 0, 0, 2016),
        (5, 'Джон Уик', 'action,thriller', 'light', 'action,violence', 'movie', 
         'Бывший наемный убийца вынужден вернуться к своему темному прошлому, чтобы отомстить.', 7.4, 0, 0, 2014),
        (6, 'Интерстеллар', 'sci-fi,drama', 'deep', 'space,science', 'movie', 
         'Фильм о группе исследователей, которые используют недавно обнаруженный пространственный тоннель, чтобы преодолеть ограничения космических путешествий.', 8.6, 0, 0, 2014),
        (7, 'Ванпанчмен', 'comedy,action', 'light', 'action,humor', 'anime', 
         'Аниме о супергерое, который может победить любого противника одним ударом и страдает от этого.', 8.8, 0, 0, 2015),
        (8, 'Паразит', 'horror,sci-fi', 'deep', 'horror,drama', 'anime', 
         'Аниме о паразитических существах, которые захватывают и контролируют мозг людей.', 8.5, 0, 0, 2014),
        (9, 'Шрек', 'comedy,fantasy', 'light', 'humor,romance', 'movie', 
         'Анимационный фильм о приключениях огра и его друзей в сказочном королевстве.', 7.9, 0, 0, 2001),
        (10, 'Унесённые призраками', 'fantasy,adventure', 'medium', 'fantasy,drama', 'anime', 
         'Аниме о девочке, которая попадает в мир духов и должна найти способ спасти своих родителей.', 8.6, 0, 0, 2001),
        (11, 'Пульп Фикшн', 'crime,drama', 'deep', 'violence,humor', 'movie', 
         'Нелинейное повествование о криминальном мире Лос-Анджелеса.', 8.9, 0, 0, 1994),
        (12, 'Ковбой Бибоп', 'sci-fi,action', 'medium', 'action,space', 'anime', 
         'Аниме о группе охотников за головами в космосе будущего.', 8.9, 0, 0, 1998),
        (13, 'Тёмный рыцарь', 'action,crime', 'deep', 'action,drama', 'movie', 
         'Фильм о борьбе Бэтмена с криминальным гением Джокером.', 9.0, 0, 0, 2008),
        (14, 'Твин Пикс', 'mystery,drama', 'deep', 'mystery,horror', 'movie', 
         'Сериал о расследовании убийства молодой девушки в маленьком городке.', 8.8, 0, 0, 1990),
        (15, 'Клинок, рассекающий демонов', 'action,fantasy', 'medium', 'action,drama', 'anime', 
         'Аниме о мальчике, который становится охотником на демонов после того, как его семья была убита.', 8.7, 0, 0, 2019)
    ]
    
    cursor.executemany('''
    INSERT OR IGNORE INTO content (id, title, genre, depth, features, type, description, rating, likes, dislikes, year)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_content)
    
    conn.commit()
    conn.close()

# Инициализация базы данных при запуске
init_db()

# Функция для взаимодействия с DeepSeek API
async def query_deepseek_api(prompt, user_history=None):
    """
    Запрашивает рекомендации у DeepSeek API на основе предпочтений пользователя и истории.
    
    Args:
        prompt (str): Текстовый запрос для DeepSeek.
        user_history (list, optional): История взаимодействий пользователя для контекста.
    
    Returns:
        dict: Ответ от DeepSeek API с рекомендациями.
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Формируем историю сообщений для контекста
    messages = [{"role": "system", "content": "Ты - эксперт по фильмам и аниме, который помогает пользователям находить контент на основе их предпочтений."}]
    
    # Добавляем историю пользователя для контекста, если она есть
    if user_history:
        history_context = "История предпочтений пользователя:\n"
        for item in user_history:
            content_info = f"- {item['title']} ({item['type']}): {item['feedback']}"
            history_context += content_info + "\n"
        
        messages.append({"role": "system", "content": history_context})
    
    # Добавляем основной запрос
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DEEPSEEK_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    error_text = await response.text()
                    logging.error(f"DeepSeek API error: {response.status} - {error_text}")
                    return None
    except Exception as e:
        logging.error(f"Error calling DeepSeek API: {e}")
        return None

# Функция для сохранения предпочтений пользователя
def save_user_preferences(user_id, preferences):
    conn = sqlite3.connect('movie_bot.db')
    cursor = conn.cursor()
    
    current_time = datetime.datetime.now().isoformat()
    
    # Проверяем, существует ли запись для пользователя
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        # Обновляем существующие предпочтения и увеличиваем счетчик взаимодействий
        cursor.execute(
            'UPDATE users SET preferences = ?, interaction_count = interaction_count + 1, last_interaction = ? WHERE user_id = ?',
            (json.dumps(preferences), current_time, user_id)
        )
    else:
        # Создаем новую запись
        cursor.execute(
            'INSERT INTO users (user_id, preferences, history, interaction_count, last_interaction) VALUES (?, ?, ?, ?, ?)',
            (user_id, json.dumps(preferences), json.dumps([]), 1, current_time)
        )
    
    conn.commit()
    conn.close()

# Функция для сохранения истории просмотра и взаимодействий
def save_user_history(user_id, content_id, feedback):
    conn = sqlite3.connect('movie_bot.db')
    cursor = conn.cursor()
    
    current_time = datetime.datetime.now().isoformat()
    
    # Получаем текущую историю
    cursor.execute('SELECT history FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    history = []
    if result and result[0]:
        history = json.loads(result[0])
    
    # Получаем информацию о контенте
    cursor.execute('SELECT title, type FROM content WHERE id = ?', (content_id,))
    content_result = cursor.fetchone()
    
    if content_result:
        title, content_type = content_result
        
        # Добавляем новую запись в историю
        history.append({
            'content_id': content_id,
            'title': title,
            'type': content_type,
            'feedback': feedback,
            'timestamp': current_time
        })
        
        # Обновляем историю в базе данных
        cursor.execute(
            'UPDATE users SET history = ? WHERE user_id = ?',
            (json.dumps(history), user_id)
        )
        
        # Добавляем запись в таблицу взаимодействий
        cursor.execute(
            'INSERT INTO user_interactions (user_id, content_id, interaction_type, timestamp) VALUES (?, ?, ?, ?)',
            (user_id, content_id, feedback, current_time)
        )
        
        # Обновляем статистику контента
        if feedback == 'like':
            cursor.execute('UPDATE content SET likes = likes + 1 WHERE id = ?', (content_id,))
        elif feedback == 'dislike':
            cursor.execute('UPDATE content SET dislikes = dislikes + 1 WHERE id = ?', (content_id,))
        
        # Пересчитываем рейтинг контента на основе лайков и дизлайков
        cursor.execute(
            '''
            UPDATE content 
            SET rating = CASE 
                WHEN (likes + dislikes) > 0 THEN (likes * 10.0) / (likes + dislikes) 
                ELSE rating 
            END 
            WHERE id = ?
            ''', 
            (content_id,)
        )
    
    conn.commit()
    conn.close()

# Функция для получения истории пользователя с деталями контента
def get_user_history_details(user_id, limit=10):
    conn = sqlite3.connect('movie_bot.db')
    cursor = conn.cursor()
    
    # Получаем взаимодействия пользователя с деталями контента
    cursor.execute('''
        SELECT 
            ui.content_id,
            c.title,
            c.genre,
            c.type,
            ui.interaction_type,
            ui.timestamp
        FROM 
            user_interactions ui
        JOIN 
            content c ON ui.content_id = c.id
        WHERE 
            ui.user_id = ?
        ORDER BY 
            ui.timestamp DESC
        LIMIT ?
    ''', (user_id, limit))
    
    history = cursor.fetchall()
    
    conn.close()
    
    # Преобразуем в список словарей для удобства использования
    detailed_history = []
    for item in history:
        detailed_history.append({
            'content_id': item[0],
            'title': item[1],
            'genre': item[2],
            'type': item[3],
            'feedback': item[4],
            'timestamp': item[5]
        })
    
    return detailed_history

# Функция для рекомендации контента на основе предпочтений и истории
async def recommend_content(preferences, user_id=None):
    conn = sqlite3.connect('movie_bot.db')
    cursor = conn.cursor()
    
    # Получаем жанр, глубину и особенности из предпочтений
    genre = preferences.get('genre', '')
    depth = preferences.get('depth', '')
    features = preferences.get('features', '')
    
    # Список уже просмотренных фильмов, чтобы не рекомендовать их снова
    exclude_ids = []
    user_history = None
    
    # Если есть ID пользователя, получаем его историю
    if user_id:
        user_history = get_user_history_details(user_id)
        exclude_ids = [item['content_id'] for item in user_history]
    
    # Формируем SQL-запрос с учетом истории просмотров и рейтинга
    query = '''
    SELECT id, title, genre, depth, features, type, description, rating, year
    FROM content
    WHERE 1=1
    '''
    params = []
    
    if genre:
        query += ' AND genre LIKE ?'
        params.append(f'%{genre}%')
    
    if depth:
        query += ' AND depth = ?'
        params.append(depth)
    
    if features:
        query += ' AND features LIKE ?'
        params.append(f'%{features}%')
    
    # Исключаем уже просмотренные фильмы
    if exclude_ids:
        placeholders = ','.join(['?'] * len(exclude_ids))
        query += f' AND id NOT IN ({placeholders})'
        params.extend(exclude_ids)
    
    # Сортируем по рейтингу (высший рейтинг первым)
    query += ' ORDER BY rating DESC'
    
    # Выполняем запрос
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    # Если нет точных совпадений, попробуем запросить DeepSeek API
    if not results and user_id:
        try:
            # Формируем запрос к DeepSeek на основе предпочтений и истории
            prompt = f"Я ищу рекомендации для {'фильма' if 'movie' in preferences.get('type', '') else 'аниме'}. "
            prompt += f"Мне нравится жанр: {genre}, "
            prompt += f"я предпочитаю {'легкий контент' if depth == 'light' else 'контент средней глубины' if depth == 'medium' else 'глубокий контент'}. "
            prompt += f"Важные элементы: {features}. "
            
            # Добавляем информацию из истории просмотров
            if user_history:
                prompt += "Вот мои предыдущие оценки: "
                for i, item in enumerate(user_history[:5]):  # Используем последние 5 оценок
                    prompt += f"{item['title']} ({item['feedback'].replace('like', 'понравилось').replace('dislike', 'не понравилось')}), "
            
            prompt += "Порекомендуй мне 3 подходящих фильма или аниме с названиями и коротким описанием."
            
            # Запрос к DeepSeek API
            deepseek_response = await query_deepseek_api(prompt, user_history)
            
            if deepseek_response and 'choices' in deepseek_response:
                ai_suggestions = deepseek_response['choices'][0]['message']['content']
                
                # Записываем рекомендации в лог для анализа
                logging.info(f"DeepSeek API рекомендации для пользователя {user_id}: {ai_suggestions}")
                
                # Теперь попробуем найти в нашей базе фильмы, похожие на рекомендации DeepSeek
                # Это упрощенная логика - в реальном приложении вы бы анализировали ответ и извлекали названия
                # Здесь мы просто ищем по популярным жанрам
                cursor.execute('''
                SELECT id, title, genre, depth, features, type, description, rating, year 
                FROM content 
                WHERE id NOT IN ({})
                ORDER BY rating DESC, RANDOM()
                LIMIT 3
                '''.format(','.join(['?'] * len(exclude_ids)) if exclude_ids else '0'), 
                exclude_ids if exclude_ids else [])
                
                ai_recommended = cursor.fetchall()
                if ai_recommended:
                    results = ai_recommended
        except Exception as e:
            logging.error(f"Ошибка при использовании DeepSeek API: {e}")
    
    conn.close()
    
    # Если все еще нет результатов, вернем случайные рекомендации с высоким рейтингом
    if not results:
        conn = sqlite3.connect('movie_bot.db')
        cursor = conn.cursor()
        
        # Исключаем уже просмотренные
        exclude_clause = f'WHERE id NOT IN ({",".join(["?"] * len(exclude_ids))})' if exclude_ids else ''
        
        cursor.execute(f'''
        SELECT id, title, genre, depth, features, type, description, rating, year 
        FROM content 
        {exclude_clause}
        ORDER BY rating DESC, RANDOM() 
        LIMIT 3
        ''', exclude_ids if exclude_ids else [])
        
        results = cursor.fetchall()
        conn.close()
    
    return results

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer(
        "👋 Привет! Я твой помощник в мире фильмов и аниме!\n\n"
        "Расскажи мне, что ты хочешь посмотреть, а я помогу подобрать что-то интересное. "
        "Например, напиши: \"Хочу посмотреть фильм\" или \"Посоветуй аниме\".\n\n"
        "Чем больше ты взаимодействуешь со мной, тем точнее будут мои рекомендации! 🎬✨"
    )

# Обработчик для начала диалога о фильмах/аниме
@dp.message_handler(lambda message: any(phrase in message.text.lower() for phrase in ['фильм', 'кино', 'посмотреть', 'аниме']))
async def start_film_dialog(message: types.Message):
    markup = InlineKeyboardMarkup(row_width=2)
    genres = [
        ('Комедия', 'comedy'),
        ('Драма', 'drama'),
        ('Фантастика', 'sci-fi'),
        ('Боевик', 'action'),
        ('Триллер', 'thriller'),
        ('Ужасы', 'horror'),
        ('Романтика', 'romance'),
        ('Фэнтези', 'fantasy'),
        ('Приключения', 'adventure')
    ]
    
    for name, callback_data in genres:
        markup.add(InlineKeyboardButton(name, callback_data=f'genre_{callback_data}'))
    
    await message.answer("Отлично! Какой жанр тебе больше нравится?", reply_markup=markup)
    await FilmDialog.waiting_for_genre.set()

# Обработчик выбора жанра
@dp.callback_query_handler(lambda c: c.data.startswith('genre_'), state=FilmDialog.waiting_for_genre)
async def process_genre(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    
    genre = callback_query.data.split('_')[1]
    
    # Сохраняем жанр в состоянии FSM
    async with state.proxy() as data:
        data['genre'] = genre
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("Лёгкое", callback_data="depth_light"),
        InlineKeyboardButton("Среднее", callback_data="depth_medium"),
        InlineKeyboardButton("Глубокое", callback_data="depth_deep")
    )
    
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Ты хочешь что-то лёгкое или с глубоким смыслом?",
        reply_markup=markup
    )
    
    await FilmDialog.waiting_for_depth.set()

# Обработчик выбора глубины
@dp.callback_query_handler(lambda c: c.data.startswith('depth_'), state=FilmDialog.waiting_for_depth)
async def process_depth(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    
    depth = callback_query.data.split('_')[1]
    
    # Сохраняем глубину в состоянии FSM
    async with state.proxy() as data:
        data['depth'] = depth
    
    markup = InlineKeyboardMarkup(row_width=2)
    features = [
        ('Экшен', 'action'),
        ('Романтика', 'romance'),
        ('Юмор', 'humor'),
        ('Драма', 'drama'),
        ('Мистика', 'mystery'),
        ('Научные', 'science')
    ]
    
    for name, callback_data in features:
        markup.add(InlineKeyboardButton(name, callback_data=f'feature_{callback_data}'))
    
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Какие элементы наиболее важны для тебя?",
        reply_markup=markup
    )
    
    await FilmDialog.waiting_for_features.set()

# Обработчик выбора особенностей
@dp.callback_query_handler(lambda c: c.data.startswith('feature_'), state=FilmDialog.waiting_for_features)
async def process_features(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    
    feature = callback_query.data.split('_')[1]
    
    # Сохраняем особенности в состоянии FSM
    async with state.proxy() as data:
        data['features'] = feature
        
        # Сохраняем предпочтения пользователя в базе данных
        preferences = {
            'genre': data.get('genre', ''),
            'depth': data.get('depth', ''),
            'features': data.get('features', '')
        }
        save_user_preferences(callback_query.from_user.id, preferences)
        
        # Получаем рекомендации на основе предпочтений
        recommendations = recommend_content(preferences)
        
        if recommendations:
            # Показываем первую рекомендацию
            rec = recommendations[0]
            rec_id, title, genres, depth, features, content_type = rec
            
            # Форматируем текст рекомендации
            type_text = "Фильм" if content_type == "movie" else "Аниме"
            genre_text = ', '.join([g.capitalize() for g in genres.split(',')])
            features_text = ', '.join([f.capitalize() for f in features.split(',')])
            
            text = (
                f"🎬 <b>{title}</b> ({type_text})\n\n"
                f"🎭 Жанр: {genre_text}\n"
                f"🎯 Особенности: {features_text}\n"
                f"💭 Глубина: {depth.capitalize()}\n\n"
                f"Как тебе эта рекомендация?"
            )
            
            # Создаем кнопки для отзыва
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("👍 Нравится", callback_data=f"feedback_like_{rec_id}"),
                InlineKeyboardButton("👎 Не нравится", callback_data=f"feedback_dislike_{rec_id}")
            )
            
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text=text,
                reply_markup=markup,
                parse_mode="HTML"
            )
            
            # Сохраняем ID контента для отзыва
            data['current_content_id'] = rec_id
            
            await FilmDialog.waiting_for_feedback.set()
        else:
            await bot.edit_message_text(
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                text="К сожалению, я не нашел подходящих рекомендаций. Давай попробуем другие критерии."
            )
            await state.finish()

# Обработчик отзыва о рекомендации
@dp.callback_query_handler(lambda c: c.data.startswith('feedback_'), state=FilmDialog.waiting_for_feedback)
async def process_feedback(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    
    feedback_parts = callback_query.data.split('_')
    feedback_type = feedback_parts[1]  # 'like' или 'dislike'
    content_id = int(feedback_parts[2])
    
    # Сохраняем отзыв пользователя в базе данных
    save_user_history(callback_query.from_user.id, content_id, feedback_type)
    
    text = "Спасибо за отзыв! Это поможет мне делать рекомендации лучше."
    if feedback_type == 'like':
        text += " Я рад, что смог найти что-то интересное для тебя! 😊"
    else:
        text += " Я учту это при следующих рекомендациях. 👍"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Еще рекомендации", callback_data="more_recommendations"))
    
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text=text,
        reply_markup=markup
    )
    
    await state.finish()

# Обработчик запроса дополнительных рекомендаций
@dp.callback_query_handler(lambda c: c.data == "more_recommendations")
async def more_recommendations(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    
    # Здесь можно было бы начать диалог заново или предложить другие рекомендации
    await bot.edit_message_text(
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        text="Хочешь получить новые рекомендации? Напиши мне, что ты хочешь посмотреть, и мы начнем заново! 🎬"
    )

# Обработчик для неизвестных сообщений
@dp.message_handler()
async def unknown_message(message: types.Message):
    await message.answer(
        "Не совсем понимаю, что ты имеешь в виду. 🤔\n\n"
        "Напиши что-то вроде «Хочу посмотреть фильм» или «Посоветуй аниме», "
        "и я помогу тебе найти что-то интересное!"
    )

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)