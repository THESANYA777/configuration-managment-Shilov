import argparse
import base64
import json
import os
import shlex
import socket
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk


class VFSError(Exception):
    """Ошибка виртуальной файловой системы."""


class VirtualFileSystem:
    """
    VFS хранится в JSON и целиком загружается в память.
    Команды оболочки не изменяют JSON и не записывают содержимое VFS на диск.

    Формат узла:
      каталог: {"type": "dir", "children": {"имя": узел, ...}}
      текстовый файл: {"type": "file", "content": "текст"}
      двоичный файл: {"type": "file", "encoding": "base64", "content": "..."}
    """

    def __init__(self, json_path: str):
        self.json_path = self._resolve_json_path(json_path)
        try:
            with self.json_path.open("r", encoding="utf-8") as stream:
                raw = json.load(stream)
        except FileNotFoundError as exc:
            raise VFSError(f"JSON-файл VFS не найден: {self.json_path}") from exc
        except json.JSONDecodeError as exc:
            raise VFSError(f"Некорректный JSON VFS: {exc}") from exc
        except OSError as exc:
            raise VFSError(f"Не удалось прочитать VFS: {exc}") from exc

        if not isinstance(raw, dict) or not isinstance(raw.get("root"), dict):
            raise VFSError("Формат VFS: в корне JSON должен находиться объект 'root'.")
        self.root = raw["root"]
        self._validate_node(self.root, "/")
        if self.root.get("type") != "dir":
            raise VFSError("Узел root должен быть каталогом.")
        self.cwd = "/"

    @staticmethod
    def _resolve_json_path(path: str) -> Path:
        candidate = Path(path).expanduser()
        if candidate.is_dir():
            # Поддержка старого значения --vfs-path, указывающего на каталог.
            for name in ("multi.json", "default.json", "vfs.json", "minimal.json"):
                possible = candidate / name
                if possible.is_file():
                    return possible
            raise VFSError(
                f"В каталоге {candidate} не найден JSON VFS "
                "(ожидался multi.json, default.json, vfs.json или minimal.json)."
            )
        return candidate

    def _validate_node(self, node: Dict[str, Any], location: str) -> None:
        if not isinstance(node, dict):
            raise VFSError(f"Узел {location}: ожидался JSON-объект.")
        kind = node.get("type")
        if kind == "dir":
            children = node.get("children", {})
            if not isinstance(children, dict):
                raise VFSError(f"Каталог {location}: 'children' должен быть объектом.")
            for name, child in children.items():
                if not isinstance(name, str) or name in ("", ".", "..") or "/" in name:
                    raise VFSError(f"Недопустимое имя узла в {location}: {name!r}")
                self._validate_node(child, str(PurePosixPath(location) / name))
        elif kind == "file":
            content = node.get("content", "")
            if not isinstance(content, str):
                raise VFSError(f"Файл {location}: 'content' должен быть строкой.")
            if node.get("encoding", "utf-8") not in ("utf-8", "base64"):
                raise VFSError(f"Файл {location}: поддерживаются utf-8 и base64.")
            if node.get("encoding", "utf-8") == "base64":
                try:
                    base64.b64decode(content, validate=True)
                except (ValueError, base64.binascii.Error) as exc:
                    raise VFSError(f"Файл {location}: неверные данные base64.") from exc
        else:
            raise VFSError(f"Узел {location}: type должен быть 'dir' или 'file'.")

    def _absolute(self, path: str = ".") -> str:
        if path.startswith("/"):
            combined = PurePosixPath(path)
        else:
            combined = PurePosixPath(self.cwd) / path
        parts: List[str] = []
        for part in combined.parts:
            if part in ("/", "", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)
        return "/" + "/".join(parts)

    def _node(self, path: str = ".") -> Dict[str, Any]:
        absolute = self._absolute(path)
        node = self.root
        if absolute == "/":
            return node
        for part in absolute.strip("/").split("/"):
            if node.get("type") != "dir":
                raise VFSError(f"Это не каталог: {part}")
            children = node.get("children", {})
            if part not in children:
                raise VFSError(f"Путь не найден: {absolute}")
            node = children[part]
        return node

    def ls(self, path: str = ".") -> str:
        node = self._node(path)
        absolute = self._absolute(path)
        if node["type"] == "file":
            return PurePosixPath(absolute).name
        children = node.get("children", {})
        if not children:
            return "(пусто)"
        lines = []
        for name in sorted(children):
            child = children[name]
            suffix = "/" if child["type"] == "dir" else ""
            lines.append(name + suffix)
        return "\n".join(lines)

    def cd(self, path: str = "/") -> str:
        node = self._node(path)
        if node["type"] != "dir":
            raise VFSError(f"Не каталог: {self._absolute(path)}")
        self.cwd = self._absolute(path)
        return ""

    def cat(self, path: str) -> str:
        node = self._node(path)
        if node["type"] != "file":
            raise VFSError(f"Это каталог, а не файл: {self._absolute(path)}")
        content = node.get("content", "")
        if node.get("encoding", "utf-8") == "base64":
            data = base64.b64decode(content)
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return (
                    f"[двоичный файл: {len(data)} байт; "
                    f"содержимое не выводится как текст]"
                )
        return content

    def tree(self, path: str = ".") -> str:
        start = self._node(path)
        if start["type"] == "file":
            return PurePosixPath(self._absolute(path)).name
        lines = [self._absolute(path)]

        def visit(node: Dict[str, Any], prefix: str) -> None:
            children = node.get("children", {})
            names = sorted(children)
            for index, name in enumerate(names):
                child = children[name]
                last = index == len(names) - 1
                lines.append(prefix + ("└── " if last else "├── ") + name +
                             ("/" if child["type"] == "dir" else ""))
                if child["type"] == "dir":
                    visit(child, prefix + ("    " if last else "│   "))
        visit(start, "")
        return "\n".join(lines)

    def pwd(self) -> str:
        return self.cwd


