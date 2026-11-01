import customtkinter as ctk
from tkinter import messagebox


class LoginWindow(ctk.CTkToplevel):
    def __init__(self, master, db, on_success, app_title):
        super().__init__(master)
        self.db = db
        self.on_success = on_success
        self.title('Login')
        self.geometry('420x440' if not self.db.has_users() else '420x330')
        self.resizable(False, False)
        self.protocol('WM_DELETE_WINDOW', master.destroy)

        ctk.CTkLabel(self, text=app_title, font=ctk.CTkFont(size=24, weight='bold')).pack(pady=(28, 14))
        self.first_run = not self.db.has_users()
        message = 'Create your administrator account' if self.first_run else 'Welcome back'
        ctk.CTkLabel(self, text=message, text_color='gray70').pack(pady=(0, 18))

        self.username = ctk.StringVar()
        self.password = ctk.StringVar()

        box = ctk.CTkFrame(self, corner_radius=18)
        box.pack(fill='x', padx=30, pady=10)
        ctk.CTkLabel(box, text='Username').pack(anchor='w', padx=18, pady=(18, 6))
        self.entry_username = ctk.CTkEntry(box, textvariable=self.username, height=36)
        self.entry_username.pack(fill='x', padx=18)
        ctk.CTkLabel(box, text='Password').pack(anchor='w', padx=18, pady=(14, 6))
        self.entry_password = ctk.CTkEntry(box, textvariable=self.password, show='*', height=36)
        self.entry_password.pack(fill='x', padx=18)
        if self.first_run:
            ctk.CTkLabel(box, text='At least 10 characters', text_color='gray70').pack(padx=18, pady=(8, 0))
            self.confirm = ctk.StringVar()
            ctk.CTkLabel(box, text='Confirm password').pack(anchor='w', padx=18, pady=(8, 4))
            ctk.CTkEntry(box, textvariable=self.confirm, show='*', height=36).pack(fill='x', padx=18)
        label = 'Create administrator' if self.first_run else 'Login'
        ctk.CTkButton(box, text=label, height=40, command=self.try_login).pack(fill='x', padx=18, pady=18)

        self.entry_username.bind('<Return>', lambda event: self.try_login())
        self.entry_password.bind('<Return>', lambda event: self.try_login())
        self.bind('<Return>', lambda event: self.try_login())
        self.bind('<KP_Enter>', lambda event: self.try_login())
        self.grab_set()
        self.focus_force()
        self.entry_username.focus_set()

    def try_login(self):
        if self.first_run:
            if self.password.get() != self.confirm.get():
                messagebox.showerror('Setup failed', 'Passwords do not match.')
                return
            try:
                self.db.setup_admin(self.username.get().strip(), self.password.get())
            except ValueError as exc:
                messagebox.showerror('Setup failed', str(exc))
                return
        row = self.db.validate_login(self.username.get().strip(), self.password.get())
        if not row:
            messagebox.showerror('Login failed', 'Invalid username or password.')
            return
        self.on_success(row)
        self.destroy()
