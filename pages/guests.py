from tkinter import messagebox
import customtkinter as ctk

from ui.base import BasePage
from ui.widgets import ModernTreeFrame


class GuestsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.selected_id = None
        self.build(); self.refresh()

    def build(self):
        ctk.CTkLabel(self, text=self.t('guests'), font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w', padx=10, pady=(10,12))
        search = ctk.CTkFrame(self, fg_color='transparent'); search.pack(fill='x', padx=10, pady=4)
        self.search_var = ctk.StringVar(); ctk.CTkEntry(search, textvariable=self.search_var, width=280, placeholder_text='Search guest...').pack(side='left')
        ctk.CTkButton(search, text=self.t('search'), width=90, command=self.refresh).pack(side='left', padx=4)
        ctk.CTkButton(search, text=self.t('reset'), width=90, fg_color='gray30', hover_color='gray25', command=lambda:(self.search_var.set(''), self.refresh())).pack(side='left', padx=4)
        form = ctk.CTkFrame(self, corner_radius=18); form.pack(fill='x', padx=10, pady=8)
        self.full_name=ctk.StringVar(); self.phone=ctk.StringVar(); self.email=ctk.StringVar(); self.id_number=ctk.StringVar(); self.nationality=ctk.StringVar(); self.address=ctk.StringVar(); self.notes=ctk.StringVar()
        grid = ctk.CTkFrame(form, fg_color='transparent'); grid.pack(fill='x', padx=12, pady=12)
        for i in range(4): grid.grid_columnconfigure(i, weight=1)
        fields=[('Full Name',self.full_name,0,0),('Phone',self.phone,0,1),('Email',self.email,0,2),('ID/Passport',self.id_number,0,3),('Nationality',self.nationality,2,0),('Address',self.address,2,1),('Notes',self.notes,2,2)]
        for label,var,row,col in fields:
            ctk.CTkLabel(grid,text=label).grid(row=row,column=col,sticky='w',padx=6,pady=(0,6))
            ctk.CTkEntry(grid,textvariable=var,height=34).grid(row=row+1,column=col,sticky='ew',padx=6,pady=(0,8))
        btns = ctk.CTkFrame(self, fg_color='transparent'); btns.pack(fill='x', padx=10, pady=4)
        ctk.CTkButton(btns,text=self.t('add'),width=110,command=self.add_guest).pack(side='left',padx=4)
        ctk.CTkButton(btns,text=self.t('update'),width=110,command=self.update_guest).pack(side='left',padx=4)
        self.delete_btn = ctk.CTkButton(btns,text=self.t('delete'),width=110,fg_color='#b91c1c',hover_color='#991b1b',command=self.delete_guest); self.delete_btn.pack(side='left',padx=4)
        ctk.CTkButton(btns,text=self.t('clear'),width=110,fg_color='gray30',hover_color='gray25',command=self.clear_form).pack(side='left',padx=4)
        if not self.app.has_permission('guest_delete'): self.delete_btn.configure(state='disabled')
        table = ctk.CTkFrame(self, corner_radius=18); table.pack(fill='both', expand=True, padx=10, pady=10)
        treef = ModernTreeFrame(table,('id','name','phone','email','idn','nation','address'),['ID','Name','Phone','Email','ID/Passport','Nationality','Address'],[50,180,120,180,120,110,180],15)
        treef.pack(fill='both', expand=True, padx=14, pady=14); self.tree=treef.tree; self.tree.bind('<<TreeviewSelect>>', self.on_select)

    def add_guest(self):
        try:
            self.db.add_guest(self.full_name.get().strip(), self.phone.get().strip(), self.email.get().strip(), self.id_number.get().strip(), self.nationality.get().strip(), self.address.get().strip(), self.notes.get().strip())
            self.app.refresh_all(); self.clear_form(); messagebox.showinfo('Success', 'Guest added.')
        except Exception as e: messagebox.showerror('Error', str(e))

    def update_guest(self):
        if not self.selected_id: return messagebox.showwarning('Select', 'Select a guest first.')
        try:
            self.db.update_guest(self.selected_id, self.full_name.get().strip(), self.phone.get().strip(), self.email.get().strip(), self.id_number.get().strip(), self.nationality.get().strip(), self.address.get().strip(), self.notes.get().strip())
            self.app.refresh_all(); self.clear_form(); messagebox.showinfo('Success', 'Guest updated.')
        except Exception as e: messagebox.showerror('Error', str(e))

    def delete_guest(self):
        if not self.selected_id: return messagebox.showwarning('Select', 'Select a guest first.')
        if messagebox.askyesno('Confirm', 'Delete selected guest?'):
            try:
                self.db.delete_guest(self.selected_id); self.app.refresh_all(); self.clear_form(); messagebox.showinfo('Success', 'Guest deleted.')
            except Exception as e: messagebox.showerror('Error', str(e))

    def on_select(self, _=None):
        sel=self.tree.selection();
        if not sel: return
        values=self.tree.item(sel[0],'values'); self.selected_id=int(values[0])
        row=next((r for r in self.db.fetch_guests() if r['id']==self.selected_id), None)
        if row:
            self.full_name.set(row['full_name'] or ''); self.phone.set(row['phone'] or ''); self.email.set(row['email'] or ''); self.id_number.set(row['id_number'] or ''); self.nationality.set(row['nationality'] or ''); self.address.set(row['address'] or ''); self.notes.set(row['notes'] or '')

    def clear_form(self):
        self.selected_id=None
        for var in [self.full_name,self.phone,self.email,self.id_number,self.nationality,self.address,self.notes]: var.set('')

    def refresh(self):
        for item in self.tree.get_children(): self.tree.delete(item)
        for row in self.db.fetch_guests(self.search_var.get().strip()):
            self.tree.insert('', 'end', values=(row['id'],row['full_name'],row['phone'],row['email'],row['id_number'],row['nationality'],row['address']))
