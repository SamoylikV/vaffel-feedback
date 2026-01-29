import asyncio
import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

class Form(StatesGroup):
    name_city_address = State()
    choose_scenario = State()
    details = State()


class GoogleSheets:    
    def __init__(self):
        self.client = None
        self.sheet = None
        self.connect()
    
    def connect(self):
        try:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                CREDENTIALS_FILE, scope
            )
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(SPREADSHEET_ID)
            logger.info("Google Sheets подключен по ссылке")
        except FileNotFoundError:
            logger.warning("Файл credentials.json не найден")
        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets: {e}")

  
    
    def save(self, scenario, name, address, details):
        if not self.sheet:
            logger.warning("Google Sheets не подключен, данные не сохранены")
            return
        
        try:
            sheets = {
                '1': 'Идея по улучшению',
                '2': 'Замечание/проблема',
                '3': 'Предложение по продукту/маркетингу',
                '4': 'Другое'
            }
            
            sheet_name = sheets[scenario]
            
            try:
                worksheet = self.sheet.worksheet(sheet_name)
            except:
                worksheet = self.sheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                worksheet.append_row(['Должность', 'Адрес Vaffel', 'Суть', 'Дата'])
            
            row = [name, address, details, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            worksheet.append_row(row)
            logger.info(f"Данные сохранены в '{sheet_name}'")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")


sheets = GoogleSheets()
router = Router()


def get_keyboard():
    keyboard = [
        [KeyboardButton(text="1️⃣ Идея по улучшению")],
        [KeyboardButton(text="2️⃣ Замечание/Проблема")],
        [KeyboardButton(text="3️⃣ Предложение по продукту/Маркетингу")],
        [KeyboardButton(text="4️⃣ Другое")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


@router.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await message.answer(
        "<b>Привет! Я - Ваффи!</b>\n\n"
        "Я здесь, чтобы собрать идеи, мысли и предложения.\n"
        "Поделитесь с нами вашим взглядом, опытом и видением, "
        "которые мы внимательно изучим и примем в работу!",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(1)
    await message.answer(
        "<b>Я хотела бы знать, кто мне пишет!</b>\n\n"
        "Укажите имя, город и адрес вашего Vaffel! :)",
        parse_mode="HTML"
    )
    await state.set_state(Form.name_city_address)


@router.message(Form.name_city_address)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(user_info=message.text)
    
    await message.answer(
        "📝 <b>Как это работает:</b>\n\n"
        "1️⃣ Вы пишете идею, предложение или замечание;\n"
        "2️⃣ Я передаю сообщение команде Vaffel!;\n"
        "3️⃣ Сильные идеи мы берем в работу и возвращаемся с решениями;\n\n"
        "<b>Выберите тип обращения:</b>",
        reply_markup=get_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(Form.choose_scenario)


@router.message(Form.choose_scenario)
async def choose_scenario(message: Message, state: FSMContext):
    text = message.text
    
    if "1️⃣" in text or text.startswith("1"):
        scenario = "1"
        prompt = (
            "<b>Опишите, пожалуйста:</b>\n\n"
            "• В чем суть идеи\n"
            "• Какую проблему решает ваша идея\n"
            "• Где будет заметен результат внедрения "
            "(гости, команда, выручка, средний чек, процессы)"
        )
    elif "2️⃣" in text or text.startswith("2"):
        scenario = "2"
        prompt = (
            "<b>Спасибо, что говорите об этом!</b>\n"
            "Напишите, пожалуйста:\n\n"
            "• в чем проблема;\n"
            "• к чему это приводит в работе;\n"
            "• опишите вариант решения, если он у вас уже есть;"
        )
    elif "3️⃣" in text or text.startswith("3"):
        scenario = "3"
        prompt = (
            "<b>Супер! Это очень ценно.</b>\n"
            "Расскажите:\n\n"
            "• про вашу идею или гипотезу;\n"
            "• почему на ваш взгляд она может сработать."
        )
    elif "4️⃣" in text or text.startswith("4"):
        scenario = "4"
        prompt = (
            "<b>Напишите все, что считаете важным.</b>\n\n"
            "Даже если мысль пока не до конца сформулирована - это нормально."
        )
    else:
        await message.answer("Пожалуйста, выберите вариант на клавиатуре.")
        return
    
    await state.update_data(scenario=scenario)
    await message.answer(prompt, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    await state.set_state(Form.details)


@router.message(Form.details)
async def process_details(message: Message, state: FSMContext):
    details = message.text
    data = await state.get_data()
    
    user_info = data.get('user_info', '')
    parts = user_info.split(',', 1)
    name = parts[0].strip() if parts else user_info
    address = parts[1].strip() if len(parts) > 1 else ''
    
    scenario = data.get('scenario')
    sheets.save(scenario, name, address, details)
    
    await message.answer(
        "<b>Подтверждение получения</b>\n\n"
        "Спасибо!\n"
        "Мы получили ваше сообщение и обязательно его разберем. "
        "Команда уже читает и думает, как их применить для развития Vaffel!",
        parse_mode="HTML"
    )
    
    await asyncio.sleep(1)
    await message.answer(
        "<b>Прощальный текст</b>\n\n"
        "Спасибо, что помогаете делать Vaffel! сильнее. "
        "Если появятся новые мысли - смело пишите вновь.\n"
        "Хорошего дня!",
        parse_mode="HTML"
    )
    
    await state.clear()


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    logger.info("🤖 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")