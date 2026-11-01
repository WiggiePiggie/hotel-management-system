from datetime import datetime, timedelta
from tkinter import messagebox
import customtkinter as ctk

from ui.base import BasePage
from ui.widgets import ModernTreeFrame


DATE_FMT = "%Y-%m-%d"


class CalendarPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.tree_frame = None
        self.tree = None
        self.build()
        self.refresh()

    def build(self):
        ctk.CTkLabel(
            self,
            text=self.t('calendar'),
            font=ctk.CTkFont(size=28, weight='bold')
        ).pack(anchor='w', padx=10, pady=(10, 12))

        bar = ctk.CTkFrame(self, fg_color='transparent')
        bar.pack(fill='x', padx=10, pady=4)

        self.start_date = ctk.StringVar(value=datetime.now().strftime(DATE_FMT))
        self.days_var = ctk.StringVar(value='7')
        self.room_filter = ctk.StringVar(value='')

        ctk.CTkLabel(bar, text='Start Date').pack(side='left', padx=(0, 4))
        ctk.CTkEntry(bar, textvariable=self.start_date, width=120).pack(side='left', padx=4)

        ctk.CTkLabel(bar, text='Days').pack(side='left', padx=(12, 4))
        self.days_menu = ctk.CTkOptionMenu(
            bar,
            variable=self.days_var,
            values=['7', '14'],
            command=lambda _=None: self.refresh()
        )
        self.days_menu.pack(side='left', padx=4)

        ctk.CTkLabel(bar, text='Room Filter').pack(side='left', padx=(12, 4))
        ctk.CTkEntry(bar, textvariable=self.room_filter, width=140).pack(side='left', padx=4)

        ctk.CTkButton(bar, text='Load', command=self.refresh).pack(side='left', padx=8)

        self.table_wrap = ctk.CTkFrame(self, corner_radius=18)
        self.table_wrap.pack(fill='both', expand=True, padx=10, pady=8)

    def refresh(self):
        try:
            start = datetime.strptime(self.start_date.get().strip(), DATE_FMT)
        except ValueError:
            return messagebox.showerror('Error', 'Invalid start date. Use YYYY-MM-DD.')

        try:
            days = int(self.days_var.get())
        except ValueError:
            days = 7

        if days not in (7, 14):
            days = 7

        rooms, reservations = self.db.occupancy_for_range(
            self.start_date.get().strip(),
            days
        )

        room_filter = self.room_filter.get().strip().lower()
        if room_filter:
            rooms = [
                r for r in rooms
                if room_filter in str(r['room_number']).lower()
                or room_filter in str(r['room_type']).lower()
            ]

        dates = [
            (start + timedelta(days=i)).strftime(DATE_FMT)
            for i in range(days)
        ]

        # destroy the whole previous frame, not just the tree widget
        if self.tree_frame is not None:
            self.tree_frame.destroy()
            self.tree_frame = None
            self.tree = None

        columns = ['room'] + dates
        widths = [140] + [100] * days
        headings = ['Room'] + [d[5:] for d in dates]

        self.tree_frame = ModernTreeFrame(
            self.table_wrap,
            columns,
            headings,
            widths,
            18
        )
        self.tree_frame.pack(fill='both', expand=True, padx=14, pady=14)
        self.tree = self.tree_frame.tree

        res_by_room = {}
        for r in reservations:
            res_by_room.setdefault(r['room_number'], []).append(r)

        for room in rooms:
            values = [f"{room['room_number']} ({room['room_type']})"]
            room_res = res_by_room.get(room['room_number'], [])

            for d in dates:
                cell = ''
                for r in room_res:
                    if r['check_in'] <= d < r['check_out']:
                        cell = f"{r['full_name']} [{r['status']}]"
                        break
                    elif d == r['check_out']:
                        cell = f"{r['full_name']} [Checkout]"
                        break

                if not cell:
                    if room['status'] == 'Maintenance':
                        cell = 'Maintenance'
                    elif room['status'] == 'Cleaning':
                        cell = 'Cleaning'
                    else:
                        cell = 'Free'

                values.append(cell)

            self.tree.insert('', 'end', values=values)