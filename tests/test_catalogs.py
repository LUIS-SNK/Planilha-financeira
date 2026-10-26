import sqlite3
import tempfile
import unittest
from pathlib import Path
from core import Store

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:'); self.addCleanup(self.store.db.close)
    def test_custom_types_keep_financial_behavior(self):
        s=self.store
        s.save_catalog('types','Salário','Receita')
        s.save_catalog('types','Compra','Despesa')
        s.add('2026-10-01','Salário','Trabalho','Recebimento',50000)
        s.add('2026-10-02','Compra','Mercado','Compra',15000)
        rows=s.rows('2026-10')
        self.assertEqual(sum(r['amount'] for r in rows if r['kind']=='Receita'),50000)
        self.assertEqual(sum(r['amount'] for r in rows if r['kind']=='Despesa'),15000)
        self.assertEqual(rows[0]['type_name'],'Compra')
        s.db.commit()
        s.save_catalog('types','Supermercado','Despesa',old='Compra')
        self.assertEqual(s.rows('2026-10')[0]['type_name'],'Supermercado')
        with self.assertRaises(ValueError): s.save_catalog('types','Supermercado','Receita',old='Supermercado')
        with self.assertRaises(ValueError): s.delete_catalog('types','Supermercado')
    def test_category_rename_keeps_transactions_and_budgets(self):
        s=self.store
        s.save_catalog('categories','Tesouro','Investimento')
        s.add('2026-10-01','Aporte','Tesouro','Aporte',10000)
        s.db.execute('INSERT INTO budgets VALUES(?,?,?)',('2026-10','Tesouro',20000)); s.db.commit()
        s.save_catalog('categories','Reserva','Investimento',old='Tesouro')
        self.assertEqual(s.rows()[0]['category'],'Reserva')
        self.assertEqual(s.db.execute('SELECT category FROM budgets').fetchone()[0],'Reserva')
        with self.assertRaises(ValueError): s.delete_catalog('categories','Reserva')
    def test_duplicate_and_default_protection(self):
        s=self.store
        for args in [('types','receita','Receita'),('categories','moradia','Categoria')]:
            with self.assertRaises(ValueError): s.save_catalog(*args)
        with self.assertRaises(ValueError): s.delete_catalog('types','Receita')
        s.save_catalog('categories','Não utilizado','Investimento')
        s.delete_catalog('categories','Não utilizado')
        self.assertNotIn('Não utilizado',[r['name'] for r in s.catalog('categories')])
    def test_existing_database_migration_and_theme_persist(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'existing.db'
            old=sqlite3.connect(p)
            old.execute("CREATE TABLE entries(id INTEGER PRIMARY KEY, date TEXT, period TEXT, kind TEXT, category TEXT, description TEXT, amount INTEGER, payment TEXT, paid INTEGER, detail TEXT)")
            old.execute("INSERT INTO entries VALUES(1,'2026-10-01','2026-10','Despesa','Categoria antiga','Histórico',12345,'Pix',1,'Original')")
            old.commit(); old.close()
            s=Store(p)
            try:
                self.assertIn('Categoria antiga',[r['name'] for r in s.catalog('categories')])
                self.assertEqual(s.rows()[0]['detail'],'Original')
                s.set_setting('theme','Escuro')
            finally: s.db.close()
            s=Store(p)
            try:
                self.assertEqual(s.setting('theme'),'Escuro')
                self.assertEqual(s.rows()[0]['amount'],12345)
            finally: s.db.close()
