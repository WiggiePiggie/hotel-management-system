from tkinter import ttk
import customtkinter as ctk


class ModernTreeFrame(ctk.CTkFrame):
    def __init__(self, parent, columns, headings, widths, height=16):
        super().__init__(parent, fg_color='transparent')
        style = ttk.Style()
        style.configure('Treeview', rowheight=28)
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))

        self.tree = ttk.Treeview(self, columns=columns, show='headings', height=height)
        for c, h, w in zip(columns, headings, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor='center')
        self.tree.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
