"""Persistência e importação; usa apenas a biblioteca padrão do Python."""
import calendar
import datetime as dt
import hashlib
import sqlite3
import zipfile
import xml.etree.ElementTree as ET
from decimal import Decimal, ROUND_HALF_UP

MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
NS = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def cents(value):
    if isinstance(value, str):
        value=value.strip().replace('R$', '').replace(' ', '')
        if ',' in value: value=value.replace('.', '').replace(',', '.')
    return int((Decimal(str(value))*100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def money(value):
    return f'R$ {value/100:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')

def excel_date(value, fallback):
    try: return (dt.datetime(1899,12,30)+dt.timedelta(days=float(value))).date().isoformat()
    except (ValueError,TypeError,OverflowError): return fallback

class Store:
    def __init__(self, path):
        self.db=sqlite3.connect(path)
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS entries(id INTEGER PRIMARY KEY, date TEXT NOT NULL, period TEXT NOT NULL, kind TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount>=0), payment TEXT DEFAULT '', paid INTEGER DEFAULT 1, detail TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS budgets(period TEXT, category TEXT, amount INTEGER, PRIMARY KEY(period,category));
        CREATE TABLE IF NOT EXISTS goals(id INTEGER PRIMARY KEY, name TEXT, target INTEGER, saved INTEGER, location TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS imports(hash TEXT PRIMARY KEY, filename TEXT, imported_at TEXT);
        ''')
    def add(self, date, kind, category, description, amount, payment='', paid=1, detail='', period=None):
        dt.date.fromisoformat(date)
        if amount<=0: raise ValueError('O valor deve ser maior que zero.')
        self.db.execute('INSERT INTO entries(date,period,kind,category,description,amount,payment,paid,detail) VALUES(?,?,?,?,?,?,?,?,?)',(date,period or date[:7],kind,category,description,amount,payment,int(paid),detail))
    def rows(self, period='', search=''):
        return self.db.execute('SELECT * FROM entries WHERE period LIKE ? AND (description LIKE ? OR category LIKE ?) ORDER BY date DESC,id DESC',(period+'%', '%'+search+'%', '%'+search+'%')).fetchall()
    def backup(self, path):
        with sqlite3.connect(path) as target: self.db.backup(target)
    def import_xlsx(self,path):
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if self.db.execute('SELECT 1 FROM imports WHERE hash=?',(digest,)).fetchone(): raise ValueError('Esta planilha já foi importada.')
        warnings=[]; count=0
        with zipfile.ZipFile(path) as z:
            strings=[]
            if 'xl/sharedStrings.xml' in z.namelist():
                strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS)]
            rels={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
            sheets={}
            for s in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets',NS):
                target=rels[s.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
                target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
                cells={}
                for c in ET.fromstring(z.read(target)).findall('.//m:sheetData/m:row/m:c',NS):
                    v=c.find('m:v',NS); val=v.text if v is not None else ''
                    if c.attrib.get('t')=='s' and val: val=strings[int(val)]
                    elif c.attrib.get('t')=='inlineStr': val=''.join(c.find('m:is',NS).itertext())
                    cells[c.attrib['r']]=val or ''
                    if c.find('m:f',NS) is not None: cells['formula:'+c.attrib['r']]=True
                sheets[s.attrib['name']]=cells
        with self.db:
            for m,name in enumerate(MONTHS,1):
                cells=sheets.get(name,{})
                # The workbook is the supplied 2026 template. Preserve its monthly grouping
                # separately from dates, which sometimes belong to preceding months.
                period=f'2026-{m:02d}'; fallback=period+'-01'
                header_rows=sorted(int(k[1:]) for k,v in cells.items() if k.startswith('K') and v.strip()=='Categoria')
                income_end=next((r for r in range(6,1001) if 'investimentos' in cells.get(f'B{r}','').lower()),23)
                for r in range(5,income_end):
                    raw=cells.get(f'D{r}','')
                    if raw:
                        try: amount=cents(raw)
                        except Exception: continue
                        if amount>0:
                            self.add(excel_date(cells.get(f'B{r}'),fallback),'Receita','Renda',cells.get(f'C{r}') or 'Receita importada',amount,period=period); count+=1
                for i,start in enumerate(header_rows):
                    end=header_rows[i+1] if i+1<len(header_rows) else 1001
                    for r in range(start+1,end):
                        if cells.get('formula:'+f'P{r}'): continue
                        raw=cells.get(f'P{r}','')
                        try: amount=cents(raw)
                        except Exception: continue
                        if amount<=0: continue
                        category=cells.get(f'K{r}') or 'Sem categoria'
                        description=cells.get(f'L{r}') or 'Despesa importada'
                        detail=f"Importado {name}, linha {r}; {cells.get(f'N{start}','Detalhe')}: {cells.get(f'N{r}','')}"
                        self.add(excel_date(cells.get(f'M{r}'),fallback),'Despesa',category,description,amount,cells.get(f'O{r}',''),cells.get(f'Q{r}') in ('1','true','TRUE'),detail,period); count+=1
                for r in range(6,60):
                    cat=cells.get(f'X{r}','')
                    try: amount=cents(cells.get(f'Y{r}',''))
                    except Exception: continue
                    if cat and amount>0: self.db.execute('INSERT OR REPLACE INTO budgets VALUES(?,?,?)',(period,cat,amount))
            cells=sheets.get('Investimentos',{})
            for loc_col,dep_col,out_col,initial_cell,label in [('H','J','L','J7','Reserva de emergência'),('O','Q','S','Q7','Investimento 1'),('V','X','Z','X7','Investimento 2')]:
                try: initial=cents(cells.get(initial_cell,'0'))
                except Exception: initial=0
                if initial>0:
                    self.add('2026-01-01','Saldo inicial',label,'Saldo anterior importado',initial); count+=1
                for m in range(1,13):
                    r=10+m
                    for col,kind in [(dep_col,'Aporte'),(out_col,'Retirada')]:
                        try: amount=cents(cells.get(f'{col}{r}',''))
                        except Exception: continue
                        if amount>0:
                            self.add(f'2026-{m:02d}-01',kind,label,cells.get(f'{loc_col}{r}') or label,amount); count+=1
            cells=sheets.get('Metas',{})
            for col,valcol in [('B','C'),('E','F'),('H','I'),('K','L')]:
                name=cells.get(col+'5','')
                if not name or 'Insira o nome' in name: continue
                try: target=cents(cells.get(valcol+'6','0')); saved=cents(cells.get(valcol+'7','0'))
                except Exception: continue
                self.db.execute('INSERT INTO goals(name,target,saved) VALUES(?,?,?)',(name,target,saved))
            self.db.execute('INSERT INTO imports VALUES(?,?,?)',(digest,path.name,dt.datetime.now().isoformat()))
        warnings.append('Abas de exemplo e totais calculados não são importados. A competência mensal é preservada mesmo quando a data pertence a outro mês. Confira os totais antes de usar.')
        return count,warnings
