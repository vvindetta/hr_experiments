import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

BOT_TOKEN = ""
ANSWER_ROOT = "answers"
ADMIN_CHAT_ID = ""  # Куда отправлять отчёты


QUESTIONS = {
    "full_name": "Давайте познакомимся! Напишите, пожалуйста, Ваши фамилию и имя!",
    "resume": "Пришлите пожалуйста ваше резюме",
    "salary_expectations": "Какой уровень заработной платы вы рассматриваете на данной позиции? (укажите сумму в долларах)?",
    "ai_usage": "Как вы используете AI-решения в разработке?",
    "biggest_challenge": "Вспомните задачу, где чувствовался настоящий челлендж - что оказалось самым трудным и чему вы научились в итоге?",
    "culture_and_team": "Что вам важно в культуре компании и команде?",
    "conflict_resolution": "Были ли у вас конфликты на рабочем месте, как вы их решали?",
    "weaknesses": "Какие ваши слабые стороны?",
    "major_failure": "Расскажите о своём самом серьёзном провале",
    "uncertainty_case": "Приведите пример задачи с высокой неопределённостью - что было самым сложным (отсутствие чёткого ТЗ, множественные попытки и т. д.) и как вы справились?",
    "motivation": "Зачем вы на самом деле работаете?",
    "stress_resistance": "Расскажите, пожалуйста, как вы обычно реагируете на стрессовые ситуации и выгорания на работе?",
    "school_image": "Если вспомнить школьные годы — как вам кажется, какое впечатление вы производили на одноклассников? Каким человеком они вас видели?",
    "tattoos": "Есть ли у вас татуировки?",
    "children": "Если это удобно, поделитесь, пожалуйста, есть ли у вас дети?",
    "nda_agreement": "Готовы ли вы подписать NDA?",
    "work_for_idea": "Насколько вам комфортно работать на проекте, где на первых этапах основной мотивацией может быть интерес к продукту, а не финансовая составляющая? Рассматриваете ли вы такие форматы?",
    "Lie": "Соврали ли вы хоть раз в ответах выше?",
}


class Questionnaire(StatesGroup):
    waiting_for_answer = State()


async def send_question(message: Message, state: FSMContext, index: int) -> None:
    keys = list(QUESTIONS.keys())
    folder_name = keys[index]
    question_text = QUESTIONS[folder_name]

    await state.update_data(question_index=index)
    await message.answer(question_text)
    await state.set_state(Questionnaire.waiting_for_answer)


async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    os.makedirs(ANSWER_ROOT, exist_ok=True)
    await send_question(message, state, index=0)


async def handle_answer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    question_index = data.get("question_index", 0)

    keys = list(QUESTIONS.keys())
    folder_name = keys[question_index]
    question_text = QUESTIONS[folder_name]

    dir_path = os.path.join(ANSWER_ROOT, folder_name)
    os.makedirs(dir_path, exist_ok=True)

    user_id_str = str(message.from_user.id)
    bot = message.bot  # <-- нужен для download

    report_answer = ""

    # 1. Ответ-файл (document)
    if message.document:
        doc = message.document
        original_name = doc.file_name or ""
        _, ext = os.path.splitext(original_name)
        file_name = user_id_str + ext
        file_path = os.path.join(dir_path, file_name)

        # ВАЖНО: скачиваем через bot.download
        await bot.download(doc, destination=file_path)

        report_answer = f"[file: {original_name}]"

    # 2. Ответ-фото
    elif message.photo:
        photo = message.photo[-1]
        file_name = user_id_str + ".jpg"
        file_path = os.path.join(dir_path, file_name)

        # Тоже через bot.download
        await bot.download(photo, destination=file_path)

        report_answer = "[photo]"

    # 3. Ответ-текстом
    else:
        answer_text = message.text or ""
        file_name = user_id_str + ".txt"
        file_path = os.path.join(dir_path, file_name)

        with open(file_path, "a", encoding="utf-8") as f:
            f.write(answer_text + "\n")

        report_answer = answer_text

    report_message = f"{question_text}\n---\n{report_answer}"
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=report_message)

    next_index = question_index + 1
    if next_index < len(QUESTIONS):
        await send_question(message, state, next_index)
    else:
        await message.answer(
            "Спасибо за информацию! Я свяжусь с вами, как только соберу фидбек."  # (нет)
        )
        await state.clear()


async def main() -> None:
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(handle_answer, Questionnaire.waiting_for_answer)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
