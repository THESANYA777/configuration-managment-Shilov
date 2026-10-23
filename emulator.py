import tkinter as tk
from tkinter import ttk
import os
import socket
import sys

class ShellEmulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Эмулятор")

        # Получаем данные ОС для заголовка: user@host
        username = os.getlogin() if os.name != 'nt' else os.environ.get('USERNAME', 'user')
        hostname = socket.gethostname()
        title = f"Эмулятор - [{username}@{hostname}]"
        self.root.title(title)

        # Область вывода (аналог терминала)
        self.output_text = tk.Text(root, wrap='word', bg='#1e1e1e', fg='#00ff00', font=("Consolas", 12))
        self.output_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Строка ввода
        self.input_frame = ttk.Frame(root)
        self.input_frame.pack(fill='x', padx=5, pady=(0, 5))

        self.prompt_label = ttk.Label(self.input_frame, text="$ ", width=3)
        self.prompt_label.pack(side='left')

        self.input_entry = ttk.Entry(self.input_frame, font=("Consolas", 12))
        self.input_entry.pack(side='left', fill='x', expand=True)
        self.input_entry.bind("<Return>", self.on_enter)
        self.input_entry.focus()

        # Инициализация
        self._print_line(f"Добро пожаловать в эмулятор оболочки (REPL). Введите 'exit' для выхода.")
        self._print_prompt()

    def _print_line(self, text: str):
        """Добавить строку в область вывода"""
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

    def _print_prompt(self):
        """Вывести приглашение к вводу"""
        self.output_text.insert(tk.END, "$ ")
        self.output_text.see(tk.END)

    def on_enter(self, event=None):
        command_line = self.input_entry.get().strip()
        self.input_entry.delete(0, tk.END)

        if not command_line:
            self._print_prompt()
            return

        # Вывод строки пользователя в область вывода (чтобы выглядело как терминал)
        self._print_line(command_line)

        # Парсинг: команда + аргументы по пробелам
        parts = command_line.split()
        cmd = parts[0].lower()
        args = parts[1:]

        try:
            result = self.execute_command(cmd, args)
            if result:
                self._print_line(result)
        except Exception as e:
            self._print_line(f"Ошибка: {e}")

        self._print_prompt()

    def execute_command(self, cmd: str, args):
        if cmd == "exit":
            self.root.quit()
            return None

        elif cmd == "ls":
            # Заглушка: выводим команду и аргументы
            return f"[ls] Вызвана команда ls с аргументами: {args}"

        elif cmd == "cd":
            if not args:
                return "[cd] Вызвана команда cd без аргументов."
            return f"[cd] Вызвана команда cd с аргументом(ами): {args}"

        else:
            raise ValueError(f"Неизвестная команда: {cmd}")


def main():
    root = tk.Tk()
    app = ShellEmulatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
