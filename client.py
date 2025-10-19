import socket
import threading
from customtkinter import *


class ChatClient:
    def __init__(self):
        self.sock = None
        self.nickname = None
        self.host = None
        self.port = None
        self.running = False

        # --- login window (root) ---
        self.win = CTk()
        self.win.geometry("400x300")
        self.win.title("OP Overlord")

        CTkLabel(self.win, text="Nickname:", font=("Arial", 14, "bold")).pack(pady=5)
        self.nickname_entry = CTkEntry(self.win, placeholder_text="Anon")
        self.nickname_entry.pack(pady=5)

        CTkLabel(self.win, text="Host:", font=("Arial", 14, "bold")).pack(pady=5)
        self.host_entry = CTkEntry(self.win, placeholder_text="127.0.0.1")
        self.host_entry.pack(pady=5)

        CTkLabel(self.win, text="Port:", font=("Arial", 14, "bold")).pack(pady=5)
        self.port_entry = CTkEntry(self.win, placeholder_text="12345")
        self.port_entry.pack(pady=5)

        self.login_button = CTkButton(self.win, text="Login", command=self.connect_server)
        self.login_button.pack(pady=20)

        self.win.protocol("WM_DELETE_WINDOW", self.close_client)
        self.win.mainloop()

    def connect_server(self):
        self.host = self.host_entry.get().strip()
        self.nickname = self.nickname_entry.get().strip() or "Anon"
        port_text = self.port_entry.get().strip()
        try:
            self.port = int(port_text) if port_text else 12345
        except ValueError:
            print("Невірний порт")
            return

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            # Надсилаємо свій нікнейм серверу
            self.sock.send(self.nickname.encode('utf-8'))
        except Exception as e:
            print("Помилка підключення:", e)
            return

        self.running = True

        # Відкриваємо вікно чату (не викликаємо mainloop знову — використаємо існуючий root)
        self.open_chat_window()

        # Окремий потік для прийому повідомлень — запускаємо після того, як UI готовий
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def open_chat_window(self):
        # reuse existing root window (self.win) to avoid starting a second mainloop
        self.chat_root = self.win
        self.chat_root.title(f"Чат ({self.nickname})")
        self.chat_root.geometry("700x500")

        # Очистимо старі віджети з вікна логіну
        for w in self.chat_root.winfo_children():
            w.destroy()

        # left side (messages)
        main_frame = CTkFrame(self.chat_root)
        main_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.text_area = CTkTextbox(main_frame, wrap="word", state="disabled")
        self.text_area.pack(fill="both", expand=True, pady=5)

        entry_frame = CTkFrame(main_frame)
        entry_frame.pack(fill="x")

        self.entry = CTkEntry(entry_frame, placeholder_text="Введіть повідомлення...")
        self.entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.entry.bind("<Return>", lambda e: self.send_message())

        send_btn = CTkButton(entry_frame, text="▶️", width=50, command=self.send_message)
        send_btn.pack(side="right", padx=5)

        # right side (users)
        side_frame = CTkFrame(self.chat_root, width=150)
        side_frame.pack(side="right", fill="y", padx=10, pady=10)

        CTkLabel(side_frame, text="Користувачі", font=("Arial", 16)).pack(pady=10)

        self.user_list = CTkTextbox(side_frame, state="disabled", width=120)
        self.user_list.pack(fill="both", expand=True, padx=5, pady=5)

        self.chat_root.protocol("WM_DELETE_WINDOW", self.close_client)
        # НЕ викликаємо mainloop тут (він вже працює)

    def receive_messages(self):
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                text = data.decode('utf-8').strip()
                if not text:
                    continue

                if text.startswith("MSG:"):
                    msg = text[4:]
                    # Викликаємо оновлення UI в головному потоці
                    try:
                        self.chat_root.after(0, self.add_message, msg)
                    except Exception:
                        # якщо UI ще не доступний — виводимо в консоль
                        print(msg)
                elif text.startswith("USERS:"):
                    users = text[6:].split(",") if text[6:] else []
                    try:
                        self.chat_root.after(0, self.update_user_list, users)
                    except Exception:
                        print("Users:", users)
            except Exception:
                break

        # Завершення при відключенні
        self.running = False
        try:
            self.sock.close()
        except:
            pass
        try:
            self.chat_root.after(0, lambda: self.add_message("⚠️ З'єднання закрито."))
        except:
            pass

    def add_message(self, data: str):
        """Додає повідомлення у чат"""
        self.text_area.configure(state="normal")
        self.text_area.insert("end", data + "\n")
        self.text_area.see("end")
        self.text_area.configure(state="disabled")

    def update_user_list(self, users):
        """Оновлює список користувачів справа"""
        self.user_list.configure(state="normal")
        self.user_list.delete("1.0", "end")
        for u in users:
            self.user_list.insert("end", u + "\n")
        self.user_list.configure(state="disabled")

    def send_message(self):
        msg = self.entry.get().strip()
        if msg:
            try:
                self.sock.send(msg.encode('utf-8'))
            except Exception:
                self.add_message("⚠️ Втрачено зв'язок із сервером!")
                self.running = False
            self.entry.delete(0, "end")

    def close_client(self):
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except:
            pass
        try:
            self.chat_root.destroy()
        except:
            try:
                self.win.destroy()
            except:
                pass


if __name__ == "__main__":
    ChatClient()