import os
from datetime import datetime, timedelta

import customtkinter as ctk
from tkinter import messagebox

from database import DatabaseManager
from ui.login import LoginWindow
from ui.translations import TRANSLATIONS
from pages.dashboard import DashboardPage
from pages.rooms import RoomsPage
from pages.guests import GuestsPage
from pages.reservations import ReservationsPage
from pages.checkin_checkout import CheckInOutPage
from pages.payments import PaymentsPage
from pages.calendar_page import CalendarPage
from pages.reports import ReportsPage
from pages.settings import SettingsPage
from pages.users import UsersPage
from pages.audit_log import AuditLogPage

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')

ROLE_PAGES = {
    'admin': ['Dashboard', 'Rooms', 'Guests', 'Reservations', 'Check In / Out', 'Payments', 'Calendar', 'Reports', 'Settings', 'Users', 'Audit Log'],
    'manager': ['Dashboard', 'Rooms', 'Guests', 'Reservations', 'Check In / Out', 'Payments', 'Calendar', 'Reports', 'Settings', 'Audit Log'],
    'reception': ['Dashboard', 'Guests', 'Reservations', 'Check In / Out', 'Payments', 'Calendar', 'Settings'],
}


class HotelApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.language = 'en'
        self.title(self.get_app_title())
        self.geometry('1500x900')
        self.minsize(1320, 780)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(base_dir, 'hotel_modern.db')
        self.backup_dir = os.path.join(base_dir, 'backups')
        self.db = DatabaseManager(self.db_path)
        self.user = None
        self.frames = {}
        self.sidebar = None
        self.content = None
        self.withdraw()
        LoginWindow(self, self.db, self.after_login, self.get_app_title())

    def t(self, key):
        return TRANSLATIONS.get(self.language, TRANSLATIONS['en']).get(key, key)

    def get_app_title(self):
        name = self.db.get_setting('hotel_name', '') if hasattr(self, 'db') else ''
        return name or self.t('app_title')

    def refresh_app_title(self):
        self.title(self.get_app_title())

    def after_login(self, user_row):
        self.user = user_row
        self.deiconify()
        self.build_ui()
        self.protocol('WM_DELETE_WINDOW', self.on_close)

    def build_ui(self):
        if self.sidebar:
            self.sidebar.destroy()
        if self.content:
            self.content.destroy()
        self.frames = {}
        self.title(self.get_app_title())
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky='nsw')
        self.sidebar.grid_propagate(False)
        self.content = ctk.CTkFrame(self, fg_color='transparent')
        self.content.grid(row=0, column=1, sticky='nsew', padx=10, pady=10)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        all_pages = {
            'Dashboard': DashboardPage(self.content, self),
            'Rooms': RoomsPage(self.content, self),
            'Guests': GuestsPage(self.content, self),
            'Reservations': ReservationsPage(self.content, self),
            'Check In / Out': CheckInOutPage(self.content, self),
            'Payments': PaymentsPage(self.content, self),
            'Calendar': CalendarPage(self.content, self),
            'Reports': ReportsPage(self.content, self),
            'Settings': SettingsPage(self.content, self),
            'Users': UsersPage(self.content, self),
            'Audit Log': AuditLogPage(self.content, self),
        }
        allowed = ROLE_PAGES.get(self.user['role'], ROLE_PAGES['reception'])
        self.frames = {name: page for name, page in all_pages.items() if name in allowed}
        for page in self.frames.values():
            page.grid(row=0, column=0, sticky='nsew')

        ctk.CTkLabel(self.sidebar, text=self.t('app_title'), font=ctk.CTkFont(size=22, weight='bold')).pack(anchor='w', padx=18, pady=(18, 6))
        ctk.CTkLabel(self.sidebar, text=f"User: {self.user['username']} ({self.user['role']})", text_color='gray70').pack(anchor='w', padx=18, pady=(0, 8))
        ctk.CTkLabel(self.sidebar, text=self.t('language'), text_color='gray70').pack(anchor='w', padx=18, pady=(8, 4))
        lang_var = ctk.StringVar(value='English' if self.language == 'en' else 'Shqip')
        ctk.CTkOptionMenu(self.sidebar, values=['English', 'Shqip'], variable=lang_var,
                          command=lambda v: self.switch_language('sq' if v == 'Shqip' else 'en')).pack(fill='x', padx=18, pady=(0, 16))

        label_map = {
            'Dashboard': self.t('dashboard'), 'Rooms': self.t('rooms'), 'Guests': self.t('guests'),
            'Reservations': self.t('reservations'), 'Check In / Out': self.t('check_in_out'), 'Payments': self.t('payments'),
            'Calendar': self.t('calendar'), 'Reports': self.t('reports'), 'Settings': self.t('settings'), 'Users': self.t('user_management'), 'Audit Log': self.t('audit_log'),
        }
        for name in self.frames:
            ctk.CTkButton(self.sidebar, text=label_map.get(name, name), width=205, height=38,
                          command=lambda n=name: self.show_frame(n)).pack(padx=18, pady=5)

        ctk.CTkButton(self.sidebar, text=self.t('manual_backup'), width=205, fg_color='gray30', hover_color='gray25', command=self.manual_backup).pack(padx=18, pady=(24, 5))
        ctk.CTkButton(self.sidebar, text=self.t('refresh_all'), width=205, fg_color='gray30', hover_color='gray25', command=self.refresh_all).pack(padx=18, pady=5)
        self.show_frame(next(iter(self.frames)))

    def switch_language(self, lang):
        self.language = lang
        self.build_ui()

    def show_frame(self, name):
        page = self.frames[name]
        refresh = getattr(page, 'refresh', None)
        if callable(refresh):
            refresh()
        page.tkraise()

    def refresh_all(self):
        for page in self.frames.values():
            refresh = getattr(page, 'refresh', None)
            if callable(refresh):
                refresh()

    def has_permission(self, action):
        role = self.user['role']
        if role == 'admin':
            return True
        manager_allowed = {'room_delete', 'guest_delete', 'reports', 'exports', 'mark_clean'}
        reception_blocked = {'room_delete', 'guest_delete', 'reports', 'room_edit_status'}
        if role == 'manager':
            return action not in set()
        return action not in reception_blocked

    def manual_backup(self):
        try:
            path = self.db.backup_database(self.backup_dir, self.user['username'])
            messagebox.showinfo('Backup', f'Backup saved to:\n{path}')
        except Exception as e:
            messagebox.showerror('Backup Error', str(e))

    def on_close(self):
        try:
            for page in self.frames.values():
                stop = getattr(page, 'stop_autosave', None)
                if callable(stop):
                    stop()
            self.db.backup_database(self.backup_dir, self.user['username'] if self.user else 'system')
        except Exception:
            pass
        self.destroy()


if __name__ == '__main__':
    app = HotelApp()
    app.mainloop()
