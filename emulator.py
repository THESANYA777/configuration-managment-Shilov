import tkinter as tk
from tkinter import ttk
import os
import socket
import sys
import argparse
import time
from typing import Optional

class ShellEmulatorGUI:
    def __init__(self, root, vfs_path: str, startup_script: Optional[str]):
        self.root = root
        self.vfs_path = vfs_path
        self.startup_script = startup_script

        # Данные ОС для заголовка
        try:
            username = os.getlogin() if os.name != 'nt' else os.environ.get('USERNAME', 'user')
        except Exception:
            username = 'user'
        hostname = socket.gethostname()
        title = f"Эмулятор - [{username}@{hostname}]"
        self.root.title(title)

        # Область вывода (терминал)
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

        # Отладочный вывод параметров (требование этапа 2)
        self._print_line("=== ОТЛАДОЧНЫЙ ВЫВОД ПАРАМЕТРОВ ===")
        self._print_line(f"VFS path: {self.vfs_path}")
        self._print_line(f"Startup script: {self.startup_script if self.startup_script else 'не задан'}")
        self._print_line("=====================================")

        # Если задан стартовый скрипт — выполняем его перед началом REPL
        if self.startup_script:
            self._print_line(f"\nЗапуск стартового скрипта: {self.startup_script}")
            self.run_startup_script(self.startup_script)
            self._print_line("[Скрипт завершён]\n")

        self._print_line("Добро пожаловать в эмулятор оболочки (REPL). Введите 'exit' для выхода.")
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

        # Показываем ввод пользователя как в терминале
        self._print_line(command_line)

        parts = command_line.split()
        cmd = parts[0].lower()
        args = parts[1:]

        try:
            result = self.execute_command(cmd, args)
            if result is not None:
                self._print_line(result)
        except Exception as e:
            self._print_line(f"Ошибка: {e}")

        self._print_prompt()

    def execute_command(self, cmd: str, args):
        if cmd == "exit":
            self.root.quit()
            return None

        elif cmd == "ls":
            return f"[ls] Вызвана команда ls с аргументами: {args}"

        elif cmd == "cd":
            if not args:
                return "[cd] Вызвана команда cd без аргументов."
            return f"[cd] Вызвана команда cd с аргументом(ами): {args}"

        else:
            raise ValueError(f"Неизвестная команда: {cmd}")

    def run_startup_script(self, script_path: str):
        """Выполняет стартовый скрипт: читает строки и выполняет их, ошибки пропускает"""
        if not os.path.isfile(script_path):
            self._print_line(f"Ошибка: файл скрипта не найден: {script_path}")
            return

        with open(script_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line or line.startswith("#"):
                    # Пропускаем пустые строки и комментарии
                    continue

                # Имитируем ввод пользователя
                self._print_line(line)

                parts = line.split()
                cmd = parts[0].lower()
                args = parts[1:]

                try:
                    result = self.execute_command(cmd, args)
                    if result is not None:
                        self._print_line(result)
                except Exception as e:
                    # Ошибочную строку пропускаем, но показываем ошибку
                    self._print_line(f"Строка {line_no}: ошибка — {e}")
                # Небольшая пауза, чтобы было видно «диалог»
                self.root.update()
                time.sleep(0.15)


def parse_args():
    parser = argparse.ArgumentParser(description="Эмулятор командной оболочки (REPL) с GUI")
    parser.add_argument("--vfs-path", type=str, default="./vfs", help="Путь к физическому расположению VFS")
    parser.add_argument("--startup-script", type=str, default=None, help="Путь к стартовому скрипту")
    return parser.parse_args()


def main():
    args = parse_args()
    root = tk.Tk()
    app = ShellEmulatorGUI(root, vfs_path=args.vfs_path, startup_script=args.startup_script)
    root.mainloop()


if __name__ == "__main__":
    main()
