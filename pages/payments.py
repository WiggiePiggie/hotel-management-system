from tkinter import messagebox
import customtkinter as ctk

from ui.base import BasePage
from ui.widgets import ModernTreeFrame


class PaymentsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.reservation_map = {}
        self.build()
        self.refresh()

    def build(self):
        ctk.CTkLabel(self, text=self.t('payments'), font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w', padx=10, pady=(10,12))

        top = ctk.CTkFrame(self, corner_radius=18)
        top.pack(fill='x', padx=10, pady=8)

        self.reservation_var = ctk.StringVar(value='')
        self.amount_var = ctk.StringVar()
        self.method_var = ctk.StringVar(value='Cash')
        self.note_var = ctk.StringVar()
        self.service_name_var = ctk.StringVar()
        self.service_amount_var = ctk.StringVar()

        outer = ctk.CTkFrame(top, fg_color='transparent')
        outer.pack(fill='x', padx=12, pady=12)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_columnconfigure(1, weight=1)

        reservation_row = ctk.CTkFrame(outer, fg_color='transparent')
        reservation_row.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 12))
        reservation_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(reservation_row, text='Reservation').grid(row=0, column=0, sticky='w', padx=6, pady=(0, 6))
        self.res_menu = ctk.CTkOptionMenu(reservation_row, variable=self.reservation_var, values=[''])
        self.res_menu.grid(row=1, column=0, sticky='ew', padx=6)

        payment_card = ctk.CTkFrame(outer, corner_radius=16)
        payment_card.grid(row=1, column=0, sticky='nsew', padx=(0, 6), pady=4)
        payment_card.grid_columnconfigure(0, weight=1)
        payment_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(payment_card, text='Add Payment Amount', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, columnspan=2, sticky='w', padx=12, pady=(12, 10))
        ctk.CTkLabel(payment_card, text='Payment Amount').grid(row=1, column=0, sticky='w', padx=12, pady=(0, 6))
        ctk.CTkEntry(payment_card, textvariable=self.amount_var, height=36, placeholder_text='100 or 100.50').grid(row=2, column=0, sticky='ew', padx=12, pady=(0,10))
        ctk.CTkLabel(payment_card, text='Method').grid(row=1, column=1, sticky='w', padx=12, pady=(0, 6))
        ctk.CTkOptionMenu(payment_card, variable=self.method_var, values=['Cash', 'Card', 'Bank Transfer']).grid(row=2, column=1, sticky='ew', padx=12, pady=(0,10))
        ctk.CTkLabel(payment_card, text='Note').grid(row=3, column=0, columnspan=2, sticky='w', padx=12, pady=(0, 6))
        ctk.CTkEntry(payment_card, textvariable=self.note_var, height=36).grid(row=4, column=0, columnspan=2, sticky='ew', padx=12, pady=(0,12))
        ctk.CTkButton(payment_card, text=self.t('add_payment'), command=self.add_payment).grid(row=5, column=0, columnspan=2, sticky='ew', padx=12, pady=(0,12))

        service_card = ctk.CTkFrame(outer, corner_radius=16)
        service_card.grid(row=1, column=1, sticky='nsew', padx=(6, 0), pady=4)
        service_card.grid_columnconfigure(0, weight=1)
        service_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(service_card, text='Add Service Amount', font=ctk.CTkFont(size=18, weight='bold')).grid(row=0, column=0, columnspan=2, sticky='w', padx=12, pady=(12, 10))
        ctk.CTkLabel(service_card, text='Service Name').grid(row=1, column=0, sticky='w', padx=12, pady=(0, 6))
        ctk.CTkEntry(service_card, textvariable=self.service_name_var, height=36).grid(row=2, column=0, sticky='ew', padx=12, pady=(0,10))
        ctk.CTkLabel(service_card, text='Service Amount').grid(row=1, column=1, sticky='w', padx=12, pady=(0, 6))
        ctk.CTkEntry(service_card, textvariable=self.service_amount_var, height=36, placeholder_text='20 or 20.50').grid(row=2, column=1, sticky='ew', padx=12, pady=(0,10))
        ctk.CTkButton(service_card, text=self.t('add_service'), command=self.add_service).grid(row=5, column=0, columnspan=2, sticky='ew', padx=12, pady=(0,12))

        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.pack(fill='x', padx=10, pady=4)
        ctk.CTkButton(actions, text=self.t('refresh'), fg_color='gray30', hover_color='gray25', command=self.refresh).pack(side='left', padx=4)

        self.summary = ctk.CTkLabel(self, text='')
        self.summary.pack(anchor='w', padx=12, pady=6)

        holder = ctk.CTkFrame(self, fg_color='transparent')
        holder.pack(fill='both', expand=True, padx=10, pady=8)
        holder.grid_columnconfigure(0, weight=1)
        holder.grid_columnconfigure(1, weight=1)
        self.pay_tree = self.make_tree(holder, 0, 'Payments', ('id','amount','method','paid_at','note'))
        self.svc_tree = self.make_tree(holder, 1, 'Services', ('id','name','amount','created_at'))

    def make_tree(self, parent, col, title, columns):
        frame = ctk.CTkFrame(parent, corner_radius=18)
        frame.grid(row=0, column=col, sticky='nsew', padx=6, pady=6)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=14, pady=(12,8))
        treef = ModernTreeFrame(frame, columns, [c.replace('_', ' ').title() for c in columns], [90,110,120,140,160][:len(columns)], 18)
        treef.pack(fill='both', expand=True, padx=14, pady=(0,14))
        return treef.tree

    def load_dropdown(self):
        self.reservation_map = {}
        vals = ['']
        for r in self.db.fetch_reservations():
            key = f"#{r['id']} - {r['full_name']} - Room(s) {r['room_number']} - {r['status']}"
            self.reservation_map[key] = r['id']
            vals.append(key)
        self.res_menu.configure(values=vals)
        if self.reservation_var.get() not in vals:
            self.reservation_var.set('')

    def selected_reservation_id(self):
        if self.reservation_var.get() not in self.reservation_map:
            raise ValueError('Select a reservation first.')
        return self.reservation_map[self.reservation_var.get()]

    def parse_amount(self, value, label='Amount'):
        raw = str(value).strip()
        if not raw:
            raise ValueError(f'{label} is required.')
        raw = raw.replace('$', '').replace('€', '').replace(' ', '')
        if ',' in raw and '.' in raw:
            raw = raw.replace(',', '')
        else:
            raw = raw.replace(',', '.')
        try:
            amount = float(raw)
        except ValueError:
            raise ValueError(f'{label} must be a valid number, like 100 or 100.50.')
        if amount <= 0:
            raise ValueError(f'{label} must be greater than 0.')
        return round(amount, 2)

    def add_payment(self):
        try:
            reservation_id = self.selected_reservation_id()
            amount = self.parse_amount(self.amount_var.get(), 'Payment amount')
            self.db.add_payment(reservation_id, amount, self.method_var.get(), self.note_var.get().strip())
            self.amount_var.set(''); self.note_var.set('')
            self.app.refresh_all(); self.load_lists()
            messagebox.showinfo('Success', 'Payment added.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def add_service(self):
        try:
            reservation_id = self.selected_reservation_id()
            service_name = self.service_name_var.get().strip()
            if not service_name:
                raise ValueError('Service name is required.')
            amount = self.parse_amount(self.service_amount_var.get(), 'Service amount')
            self.db.add_service(reservation_id, service_name, amount)
            self.service_name_var.set(''); self.service_amount_var.set('')
            self.app.refresh_all(); self.load_lists()
            messagebox.showinfo('Success', 'Service added.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def load_lists(self):
        for t in (self.pay_tree, self.svc_tree):
            for item in t.get_children():
                t.delete(item)
        if self.reservation_var.get() not in self.reservation_map:
            self.summary.configure(text='')
            return
        reservation_id = self.reservation_map[self.reservation_var.get()]
        for p in self.db.fetch_payments(reservation_id):
            self.pay_tree.insert('', 'end', values=(p['id'], p['amount'], p['method'], p['paid_at'], p['note']))
        for s in self.db.fetch_services(reservation_id):
            self.svc_tree.insert('', 'end', values=(s['id'], s['service_name'], s['amount'], s['created_at']))
        res = self.db.get_reservation(reservation_id)
        services_total = self.db.reservation_services_total(reservation_id)
        paid_total = self.db.reservation_paid_total(reservation_id)
        balance = self.db.reservation_balance(reservation_id)
        grand = float(res['total_price']) + services_total
        self.summary.configure(text=f"{self.t('room_total')}: ${float(res['total_price']):.2f}   {self.t('extras')}: ${services_total:.2f}   {self.t('grand_total')}: ${grand:.2f}   Paid: ${paid_total:.2f}   {self.t('balance')}: ${balance:.2f}")

    def refresh(self):
        self.load_dropdown()
        self.load_lists()
