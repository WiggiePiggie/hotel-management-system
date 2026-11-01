import customtkinter as ctk

from ui.base import BasePage
from ui.widgets import ModernTreeFrame


class AuditLogPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.build()
        self.refresh()

    def build(self):
        ctk.CTkLabel(self, text=self.t('audit_log'), font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w', padx=10, pady=(10,12))
        top = ctk.CTkFrame(self, fg_color='transparent')
        top.pack(fill='x', padx=10, pady=4)
        self.search_var = ctk.StringVar()
        ctk.CTkEntry(top, textvariable=self.search_var, width=260, placeholder_text=self.t('search')).pack(side='left')
        ctk.CTkButton(top, text=self.t('search'), width=90, command=self.refresh).pack(side='left', padx=4)
        ctk.CTkButton(top, text=self.t('reset'), width=90, fg_color='gray30', hover_color='gray25', command=lambda: (self.search_var.set(''), self.refresh())).pack(side='left', padx=4)

        table_card = ctk.CTkFrame(self, corner_radius=18)
        table_card.pack(fill='both', expand=True, padx=10, pady=10)
        tree_frame = ModernTreeFrame(
            table_card,
            columns=('id','created_at','username','action','details'),
            headings=['ID', self.t('time'), self.t('username'), self.t('action'), self.t('details')],
            widths=[60,160,120,160,520],
            height=18
        )
        tree_frame.pack(fill='both', expand=True, padx=14, pady=14)
        self.tree = tree_frame.tree

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.db.fetch_audit_logs(self.search_var.get().strip()):
            self.tree.insert('', 'end', values=(row['id'], row['created_at'], row['username'], row['action'], row['details']))
