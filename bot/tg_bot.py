from asgiref.sync import sync_to_async
import django
import logging
import os
import sys
from datetime import datetime, timedelta
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from dotenv import load_dotenv
load_dotenv()


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_tracker.settings')
django.setup()

from django.contrib.auth.models import User  # noqa: E402
from expenses.models import Expense  # noqa: E402

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def get_or_create_user(update: Update) -> User:
    if update.message:
        tg_user = update.message.from_user
    else:
        tg_user = update.callback_query.from_user
    username = f"tg_{tg_user.id}"

    user, created = await sync_to_async(User.objects.get_or_create)(
        username=username
    )
    if created:
        user.first_name = tg_user.first_name
        user.last_name = tg_user.last_name or ""
        await sync_to_async(user.save)()

    return user


async def add_expense(update: Update, context: CallbackContext) -> None:
    if context.user_data.get("awaiting_month_input"):
        await handle_custom_month_input(update, context)
        return

    user = await get_or_create_user(update)
    text = update.message.text

    try:
        *category_words, amount_str = text.split()
        category = " ".join(category_words)
        amount = float(amount_str)

        await sync_to_async(Expense.objects.create)(
            user=user, amount=amount, category=category
        )

        await update.message.reply_text(
            f'Расход {amount} руб. на "{category}" добавлен.'
        )
    except Exception as e:
        logging.error(f"Error adding expense: {e}")
        await update.message.reply_text(
            f"❌ Ошибка: {e}\nФормат: категория сумма"
        )


async def build_report_for_month(user: User, year: int, month: int) -> str:
    """Возвращает текст отчёта за указанный месяц."""

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    expenses = await sync_to_async(
        lambda: list(
            Expense.objects.filter(
                user=user,
                created_at__gte=start_date,
                created_at__lt=end_date
            )
        )
    )()

    # Нет расходов
    if not expenses:
        return f"За {month:02d}.{year} расходов нет."

    totals = {}
    for exp in expenses:
        totals[exp.category] = totals.get(exp.category, 0) + float(exp.amount)

    report = f"📊 Отчёт за {month:02d}.{year}:\n\n"
    for cat, summ in totals.items():
        report += f"- {cat}: {summ:.2f} руб.\n"

    return report


def get_main_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📊 Отчет")]],
        resize_keyboard=True
    )


async def send_report_options(update: Update, context: CallbackContext):
    """Показывает inline-кнопки выбора периода."""

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Текущий месяц",
                callback_data="report_current",
            ),
        ],
        [
            InlineKeyboardButton(
                "Предыдущий месяц",
                callback_data="report_previous",
            ),
        ],
        [
            InlineKeyboardButton(
                "Ввести месяц вручную",
                callback_data="report_custom",
            ),
        ]
    ])

    await update.message.reply_text(
        "Выберите период:",
        reply_markup=keyboard
    )


async def month_from_callback(callback_data: str):
    """Возвращает year, month."""
    now = datetime.now()

    if callback_data == "report_current":
        return now.year, now.month

    if callback_data == "report_previous":
        first_day = now.replace(day=1)
        prev_month_last_day = first_day - timedelta(days=1)
        return prev_month_last_day.year, prev_month_last_day.month


async def handle_report_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    user = await get_or_create_user(update)
    data = query.data

    # --- Ввести месяц вручную ---
    if data == "report_custom":
        context.user_data["awaiting_month_input"] = True
        await query.message.reply_text(
            "Введите месяц в формате ММ.ГГГГ (например, 07.2025):"
        )
        return

    # --- Текущий / предыдущий месяц ---
    year, month = await month_from_callback(data)
    report_text = await build_report_for_month(user, year, month)

    await query.message.reply_text(report_text)


async def handle_custom_month_input(update: Update, context: CallbackContext):
    text = update.message.text.strip()

    try:
        month_str, year_str = text.split(".")
        month = int(month_str)
        year = int(year_str)

        if not (1 <= month <= 12):
            raise ValueError

    except Exception:
        await update.message.reply_text(
            "❌ Неверный формат. Используй ММ.ГГГГ (например, 11.2025)."
        )
        return

    context.user_data["awaiting_month_input"] = False

    user = await get_or_create_user(update)
    report = await build_report_for_month(user, year, month)
    await update.message.reply_text(report)


async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Я бот учёта расходов.\n"
        "Просто отправляй: категория сумма\n"
        "Например: еда 300\n\n"
        "А для отчёта нажми кнопку ниже.",
        reply_markup=get_main_keyboard()
    )


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex("^📊 Отчет$"),
            send_report_options
        )
    )

    application.add_handler(CallbackQueryHandler(handle_report_callback))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, add_expense)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
