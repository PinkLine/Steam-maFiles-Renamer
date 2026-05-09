import os
import json
import re
import customtkinter as ctk
from tkinter import filedialog, messagebox

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MafileRenamer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Steam maFile Renamer v2")
        self.geometry("700x600")
        self.resizable(True, True)

        # Заголовок
        ctk.CTkLabel(self, text="Переименование ma-файлов Steam",
                     font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)

        # Выбор папки
        folder_frame = ctk.CTkFrame(self)
        folder_frame.pack(fill="x", padx=20, pady=10)

        self.folder_var = ctk.StringVar(value="")
        ctk.CTkEntry(folder_frame, textvariable=self.folder_var, height=35,
                     placeholder_text="Путь к папке с ma-файлами").pack(side="left", fill="x", expand=True, padx=(5, 5))
        ctk.CTkButton(folder_frame, text="Обзор", width=80, command=self.browse_folder).pack(side="right", padx=(0, 5))

        # Галочки
        checkbox_frame = ctk.CTkFrame(self)
        checkbox_frame.pack(fill="x", padx=20, pady=5)

        self.overwrite_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(checkbox_frame, text="Заменять существующие файлы",
                        variable=self.overwrite_var).pack(anchor="w", pady=2)

        self.all_extensions_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(checkbox_frame, text="Обрабатывать файлы без .maFile (txt, json и др.)",
                        variable=self.all_extensions_var).pack(anchor="w", pady=2)

        # Кнопка переименования
        ctk.CTkButton(self, text="Переименовать все файлы", height=45,
                      font=ctk.CTkFont(size=15, weight="bold"),
                      command=self.rename_files).pack(pady=15, padx=20)

        # Лог
        ctk.CTkLabel(self, text="Лог:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20)
        self.log_text = ctk.CTkTextbox(self, height=300, font=("Consolas", 11))
        self.log_text.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        self.log_text.configure(state="disabled")

    def browse_folder(self):
        folder = filedialog.askdirectory(title="Выберите папку с ma-файлами")
        if folder:
            self.folder_var.set(folder)

    def add_log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        self.update()

    def extract_account_name(self, data, filename):
        """Пытается вытащить логин из JSON-данных всеми возможными способами."""
        # Способ 1: поле account_name
        name = data.get("account_name", "").strip()
        if name:
            return name

        # Способ 2: разбор uri (otpauth://totp/Steam:LOGIN?secret=...)
        uri = data.get("uri", "")
        if "Steam:" in uri:
            try:
                name = uri.split("Steam:")[1].split("?")[0].strip()
                if name:
                    return name
            except:
                pass

        # Способ 3: Session.AccountName
        session = data.get("Session", {})
        if isinstance(session, dict):
            name = session.get("AccountName", "").strip()
            if name:
                return name

        # Способ 4: пробуем вытащить из steamLoginSecure (логин до первого %7C)
        steam_login = session.get("steamLoginSecure", "") if isinstance(session, dict) else ""
        if steam_login and "%7C" in steam_login:
            try:
                name = steam_login.split("%7C")[0].strip()
                if name and not name.isdigit():
                    return name
            except:
                pass

        # Способ 5: если имя файла — цифры (SteamID64), возвращаем его без расширения
        name_without_ext = os.path.splitext(filename)[0]
        if name_without_ext.isdigit() and len(name_without_ext) == 17:
            return name_without_ext  # SteamID64 — лучше чем ничего

        return ""

    def rename_files(self):
        folder = self.folder_var.get().strip()
        if not folder:
            messagebox.showwarning("Внимание", "Укажите путь к папке с ma-файлами.")
            return
        if not os.path.exists(folder):
            messagebox.showerror("Ошибка", f"Папка не найдена:\n{folder}")
            return

        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

        overwrite = self.overwrite_var.get()
        all_ext = self.all_extensions_var.get()

        self.add_log(f"📁 Папка: {folder}")
        self.add_log(f"🔄 Режим замены: {'ВКЛ' if overwrite else 'ВЫКЛ'}")
        self.add_log(f"📎 Обработка всех расширений: {'ДА' if all_ext else 'только .maFile'}")

        # Собираем список файлов
        files = []
        for f in os.listdir(folder):
            full_path = os.path.join(folder, f)
            if not os.path.isfile(full_path):
                continue
            if f.endswith(".maFile") or all_ext:
                files.append(f)

        self.add_log(f"📋 Найдено файлов для обработки: {len(files)}\n")

        if not files:
            self.add_log("Нет файлов для обработки.")
            return

        renamed = 0
        skipped = 0
        errors = 0

        for filename in files:
            filepath = os.path.join(folder, filename)

            # Читаем файл
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        self.add_log(f"[!] Пустой файл: {filename}, пропускаю.")
                        skipped += 1
                        continue
                    data = json.loads(content)
            except json.JSONDecodeError:
                self.add_log(f"[!] Не JSON: {filename}, пропускаю.")
                errors += 1
                continue
            except IOError:
                self.add_log(f"[!] Ошибка чтения: {filename}, пропускаю.")
                errors += 1
                continue

            # Ищем логин
            account_name = self.extract_account_name(data, filename)

            if not account_name:
                self.add_log(f"[-] Не найден логин: {filename}, пропускаю.")
                skipped += 1
                continue

            new_filename = f"{account_name}.maFile"
            new_filepath = os.path.join(folder, new_filename)

            self.add_log(f"🔍 {filename} -> логин: '{account_name}'")

            # Уже правильное имя?
            if filename == new_filename:
                self.add_log(f"  ✓ Уже назван правильно: {new_filename}")
                skipped += 1
                continue

            # Существующий файл
            if os.path.exists(new_filepath):
                if overwrite:
                    try:
                        os.remove(new_filepath)
                        self.add_log(f"  🗑 Удалён старый: {new_filename}")
                    except OSError as e:
                        self.add_log(f"  ❌ Не удалось удалить: {e}")
                        errors += 1
                        continue
                else:
                    self.add_log(f"  ⚠ Файл существует (пропуск): {new_filename}")
                    skipped += 1
                    continue

            # Переименование
            try:
                os.rename(filepath, new_filepath)
                self.add_log(f"  ✅ ПЕРЕИМЕНОВАН: {filename} -> {new_filename}")
                renamed += 1
            except OSError as e:
                self.add_log(f"  ❌ Ошибка: {e}")
                errors += 1

        self.add_log(f"\n{'='*50}")
        self.add_log(f"✅ Переименовано: {renamed}")
        self.add_log(f"⏭ Пропущено: {skipped}")
        self.add_log(f"❌ Ошибок: {errors}")
        messagebox.showinfo("Готово",
                           f"Переименовано: {renamed}\nПропущено: {skipped}\nОшибок: {errors}")

if __name__ == "__main__":
    app = MafileRenamer()
    app.mainloop()