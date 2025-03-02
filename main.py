from aiogram import Bot, types, executor
from aiogram.dispatcher import Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from key import API, API_KEY, SECRET_API_KEY
from generation import Text2ImageAPI
import logging

logging.basicConfig(level=logging.INFO)

API_TOKEN = API

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

user_states = {}
api_instance = Text2ImageAPI('https://api-key.fusionbrain.ai/', API_KEY, SECRET_API_KEY)

styles = [
    {"name": "KANDINSKY", "title": "Кандинский", "titleEn": "Kandinsky",
     "image": "https://cdn.fusionbrain.ai/static/download/img-style-kandinsky.png"},
    {"name": "UHD", "title": "Детальное фото", "titleEn": "Detailed photo",
     "image": "https://cdn.fusionbrain.ai/static/download/img-style-detail-photo.png"},
    {"name": "ANIME", "title": "Аниме", "titleEn": "Anime",
     "image": "https://cdn.fusionbrain.ai/static/download/img-style-anime.png"},
    {"name": "DEFAULT", "title": "Свой стиль", "titleEn": "No style",
     "image": "https://cdn.fusionbrain.ai/static/download/img-style-personal.png"}
]


def reset_user_state(user_id):
    user_states[user_id] = {'positive_request': None, 'negative_request': None, 'style': 'DEFAULT', 'awaiting': None}


@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    reset_user_state(user_id)
    start_msg = ("Привет! Этот бот принимает от тебя положительный запрос, негативный запрос и стиль, "
                 "а затем возвращает изображение в формате PNG.\n"
                 "Пожалуйста, отправь положительный запрос (/positive).")
    await message.reply(start_msg)


@dp.message_handler(commands=['positive'])
async def positive_request_command(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]['awaiting'] = 'positive'
    await message.reply("Отправь мне положительный запрос (текст или фразу).")


@dp.message_handler(commands=['negative'])
async def negative_request_command(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]['awaiting'] = 'negative'
    await message.reply("Отправь мне негативный запрос (текст или фразу) или используй /skip_negative для пропуска.")


@dp.message_handler(commands=['skip_negative'])
async def skip_negative_command(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id]['negative_request'] = None
    user_states[user_id]['awaiting'] = 'style'
    await message.reply("Негативный запрос пропущен. Выбери стиль (/style).")


@dp.message_handler(commands=['style'])
async def style_command(message: types.Message):
    user_id = message.from_user.id
    markup = InlineKeyboardMarkup(row_width=2)
    for style in styles:
        markup.add(InlineKeyboardButton(text=style['title'], callback_data=style['name']))
    await message.reply("Выбери стиль:", reply_markup=markup)


@dp.callback_query_handler(lambda c: c.data in [style['name'] for style in styles])
async def process_style_selection(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_states[user_id]['style'] = callback_query.data
    user_states[user_id]['awaiting'] = 'generate'
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id,
                           f"Стиль установлен: {user_states[user_id]['style']}\nТеперь используй /generate для генерации изображения.")


@dp.message_handler(commands=['generate'])
async def generate_image(message: types.Message):
    user_id = message.from_user.id
    user_data = user_states.get(user_id, {})
    if user_data.get('positive_request') and user_data.get('awaiting') == 'generate':
        model_id = api_instance.get_model()
        uuid = api_instance.generate(positive_request=user_data['positive_request'],
                                     negative_request=user_data.get('negative_request', ""),
                                     style=user_data['style'],
                                     model=model_id)
        images = api_instance.check_generation(uuid, user_id)
        if images:
            with open(images[0], "rb") as photo:
                await message.reply_photo(photo)
            await message.reply("Готово! Если хочешь еще используй /start.")
        else:
            await message.reply("Произошла ошибка при генерации изображения.")
    else:
        await message.reply('Пожалуйста, убедись, что ты выбрал положительный запрос и стиль.')


@dp.message_handler(content_types=types.ContentType.TEXT)
async def set_request(message: types.Message):
    user_id = message.from_user.id
    awaiting = user_states.get(user_id, {}).get('awaiting')
    if awaiting:
        user_states[user_id][awaiting + '_request'] = message.text
        user_states[user_id]['awaiting'] = 'negative' if awaiting == 'positive' else 'style'
        await message.reply(f"{awaiting.capitalize()} запрос установлен: {message.text}\n" +
                            (
                                "Отправь негативный запрос (/negative) или пропусти его (/skip_negative)." if awaiting == 'positive' else "Выбери стиль (/style)."
                            ))


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)