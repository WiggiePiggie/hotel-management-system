from tkinter import messagebox
import customtkinter as ctk

from ui.base import BasePage
from ui.widgets import ModernTreeFrame


class CheckInOutPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.build()
        self.refresh()

    def build(self):
        ctk.CTkLabel(self, text=self.t('check_in_out'), font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w', padx=10, pady=(10,12))
        ctk.CTkLabel(self, text='Reserved bookings can be checked in. Checked-in bookings can be checked out.').pack(anchor='w', padx=10)
        holder = ctk.CTkFrame(self, fg_color='transparent')
        holder.pack(fill='both', expand=True, padx=10, pady=8)
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_columnconfigure(1, weight=1)
        self.checkin_tree = self.make_tree(holder, 0, 'Ready For Check-In')
        self.checkout_tree = self.make_tree(holder, 1, 'Ready For Check-Out')
        btns = ctk.CTkFrame(self, fg_color='transparent')
        btns.pack(fill='x', padx=10, pady=4)
        ctk.CTkButton(btns, text=self.t('check_in_selected'), command=self.check_in).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('check_out_selected'), command=self.check_out).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('refresh'), fg_color='gray30', hover_color='gray25', command=self.refresh).pack(side='left', padx=4)

    def make_tree(self, parent, col, title):
        frame = ctk.CTkFrame(parent, corner_radius=18)
        frame.grid(row=0, column=col, sticky='nsew', padx=6, pady=6)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=14, pady=(12,8))
        treef = ModernTreeFrame(frame, ('id','guest','rooms','checkin','checkout','balance'), ['ID','Guest','Rooms','Check In','Check Out','Balance'], [50,170,180,90,90,90], 18)
        treef.pack(fill='both', expand=True, padx=14, pady=(0,14))
        return treef.tree

    def refresh(self):
        for tree in (self.checkin_tree, self.checkout_tree):
            for item in tree.get_children():
                tree.delete(item)
        for row in self.db.fetch_reservations():
            vals = (row['id'], row['full_name'], row['room_number'], row['check_in'], row['check_out'], f"{self.db.reservation_balance(row['id']):.2f}")
            if row['status'] == 'Reserved':
                self.checkin_tree.insert('', 'end', values=vals)
            elif row['status'] == 'Checked In':
                self.checkout_tree.insert('', 'end', values=vals)

    def check_in(self):
        sel = self.checkin_tree.selection()
        if not sel:
            return messagebox.showwarning('Select', 'Select a reservation to check in.')
        reservation_id = int(self.checkin_tree.item(sel[0], 'values')[0])
        self.db.check_in_reservation(reservation_id)
        self.app.refresh_all()
        messagebox.showinfo('Success', 'Guest checked in.')

    def check_out(self):
        sel = self.checkout_tree.selection()
        if not sel:
            return messagebox.showwarning('Select', 'Select a reservation to check out.')
        reservation_id = int(self.checkout_tree.item(sel[0], 'values')[0])
        balance = self.db.reservation_balance(reservation_id)
        if balance > 0 and not messagebox.askyesno('Outstanding Balance', f'Balance due is ${balance:.2f}. Continue checkout anyway?'):
            return
        self.db.check_out_reservation(reservation_id)
        self.app.refresh_all()
        messagebox.showinfo('Success', 'Guest checked out. Room(s) moved to Cleaning.')
