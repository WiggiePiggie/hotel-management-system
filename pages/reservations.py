from tkinter import filedialog, messagebox
import customtkinter as ctk
from tkcalendar import Calendar

from ui.base import BasePage
from ui.widgets import ModernTreeFrame
from utils import parse_date, valid_date_range


class ReservationsPage(BasePage):
    AUTOSAVE_MS = 1000

    def __init__(self, parent, app):
        super().__init__(parent, app, fg_color='transparent')
        self.selected_id = None
        self.guest_map = {}
        self.available_room_map = {}
        self.selected_rooms = []
        self._job = None
        self.create_panel_visible = False

        self.build()
        self.refresh()
        self.load_draft()
        self.start_autosave()

    def build(self):
        ctk.CTkLabel(
            self,
            text=self.t('reservations'),
            font=ctk.CTkFont(size=28, weight='bold')
        ).pack(anchor='w', padx=10, pady=(10, 12))

        # ---------------- search / filters ----------------
        search = ctk.CTkFrame(self, fg_color='transparent')
        search.pack(fill='x', padx=10, pady=6)

        self.search_var = ctk.StringVar()
        self.status_filter = ctk.StringVar(value='')
        self.filter_date_from = ctk.StringVar()
        self.filter_date_to = ctk.StringVar()

        ctk.CTkEntry(
            search,
            textvariable=self.search_var,
            width=220,
            placeholder_text='Search reservation...'
        ).pack(side='left', padx=4)

        self.status_filter_menu = ctk.CTkOptionMenu(
            search,
            variable=self.status_filter,
            values=['', 'Reserved', 'Checked In', 'Checked Out', 'Cancelled']
        )
        self.status_filter_menu.pack(side='left', padx=4)

        ctk.CTkEntry(
            search,
            textvariable=self.filter_date_from,
            width=130,
            placeholder_text='From YYYY-MM-DD'
        ).pack(side='left', padx=4)

        ctk.CTkEntry(
            search,
            textvariable=self.filter_date_to,
            width=130,
            placeholder_text='To YYYY-MM-DD'
        ).pack(side='left', padx=4)

        ctk.CTkButton(search, text='Apply', command=self.refresh).pack(side='left', padx=4)
        ctk.CTkButton(
            search,
            text='Reset',
            fg_color='gray30',
            hover_color='gray25',
            command=self.reset_filters
        ).pack(side='left', padx=4)

        ctk.CTkButton(
            search,
            text='Create Reservation',
            command=self.toggle_create_panel
        ).pack(side='right', padx=4)

        # ---------------- reservations list first ----------------
        self.table_card = ctk.CTkFrame(self, corner_radius=18)
        self.table_card.pack(fill='both', expand=True, padx=10, pady=8)

        self.treef = ModernTreeFrame(
            self.table_card,
            ('id', 'guest', 'rooms', 'room_count', 'check_in', 'check_out', 'adults', 'children', 'total', 'status'),
            ['ID', 'Guest', 'Rooms', 'Count', 'Check In', 'Check Out', 'Adults', 'Children', 'Total', 'Status'],
            [55, 170, 180, 70, 95, 95, 70, 80, 100, 100],
            14
        )
        self.treef.pack(fill='both', expand=True, padx=14, pady=14)
        self.tree = self.treef.tree
        self.tree.bind('<<TreeviewSelect>>', self.on_select)

        # ---------------- hidden create/edit panel ----------------
        self.create_panel = ctk.CTkFrame(self, corner_radius=18)

        # variables
        self.guest_var = ctk.StringVar(value='')
        self.new_guest_name = ctk.StringVar()
        self.new_guest_phone = ctk.StringVar()
        self.new_guest_email = ctk.StringVar()
        self.room_type_filter = ctk.StringVar()
        self.check_in = ctk.StringVar()
        self.check_out = ctk.StringVar()
        self.adults = ctk.StringVar(value='1')
        self.children_var = ctk.StringVar(value='0')
        self.status = ctk.StringVar(value='Reserved')
        self.total_var = ctk.StringVar(value='0.00')
        self.notes_var = ctk.StringVar()
        self.room_price_var = ctk.StringVar()
        self.room_note_var = ctk.StringVar()

        form = ctk.CTkFrame(self.create_panel, corner_radius=18)
        form.pack(fill='x', padx=10, pady=8)

        grid = ctk.CTkFrame(form, fg_color='transparent')
        grid.pack(fill='x', padx=12, pady=12)
        for i in range(5):
            grid.grid_columnconfigure(i, weight=1)

        ctk.CTkLabel(grid, text='Existing Guest').grid(row=0, column=0, sticky='w', padx=6, pady=(0, 6))
        self.guest_menu = ctk.CTkOptionMenu(grid, variable=self.guest_var, values=[''])
        self.guest_menu.grid(row=1, column=0, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text='New Guest Name').grid(row=0, column=1, sticky='w', padx=6, pady=(0, 6))
        ctk.CTkEntry(grid, textvariable=self.new_guest_name, height=34).grid(row=1, column=1, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text='New Guest Phone').grid(row=0, column=2, sticky='w', padx=6, pady=(0, 6))
        ctk.CTkEntry(grid, textvariable=self.new_guest_phone, height=34).grid(row=1, column=2, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text='New Guest Email').grid(row=0, column=3, sticky='w', padx=6, pady=(0, 6))
        ctk.CTkEntry(grid, textvariable=self.new_guest_email, height=34).grid(row=1, column=3, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text=self.t('room_type_filter')).grid(row=0, column=4, sticky='w', padx=6, pady=(0, 6))
        ctk.CTkEntry(grid, textvariable=self.room_type_filter, height=34).grid(row=1, column=4, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text='Check In').grid(row=2, column=0, sticky='w', padx=6, pady=(10, 6))
        d1 = ctk.CTkFrame(grid, fg_color='transparent')
        d1.grid(row=3, column=0, sticky='ew', padx=6)
        ctk.CTkEntry(d1, textvariable=self.check_in, height=34, width=110).pack(side='left', fill='x', expand=True)
        ctk.CTkButton(d1, text='📅', width=36, command=lambda: self.pick_date(self.check_in)).pack(side='left', padx=(4, 0))

        ctk.CTkLabel(grid, text='Check Out').grid(row=2, column=1, sticky='w', padx=6, pady=(10, 6))
        d2 = ctk.CTkFrame(grid, fg_color='transparent')
        d2.grid(row=3, column=1, sticky='ew', padx=6)
        ctk.CTkEntry(d2, textvariable=self.check_out, height=34, width=110).pack(side='left', fill='x', expand=True)
        ctk.CTkButton(d2, text='📅', width=36, command=lambda: self.pick_date(self.check_out)).pack(side='left', padx=(4, 0))

        ctk.CTkLabel(grid, text='Adults').grid(row=2, column=2, sticky='w', padx=6, pady=(10, 6))
        ctk.CTkEntry(grid, textvariable=self.adults, height=34).grid(row=3, column=2, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text='Children').grid(row=2, column=3, sticky='w', padx=6, pady=(10, 6))
        ctk.CTkEntry(grid, textvariable=self.children_var, height=34).grid(row=3, column=3, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text='Status').grid(row=2, column=4, sticky='w', padx=6, pady=(10, 6))
        self.status_menu = ctk.CTkOptionMenu(
            grid,
            variable=self.status,
            values=['Reserved', 'Checked In', 'Checked Out', 'Cancelled']
        )
        self.status_menu.grid(row=3, column=4, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text='Reservation Notes').grid(row=4, column=0, sticky='w', padx=6, pady=(10, 6))
        ctk.CTkEntry(grid, textvariable=self.notes_var, height=34).grid(row=5, column=0, columnspan=3, sticky='ew', padx=6)

        ctk.CTkLabel(grid, text='Total').grid(row=4, column=3, sticky='w', padx=6, pady=(10, 6))
        ctk.CTkEntry(grid, textvariable=self.total_var, height=34, state='readonly').grid(row=5, column=3, sticky='ew', padx=6)

        ctk.CTkButton(grid, text='Find Available Rooms', command=self.find_rooms).grid(row=5, column=4, sticky='ew', padx=6)

        middle = ctk.CTkFrame(self.create_panel, fg_color='transparent')
        middle.pack(fill='x', expand=False, padx=10, pady=8)
        middle.grid_columnconfigure(0, weight=1)
        middle.grid_columnconfigure(1, weight=1)

        avail = ctk.CTkFrame(middle, corner_radius=18)
        avail.grid(row=0, column=0, sticky='nsew', padx=(0, 6))
        ctk.CTkLabel(avail, text='Available Rooms', font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=14, pady=(12, 8))
        avail_treef = ModernTreeFrame(
            avail,
            ('id', 'room_number', 'room_type', 'default_price', 'capacity'),
            ['ID', 'Room', 'Type', 'Default Price', 'Capacity'],
            [60, 90, 120, 120, 90],
            6
        )
        avail_treef.pack(fill='both', expand=True, padx=14, pady=(0, 10))
        self.available_tree = avail_treef.tree

        addbox = ctk.CTkFrame(avail, fg_color='transparent')
        addbox.pack(fill='x', padx=14, pady=(0, 14))
        addbox.grid_columnconfigure(0, weight=1)
        addbox.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(addbox, text='Custom Price').grid(row=0, column=0, sticky='w', padx=4, pady=(0, 6))
        ctk.CTkLabel(addbox, text='Room Note').grid(row=0, column=1, sticky='w', padx=4, pady=(0, 6))
        ctk.CTkEntry(addbox, textvariable=self.room_price_var, height=34, placeholder_text='Blank = default').grid(row=1, column=0, sticky='ew', padx=4)
        ctk.CTkEntry(addbox, textvariable=self.room_note_var, height=34).grid(row=1, column=1, sticky='ew', padx=4)
        ctk.CTkButton(addbox, text='Add Room →', command=self.add_selected_room).grid(row=2, column=0, columnspan=2, sticky='ew', padx=4, pady=(10, 0))

        selected = ctk.CTkFrame(middle, corner_radius=18)
        selected.grid(row=0, column=1, sticky='nsew', padx=(6, 0))
        ctk.CTkLabel(selected, text='Selected Rooms', font=ctk.CTkFont(size=18, weight='bold')).pack(anchor='w', padx=14, pady=(12, 8))
        sel_treef = ModernTreeFrame(
            selected,
            ('room_id', 'room_number', 'room_type', 'room_price', 'room_notes'),
            ['Room ID', 'Room', 'Type', 'Reserved Price', 'Note'],
            [70, 90, 120, 120, 170],
            6
        )
        sel_treef.pack(fill='both', expand=True, padx=14, pady=(0, 10))
        self.selected_tree = sel_treef.tree
        ctk.CTkButton(selected, text='← Remove Room', fg_color='gray30', hover_color='gray25', command=self.remove_selected_room).pack(fill='x', padx=14, pady=(0, 14))

        btns = ctk.CTkFrame(self.create_panel, fg_color='transparent')
        btns.pack(fill='x', padx=10, pady=4)

        btn_row1 = ctk.CTkFrame(btns, fg_color='transparent')
        btn_row1.pack(fill='x', pady=(0, 4))
        btn_row2 = ctk.CTkFrame(btns, fg_color='transparent')
        btn_row2.pack(fill='x')

        ctk.CTkButton(btn_row1, text='Calculate Total', command=self.update_total_from_selected_rooms).pack(side='left', padx=4)
        ctk.CTkButton(btn_row1, text=self.t('add_reservation'), command=self.add_reservation).pack(side='left', padx=4)
        ctk.CTkButton(btn_row1, text=self.t('update_selected'), command=self.update_reservation).pack(side='left', padx=4)
        ctk.CTkButton(btn_row2, text=self.t('cancel_reservation'), fg_color='#b91c1c', hover_color='#991b1b', command=self.cancel_reservation).pack(side='left', padx=4)
        ctk.CTkButton(btn_row2, text=self.t('export_invoice'), command=self.export_invoice).pack(side='left', padx=4)
        ctk.CTkButton(btn_row2, text=self.t('clear'), fg_color='gray30', hover_color='gray25', command=self.clear_form).pack(side='left', padx=4)

    def toggle_create_panel(self):
        self.create_panel_visible = not self.create_panel_visible
        if self.create_panel_visible:
            self.create_panel.pack(fill='x', padx=10, pady=8, before=self.table_card)
        else:
            self.create_panel.pack_forget()

    def pick_date(self, target_var):
        popup = ctk.CTkToplevel(self)
        popup.title('Select Date')
        popup.geometry('320x360')
        popup.transient(self.winfo_toplevel())
        popup.grab_set()
        popup.lift()
        popup.focus_force()

        current_value = target_var.get().strip()

        try:
            year, month, day = map(int, current_value.split('-'))
            cal = Calendar(
                popup,
                selectmode='day',
                year=year,
                month=month,
                day=day,
                date_pattern='yyyy-mm-dd'
            )
        except Exception:
            cal = Calendar(
                popup,
                selectmode='day',
                date_pattern='yyyy-mm-dd'
            )

        cal.pack(fill='both', expand=True, padx=12, pady=12)

        def apply_date():
            target_var.set(cal.get_date())
            self.update_total_from_selected_rooms()
            self.save_draft()
            popup.destroy()

        ctk.CTkButton(
            popup,
            text='Use Date',
            command=apply_date
        ).pack(fill='x', padx=12, pady=(0, 12))

    def load_guest_dropdown(self):
        guests = self.db.fetch_guests()
        self.guest_map = {}
        values = ['']
        for g in guests:
            key = f"{g['full_name']} (ID {g['id']})"
            self.guest_map[key] = g['id']
            values.append(key)
        self.guest_menu.configure(values=values)
        if self.guest_var.get() not in values:
            self.guest_var.set('')

    def get_form_data(self):
        return {
            'guest_var': self.guest_var.get(),
            'new_guest_name': self.new_guest_name.get(),
            'new_guest_phone': self.new_guest_phone.get(),
            'new_guest_email': self.new_guest_email.get(),
            'room_type_filter': self.room_type_filter.get(),
            'check_in': self.check_in.get(),
            'check_out': self.check_out.get(),
            'adults': self.adults.get(),
            'children_var': self.children_var.get(),
            'status': self.status.get(),
            'total_var': self.total_var.get(),
            'notes_var': self.notes_var.get(),
            'search_var': self.search_var.get(),
            'status_filter': self.status_filter.get(),
            'filter_date_from': self.filter_date_from.get(),
            'filter_date_to': self.filter_date_to.get(),
            'selected_rooms': self.selected_rooms,
        }

    def save_draft(self):
        try:
            self.db.save_form_draft('reservations_form', self.get_form_data())
        except Exception:
            pass

    def load_draft(self):
        draft = self.db.load_form_draft('reservations_form')
        if not draft:
            return
        self.load_guest_dropdown()
        self.guest_var.set(draft.get('guest_var', ''))
        self.new_guest_name.set(draft.get('new_guest_name', ''))
        self.new_guest_phone.set(draft.get('new_guest_phone', ''))
        self.new_guest_email.set(draft.get('new_guest_email', ''))
        self.room_type_filter.set(draft.get('room_type_filter', ''))
        self.check_in.set(draft.get('check_in', ''))
        self.check_out.set(draft.get('check_out', ''))
        self.adults.set(draft.get('adults', '1'))
        self.children_var.set(draft.get('children_var', '0'))
        self.status.set(draft.get('status', 'Reserved'))
        self.total_var.set(draft.get('total_var', '0.00'))
        self.notes_var.set(draft.get('notes_var', ''))
        self.search_var.set(draft.get('search_var', ''))
        self.status_filter.set(draft.get('status_filter', ''))
        self.filter_date_from.set(draft.get('filter_date_from', ''))
        self.filter_date_to.set(draft.get('filter_date_to', ''))
        self.selected_rooms = draft.get('selected_rooms', []) or []
        self.refresh_selected_rooms()
        self.update_total_from_selected_rooms()

    def start_autosave(self):
        self.save_draft()
        self._job = self.after(self.AUTOSAVE_MS, self.start_autosave)

    def stop_autosave(self):
        if self._job:
            self.after_cancel(self._job)
            self._job = None

    def parse_amount(self, value, label='Amount'):
        raw = str(value).strip()
        if not raw:
            raise ValueError(f'{label} is required.')
        raw = raw.replace('$', '').replace('€', '').replace(' ', '')
        if ',' in raw and '.' in raw:
            raw = raw.replace(',', '')
        else:
            raw = raw.replace(',', '.')
        val = float(raw)
        if val <= 0:
            raise ValueError(f'{label} must be greater than 0.')
        return round(val, 2)

    def find_rooms(self):
        try:
            check_in = self.check_in.get().strip()
            check_out = self.check_out.get().strip()
            if not valid_date_range(check_in, check_out):
                raise ValueError('Invalid dates. Use YYYY-MM-DD and check-out after check-in.')

            rooms = self.db.available_rooms_for_dates(
                check_in,
                check_out,
                self.room_type_filter.get().strip()
            )

            self.available_room_map = {}
            for item in self.available_tree.get_children():
                self.available_tree.delete(item)

            selected_room_ids = {r['room_id'] for r in self.selected_rooms}
            for r in rooms:
                if r['id'] in selected_room_ids:
                    continue
                self.available_room_map[r['id']] = {
                    'room_id': r['id'],
                    'room_number': r['room_number'],
                    'room_type': r['room_type'],
                    'default_price': float(r['price_per_night']),
                    'capacity': int(r['capacity'])
                }
                self.available_tree.insert(
                    '',
                    'end',
                    values=(
                        r['id'],
                        r['room_number'],
                        r['room_type'],
                        f"{float(r['price_per_night']):.2f}",
                        r['capacity']
                    )
                )
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def add_selected_room(self):
        try:
            selected = self.available_tree.selection()
            if not selected:
                raise ValueError('Select a room from the available rooms list.')

            values = self.available_tree.item(selected[0], 'values')
            room_id = int(values[0])
            room_number = values[1]
            room_type = values[2]
            default_price = float(values[3])

            room_price = default_price if not self.room_price_var.get().strip() else self.parse_amount(self.room_price_var.get(), 'Room price')

            for item in self.selected_rooms:
                if item['room_id'] == room_id:
                    raise ValueError('This room is already added.')

            self.selected_rooms.append({
                'room_id': room_id,
                'room_number': room_number,
                'room_type': room_type,
                'room_price': room_price,
                'room_notes': self.room_note_var.get().strip()
            })

            self.room_price_var.set('')
            self.room_note_var.set('')
            self.refresh_selected_rooms()
            self.find_rooms()
            self.update_total_from_selected_rooms()
            self.save_draft()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def remove_selected_room(self):
        try:
            selected = self.selected_tree.selection()
            if not selected:
                raise ValueError('Select a room from the selected rooms list.')
            room_id = int(self.selected_tree.item(selected[0], 'values')[0])
            self.selected_rooms = [r for r in self.selected_rooms if r['room_id'] != room_id]
            self.refresh_selected_rooms()
            self.find_rooms()
            self.update_total_from_selected_rooms()
            self.save_draft()
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def refresh_selected_rooms(self):
        for item in self.selected_tree.get_children():
            self.selected_tree.delete(item)
        for room in self.selected_rooms:
            self.selected_tree.insert(
                '',
                'end',
                values=(
                    room['room_id'],
                    room['room_number'],
                    room['room_type'],
                    f"{float(room['room_price']):.2f}",
                    room.get('room_notes', '')
                )
            )

    def update_total_from_selected_rooms(self):
        try:
            check_in = self.check_in.get().strip()
            check_out = self.check_out.get().strip()
            if not valid_date_range(check_in, check_out):
                self.total_var.set('0.00')
                return
            nights = (parse_date(check_out) - parse_date(check_in)).days
            total = sum(float(room['room_price']) * nights for room in self.selected_rooms)
            self.total_var.set(f'{total:.2f}')
        except Exception:
            self.total_var.set('0.00')

    def form_values(self):
        selected_guest = self.guest_var.get().strip()
        typed_name = self.new_guest_name.get().strip()
        typed_phone = self.new_guest_phone.get().strip()
        typed_email = self.new_guest_email.get().strip()

        if selected_guest in self.guest_map:
            guest_id = self.guest_map[selected_guest]
        elif typed_name:
            guest_id = self.db.add_guest(typed_name, typed_phone, typed_email, '', '', '', '')
            self.load_guest_dropdown()
        else:
            raise ValueError('Select an existing guest or type a new guest name.')

        if not valid_date_range(self.check_in.get().strip(), self.check_out.get().strip()):
            raise ValueError('Invalid dates. Use YYYY-MM-DD and check-out after check-in.')

        adults = int(self.adults.get())
        children = int(self.children_var.get())

        if adults < 1:
            raise ValueError('Adults must be at least 1.')
        if children < 0:
            raise ValueError('Children cannot be negative.')
        if not self.selected_rooms:
            raise ValueError('Add at least one room.')

        return guest_id, adults, children, self.notes_var.get().strip(), self.selected_rooms

    def add_reservation(self):
        try:
            guest_id, adults, children, notes, room_items = self.form_values()
            self.db.add_reservation(
                guest_id=guest_id,
                check_in=self.check_in.get().strip(),
                check_out=self.check_out.get().strip(),
                adults=adults,
                children=children,
                status=self.status.get(),
                notes=notes,
                room_items=room_items
            )
            self.db.clear_form_draft('reservations_form')
            self.app.refresh_all()
            self.clear_form()
            self.refresh()
            messagebox.showinfo('Success', 'Reservation added.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def update_reservation(self):
        if not self.selected_id:
            return messagebox.showwarning('Select', 'Select a reservation first.')
        try:
            guest_id, adults, children, notes, room_items = self.form_values()
            self.db.update_reservation(
                reservation_id=self.selected_id,
                guest_id=guest_id,
                check_in=self.check_in.get().strip(),
                check_out=self.check_out.get().strip(),
                adults=adults,
                children=children,
                status=self.status.get(),
                notes=notes,
                room_items=room_items
            )
            self.db.clear_form_draft('reservations_form')
            self.app.refresh_all()
            self.clear_form()
            self.refresh()
            messagebox.showinfo('Success', 'Reservation updated.')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def cancel_reservation(self):
        if not self.selected_id:
            return messagebox.showwarning('Select', 'Select a reservation first.')
        if messagebox.askyesno('Confirm', 'Cancel selected reservation?'):
            try:
                self.db.cancel_reservation(self.selected_id)
                self.app.refresh_all()
                self.clear_form()
                self.refresh()
                messagebox.showinfo('Success', 'Reservation cancelled.')
            except Exception as e:
                messagebox.showerror('Error', str(e))

    def export_invoice(self):
        if not self.selected_id:
            return messagebox.showwarning('Select', 'Select a reservation first.')
        path = filedialog.asksaveasfilename(
            title='Save Invoice PDF',
            defaultextension='.pdf',
            filetypes=[('PDF files', '*.pdf')]
        )
        if not path:
            return
        try:
            self.db.export_invoice_pdf(self.selected_id, path, hotel_name=self.app.get_app_title())
            messagebox.showinfo('Saved', f'Invoice exported to:\n{path}')
        except Exception as e:
            messagebox.showerror('Error', str(e))

    def on_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return

        vals = self.tree.item(sel[0], 'values')
        self.selected_id = int(vals[0])
        guest_name = vals[1]

        for label in self.guest_map:
            if label.startswith(guest_name + ' ('):
                self.guest_var.set(label)
                break

        res = self.db.get_reservation(self.selected_id)
        self.check_in.set(res['check_in'])
        self.check_out.set(res['check_out'])
        self.adults.set(res['adults'])
        self.children_var.set(res['children'])
        self.total_var.set(f"{float(res['total_price']):.2f}")
        self.status.set(res['status'])
        self.notes_var.set(res['notes'] or '')

        self.new_guest_name.set('')
        self.new_guest_phone.set('')
        self.new_guest_email.set('')

        self.selected_rooms = []
        for rr in self.db.fetch_reservation_rooms(self.selected_id):
            self.selected_rooms.append({
                'room_id': rr['room_id'],
                'room_number': rr['room_number'],
                'room_type': rr['room_type'],
                'room_price': float(rr['room_price']),
                'room_notes': rr['room_notes'] or ''
            })

        if not self.create_panel_visible:
            self.toggle_create_panel()

        self.refresh_selected_rooms()
        self.find_rooms()
        self.update_total_from_selected_rooms()
        self.save_draft()

    def clear_form(self):
        self.selected_id = None
        self.guest_var.set('')
        self.new_guest_name.set('')
        self.new_guest_phone.set('')
        self.new_guest_email.set('')
        self.room_type_filter.set('')
        self.check_in.set('')
        self.check_out.set('')
        self.adults.set('1')
        self.children_var.set('0')
        self.total_var.set('0.00')
        self.status.set('Reserved')
        self.notes_var.set('')
        self.room_price_var.set('')
        self.room_note_var.set('')
        self.selected_rooms = []

        self.refresh_selected_rooms()
        for item in self.available_tree.get_children():
            self.available_tree.delete(item)

        self.db.clear_form_draft('reservations_form')

    def reset_filters(self):
        self.search_var.set('')
        self.status_filter.set('')
        self.filter_date_from.set('')
        self.filter_date_to.set('')
        self.refresh()

    def refresh(self):
        self.load_guest_dropdown()

        for item in self.tree.get_children():
            self.tree.delete(item)

        rows = self.db.fetch_reservations(
            self.search_var.get().strip(),
            self.status_filter.get().strip(),
            self.filter_date_from.get().strip(),
            self.filter_date_to.get().strip()
        )

        for row in rows:
            self.tree.insert(
                '',
                'end',
                values=(
                    row['id'],
                    row['full_name'],
                    row['room_number'],
                    row['room_count'],
                    row['check_in'],
                    row['check_out'],
                    row['adults'],
                    row['children'],
                    f"{float(row['total_price']):.2f}",
                    row['status']
                )
            )