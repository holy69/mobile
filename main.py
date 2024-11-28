import sqlite3
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.graphics import Rectangle, Color

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('calculator.db')
    cursor = conn.cursor()

    # Создаем таблицы, если они еще не существуют
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS calculations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        calculation TEXT,
                        result TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS roles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        role_name TEXT NOT NULL)''')

    # Добавляем роли
    cursor.execute('''INSERT OR IGNORE INTO roles (role_name) VALUES ('admin')''')
    cursor.execute('''INSERT OR IGNORE INTO roles (role_name) VALUES ('user')''')

    conn.commit()
    conn.close()


# Окно калькулятора
class CalculatorWindow(Screen):
    def __init__(self, username, role, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.role = role
        self.layout = GridLayout(cols=4, padding=[10, 10, 10, 10], spacing=10)

        # Экран калькулятора
        self.result = TextInput(font_size=32, readonly=True, halign='right', multiline=False)
        self.layout.add_widget(self.result)

        # История вычислений
        self.history_label = Label(text="История:\n", size_hint_y=None, height=200)
        self.layout.add_widget(self.history_label)

        # Сетка кнопок
        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            'C', '0', '=', '+'
        ]

        for button in buttons:
            self.layout.add_widget(Button(text=button, on_press=self.on_button_press))

        # Кнопка очистки истории
        self.layout.add_widget(Button(text="Очистить историю", on_press=self.clear_history))

        # Если администратор, добавляем кнопку статистики
        if self.role == "admin":
            self.layout.add_widget(Button(text="Статистика", on_press=self.view_statistics))

        self.add_widget(self.layout)

        # Рисуем фон
        with self.canvas.before:
            Color(0.9, 0.9, 0.9, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)

    def on_button_press(self, instance):
        current = self.result.text
        text = instance.text

        if text == 'C':
            self.result.text = ''
        elif text == '=':
            try:
                calculation = self.result.text
                result = str(eval(calculation))
                self.result.text = result
                self.save_calculation(calculation, result)
                self.update_history(calculation, result)
            except Exception:
                self.result.text = 'Ошибка'
        else:
            self.result.text = current + text

    def save_calculation(self, calculation, result):
        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=?", (self.username,))
        user_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO calculations (user_id, calculation, result) VALUES (?, ?, ?)",
                       (user_id, calculation, result))
        conn.commit()
        conn.close()

    def clear_history(self, instance):
        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM calculations WHERE user_id = (SELECT id FROM users WHERE username=?)", (self.username,))
        conn.commit()
        conn.close()
        self.history_label.text = "История очищена."

    def update_history(self, calculation, result):
        history_text = self.history_label.text
        history_text += f"{calculation} = {result}\n"
        self.history_label.text = history_text

    def view_statistics(self, instance):
        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT users.username, calculations.calculation, calculations.result, calculations.timestamp
                          FROM calculations
                          JOIN users ON users.id = calculations.user_id
                          ORDER BY calculations.timestamp DESC LIMIT 10''')
        stats = cursor.fetchall()
        conn.close()

        stats_text = "Последние вычисления:\n"
        for stat in stats:
            stats_text += f"Пользователь: {stat[0]}, Выражение: {stat[1]}, Результат: {stat[2]}, Время: {stat[3]}\n"

        popup = Popup(title="Статистика", content=Label(text=stats_text), size_hint=(0.8, 0.8))
        popup.open()

    def on_size(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# Окно входа
class LoginWindow(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        self.username_input = TextInput(hint_text="Имя пользователя", multiline=False)
        self.password_input = TextInput(hint_text="Пароль", password=True, multiline=False)

        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)

        self.login_button = Button(text="Войти", on_press=self.login_user)
        self.register_button = Button(text="Зарегистрироваться", on_press=self.switch_to_register)
        self.reset_password_button = Button(text="Сбросить пароль", on_press=self.reset_password)

        self.layout.add_widget(self.login_button)
        self.layout.add_widget(self.register_button)
        self.layout.add_widget(self.reset_password_button)

        self.add_widget(self.layout)

    def login_user(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()

        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()

        if user:
            role = user[3]
            self.parent.switch_to(CalculatorWindow(username, role))
        else:
            self.show_popup('Ошибка', 'Неверное имя пользователя или пароль.')

    def reset_password(self, instance):
        username = self.username_input.text.strip()

        if not username:
            self.show_popup('Ошибка', 'Введите имя пользователя для сброса пароля.')
            return

        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user:
            self.show_reset_popup(username)
        else:
            self.show_popup('Ошибка', 'Пользователь с таким именем не найден.')

    def show_reset_popup(self, username):
        layout = BoxLayout(orientation='vertical', spacing=10)

        new_password_input = TextInput(hint_text="Введите новый пароль", password=True)
        layout.add_widget(new_password_input)

        def confirm_reset(instance):
            new_password = new_password_input.text.strip()
            if not new_password:
                reset_popup.content = Label(text="Пароль не может быть пустым!")
            else:
                conn = sqlite3.connect('calculator.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET password = ? WHERE username = ?', (new_password, username))
                conn.commit()
                conn.close()
                reset_popup.dismiss()
                self.show_popup('Успех', 'Пароль успешно сброшен!')

        reset_button = Button(text="Сбросить пароль", on_press=confirm_reset)
        layout.add_widget(reset_button)

        reset_popup = Popup(title=f"Сброс пароля для {username}", content=layout, size_hint=(0.8, 0.5))
        reset_popup.open()

    def switch_to_register(self, instance):
        self.parent.current = 'register'

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(None, None), size=(400, 200))
        popup.open()
# Окно калькулятора
class CalculatorWindow(Screen):
    def __init__(self, username, role, **kwargs):
        super().__init__(**kwargs)
        self.username = username
        self.role = role
        self.layout = GridLayout(cols=4, padding=[10, 10, 10, 10], spacing=10)

        # Экран калькулятора
        self.result = TextInput(font_size=32, readonly=True, halign='right', multiline=False)
        self.layout.add_widget(self.result)

        # История вычислений
        self.history_label = Label(text="История:\n", size_hint_y=None, height=200)
        self.layout.add_widget(self.history_label)

        # Сетка кнопок
        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            'C', '0', '=', '+'
        ]

        for button in buttons:
            self.layout.add_widget(Button(text=button, on_press=self.on_button_press))

        # Кнопка очистки истории
        self.layout.add_widget(Button(text="Очистить историю", on_press=self.clear_history))

        # Если администратор, добавляем кнопку статистики
        if self.role == "admin":
            self.layout.add_widget(Button(text="Статистика", on_press=self.view_statistics))

        self.add_widget(self.layout)

        # Рисуем фон
        with self.canvas.before:
            Color(0.9, 0.9, 0.9, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)

    def on_button_press(self, instance):
        current = self.result.text
        text = instance.text

        if text == 'C':
            self.result.text = ''
        elif text == '=':
            try:
                calculation = self.result.text
                result = str(eval(calculation))
                self.result.text = result
                self.save_calculation(calculation, result)
                self.update_history(calculation, result)
            except Exception:
                self.result.text = 'Ошибка'
        else:
            self.result.text = current + text

    def save_calculation(self, calculation, result):
        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username=?", (self.username,))
        user_id = cursor.fetchone()[0]
        cursor.execute("INSERT INTO calculations (user_id, calculation, result) VALUES (?, ?, ?)",
                       (user_id, calculation, result))
        conn.commit()
        conn.close()

    def clear_history(self, instance):
        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM calculations WHERE user_id = (SELECT id FROM users WHERE username=?)", (self.username,))
        conn.commit()
        conn.close()
        self.history_label.text = "История очищена."

    def update_history(self, calculation, result):
        history_text = self.history_label.text
        history_text += f"{calculation} = {result}\n"
        self.history_label.text = history_text

    def view_statistics(self, instance):
        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute('''SELECT users.username, calculations.calculation, calculations.result, calculations.timestamp
                          FROM calculations
                          JOIN users ON users.id = calculations.user_id
                          ORDER BY calculations.timestamp DESC LIMIT 10''')
        stats = cursor.fetchall()
        conn.close()

        stats_text = "Последние вычисления:\n"
        for stat in stats:
            stats_text += f"Пользователь: {stat[0]}, Выражение: {stat[1]}, Результат: {stat[2]}, Время: {stat[3]}\n"

        popup = Popup(title="Статистика", content=Label(text=stats_text), size_hint=(0.8, 0.8))
        popup.open()

    def on_size(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


# Окно входа
class LoginWindow(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        self.username_input = TextInput(hint_text="Имя пользователя", multiline=False)
        self.password_input = TextInput(hint_text="Пароль", password=True, multiline=False)

        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)

        self.login_button = Button(text="Войти", on_press=self.login_user)
        self.register_button = Button(text="Зарегистрироваться", on_press=self.switch_to_register)
        self.reset_password_button = Button(text="Сбросить пароль", on_press=self.reset_password)

        self.layout.add_widget(self.login_button)
        self.layout.add_widget(self.register_button)
        self.layout.add_widget(self.reset_password_button)

        self.add_widget(self.layout)

    def login_user(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()

        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()

        if user:
            role = user[3]
            self.parent.switch_to(CalculatorWindow(username, role))
        else:
            self.show_popup('Ошибка', 'Неверное имя пользователя или пароль.')

    def reset_password(self, instance):
        username = self.username_input.text.strip()

        if not username:
            self.show_popup('Ошибка', 'Введите имя пользователя для сброса пароля.')
            return

        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user:
            self.show_reset_popup(username)
        else:
            self.show_popup('Ошибка', 'Пользователь с таким именем не найден.')

    def show_reset_popup(self, username):
        layout = BoxLayout(orientation='vertical', spacing=10)

        new_password_input = TextInput(hint_text="Введите новый пароль", password=True)
        layout.add_widget(new_password_input)

        def confirm_reset(instance):
            new_password = new_password_input.text.strip()
            if not new_password:
                reset_popup.content = Label(text="Пароль не может быть пустым!")
            else:
                conn = sqlite3.connect('calculator.db')
                cursor = conn.cursor()
                cursor.execute('UPDATE users SET password = ? WHERE username = ?', (new_password, username))
                conn.commit()
                conn.close()
                reset_popup.dismiss()
                self.show_popup('Успех', 'Пароль успешно сброшен!')

        reset_button = Button(text="Сбросить пароль", on_press=confirm_reset)
        layout.add_widget(reset_button)

        reset_popup = Popup(title=f"Сброс пароля для {username}", content=layout, size_hint=(0.8, 0.5))
        reset_popup.open()

    def switch_to_register(self, instance):
        self.parent.current = 'register'

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(None, None), size=(400, 200))
        popup.open()


# Окно регистрации
class RegisterWindow(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        self.username_input = TextInput(hint_text="Имя пользователя")
        self.password_input = TextInput(hint_text="Пароль", password=True)
        self.role_input = TextInput(hint_text="Роль (user/admin)")

        self.layout.add_widget(self.username_input)
        self.layout.add_widget(self.password_input)
        self.layout.add_widget(self.role_input)

        self.register_button = Button(text="Зарегистрироваться", on_press=self.register_user)
        self.layout.add_widget(self.register_button)

        self.add_widget(self.layout)

    def register_user(self, instance):
        username = self.username_input.text.strip()
        password = self.password_input.text.strip()
        role = self.role_input.text.strip()

        if not username or not password or not role:
            self.show_popup("Ошибка", "Пожалуйста, заполните все поля.")
            return

        conn = sqlite3.connect('calculator.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

        if user:
            self.show_popup("Ошибка", "Пользователь с таким именем уже существует.")
        else:
            cursor.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                           (username, password, role))
            conn.commit()
            self.show_popup("Успех", "Пользователь успешно зарегистрирован.")
            self.username_input.text = ""
            self.password_input.text = ""
            self.role_input.text = ""

        conn.close()

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(None, None), size=(400, 200))
        popup.open()


# Основное окно
class CalculatorApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginWindow(name="login"))
        sm.add_widget(RegisterWindow(name="register"))

        return sm


if __name__ == '__main__':
    init_db()
    CalculatorApp().run()
