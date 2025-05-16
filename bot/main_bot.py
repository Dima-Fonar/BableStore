import os
import sys
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import Updater, Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes
import asyncio
from app import db, create_app
from app.models import Category, Product, Order, OrderItem
from bot.keyboards import get_categories_keyboard, get_materials_keyboard, get_product_card
from config import Config  # Импортируем конфиг

# Определение состояний для ConversationHandler
CATEGORY, MATERIAL, PRODUCT, CART, ORDER_FORM, PAYMENT, CONFIRM_PAYMENT, DELIVERY, ADDRESS = range(9)

# Используем UPLOAD_FOLDER из конфига
UPLOADS_DIR = Config.UPLOAD_FOLDER

# Inline-клавиатура в одну линию
def get_inline_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]
    ])

# ... (остальной код остается без изменений, просто замените UPLOADS_DIR на Config.UPLOAD_FOLDER в соответствующих местах)

# Функция start для обработки команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Received /start command")  # Отладка
    await update.message.reply_text("Добро пожаловать! Выберите действие:", reply_markup=get_inline_menu())
    return CATEGORY

# Функции для обработки различных состояний
async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Showing categories")  # Отладка
    categories = Category.query.all()
    keyboard = get_categories_keyboard(categories)
    new_keyboard = InlineKeyboardMarkup(
        keyboard.inline_keyboard + tuple([[InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]])
    )
    if update.callback_query.message.photo:
        await update.callback_query.message.edit_caption(
            caption="Выберите категорию:",
            reply_markup=new_keyboard
        )
    elif update.callback_query.message.text:
        await update.callback_query.message.edit_text("Выберите категорию:", reply_markup=new_keyboard)
    else:
        await update.callback_query.message.chat.send_message(
            text="Выберите категорию:",
            reply_markup=new_keyboard
        )
    return MATERIAL

async def show_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Showing materials")  # Отладка
    category_id = int(update.callback_query.data.split('_')[1])
    products = Product.query.filter_by(category_id=category_id).all()
    materials = list(set(product.material for product in products))
    keyboard = get_materials_keyboard(category_id, materials)
    new_keyboard = InlineKeyboardMarkup(
        keyboard.inline_keyboard + tuple([[InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]])
    )
    if update.callback_query.message.photo:
        await update.callback_query.message.edit_caption(
            caption="Выберите материал:",
            reply_markup=new_keyboard
        )
    elif update.callback_query.message.text:
        await update.callback_query.message.edit_text("Выберите материал:", reply_markup=new_keyboard)
    else:
        await update.callback_query.message.chat.send_message(
            text="Выберите материал:",
            reply_markup=new_keyboard
        )
    return PRODUCT

async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Current state: {context.user_data.get('__current_state')}")  # Отладка состояния
    _, category_id, material = update.callback_query.data.split('_')
    products = Product.query.filter_by(category_id=int(category_id), material=material).all()
    if not products:
        await update.callback_query.message.edit_text("Товары не найдены.", reply_markup=get_inline_menu())
        return ConversationHandler.END
    context.user_data['products'] = products
    context.user_data['current_index'] = 0
    product = products[0]
    keyboard = get_product_card(product.id, 0, len(products))
    new_keyboard = InlineKeyboardMarkup(
        keyboard.inline_keyboard + tuple([[InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]])
    )
    image_path = os.path.join(UPLOADS_DIR, product.image) if product.image else None
    print(f"Attempting to load image from: {image_path}, Image value: {product.image}, File exists: {os.path.exists(image_path) if image_path else False}")
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as photo:
                print(f"Sending photo from: {image_path}, Size: {os.path.getsize(image_path)} bytes")
                message = await update.callback_query.message.chat.send_photo(
                    photo=photo,
                    caption=f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}",
                    reply_markup=new_keyboard
                )
                context.user_data['current_message_id'] = message.message_id
        except Exception as e:
            print(f"Error sending image: {e}")
            await update.callback_query.message.edit_text(
                f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}\n(Ошибка загрузки изображения: {e})",
                reply_markup=new_keyboard
            )
    else:
        dir_contents = os.listdir(UPLOADS_DIR) if os.path.exists(UPLOADS_DIR) else "Directory does not exist"
        print(f"Image file not found at: {image_path}. Checking directory contents: {dir_contents}")
        message = await update.callback_query.message.chat.send_message(
            text=f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}\n(Изображение отсутствует. Проверьте файлы в {UPLOADS_DIR})",
            reply_markup=new_keyboard
        )
        context.user_data['current_message_id'] = message.message_id
    return PRODUCT

