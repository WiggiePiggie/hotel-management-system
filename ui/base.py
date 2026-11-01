import customtkinter as ctk


class BasePage(ctk.CTkFrame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.db = app.db

    def t(self, key):
        return self.app.t(key)

    def refresh(self):
        pass

    def stop_autosave(self):
        pass
