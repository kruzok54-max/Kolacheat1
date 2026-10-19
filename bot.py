import asyncio
from datetime import datetime, timedelta
from threading import Thread
import secrets
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from flask import Flask, jsonify, request

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8900029148:AAFedGA5l_BkFbmIbTlWngpXT_sc7mUm8_c"
ADMIN_ID = 8698171733  # Твой Telegram ID

app = Flask(__name__)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# База данных ключей в памяти
KEYS_DB = {}
BETA_CLAIMED_USERS = set()


# ==========================================
# 1. API СЕРВЕР (Для твоего APK-мода)
# ==========================================
@app.route("/key", methods=["POST", "GET"])
def check_key():
  key = request.args.get("key") or (
      request.json.get("key") if request.is_json else None
  )
  hwid = request.args.get("hwid") or (
      request.json.get("hwid") if request.is_json else None
  )

  if not key or key not in KEYS_DB:
    return jsonify({"status": "error", "message": "Неверный ключ!"}), 403

  key_data = KEYS_DB[key]

  # Проверка срока
  if key_data["expires"] and datetime.now() > key_data["expires"]:
    return jsonify({"status": "error", "message": "Срок ключа истёк!"}), 403

  # Привязка HWID устройства
  if key_data["hwid"] is None and hwid:
    key_data["hwid"] = hwid

  if key_data["hwid"] and hwid and key_data["hwid"] != hwid:
    return (
        jsonify(
            {"status": "error", "message": "Ключ привязан к другому устройству!"}
        ),
        403,
    )

  return jsonify({"status": "success", "message": "KolaCheat Доступ разрешен!"})


def run_flask():
  import os

  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)


# ==========================================
# 2. TELEGRAM БОТ (KolaCheat)
# ==========================================
def get_user_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🔥 Получить бету на 20 часов + APK",
                  callback_data="get_beta",
              )
          ],
          [
              InlineKeyboardButton(
                  text="💎 Купить подписку KolaCheat", callback_data="buy_sub"
              )
          ],
      ]
  )


def get_admin_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="➕ Создать бесконечный ключ",
                  callback_data="gen_inf_key",
              )
          ],
          [
              InlineKeyboardButton(
                  text="⏳ Создать ключ на 24 часа",
                  callback_data="gen_24h_key",
              )
          ],
          [
              InlineKeyboardButton(
                  text="📊 Список всех ключей", callback_data="list_keys"
              )
          ],
      ]
  )


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
  user_id = message.from_user.id
  if user_id == ADMIN_ID:
    await message.answer(
        "👋 Привет, Админ!\n\nПанель управления **KolaCheat**.",
        reply_markup=get_admin_keyboard(),
        parse_mode="Markdown",
    )
  else:
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        "Добро пожаловать в **KolaCheat**! Выбери действие:",
        reply_markup=get_user_keyboard(),
        parse_mode="Markdown",
    )


@dp.callback_query(F.data == "get_beta")
async def process_beta(callback: types.CallbackQuery):
  user_id = callback.from_user.id
  if user_id in BETA_CLAIMED_USERS:
    await callback.answer(
        "❌ Вы уже получали бесплатный бета-ключ!", show_alert=True
    )
    return

  beta_key = f"KOLA-BETA-{secrets.token_hex(4).upper()}"
  expire_time = datetime.now() + timedelta(hours=20)
  KEYS_DB[beta_key] = {"expires": expire_time, "hwid": None}
  BETA_CLAIMED_USERS.add(user_id)

  await callback.message.answer(
      f"🎉 **Ваш бета-ключ KolaCheat активирован!**\n\n"
      f"🔑 **Ключ:** `{beta_key}`\n"
      f"⏱ **Действителен:** 20 часов\n\n"
      f"📥 **Ссылка на APK:** Сюда вставь ссылку на скачивание твоего мода\n\n"
      f"Скопируй ключ и вставь в приложение!",
      parse_mode="Markdown",
  )
  await callback.answer()


@dp.callback_query(F.data == "buy_sub")
async def process_buy(callback: types.CallbackQuery):
  await callback.message.answer(
      "🛒 **Покупка KolaCheat**\n\nНапиши админу для покупки: @твой_тег",
      parse_mode="Markdown",
  )
  await callback.answer()


@dp.callback_query(F.data == "gen_inf_key")
async def process_gen_inf(callback: types.CallbackQuery):
  if callback.from_user.id != ADMIN_ID:
    return
  key = f"KOLA-INF-{secrets.token_hex(4).upper()}"
  KEYS_DB[key] = {"expires": None, "hwid": None}
  await callback.message.answer(
      f"✅ **Бесконечный ключ:**\n`{key}`", parse_mode="Markdown"
  )
  await callback.answer()


@dp.callback_query(F.data == "gen_24h_key")
async def process_gen_24h(callback: types.CallbackQuery):
  if callback.from_user.id != ADMIN_ID:
    return
  key = f"KOLA-24H-{secrets.token_hex(4).upper()}"
  expire_time = datetime.now() + timedelta(hours=24)
  KEYS_DB[key] = {"expires": expire_time, "hwid": None}
  await callback.message.answer(
      f"✅ **Ключ на 24 часа:**\n`{key}`", parse_mode="Markdown"
  )
  await callback.answer()


@dp.callback_query(F.data == "list_keys")
async def process_list_keys(callback: types.CallbackQuery):
  if callback.from_user.id != ADMIN_ID:
    return
  if not KEYS_DB:
    await callback.message.answer("🔑 Ключей пока нет.")
    await callback.answer()
    return

  msg = "<b>📋 Активные ключи:</b>\n\n"
  for k, v in KEYS_DB.items():
    exp = (
        v["expires"].strftime("%Y-%m-%d %H:%M")
        if v["expires"]
        else "Бесконечный"
    )
    hw = v["hwid"] if v["hwid"] else "Не привязан"
    msg += f"🔑 <code>{k}</code> | До: {exp} | HWID: {hw}\n"
  await callback.message.answer(msg, parse_mode="HTML")
  await callback.answer()


async def main():
  server_thread = Thread(target=run_flask)
  server_thread.daemon = True
  server_thread.start()
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
