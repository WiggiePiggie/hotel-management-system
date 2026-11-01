from datetime import datetime, timedelta
import customtkinter as ctk

from ui.base import BasePage


class DashboardPage(BasePage):
    AUTO_REFRESH_MS = 5000
    CLOCK_REFRESH_MS = 1000

    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.cards = {}
        self._job = None
        self._clock_job = None
        self.build()
        self.refresh()
        self.auto_refresh()
        self.start_clock()

    def build(self):
        top = ctk.CTkFrame(self, fg_color='transparent')
        top.pack(fill='x', padx=10, pady=(10, 6))

        ctk.CTkLabel(
            top,
            text=self.t('dashboard'),
            font=ctk.CTkFont(size=28, weight='bold')
        ).pack(side='left')

        self.datetime_label = ctk.CTkLabel(
            top,
            text='',
            font=ctk.CTkFont(size=18, weight='bold')
        )
        self.datetime_label.pack(side='right')

        cards_wrap = ctk.CTkFrame(self, corner_radius=20)
        cards_wrap.pack(fill='x', padx=10, pady=6)

        grid = ctk.CTkFrame(cards_wrap, fg_color='transparent')
        grid.pack(fill='x', padx=10, pady=10)

        for i in range(4):
            grid.grid_columnconfigure(i, weight=1)

        items = [
            ('Total Rooms', 'total_rooms'),
            ('Available', 'available_rooms'),
            ('Occupied', 'occupied_rooms'),
            ('Reserved', 'reserved_rooms'),
            ('Guests', 'total_guests'),
            ('Reservations', 'total_reservations'),
            ('Paid Revenue', 'paid_revenue'),
            ('Cancelled', 'cancelled'),
        ]

        for idx, (label, key) in enumerate(items):
            card = ctk.CTkFrame(grid, corner_radius=18)
            card.grid(row=idx // 4, column=idx % 4, padx=8, pady=8, sticky='nsew')
            ctk.CTkLabel(card, text=label, text_color='gray70').pack(anchor='w', padx=16, pady=(14, 4))
            value = ctk.CTkLabel(card, text='0', font=ctk.CTkFont(size=24, weight='bold'))
            value.pack(anchor='w', padx=16, pady=(0, 14))
            self.cards[key] = value

        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(fill='both', expand=True, padx=10, pady=10)

        for i in range(3):
            bottom.grid_columnconfigure(i, weight=1)

        self.checkins = self._listbox_card(bottom, 0, 'Today Check-Ins')
        self.due_checkouts = self._listbox_card(bottom, 1, 'Due For Checkout Today')
        self.done_checkouts = self._listbox_card(bottom, 2, 'Already Checked Out Today')

    def _listbox_card(self, parent, col, title):
        card = ctk.CTkFrame(parent, corner_radius=18)
        card.grid(row=0, column=col, padx=6, pady=6, sticky='nsew')
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=14, pady=(12, 8))

        import tkinter as tk
        lb = tk.Listbox(card, height=18, bd=0, highlightthickness=0, font=('Segoe UI', 10))
        lb.pack(fill='both', expand=True, padx=14, pady=(0, 14))
        return lb

    def update_clock(self):
        now = datetime.now()
        self.datetime_label.configure(text=now.strftime('Date: %Y-%m-%d   Time: %H:%M:%S'))
        self._clock_job = self.after(self.CLOCK_REFRESH_MS, self.update_clock)

    def start_clock(self):
        if self._clock_job is None:
            self.update_clock()

    def stop_autosave(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None
        if self._clock_job:
            self.after_cancel(self._clock_job)
            self._clock_job = None

    def refresh(self):
        stats = self.db.get_dashboard_stats()
        for k, widget in self.cards.items():
            widget.configure(text=str(stats[k]))

        today = datetime.now().strftime('%Y-%m-%d')

        for lb in (self.checkins, self.due_checkouts, self.done_checkouts):
            lb.delete(0, 'end')

        groups = [
            (self.checkins, self.db.fetch_today_checkins(today), 'No check-ins today.'),
            (self.due_checkouts, self.db.fetch_due_today_checkouts(today), 'No pending checkouts today.'),
            (self.done_checkouts, self.db.fetch_completed_today_checkouts(today), 'No completed checkouts today.'),
        ]

        for lb, rows, empty in groups:
            if rows:
                for row in rows:
                    lb.insert('end', f"#{row['id']} - {row['full_name']} - {row['room_number']}")
            else:
                lb.insert('end', empty)

    def auto_refresh(self):
        self.refresh()
        self._job = self.after(self.AUTO_REFRESH_MS, self.auto_refresh)

    