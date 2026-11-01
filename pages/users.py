from tkinter import messagebox
import customtkinter as ctk

from ui.base import BasePage
from ui.widgets import ModernTreeFrame


class UsersPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.selected_id = None
        self.build()
        self.refresh()

    def build(self):
        ctk.CTkLabel(self, text=self.t('user_management'), font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w', padx=10, pady=(10,12))

        form = ctk.CTkFrame(self, corner_radius=18)
        form.pack(fill='x', padx=10, pady=8)
        grid = ctk.CTkFrame(form, fg_color='transparent')
        grid.pack(fill='x', padx=12, pady=12)
        for i in range(4):
            grid.grid_columnconfigure(i, weight=1)

        self.username = ctk.StringVar()
        self.password = ctk.StringVar()
        self.role = ctk.StringVar(value='reception')

        ctk.CTkLabel(grid, text=self.t('username')).grid(row=0, column=0, sticky='w', padx=6, pady=(0,6))
        ctk.CTkEntry(grid, textvariable=self.username, height=34).grid(row=1, column=0, sticky='ew', padx=6)
        ctk.CTkLabel(grid, text=self.t('new_password')).grid(row=0, column=1, sticky='w', padx=6, pady=(0,6))
        ctk.CTkEntry(grid, textvariable=self.password, show='*', height=34).grid(row=1, column=1, sticky='ew', padx=6)
        ctk.CTkLabel(grid, text='Role').grid(row=0, column=2, sticky='w', padx=6, pady=(0,6))
        ctk.CTkOptionMenu(grid, variable=self.role, values=['admin', 'manager', 'reception']).grid(row=1, column=2, sticky='ew', padx=6)

        btns = ctk.CTkFrame(self, fg_color='transparent')
        btns.pack(fill='x', padx=10, pady=4)
        ctk.CTkButton(btns, text=self.t('add'), width=110, command=self.add_user).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('update'), width=110, command=self.update_user).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('reset_password'), width=140, command=self.reset_password).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('delete'), width=110, fg_color='#b91c1c', hover_color='#991b1b', command=self.delete_user).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('clear'), width=110, fg_color='gray30', hover_color='gray25', command=self.clear_form).pack(side='left', padx=4)

        table_card = ctk.CTkFrame(self, corner_radius=18)
        table_card.pack(fill='both', expand=True, padx=10, pady=10)
        tree_frame = ModernTreeFrame(table_card, columns=('id','username','role'), headings=['ID', self.t('username'), 'Role'], widths=[70,220,140], height=15)
        tree_frame.pack(fill='both', expand=True, padx=14, pady=14)
        self.tree = tree_frame.tree
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], 'values')
        self.selected_id = int(vals[0])
        self.username.set(vals[1])
        self.role.set(vals[2])
        self.password.set('')

    def clear_form(self):
        self.selected_id = None
        self.username.set('')
        self.password.set('')
        self.role.set('reception')

    def add_user(self):
        try:
            self.db.create_user(self.username.get().strip(), self.password.get(), self.role.get(), self.app.user['username'])
            self.refresh()
            self.clear_form()
            messagebox.showinfo(self.t('user_management'), self.t('user_added'))
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def update_user(self):
        if not self.selected_id:
            return messagebox.showwarning('Select', self.t('select_user_first'))
        try:
            self.db.update_user(self.selected_id, self.username.get().strip(), self.role.get(), self.app.user['username'])
            self.refresh()
            messagebox.showinfo(self.t('user_management'), self.t('user_updated'))
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def reset_password(self):
        if not self.selected_id:
            return messagebox.showwarning('Select', self.t('select_user_first'))
        try:
            self.db.reset_user_password(self.selected_id, self.password.get(), self.app.user['username'])
            self.password.set('')
            messagebox.showinfo(self.t('user_management'), self.t('password_updated'))
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def delete_user(self):
        if not self.selected_id:
            return messagebox.showwarning('Select', self.t('select_user_first'))
        if messagebox.askyesno(self.t('user_management'), self.t('confirm_delete_user')):
            try:
                self.db.delete_user(self.selected_id, self.app.user['username'])
                self.refresh()
                self.clear_form()
                messagebox.showinfo(self.t('user_management'), self.t('user_deleted'))
            except Exception as e:
                messagebox.showerror('Error', str(e))

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.db.list_users():
            self.tree.insert('', 'end', values=(row['id'], row['username'], row['role']))