async def navigate_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Current state: {context.user_data.get('__current_state')}")
    products = context.user_data.get('products', [])
    current_index = context.user_data.get('current_index', 0)
    if 'next' in update.callback_query.data:
        current_index += 1
    elif 'prev' in update.callback_query.data:
        current_index -= 1
    context.user_data['current_index'] = current_index
    product = products[current_index]
    keyboard = get_product_card(product.id, current_index, len(products))
    new_keyboard = InlineKeyboardMarkup(
        keyboard.inline_keyboard + tuple([[InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]])
    )
    image_path = os.path.join(UPLOADS_DIR, product.image) if product.image else None
    print(f"Attempting to load image from: {image_path}, Image value: {product.image}, File exists: {os.path.exists(image_path) if image_path else False}")
    message_id = context.user_data.get('current_message_id')
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as photo:
                print(f"Editing photo from: {image_path}, Size: {os.path.getsize(image_path)} bytes")
                media = InputMediaPhoto(media=photo, caption=f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}")
                await context.bot.edit_message_media(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=new_keyboard
                )
        except Exception as e:
            print(f"Error editing image: {e}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}\n(Ошибка загрузки изображения: {e})",
                reply_markup=new_keyboard
            )
    else:
        dir_contents = os.listdir(UPLOADS_DIR) if os.path.exists(UPLOADS_DIR) else "Directory does not exist"
        print(f"Image file not found at: {image_path}. Checking directory contents: {dir_contents}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}\n(Изображение отсутствует. Проверьте файлы в {UPLOADS_DIR})",
            reply_markup=new_keyboard
        )
    return PRODUCT

async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Current state: {context.user_data.get('__current_state')}")
    product_id = int(update.callback_query.data.split('_')[1])
    if 'cart' not in context.user_data:
        context.user_data['cart'] = []
    context.user_data['cart'].append(product_id)
    print(f"Added to cart: {product_id}, Cart contents: {context.user_data['cart']}")
    products = context.user_data.get('products', [])
    current_index = context.user_data.get('current_index', 0)
    product = products[current_index]
    keyboard = get_product_card(product.id, current_index, len(products))
    new_keyboard = InlineKeyboardMarkup(
        keyboard.inline_keyboard + tuple([[InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]])
    )
    image_path = os.path.join(UPLOADS_DIR, product.image) if product.image else None
    print(f"Attempting to load image from: {image_path}, Image value: {product.image}, File exists: {os.path.exists(image_path) if image_path else False}")
    message_id = context.user_data.get('current_message_id')
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as photo:
                print(f"Editing photo from: {image_path}, Size: {os.path.getsize(image_path)} bytes")
                media = InputMediaPhoto(media=photo, caption=f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}\nТовар добавлен в корзину!")
                await context.bot.edit_message_media(
                    chat_id=update.effective_chat.id,
                    message_id=message_id,
                    media=media,
                    reply_markup=new_keyboard
                )
        except Exception as e:
            print(f"Error editing image: {e}")
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}\nТовар добавлен в корзину!\n(Ошибка загрузки изображения: {e})",
                reply_markup=new_keyboard
            )
    else:
        dir_contents = os.listdir(UPLOADS_DIR) if os.path.exists(UPLOADS_DIR) else "Directory does not exist"
        print(f"Image file not found at: {image_path}. Checking directory contents: {dir_contents}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=message_id,
            text=f"{product.name}\nМатериал: {product.material}\nЦена: {product.price}\nТовар добавлен в корзину!\n(Изображение отсутствует. Проверьте файлы в {UPLOADS_DIR})",
            reply_markup=new_keyboard
        )
    return PRODUCT

