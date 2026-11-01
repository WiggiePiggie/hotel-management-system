import calendar
from datetime import datetime
import customtkinter as ctk


class DatePickerDialog(ctk.CTkToplevel):
    def __init__(self, master, initial_date=None, on_select=None):
        super().__init__(master)
        self.on_select = on_select
        self.title('Pick Date')
        self.geometry('320x320')
        self.resizable(False, False)
        dt = datetime.strptime(initial_date, '%Y-%m-%d') if initial_date else datetime.now()
        self.year = dt.year
        self.month = dt.month
        self.header = ctk.CTkFrame(self)
        self.header.pack(fill='x', padx=10, pady=10)
        ctk.CTkButton(self.header, text='<', width=36, command=self.prev_month).pack(side='left')
        self.title_lbl = ctk.CTkLabel(self.header, text='')
        self.title_lbl.pack(side='left', expand=True)
        ctk.CTkButton(self.header, text='>', width=36, command=self.next_month).pack(side='right')
        self.body = ctk.CTkFrame(self)
        self.body.pack(fill='both', expand=True, padx=10, pady=10)
        self.draw_calendar()
        self.grab_set()

    def prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self.draw_calendar()

    def next_month(self):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self.draw_calendar()

    def choose(self, day):
        value = f'{self.year:04d}-{self.month:02d}-{day:02d}'
        if self.on_select:
            self.on_select(value)
        self.destroy()

    def draw_calendar(self):
        for child in self.body.winfo_children():
            child.destroy()
        self.title_lbl.configure(text=f'{calendar.month_name[self.month]} {self.year}')
        names = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su']
        for i, name in enumerate(names):
            ctk.CTkLabel(self.body, text=name).grid(row=0, column=i, padx=2, pady=2)
        month_days = calendar.monthcalendar(self.year, self.month)
        for r, week in enumerate(month_days, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    ctk.CTkLabel(self.body, text='').grid(row=r, column=c, padx=2, pady=2)
                else:
                    ctk.CTkButton(self.body, text=str(day), width=36, height=32,
                                  command=lambda d=day: self.choose(d)).grid(row=r, column=c, padx=2, pady=2)
