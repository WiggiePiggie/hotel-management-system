from tkinter import filedialog, messagebox
import customtkinter as ctk

from ui.base import BasePage


class SettingsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.build()
        self.refresh()

    def build(self):
        ctk.CTkLabel(self, text=self.t('settings'), font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w', padx=10, pady=(10,12))

        hotel_card = ctk.CTkFrame(self, corner_radius=18)
        hotel_card.pack(fill='x', padx=10, pady=8)
        ctk.CTkLabel(hotel_card, text=self.t('hotel_information'), font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=14, pady=(12,8))

        self.hotel_name = ctk.StringVar()
        self.hotel_address = ctk.StringVar()
        self.hotel_phone = ctk.StringVar()
        self.hotel_email = ctk.StringVar()
        self.hotel_logo_path = ctk.StringVar()
        self.invoice_footer = ctk.StringVar()

        grid = ctk.CTkFrame(hotel_card, fg_color='transparent')
        grid.pack(fill='x', padx=12, pady=12)
        for i in range(2):
            grid.grid_columnconfigure(i, weight=1)

        items = [
            (self.t('hotel_name'), self.hotel_name, 0, 0),
            (self.t('hotel_phone'), self.hotel_phone, 0, 1),
            (self.t('hotel_address'), self.hotel_address, 2, 0),
            (self.t('hotel_email'), self.hotel_email, 2, 1),
            (self.t('invoice_footer'), self.invoice_footer, 4, 0),
        ]
        for label, var, row, col in items:
            ctk.CTkLabel(grid, text=label).grid(row=row, column=col, sticky='w', padx=6, pady=(0,6))
            ctk.CTkEntry(grid, textvariable=var, height=34).grid(row=row+1, column=col, sticky='ew', padx=6, pady=(0,8))

        ctk.CTkLabel(grid, text=self.t('hotel_logo')).grid(row=4, column=1, sticky='w', padx=6, pady=(0,6))
        logo_row = ctk.CTkFrame(grid, fg_color='transparent')
        logo_row.grid(row=5, column=1, sticky='ew', padx=6)
        ctk.CTkEntry(logo_row, textvariable=self.hotel_logo_path, height=34).pack(side='left', fill='x', expand=True)
        ctk.CTkButton(logo_row, text=self.t('browse'), width=90, command=self.pick_logo).pack(side='left', padx=(6,0))

        ctk.CTkButton(hotel_card, text=self.t('save_settings'), command=self.save_settings).pack(anchor='e', padx=14, pady=(0,14))

        pwd_card = ctk.CTkFrame(self, corner_radius=18)
        pwd_card.pack(fill='x', padx=10, pady=8)
        ctk.CTkLabel(pwd_card, text=self.t('change_password'), font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=14, pady=(12,8))

        self.current_password = ctk.StringVar()
        self.new_password = ctk.StringVar()
        self.confirm_password = ctk.StringVar()

        pwd_grid = ctk.CTkFrame(pwd_card, fg_color='transparent')
        pwd_grid.pack(fill='x', padx=12, pady=12)
        for i in range(3):
            pwd_grid.grid_columnconfigure(i, weight=1)
        for idx, (label, var) in enumerate([
            (self.t('current_password'), self.current_password),
            (self.t('new_password'), self.new_password),
            (self.t('confirm_password'), self.confirm_password),
        ]):
            ctk.CTkLabel(pwd_grid, text=label).grid(row=0, column=idx, sticky='w', padx=6, pady=(0,6))
            ctk.CTkEntry(pwd_grid, textvariable=var, show='*', height=34).grid(row=1, column=idx, sticky='ew', padx=6)

        ctk.CTkButton(pwd_card, text=self.t('update_password'), command=self.update_password).pack(anchor='e', padx=14, pady=(0,14))

        restore_card = ctk.CTkFrame(self, corner_radius=18)
        restore_card.pack(fill='x', padx=10, pady=8)
        ctk.CTkLabel(restore_card, text=self.t('backup_restore'), font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=14, pady=(12,8))
        row = ctk.CTkFrame(restore_card, fg_color='transparent')
        row.pack(fill='x', padx=12, pady=12)
        self.backup_path = ctk.StringVar()
        ctk.CTkEntry(row, textvariable=self.backup_path, height=34).pack(side='left', fill='x', expand=True)
        ctk.CTkButton(row, text=self.t('browse'), width=90, command=self.pick_backup).pack(side='left', padx=(6,0))
        ctk.CTkButton(restore_card, text=self.t('restore_backup'), fg_color='#b45309', hover_color='#92400e', command=self.restore_backup).pack(anchor='e', padx=14, pady=(0,14))

    def pick_logo(self):
        path = filedialog.askopenfilename(title=self.t('select_logo'), filetypes=[('Image files', '*.png;*.jpg;*.jpeg;*.gif;*.bmp')])
        if path:
            self.hotel_logo_path.set(path)

    def save_settings(self):
        self.db.set_settings({
            'hotel_name': self.hotel_name.get().strip(),
            'hotel_address': self.hotel_address.get().strip(),
            'hotel_phone': self.hotel_phone.get().strip(),
            'hotel_email': self.hotel_email.get().strip(),
            'hotel_logo_path': self.hotel_logo_path.get().strip(),
            'invoice_footer': self.invoice_footer.get().strip(),
        })
        self.app.refresh_app_title()
        messagebox.showinfo(self.t('settings'), self.t('settings_saved'))

    def update_password(self):
        if self.new_password.get() != self.confirm_password.get():
            return messagebox.showerror('Error', self.t('passwords_do_not_match'))
        try:
            self.db.change_user_password(self.app.user['username'], self.current_password.get(), self.new_password.get())
            self.current_password.set(''); self.new_password.set(''); self.confirm_password.set('')
            messagebox.showinfo(self.t('change_password'), self.t('password_updated'))
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def pick_backup(self):
        path = filedialog.askopenfilename(title=self.t('select_backup'), filetypes=[('Database files', '*.db'), ('All files', '*.*')])
        if path:
            self.backup_path.set(path)

    def restore_backup(self):
        path = self.backup_path.get().strip()
        if not path:
            return messagebox.showwarning(self.t('backup_restore'), self.t('select_backup_first'))
        if not messagebox.askyesno(self.t('backup_restore'), self.t('confirm_restore_backup')):
            return
        try:
            self.db.restore_database(path, self.app.user['username'])
            messagebox.showinfo(self.t('backup_restore'), self.t('backup_restored_restart'))
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def refresh(self):
        settings = self.db.get_settings()
        self.hotel_name.set(settings.get('hotel_name', ''))
        self.hotel_address.set(settings.get('hotel_address', ''))
        self.hotel_phone.set(settings.get('hotel_phone', ''))
        self.hotel_email.set(settings.get('hotel_email', ''))
        self.hotel_logo_path.set(settings.get('hotel_logo_path', ''))
        self.invoice_footer.set(settings.get('invoice_footer', ''))
