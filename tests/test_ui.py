import os
import sys
import tempfile
import tkinter as tk
import unittest
from app import App
from widgets import CalendarPicker, PALETTES

class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            root=tk.Tk(); root.withdraw(); root.destroy()
        except tk.TclError as e:
            if sys.platform in ('win32','darwin'): raise
            raise unittest.SkipTest(f'Sessão gráfica indisponível: {e}')
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.app=App(self.directory.name,welcome=False)
        self.errors=[]
        self.app.report_callback_exception=lambda *error:self.errors.append(error)
        self.app.update()
    def tearDown(self):
        self.app.close(); self.directory.cleanup()
        self.assertEqual(self.errors,[])
    def test_calendar_leap_day_and_month(self):
        var=tk.StringVar(self.app,value='2024-02-01')
        popup=CalendarPicker(self.app,var); popup.choose(29)
        self.assertEqual(var.get(),'2024-02-29')
        month=tk.StringVar(self.app,value='2026-12')
        popup=CalendarPicker(self.app,month,True); popup.move(1); popup.choose()
        self.assertEqual(month.get(),'2027-01')
    def test_theme_populated_charts_and_form(self):
        a=self.app
        a.store.save_catalog('types','Salário','Receita')
        a.store.add('2026-10-01','Salário','Trabalho','Pagamento',400000)
        a.store.add('2026-10-02','Despesa','Moradia','Aluguel',100000,paid=False)
        a.store.add('2026-10-03','Aporte','Reserva de emergência','Depósito',25000)
        a.store.db.commit(); a.period.set('2026-10'); a.refresh(); a.update()
        self.assertEqual(len(a.entries.get_children()),3)
        for canvas in a.dashboard.canvases: self.assertGreater(len(canvas.find_all()),1)
        a.mode.set('Escuro');a.apply_theme();a.update()
        self.assertEqual(a.store.setting('theme'),'Escuro')
        for canvas in a.dashboard.canvases: self.assertEqual(canvas.cget('background'),PALETTES['Escuro']['panel'])
        a.mode.set('Claro');a.apply_theme();a.update()
        a.entry_dialog(); a.update()
        dialogs=[w for w in a.winfo_children() if isinstance(w,tk.Toplevel)]
        self.assertEqual(len(dialogs),1); dialogs[0].destroy()
        a.catalog_dialog('categories');a.update()
        dialogs=[w for w in a.winfo_children() if isinstance(w,tk.Toplevel)]
        self.assertEqual(len(dialogs),1);dialogs[0].destroy()
