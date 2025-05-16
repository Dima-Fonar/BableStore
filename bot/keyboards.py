from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu():
       keyboard = [
           [InlineKeyboardButton("Каталог товаров", callback_data='catalog')],
           [InlineKeyboardButton("Корзина", callback_data='cart')]
       ]
       return InlineKeyboardMarkup(keyboard)

def get_categories_keyboard(categories):
       keyboard = [[InlineKeyboardButton(category.name, callback_data=f'category_{category.id}')] for category in categories]
       return InlineKeyboardMarkup(keyboard)

def get_materials_keyboard(category_id, materials):
       keyboard = [[InlineKeyboardButton(material, callback_data=f'material_{category_id}_{material}')] for material in materials]
       return InlineKeyboardMarkup(keyboard)

def get_product_card(product_id, current_index, total_products):
       keyboard = [
           [InlineKeyboardButton("Добавить в корзину", callback_data=f'buy_{product_id}')],
           [
               InlineKeyboardButton("⬅️", callback_data='prev_product') if current_index > 0 else InlineKeyboardButton(" ", callback_data='noop'),
               InlineKeyboardButton("➡️", callback_data='next_product') if current_index < total_products - 1 else InlineKeyboardButton(" ", callback_data='noop')
           ]
       ]
       return InlineKeyboardMarkup(keyboard)