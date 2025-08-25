import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN. Создай .env и вставь токен бота.")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----- ДАННЫЕ СТЕЛЛАЖЕЙ (исходное наполнение т/б) -----
STELLAZHI: dict[int, list[str]] = {
    1:  ["231","232","233","234","235","236","237","238","239","240","241","242","243","244","245","246","247","248","249","250","251","252","253","254","255","256","257","258","259","260","261","262","263","264","265","266","267","268","269","270","271","272","273","274","275","276","277","278","279","280","281"],
    2:  ["095","096","097","098","099","100","101","102","103","104"],
    3:  ["021","022","023","024","025","026","027","028","029","030"],
    4:  ["031","032","033","034","035","036","037","038","039","040","051","052","053","054","055","056"],
    5:  ["041","042","043","044","045","046","047","048","049","050"],
    6:  ["057","058","059","060","061","062","063","064","065","066"],
    7:  ["077","078","079","080","081"],
    8:  ["082","083","084","085","086","087","088","089","090","091","092","093","094"],
    9:  ["105","106","107","108","109","110","111","112","113","114","115","116","117","118","119","120","131","132","133","134","135","136","137","138","139","140","141","142","143","144","145","146","147","148","149","150","151","152","153","154"],
    10: ["155","156","157","158","159","160","161","162","163","164","165","166","167","168","169","170","171","172","173","174","175","176","177","178","179","180","181","182","183","184","185","186","187","188","189","190","191","192","193","194","195","196","197","198","199","200"],
    11: ["201","202","203","204","205","206","207","208","209","210"],
    12: ["211","212","213","214","215","216","217","218","219","220"],
    13: ["221","222","223","224","225","226","227","228","229","230"],
    14: ["121","122","123","124","125","126","127","128","129","130"],
    15: ["011","012","013","014","015","016","017","018","019","020"],
    16: ["001","002","003","004","005","006","007","008","009","010"],
    17: ["067","068","069","070","071","072","073","074","075","076"],
}

# ----- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ -----
def normalize_input_to_tb_set(raw: str) -> set[str]:
    """
    '1 4 5 6 3' -> {'001','004','005','006','003'}.
    Берём только числовые токены. Нули слева до ширины 3.
    """
    items = []
    for token in raw.replace(",", " ").split():
        if token.isdigit():
            items.append(str(int(token)).zfill(3))
    return set(items)

def normalize_input_list(raw: str) -> list[str]:
    """
    Возвращает НОРМАЛИЗОВАННЫЙ список (с сохранением повторов):
    raw: "1 4 5 6 3 3" -> ["001","004","005","006","003","003"]
    """
    items: list[str] = []
    for token in raw.replace(",", " ").split():
        if token.isdigit():
            items.append(str(int(token)).zfill(3))
    return items


def find_duplicates(seq: list[str]) -> list[str]:
    """Находит повторные вводы (элементы с count > 1), возвращает отсортированный список уникальных значений."""
    from collections import Counter
    c = Counter(seq)
    dups = sorted([k for k, v in c.items() if v > 1], key=lambda x: int(x))
    return dups

def compress_ranges(sorted_str_nums: list[str]) -> list[tuple[int, int]]:
    """Схлопывает отсортированный список строк-чисел в диапазоны."""
    nums = [int(x) for x in sorted_str_nums]
    if not nums:
        return []
    ranges = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            ranges.append((start, prev))
            start = prev = n
    ranges.append((start, prev))
    return ranges

def format_ranges(sorted_str_nums: list[str]) -> str:
    """Вернёт строку вида: 'с 231 по 250, 252, с 254 по 260'."""
    rngs = compress_ranges(sorted_str_nums)
    parts = []
    for a, b in rngs:
        if a == b:
            parts.append(f"{a:03d}")
        else:
            parts.append(f"с {a:03d} по {b:03d}")
    return ", ".join(parts) if parts else "—"

def compute_tb_result(raw: str) -> str:
    """Считает ответ по логике для произвольной сырой строки.
    Добавляет отметку о повторно введённых башмаках и количество в каждом стеллаже.
    """
    all_entered = normalize_input_list(raw)
    taken = set(all_entered)
    duplicates = find_duplicates(all_entered)

    all_valid = {tb for vals in STELLAZHI.values() for tb in vals}
    invalid = [tb for tb in set(all_entered) if tb not in all_valid]

    remaining_by_shelf: dict[int, list[str]] = {}
    total = 0
    for shelf in sorted(STELLAZHI.keys()):
        left = [tb for tb in STELLAZHI[shelf] if tb not in taken]
        if left:
            remaining_by_shelf[shelf] = left
            total += len(left)

    lines = [f"В стеллажах осталось {total} т/б."]

    if duplicates:
        lines.append("Повторно введены: " + ", ".join(duplicates))

    if invalid:
        lines.append("❌ В парке нет башмаков: " + ", ".join(sorted(invalid, key=lambda x: int(x))))

    for shelf in sorted(remaining_by_shelf.keys()):
        left_sorted = sorted(remaining_by_shelf[shelf], key=lambda x: int(x))
        count = len(left_sorted)
        lines.append(f"{shelf} стеллаж: {count} т/б — {format_ranges(left_sorted)}")

    return "\n".join(lines)

# ----- КОМАНДЫ -----
@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📖 Помощь", callback_data="help")],
    ])
    text = (
        "👋 Привет! Я **ShoesTracker** 👟 — бот для учёта тормозных башмаков.\n\n"
        "Я помогу тебе:\n"
        "• указывать снятые башмаки,\n"
        "• показывать, сколько осталось в стеллажах,\n"
        "• быстро находить нужный номер.\n\n"
        "ℹ️ Просто введи номера башмаков через пробел или запятую, например:\n"
        "`1 4 5 6 3`"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=kb)

@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📖 **Инструкция по ShoesTracker:**\n\n"
        "• `/start` — приветствие и краткое руководство\n"
        "• `/help` — список команд\n\n"
        "👉 Просто вводи номера башмаков через пробел или запятую — я сам нормализую (001, 002...)."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.callback_query()
async def on_menu_click(call: CallbackQuery):
    data = call.data
    if data == "help":
        await call.message.answer(
            "📖 **Инструкция по ShoesTracker:**\n\n"
            "• `/start` — приветствие и краткое руководство\n"
            "• `/help` — список команд\n\n"
            "👉 Просто вводи номера башмаков через пробел или запятую — я сам нормализую (001, 002...).",
            parse_mode="Markdown"
        )
    await call.answer()

@dp.message(F.text & ~F.text.startswith("/"))
async def echo_text(message: Message):
    result = compute_tb_result(message.text)
    await message.answer(result)

# ----- DIAG CATCH-ALL -----
@dp.update()
async def catch_all(update: Update):
    logging.info(f"CATCH-ALL update type: {update.event_type}")
    if update.message:
        try:
            await update.message.answer("👋 Я здесь. Получаю апдейты.")
        except Exception as e:
            logging.exception(f"Reply failed: {e}")

# ----- ЗАПУСК -----
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())