async def show_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Current state: {context.user_data.get('__current_state')}")
    cart = context.user_data.get('cart', [])
    print(f"Showing cart: {cart}")
    if not cart:
        await update.callback_query.message.edit_text("Корзина пуста.", reply_markup=get_inline_menu())
        return ConversationHandler.END
    products = Product.query.filter(Product.id.in_(cart)).all()
    if not products:
        await update.callback_query.message.edit_text("Товары в корзине не найдены.", reply_markup=get_inline_menu())
        return ConversationHandler.END
    total = sum(product.price for product in products)
    message = "Ваша корзина:\n" + "\n".join(f"{p.name}: {p.price}" for p in products) + f"\nИтого: {total}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Оформить заказ", callback_data='checkout')],
        [InlineKeyboardButton("Назад", callback_data='back_to_catalog')],
        [InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]
    ])
    if update.callback_query.message.photo:
        await update.callback_query.message.edit_caption(
            caption=message,
            reply_markup=keyboard
        )
    elif update.callback_query.message.text:
        current_message = update.callback_query.message.text if update.callback_query.message.text else ""
        current_reply_markup = update.callback_query.message.reply_markup.to_json() if update.callback_query.message.reply_markup else ""
        new_reply_markup = keyboard.to_json()
        if current_message != message or current_reply_markup != new_reply_markup:
            await update.callback_query.message.edit_text(message, reply_markup=keyboard)
        else:
            print("Message not modified, skipping edit_text")
    else:
        await update.callback_query.message.chat.send_message(
            text=message,
            reply_markup=keyboard
        )
    return CART

async def checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Entering checkout, current state: {context.user_data.get('__current_state')}")
    if update.callback_query.message.photo:
        await update.callback_query.message.edit_caption(
            caption="Введите ваше имя:",
            reply_markup=get_inline_menu()
        )
    elif update.callback_query.message.text:
        await update.callback_query.message.edit_text("Введите ваше имя:", reply_markup=get_inline_menu())
    else:
        await update.callback_query.message.chat.send_message(
            text="Введите ваше имя:",
            reply_markup=get_inline_menu()
        )
    return ORDER_FORM

async def save_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Saving name: {update.message.text}, current state: {context.user_data.get('__current_state')}")
    context.user_data['name'] = update.message.text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Наличные", callback_data='cash')],
        [InlineKeyboardButton("Карта", callback_data='card')],
        [InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]
    ])
    await update.message.reply_text("Выберите способ оплаты:", reply_markup=keyboard)
    return PAYMENT

async def save_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Saving payment: {update.callback_query.data}, current state: {context.user_data.get('__current_state')}")
    context.user_data['payment'] = update.callback_query.data
    if context.user_data['payment'] == 'card':
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Оплатить", callback_data='pay_now')],
            [InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]
        ])
        message = "Подтвердите оплату по карте:"
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Подтвердить", callback_data='confirm_cash')],
            [InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]
        ])
        message = "Подтвердите оплату наличными при получении:"
    if update.callback_query.message.photo:
        await update.callback_query.message.edit_caption(
            caption=message,
            reply_markup=keyboard
        )
    elif update.callback_query.message.text:
        await update.callback_query.message.edit_text(message, reply_markup=keyboard)
    else:
        await update.callback_query.message.chat.send_message(
            text=message,
            reply_markup=keyboard
        )
    return CONFIRM_PAYMENT

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Confirming payment: {update.callback_query.data}, current state: {context.user_data.get('__current_state')}")
    payment_method = context.user_data.get('payment')
    if payment_method == 'card' and update.callback_query.data == 'pay_now':
        context.user_data['payment_confirmed'] = True
        message = "Оплата по карте подтверждена! (Для теста, ссылка на оплату не отправляется)"
    else:
        context.user_data['payment_confirmed'] = True
        message = "Оплата наличными подтверждена!"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Доставка", callback_data='delivery')],
        [InlineKeyboardButton("Самовывоз", callback_data='pickup')],
        [InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]
    ])
    if update.callback_query.message.photo:
        await update.callback_query.message.edit_caption(
            caption=f"{message}\nВыберите способ доставки:",
            reply_markup=keyboard
        )
    elif update.callback_query.message.text:
        await update.callback_query.message.edit_text(f"{message}\nВыберите способ доставки:", reply_markup=keyboard)
    else:
        await update.callback_query.message.chat.send_message(
            text=f"{message}\nВыберите способ доставки:",
            reply_markup=keyboard
        )
    return DELIVERY

