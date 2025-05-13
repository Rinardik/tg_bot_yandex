from aiogram.fsm.state import State, StatesGroup


# Состояния регистрации
class RegistrationForm(StatesGroup):
    name = State()
    phone = State()
    password = State()
    password_confirm = State()


# Состояния входа
class LoginStates(StatesGroup):
    phone = State()
    password = State()


# Состояния восстановления пароля
class RecoveryForm(StatesGroup):
    phone = State()
    code = State()
    new_password = State()
    confirm_new_password = State()


# Состояния для работы с товарами
class ProductForm(StatesGroup):
    name = State()             # Название товара
    description = State()     # Описание
    price = State()           # Цена
    category = State()        # Категория
    subcategory = State()     # Подкатегория
    photo = State()           # Фото


# Состояния добавления категории
class CategoryForm(StatesGroup):
    name = State()  # Ввод названия категории


# Состояния добавления подкатегории
class SubcategoryForm(StatesGroup):
    category_name = State()      # Ввод названия категории
    subcategory_name = State()   # Ввод названия подкатегории


# Состояния редактирования товара
class RedactForm(StatesGroup):
    product_id = State()
    name = State()
    description = State()
    price = State()
    category = State()
    subcategory = State()
    photo = State()
    available = State()


# Состояние удаления товара
class DeleteForm(StatesGroup):
    id = State()