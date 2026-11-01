from tkinter import filedialog, messagebox
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from ui.base import BasePage
from ui.widgets import ModernTreeFrame


class ReportsPage(BasePage):
    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.canvas = None
        self.build(); self.refresh()

    def build(self):
        ctk.CTkLabel(self, text=self.t('reports'), font=ctk.CTkFont(size=28, weight='bold')).pack(anchor='w', padx=10, pady=(10,12))
        btns = ctk.CTkFrame(self, fg_color='transparent'); btns.pack(fill='x', padx=10, pady=4)
        ctk.CTkButton(btns, text=self.t('export_excel'), command=self.export_excel).pack(side='left', padx=4)
        ctk.CTkButton(btns, text=self.t('export_csv'), command=self.export_csv).pack(side='left', padx=4)
        self.summary = ctk.CTkLabel(self, text=''); self.summary.pack(anchor='w', padx=12, pady=4)
        top = ctk.CTkFrame(self, fg_color='transparent'); top.pack(fill='both', expand=True, padx=10, pady=8)
        top.grid_columnconfigure(0, weight=1); top.grid_columnconfigure(1, weight=1)
        self.chart_card = ctk.CTkFrame(top, corner_radius=18); self.chart_card.grid(row=0, column=0, sticky='nsew', padx=6, pady=6)
        table = ctk.CTkFrame(top, corner_radius=18); table.grid(row=0, column=1, sticky='nsew', padx=6, pady=6)
        treef = ModernTreeFrame(table, ('day','income'), ['Day','Income'], [140,120], 16)
        treef.pack(fill='both', expand=True, padx=14, pady=14); self.tree = treef.tree

    def refresh(self):
        rows = self.db.daily_income()
        for item in self.tree.get_children(): self.tree.delete(item)
        total = 0.0
        days = []; vals = []
        for row in reversed(rows):
            total += float(row['total'])
            days.append(row['day'][5:]); vals.append(float(row['total']))
        for row in rows:
            self.tree.insert('', 'end', values=(row['day'], f"${float(row['total']):.2f}"))
        stats = self.db.get_dashboard_stats(); occupancy = round((stats['occupied_rooms'] / stats['total_rooms']) * 100, 2) if stats['total_rooms'] else 0
        self.summary.configure(text=f"Paid revenue: ${stats['paid_revenue']:.2f}   Occupancy: {occupancy}%   Cancelled: {stats['cancelled']}   Cleaning: {stats['cleaning_rooms']}")
        for child in self.chart_card.winfo_children(): child.destroy()
        fig = Figure(figsize=(5.4, 3.8), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(days, vals, marker='o')
        ax.set_title('Daily Income')
        ax.set_ylabel('Income')
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_card)
        self.canvas.draw(); self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)

    def export_excel(self):
        path = filedialog.asksaveasfilename(title='Export Excel', defaultextension='.xlsx', filetypes=[('Excel files', '*.xlsx')])
        if not path: return
        try:
            self.db.export_excel_report(path); messagebox.showinfo('Saved', f'Excel exported to:\n{path}')
        except Exception as e: messagebox.showerror('Error', str(e))

    def export_csv(self):
        path = filedialog.asksaveasfilename(title='Export CSV', defaultextension='.csv', filetypes=[('CSV files', '*.csv')])
        if not path: return
        try:
            self.db.export_reservations_csv(path); messagebox.showinfo('Saved', f'CSV exported to:\n{path}')
        except Exception as e: messagebox.showerror('Error', str(e))
