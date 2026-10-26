import tempfile
import unittest
import zipfile
from pathlib import Path
from core import Store, cents, money

class FinanceTests(unittest.TestCase):
    def test_money_rounding(self):
        self.assertEqual(cents('1.234,56'),123456)
        self.assertEqual(cents('0,105'),11)
        self.assertEqual(money(-123456),'R$ -1.234,56')
    def test_backup(self):
        store=Store(':memory:')
        store.add('2026-07-04','Despesa','Contas','Luz',12000,paid=False)
        store.db.commit()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'copy.db'; store.backup(path)
            copied=Store(path)
            self.assertEqual(copied.rows('2026-07')[0]['amount'],12000)
            self.assertEqual(copied.rows('2026-07')[0]['paid'],0)
    def test_import_layout_and_duplicate(self):
        # Synthetic workbook: the monthly investment must not become income;
        # cached formulas must not become expense transactions.
        ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        def cell(ref,value):
            return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'
        def sheet(cells): return f'<worksheet xmlns="{ns}"><sheetData><row r="1">{cells}</row></sheetData></worksheet>'
        monthly=''.join([cell('C5','Salário'),cell('D5','1000'),cell('B23','Reserva de emergência/ investimentos'),cell('D26','80'),cell('K5','Categoria'),cell('K6','Moradia'),cell('L6','Aluguel'),cell('M6','46204'),cell('P6','300'),cell('Q6','1'),cell('K7','Contas'),cell('P7','25'),'<c r="P38"><f>SUM(P6:P7)</f><v>325</v></c>'])
        investments=''.join([cell('J7','10'),cell('J17','80'),cell('L18','5'),cell('H17','Banco')])
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.xlsx'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Jul" sheetId="1" r:id="rId1"/><sheet name="Investimentos" sheetId="2" r:id="rId2"/></sheets></workbook>')
                z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>')
                z.writestr('xl/worksheets/sheet1.xml',sheet(monthly)); z.writestr('xl/worksheets/sheet2.xml',sheet(investments))
            store=Store(':memory:'); count,_=store.import_xlsx(p)
            self.assertEqual(count,6)
            rows=store.rows('2026-07')
            self.assertEqual(sum(r['amount'] for r in rows if r['kind']=='Receita'),100000)
            self.assertEqual(sum(r['amount'] for r in rows if r['kind']=='Despesa'),32500)
            self.assertEqual(sum(r['amount'] for r in rows if r['kind']=='Aporte'),8000)
            with self.assertRaises(ValueError): store.import_xlsx(p)
            self.assertEqual(len(store.rows()),6)
    def test_invalid_value(self):
        s=Store(':memory:')
        with self.assertRaises(ValueError): s.add('2026-01-01','Receita','Renda','Teste',-1)

if __name__=='__main__': unittest.main()