async def save_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Saving delivery: {update.callback_query.data}, current state: {context.user_data.get('__current_state')}")
    context.user_data['delivery'] = update.callback_query.data
    if context.user_data['delivery'] == 'delivery':
        message = "Пожалуйста, укажите адрес доставки:"
        keyboard = get_inline_menu()
        if update.callback_query.message.photo:
            await update.callback_query.message.edit_caption(
                caption=message,
                reply_markup=keyboard
            )
        elif update.callback_query.message.text:
            await update.callback_query.message.edit_text(message, reply_markup=keyboard)
        else:
            await update.callback_query.message.chat.send_message(
                text=message,
                reply_markup=keyboard
            )
        return ADDRESS
    else:
        order = Order(
            customer_name=context.user_data['name'],
            telegram_id=str(update.effective_user.id),
            payment_method=context.user_data['payment'],
            delivery_method=context.user_data['delivery'],
            address="Самовывоз"
        )
        db.session.add(order)
        db.session.commit()
        cart = context.user_data.get('cart', [])
        for product_id in cart:
            order_item = OrderItem(order_id=order.id, product_id=product_id, quantity=1)
            db.session.add(order_item)
        db.session.commit()
        context.user_data['cart'] = []
        message = "Заказ оформлен! Спасибо! Вы выбрали самовывоз.\nВведите /start для продолжения."
        if update.callback_query.message.photo:
            await update.callback_query.message.edit_caption(
                caption=message,
                reply_markup=get_inline_menu()
            )
        elif update.callback_query.message.text:
            await update.callback_query.message.edit_text(message, reply_markup=get_inline_menu())
        else:
            await update.callback_query.message.chat.send_message(
                text=message,
                reply_markup=get_inline_menu()
            )
        context.user_data.clear()
        return ConversationHandler.END

async def save_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Saving address: {update.message.text}, current state: {context.user_data.get('__current_state')}")
    context.user_data['address'] = update.message.text
    order = Order(
        customer_name=context.user_data['name'],
        telegram_id=str(update.effective_user.id),
        payment_method=context.user_data['payment'],
        delivery_method=context.user_data['delivery'],
        address=context.user_data['address']
    )
    db.session.add(order)
    db.session.commit()
    cart = context.user_data.get('cart', [])
    for product_id in cart:
        order_item = OrderItem(order_id=order.id, product_id=product_id, quantity=1)
        db.session.add(order_item)
    db.session.commit()
    context.user_data['cart'] = []
    message = "Заказ оформлен! Спасибо!\nВведите /start для продолжения."
    await update.message.reply_text(message, reply_markup=get_inline_menu())
    context.user_data.clear()
    return ConversationHandler.END

# Обработчик для возврата к каталогу
async def back_to_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Returning to catalog")
    categories = Category.query.all()
    keyboard = get_categories_keyboard(categories)
    new_keyboard = InlineKeyboardMarkup(
        keyboard.inline_keyboard + tuple([[InlineKeyboardButton("Каталог товаров", callback_data='catalog'), InlineKeyboardButton("Корзина", callback_data='cart')]])
    )
    if update.callback_query.message.photo:
        await update.callback_query.message.edit_caption(
            caption="Выберите категорию:",
            reply_markup=new_keyboard
        )
    elif update.callback_query.message.text:
        await update.callback_query.message.edit_text("Выберите категорию:", reply_markup=new_keyboard)
    else:
        await update.callback_query.message.chat.send_message(
            text="Выберите категорию:",
            reply_markup=new_keyboard
        )
    return MATERIAL

# Настройка ConversationHandler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        CATEGORY: [CallbackQueryHandler(show_categories, pattern='catalog')],
        MATERIAL: [CallbackQueryHandler(show_materials, pattern='category_')],
        PRODUCT: [
            CallbackQueryHandler(show_product, pattern='material_'),
            CallbackQueryHandler(navigate_product, pattern='next_|prev_'),
            CallbackQueryHandler(add_to_cart, pattern='buy_'),
            CallbackQueryHandler(show_cart, pattern='cart')
        ],
        CART: [
            CallbackQueryHandler(show_cart, pattern='cart'),
            CallbackQueryHandler(show_categories, pattern='catalog'),
            CallbackQueryHandler(checkout, pattern='checkout')
        ],
        ORDER_FORM: [CallbackQueryHandler(checkout, pattern='checkout'), MessageHandler(filters.TEXT & ~filters.COMMAND, save_name)],
        PAYMENT: [CallbackQueryHandler(save_payment)],
        CONFIRM_PAYMENT: [CallbackQueryHandler(confirm_payment, pattern='pay_now|confirm_cash')],
        DELIVERY: [CallbackQueryHandler(save_delivery)],
        ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_address)]
    },
    fallbacks=[CallbackQueryHandler(back_to_catalog, pattern='back_to_catalog'), CallbackQueryHandler(show_cart, pattern='cart')],
    per_message=False
)

# Основная функция для запуска бота
async def main():
    print("Current working directory:", os.getcwd())
    print("Python path:", sys.path)
    app = create_app()
    with app.app_context():
        bot_app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        bot_app.add_handler(conv_handler)
        print("Starting bot")
        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()
        await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())