class ShellEmulatorGUI:
    def __init__(self, root, vfs_path: str, startup_script: Optional[str]):
        self.root = root
        self.vfs_path = vfs_path
        self.startup_script = startup_script

        try:
            username = os.getlogin() if os.name != "nt" else os.environ.get("USERNAME", "user")
        except Exception:
            username = os.environ.get("USER", "user")
        hostname = socket.gethostname()
        self.root.title(f"Эмулятор - [{username}@{hostname}]")

        try:
            self.vfs = VirtualFileSystem(vfs_path)
            self.vfs_error = None
        except VFSError as exc:
            self.vfs = None
            self.vfs_error = str(exc)

        self.output_text = tk.Text(
            root, wrap="word", bg="#1e1e1e", fg="#00ff00",
            insertbackground="#ffffff", font=("Consolas", 12)
        )
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.input_frame = ttk.Frame(root)
        self.input_frame.pack(fill="x", padx=5, pady=(0, 5))
        self.prompt_label = ttk.Label(self.input_frame, text="$ ", width=3)
        self.prompt_label.pack(side="left")
        self.input_entry = ttk.Entry(self.input_frame, font=("Consolas", 12))
        self.input_entry.pack(side="left", fill="x", expand=True)
        self.input_entry.bind("<Return>", self.on_enter)
        self.input_entry.focus()

        # Сохраняем диагностический вывод предыдущего этапа.
        self._print_line("=== ОТЛАДОЧНЫЙ ВЫВОД ПАРАМЕТРОВ ===")
        self._print_line(f"VFS path: {self.vfs_path}")
        self._print_line(f"Startup script: {self.startup_script if self.startup_script else 'не задан'}")
        self._print_line("=====================================")
        if self.vfs_error:
            self._print_line(f"Ошибка загрузки VFS: {self.vfs_error}")
        else:
            self._print_line(f"VFS загружена в память: {self.vfs.json_path}")
        if self.startup_script:
            self._print_line(f"\nЗапуск стартового скрипта: {self.startup_script}")
            self.run_startup_script(self.startup_script)
            self._print_line("[Скрипт завершён]\n")
        self._print_line("Добро пожаловать в эмулятор оболочки (REPL). Введите 'help' для справки, 'exit' для выхода.")
        self._print_prompt()

    def _print_line(self, text: str):
        self.output_text.insert(tk.END, text + "\n")
        self.output_text.see(tk.END)

    def _print_prompt(self):
        cwd = self.vfs.pwd() if self.vfs else "?"
        self.output_text.insert(tk.END, f"{cwd} $ ")
        self.output_text.see(tk.END)

    def on_enter(self, event=None):
        command_line = self.input_entry.get().strip()
        self.input_entry.delete(0, tk.END)
        if not command_line:
            self._print_prompt()
            return
        self._print_line(command_line)
        try:
            parts = shlex.split(command_line)
            if parts:
                result = self.execute_command(parts[0].lower(), parts[1:])
                if result is not None and result != "":
                    self._print_line(result)
        except Exception as exc:
            self._print_line(f"Ошибка: {exc}")
        self._print_prompt()

    def execute_command(self, cmd: str, args: List[str]):
        if cmd == "exit":
            self.root.quit()
            return None
        if cmd == "help":
            return (
                "Доступные команды:\n"
                "  help                 — справка\n"
                "  ls [путь]            — список файлов и каталогов\n"
                "  cd [путь]            — перейти в каталог (без аргумента: /)\n"
                "  pwd                  — текущий виртуальный каталог\n"
                "  cat <файл>           — вывести текстовый файл\n"
                "  tree [путь]          — дерево VFS\n"
                "  vfsinfo              — сведения о загруженной VFS\n"
                "  exit                 — выход\n"
                "Пути абсолютные (/docs/readme.txt) или относительные (../file.txt)."
            )
        if cmd in ("ls", "cd", "pwd", "cat", "tree", "vfsinfo") and self.vfs is None:
            raise VFSError("VFS не загружена. Проверьте --vfs-path и JSON-файл.")
        if cmd == "ls":
            if len(args) > 1:
                raise ValueError("Использование: ls [путь]")
            return self.vfs.ls(args[0] if args else ".")
        if cmd == "cd":
            if len(args) > 1:
                raise ValueError("Использование: cd [путь]")
            return self.vfs.cd(args[0] if args else "/")
        if cmd == "pwd":
            if args:
                raise ValueError("Использование: pwd")
            return self.vfs.pwd()
        if cmd == "cat":
            if len(args) != 1:
                raise ValueError("Использование: cat <файл>")
            return self.vfs.cat(args[0])
        if cmd == "tree":
            if len(args) > 1:
                raise ValueError("Использование: tree [путь]")
            return self.vfs.tree(args[0] if args else ".")
        if cmd == "vfsinfo":
            if args:
                raise ValueError("Использование: vfsinfo")
            return (
                f"JSON: {self.vfs.json_path}\n"
                f"Текущий каталог: {self.vfs.pwd()}\n"
                "Режим: только чтение; изменения VFS не сохраняются."
            )
        raise ValueError(f"Неизвестная команда: {cmd}")

    def run_startup_script(self, script_path: str):
        if not os.path.isfile(script_path):
            self._print_line(f"Ошибка: файл скрипта не найден: {script_path}")
            return
        try:
            with open(script_path, "r", encoding="utf-8") as stream:
                for line_no, line in enumerate(stream, start=1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    self._print_line(f"$ {line}")
                    try:
                        parts = shlex.split(line)
                        if parts:
                            result = self.execute_command(parts[0].lower(), parts[1:])
                            if result is not None and result != "":
                                self._print_line(result)
                    except Exception as exc:
                        self._print_line(f"Строка {line_no}: ошибка — {exc}")
                    self.root.update()
                    time.sleep(0.05)
        except OSError as exc:
            self._print_line(f"Ошибка чтения стартового скрипта: {exc}")


def parse_args():
    parser = argparse.ArgumentParser(description="Эмулятор командной оболочки (REPL) с GUI и VFS в памяти")
    parser.add_argument(
        "--vfs-path", type=str, default="./vfs/multi.json",
        help="Путь к JSON-файлу VFS (или каталогу, содержащему multi.json/default.json/vfs.json/minimal.json)"
    )
    parser.add_argument("--startup-script", type=str, default=None, help="Путь к стартовому скрипту команд эмулятора")
    return parser.parse_args()


def main():
    args = parse_args()
    root = tk.Tk()
    ShellEmulatorGUI(root, vfs_path=args.vfs_path, startup_script=args.startup_script)
    root.mainloop()


if __name__ == "__main__":
    main()
