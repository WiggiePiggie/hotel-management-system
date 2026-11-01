from tkinter import messagebox
import customtkinter as ctk

from ui.base import BasePage
from ui.widgets import ModernTreeFrame


class RoomsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.selected_id = None
        self.build()
        self.refresh()

    def build(self):
        ctk.CTkLabel(self, text=self.t('rooms'), font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w', padx=10, pady=(10, 12))
        form = ctk.CTkFrame(self, corner_radius=18)
        form.pack(fill='x', padx=10, pady=8)
        self.room_number = ctk.StringVar(); self.room_type = ctk.StringVar(); self.capacity = ctk.StringVar(); self.price = ctk.StringVar(); self.floor_no = ctk.StringVar(value='1')
        self.breakfast = ctk.IntVar(value=0); self.sea_view = ctk.IntVar(value=0); self.smoking = ctk.IntVar(value=0); self.status = ctk.StringVar(value='Available')
        grid = ctk.CTkFrame(form, fg_color='transparent'); grid.pack(fill='x', padx=12, pady=12)
        for i in range(6): grid.grid_columnconfigure(i, weight=1)
        for label, var, col in [('Room Number', self.room_number, 0), ('Room Type', self.room_type, 1), ('Capacity', self.capacity, 2), ('Price/Night', self.price, 3), ('Floor', self.floor_no, 4)]:
            ctk.CTkLabel(grid, text=label).grid(row=0, column=col, sticky='w', padx=6, pady=(0, 6))
            ctk.CTkEntry(grid, textvariable=var, height=34).grid(row=1, column=col, sticky='ew', padx=6)
        ctk.CTkLabel(grid, text='Status').grid(row=0, column=5, sticky='w', padx=6, pady=(0, 6))
        self.status_menu = ctk.CTkOptionMenu(grid, variable=self.status, values=['Available', 'Reserved', 'Occupied', 'Cleaning', 'Maintenance'])
        self.status_menu.grid(row=1, column=5, sticky='ew', padx=6)
        opts = ctk.CTkFrame(form, fg_color='transparent'); opts.pack(fill='x', padx=16, pady=(0, 10))
        ctk.CTkCheckBox(opts, text='Breakfast Included', variable=self.breakfast, onvalue=1, offvalue=0).pack(side='left', padx=8)
        ctk.CTkCheckBox(opts, text='Sea View', variable=self.sea_view, onvalue=1, offvalue=0).pack(side='left', padx=8)
        ctk.CTkCheckBox(opts, text='Smoking Allowed', variable=self.smoking, onvalue=1, offvalue=0).pack(side='left', padx=8)
        btns = ctk.CTkFrame(self, fg_color='transparent'); btns.pack(fill='x', padx=10, pady=4)
        ctk.CTkButton(btns, text=self.t('add'), width=110, command=self.add_room).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('update'), width=110, command=self.update_room).pack(side='left', padx=4)
        self.delete_btn = ctk.CTkButton(btns, text=self.t('delete'), width=110, fg_color='#b91c1c', hover_color='#991b1b', command=self.delete_room)
        self.delete_btn.pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('mark_room_clean'), width=150, command=self.mark_clean).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('clear'), width=110, fg_color='gray30', hover_color='gray25', command=self.clear_form).pack(side='left', padx=4)
        if not self.app.has_permission('room_delete'):
            self.delete_btn.configure(state='disabled')
        table = ctk.CTkFrame(self, corner_radius=18); table.pack(fill='both', expand=True, padx=10, pady=10)
        treef = ModernTreeFrame(table, ('id','room','type','cap','price','floor','breakfast','sea','smoking','status'), ['ID','Room','Type','Cap','Price','Floor','Breakfast','Sea View','Smoking','Status'], [50,80,120,60,90,60,90,80,80,90], 16)
        treef.pack(fill='both', expand=True, padx=14, pady=14); self.tree = treef.tree; self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def add_room(self):
        try:
            self.db.add_room(self.room_number.get().strip(), self.room_type.get().strip(), int(self.capacity.get()), float(self.price.get()), int(self.floor_no.get()), int(self.breakfast.get()), int(self.sea_view.get()), int(self.smoking.get()), self.status.get())
            self.app.refresh_all(); self.clear_form(); messagebox.showinfo('Success', 'Room added.')
        except Exception as e: messagebox.showerror('Error', str(e))

    def update_room(self):
        if not self.selected_id: return messagebox.showwarning('Select', 'Select a room first.')
        try:
            self.db.update_room(self.selected_id, self.room_number.get().strip(), self.room_type.get().strip(), int(self.capacity.get()), float(self.price.get()), int(self.floor_no.get()), int(self.breakfast.get()), int(self.sea_view.get()), int(self.smoking.get()), self.status.get())
            self.app.refresh_all(); self.clear_form(); messagebox.showinfo('Success', 'Room updated.')
        except Exception as e: messagebox.showerror('Error', str(e))

    def delete_room(self):
        if not self.selected_id: return messagebox.showwarning('Select', 'Select a room first.')
        if messagebox.askyesno('Confirm', 'Delete selected room?'):
            try:
                self.db.delete_room(self.selected_id); self.app.refresh_all(); self.clear_form(); messagebox.showinfo('Success', 'Room deleted.')
            except Exception as e: messagebox.showerror('Error', str(e))

    def mark_clean(self):
        if not self.selected_id: return messagebox.showwarning('Select', 'Select a room first.')
        try:
            self.db.mark_room_clean(self.selected_id); self.app.refresh_all(); messagebox.showinfo('Success', 'Room marked available/reserved based on current bookings.')
        except Exception as e: messagebox.showerror('Error', str(e))

    def on_select(self, _=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0], 'values')
        self.selected_id = int(vals[0]); self.room_number.set(vals[1]); self.room_type.set(vals[2]); self.capacity.set(vals[3]); self.price.set(vals[4]); self.floor_no.set(vals[5]); self.breakfast.set(1 if vals[6]=='Yes' else 0); self.sea_view.set(1 if vals[7]=='Yes' else 0); self.smoking.set(1 if vals[8]=='Yes' else 0); self.status.set(vals[9])

    def clear_form(self):
        self.selected_id = None
        for var, val in [(self.room_number,''),(self.room_type,''),(self.capacity,''),(self.price,''),(self.floor_no,'1')]: var.set(val)
        self.breakfast.set(0); self.sea_view.set(0); self.smoking.set(0); self.status.set('Available')

    def refresh(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for row in self.db.fetch_rooms():
            self.tree.insert('', 'end', values=(row['id'],row['room_number'],row['room_type'],row['capacity'],row['price_per_night'],row['floor_no'],'Yes' if row['breakfast_included'] else 'No','Yes' if row['sea_view'] else 'No','Yes' if row['smoking_allowed'] else 'No',row['status']))
