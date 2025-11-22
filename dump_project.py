import os
from datetime import datetime

# Какие папки игнорировать (чтобы не тащить venv, медиа, кэш и т.п.)
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "staticfiles",
    "media",
    ".idea",
    ".vscode",
}

# Какие расширения файлов пропускать (бинарные и тяжёлые)
IGNORED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite3",
    ".sqlite",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".pdf",
    ".zip",
    ".rar",
    ".7z",
    ".exe",
    ".dll",
    ".so",
}


def is_binary_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in IGNORED_EXTENSIONS


def build_tree_and_collect_files(root: str):
    """
    Обходит проект, строит дерево директорий и собирает список файлов,
    которые потом будем выгружать целиком.
    """
    tree_lines = []
    file_paths = []

    root = os.path.abspath(root)
    root_name = os.path.basename(root.rstrip(os.sep))

    # Добавляем корень один раз
    tree_lines.append(f"{root_name}/")

    for current_root, dirs, files in os.walk(root):
        # Отбрасываем ненужные директории
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS and not d.startswith(".")
        ]

        rel_root = os.path.relpath(current_root, root)
        if rel_root == ".":
            depth = 0
        else:
            depth = rel_root.count(os.sep) + 1

        indent = "    " * depth

        if rel_root != ".":
            tree_lines.append(f"{indent}{os.path.basename(current_root)}/")

        # Файлы
        for name in sorted(files):
            if is_binary_file(name):
                continue
            file_rel_path = os.path.join(rel_root, name) if rel_root != "." else name
            file_abs_path = os.path.join(current_root, name)

            tree_lines.append(f"{indent}    {name}")
            file_paths.append((file_rel_path, file_abs_path))

    return tree_lines, file_paths


def dump_project(root: str, output_filename: str = "project_dump.txt"):
    tree_lines, file_paths = build_tree_and_collect_files(root)

    root = os.path.abspath(root)
    header = [
        "#" * 80,
        "# PROJECT DUMP",
        f"# Root: {root}",
        f"# Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "#" * 80,
        "",
    ]

    with open(output_filename, "w", encoding="utf-8", errors="replace") as f:
        # Шапка
        f.write("\n".join(header))

        # Дерево проекта
        f.write("PROJECT TREE:\n")
        f.write("-" * 80 + "\n")
        for line in tree_lines:
            f.write(line + "\n")

        # Разделитель
        f.write("\n\n")
        f.write("=" * 80 + "\n")
        f.write("FILES CONTENT:\n")
        f.write("=" * 80 + "\n\n")

        # Содержимое файлов
        for rel_path, abs_path in file_paths:
            f.write("#" * 80 + "\n")
            f.write(f"# File: {rel_path}\n")
            f.write("#" * 80 + "\n\n")

            try:
                with open(abs_path, "r", encoding="utf-8", errors="replace") as src:
                    f.write(src.read())
            except Exception as e:
                f.write(f"<< ERROR READING FILE: {e} >>\n")

            f.write("\n\n")

    print(f"Готово! Файл с дампом проекта: {output_filename}")


if __name__ == "__main__":
    # Точка входа: текущая папка — корень проекта (parkshare_ru_pwa)
    project_root = os.path.dirname(os.path.abspath(__file__))
    dump_project(project_root)
