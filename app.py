import calendar
import csv
import datetime as dt
import os
import sys
import tempfile
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from core import Store, cents, money, BEHAVIORS
from widgets import CalendarPicker, Dashboard, PALETTES, FONT_FAMILY

from paths import data_directory

DATA=data_directory()

class App(tk.Tk):
    def __init__(self, data_dir=None, welcome=True):
        super().__init__()
        self.title('Minhas Finanças')
        width=min(1280,self.winfo_screenwidth()-80); height=min(840,self.winfo_screenheight()-80)
        self.geometry(f'{width}x{height}'); self.minsize(min(1100,width),min(700,height))
        self.configure(bg='#f2f5fa')
        self.data_dir=Path(data_dir) if data_dir else DATA
        self.data_dir.mkdir(parents=True,exist_ok=True)
        self.store=Store(self.data_dir/'financas.db')
        backup=self.data_dir/'backups'; backup.mkdir(exist_ok=True)
        self.store.backup(backup/f'{dt.date.today()}.db')
        self.style=style=ttk.Style(self); style.theme_use('clam')
        style.configure('.',font=(FONT_FAMILY,11),background='#f2f5fa',foreground='#17283e')
        style.configure('TButton',padding=9); style.configure('Treeview',rowheight=32,background='white',fieldbackground='white')
        style.configure('Treeview.Heading',font=(FONT_FAMILY,10,'bold'),padding=8)
        top=ttk.Frame(self,padding=20); top.pack(fill='x')
        ttk.Label(top,text='Minhas Finanças',font=(FONT_FAMILY,23,'bold')).pack(side='left')
        ttk.Button(top,text='+ Novo lançamento',command=self.entry_dialog).pack(side='right')
        self.mode=tk.StringVar(value=self.store.setting('theme','Claro'))
        theme=ttk.Combobox(top,textvariable=self.mode,values=['Claro','Escuro'],state='readonly',width=8)
        theme.pack(side='right',padx=12); theme.bind('<<ComboboxSelected>>',lambda e:self.apply_theme())
        ttk.Label(top,text='Aparência:').pack(side='right')
        bar=ttk.Frame(self,padding=(20,0)); bar.pack(fill='x')
        ttk.Label(bar,text='Período (AAAA-MM ou AAAA):').pack(side='left')
        self.period=tk.StringVar(value=dt.date.today().strftime('%Y-%m'))
        ttk.Entry(bar,textvariable=self.period,width=10).pack(side='left',padx=8)
        ttk.Button(bar,text='Calendário',command=lambda:CalendarPicker(self,self.period,True)).pack(side='left',padx=(0,5))
        ttk.Button(bar,text='Atualizar',command=self.refresh).pack(side='left')
        ttk.Button(bar,text='Importar Excel',command=self.import_file).pack(side='right')
        ttk.Button(bar,text='Exportar CSV',command=self.export).pack(side='right',padx=8)
        ttk.Button(bar,text='Backup',command=self.backup).pack(side='right')
        tabs=ttk.Notebook(self); tabs.pack(fill='both',expand=True,padx=20,pady=18)
        self.pages={}
        for name in ['Visão geral','Lançamentos','Orçamentos','Investimentos','Metas','Planejamento','Resumo anual','Cartões','Cadastros']:
            f=ttk.Frame(tabs,padding=15); tabs.add(f,text=name); self.pages[name]=f
        self.catalog_tables={}
        registrations=ttk.Notebook(self.pages['Cadastros']); registrations.pack(fill='both',expand=True)
        for catalog,title,column in [('types','Tipos de lançamento','Comportamento financeiro'),('categories','Categorias e investimentos','Grupo')]:
            frame=ttk.Frame(registrations,padding=10); registrations.add(frame,text=title)
            ttk.Label(frame,text='Tipos personalizados usam o comportamento escolhido para calcular os totais.' if catalog=='types' else 'Cadastre categorias e investimentos antes de registrar movimentações.').pack(anchor='w')
            actions=ttk.Frame(frame); actions.pack(fill='x',pady=8)
            for label,callback in [('Novo',lambda c=catalog:self.catalog_dialog(c)),('Editar',lambda c=catalog:self.catalog_dialog(c,True)),('Excluir',lambda c=catalog:self.catalog_delete(c))]:
                ttk.Button(actions,text=label,command=callback).pack(side='left',padx=4)
            self.catalog_tables[catalog]=self.table(frame,['Nome',column])
        self.annual=self.table(self.pages['Resumo anual'],['Mês','Entradas','Despesas','Aportes','Saldo previsto','Maior categoria'])
        self.cards=self.table(self.pages['Cartões'],['Mês','Cartão','Compras','Valor pendente'])
        ttk.Label(self.pages['Cartões'],text='Agrupa lançamentos com pagamento Cartão ou Crédito. Valores por competência; fechamento e vencimento não são calculados.').pack(anchor='w')
        self.tasks=self.table(self.pages['Planejamento'],['Competência','Objetivo do mês','Concluído'])
        ttk.Button(self.pages['Planejamento'],text='Novo objetivo do mês',command=self.task_dialog).pack(side='left')
        ttk.Button(self.pages['Planejamento'],text='Concluir / reabrir',command=self.task_toggle).pack(side='left',padx=5)
        ttk.Button(self.pages['Planejamento'],text='Calcular reserva ideal',command=self.reserve_dialog).pack(side='right')
        self.summary=ttk.Frame(self.pages['Visão geral']); self.summary.pack(fill='x')
        self.dashboard=Dashboard(self.pages['Visão geral']); self.dashboard.pack(fill='both',expand=True,pady=12)
        self.search=tk.StringVar(); searchbar=ttk.Frame(self.pages['Lançamentos']); searchbar.pack(fill='x')
        ttk.Label(searchbar,text='Buscar:').pack(side='left'); ttk.Entry(searchbar,textvariable=self.search).pack(side='left',padx=8)
        ttk.Button(searchbar,text='Filtrar',command=self.refresh).pack(side='left')
        for title,cmd in [('Editar',self.edit),('Marcar pago / pendente',self.toggle),('Excluir',self.delete)]: ttk.Button(searchbar,text=title,command=cmd).pack(side='right',padx=3)
        self.entries=self.table(self.pages['Lançamentos'],['Data','Tipo','Categoria','Descrição','Valor','Pagamento','Situação'])
        ttk.Label(self.pages['Lançamentos'],text='Dê dois cliques para editar. O período corresponde à competência do lançamento.').pack(anchor='w')
        self.entries.bind('<Double-1>',lambda e:self.edit())
        ttk.Button(self.pages['Orçamentos'],text='Definir limite mensal',command=self.budget_dialog).pack(anchor='e')
        self.budgets=self.table(self.pages['Orçamentos'],['Categoria','Limite','Gasto','Disponível','Status'])
        ttk.Label(self.pages['Investimentos'],text='Use Novo lançamento para aportes, retiradas e saldos iniciais. A categoria identifica a reserva ou o investimento.').pack(anchor='w')
        self.invest=self.table(self.pages['Investimentos'],['Investimento','Saldo inicial','Aportes','Retiradas','Saldo total'])
        ttk.Button(self.pages['Metas'],text='Nova meta',command=self.goal_dialog).pack(anchor='e')
        self.goals=self.table(self.pages['Metas'],['Meta','Objetivo','Guardado','Falta','Progresso','Local'])
        self.goals.bind('<Double-1>',lambda e:self.goal_dialog(True))
        ttk.Button(self.pages['Metas'],text='Excluir meta selecionada',command=self.delete_goal).pack(anchor='e')
        ttk.Label(self,text=f'Dados locais | Backup diário automático | {self.data_dir}',padding=(20,5)).pack(anchor='w')
        self.apply_theme(persist=False)
        self.refresh()
        self.protocol('WM_DELETE_WINDOW',self.close)
        if welcome and not self.store.db.execute('SELECT 1 FROM entries LIMIT 1').fetchone():
            self.after(400,lambda:messagebox.showinfo('Bem-vinda','Importe sua planilha pelo botão Importar Excel. Seus dados ficam somente neste computador. Depois, use Novo lançamento para registrar movimentações.'))
    def close(self):
        self.store.db.close(); self.destroy()
    def apply_theme(self,persist=True):
        mode=self.mode.get()
        if mode not in PALETTES: mode='Claro'; self.mode.set(mode)
        p=PALETTES[mode]; style=self.style
        self.configure(bg=p['bg'])
        style.configure('.',background=p['bg'],foreground=p['text'])
        style.configure('TEntry',fieldbackground=p['field'],foreground=p['text'],insertcolor=p['text'])
        style.configure('TCombobox',fieldbackground=p['field'],background=p['bg'],foreground=p['text'],arrowcolor=p['text'])
        style.map('TCombobox',fieldbackground=[('readonly',p['field'])],foreground=[('readonly',p['text'])],selectbackground=[('readonly',p['select'])],selectforeground=[('readonly',p['text'])])
        style.configure('TButton',background=p['field'],foreground=p['text'],bordercolor=p['line'])
        style.map('TButton',background=[('active',p['select'])],foreground=[('active',p['text'])])
        style.configure('Selected.TButton',background=p['select'])
        style.configure('Treeview',background=p['panel'],fieldbackground=p['panel'],foreground=p['text'])
        style.map('Treeview',background=[('selected',p['select'])],foreground=[('selected',p['text'])])
        style.configure('Treeview.Heading',background=p['field'],foreground=p['text'])
        style.configure('TNotebook.Tab',background=p['field'],foreground=p['text'],padding=(9,7))
        style.map('TNotebook.Tab',background=[('selected',p['select']),('active',p['select'])],foreground=[('selected',p['text']),('active',p['text'])])
        style.map('Treeview.Heading',background=[('active',p['select'])])
        self.option_add('*TCombobox*Listbox.background',p['field'])
        self.option_add('*TCombobox*Listbox.foreground',p['text'])
        self.option_add('*TCombobox*Listbox.selectBackground',p['select'])
        self.option_add('*TCombobox*Listbox.selectForeground',p['text'])
        self.dashboard.theme(p)
        if persist: self.store.set_setting('theme',mode)
    def catalog_dialog(self,catalog,edit=False):
        key=self.selected(self.catalog_tables[catalog]) if edit else None
        if edit and key is None: return
        record=next((r for r in self.store.catalog(catalog) if r['name']==key),None)
        options=BEHAVIORS if catalog=='types' else ['Categoria','Investimento']
        default=record['behavior' if catalog=='types' else 'section'] if record else options[0]
        def save(v): self.store.save_catalog(catalog,v['name'],v['classification'],key)
        self.form('Editar cadastro' if edit else 'Novo cadastro',[('name','Nome',key or '',None),('classification','Comportamento financeiro' if catalog=='types' else 'Grupo',default,options)],save)
    def catalog_delete(self,catalog):
        key=self.selected(self.catalog_tables[catalog])
        if key is None: return
        if messagebox.askyesno('Excluir cadastro',f'Excluir {key}?'):
            try: self.store.delete_catalog(catalog,key); self.refresh()
            except ValueError as e: messagebox.showerror('Cadastro em uso',str(e))
    def table(self,parent,cols):
        box=ttk.Frame(parent); box.pack(fill='both',expand=True,pady=10)
        tree=ttk.Treeview(box,columns=cols,show='headings',selectmode='browse')
        for c in cols: tree.heading(c,text=c); tree.column(c,width=130,minwidth=65)
        scroll=ttk.Scrollbar(box,orient='vertical',command=tree.yview); tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); tree.pack(fill='both',expand=True)
        return tree
    def fill(self,tree,rows):
        tree.delete(*tree.get_children())
        for key,values in rows: tree.insert('', 'end',iid=str(key),values=values)
    def refresh(self):
        period=self.period.get().strip()
        try:
            if len(period)==7: dt.date.fromisoformat(period+'-01')
            elif len(period)==4: int(period)
            else: raise ValueError()
        except ValueError: messagebox.showerror('Período','Use AAAA-MM para um mês ou AAAA para o ano.'); return
        allrows=self.store.rows(period)
        sums={k:sum(r['amount'] for r in allrows if r['kind']==k) for k in ['Receita','Despesa','Aporte','Retirada']}
        pending=sum(r['amount'] for r in allrows if r['kind']=='Despesa' and not r['paid'])
        for w in self.summary.winfo_children(): w.destroy()
        for label,value in [('Entradas',sums['Receita']),('Despesas previstas',sums['Despesa']),('Saldo previsto',sums['Receita']-sums['Despesa']-sums['Aporte']+sums['Retirada']),('A pagar',pending)]:
            f=ttk.Frame(self.summary,padding=12); f.pack(side='left',expand=True,fill='x')
            ttk.Label(f,text=label).pack(anchor='w'); ttk.Label(f,text=money(value),font=(FONT_FAMILY,20,'bold')).pack(anchor='w')
        self.fill(self.entries,[(r['id'],[r['date'],r['type_name'],r['category'],r['description'],money(r['amount']),r['payment'],'Pago' if r['paid'] else 'Pendente']) for r in self.store.rows(period,self.search.get())])
        categories={}
        for r in allrows:
            if r['kind']=='Despesa': categories[r['category']]=categories.get(r['category'],0)+r['amount']
        self.dashboard.set_data(allrows,self.store.rows(period[:4]),self.store.rows(),period[:4])
        for catalog,tree in self.catalog_tables.items():
            self.fill(tree,[(r['name'],[r['name'],r['behavior'] if catalog=='types' else r['section']]) for r in self.store.catalog(catalog)])
        annual=[]
        for month in range(1,13):
            month_period=f'{period[:4]}-{month:02d}'; month_rows=self.store.rows(month_period)
            totals={k:sum(r['amount'] for r in month_rows if r['kind']==k) for k in ['Receita','Despesa','Aporte','Retirada']}
            cats={}
            for r in month_rows:
                if r['kind']=='Despesa': cats[r['category']]=cats.get(r['category'],0)+r['amount']
            annual.append((month,[month_period,money(totals['Receita']),money(totals['Despesa']),money(totals['Aporte']),money(totals['Receita']-totals['Despesa']-totals['Aporte']+totals['Retirada']),max(cats,key=cats.get) if cats else '—']))
        self.fill(self.annual,annual)
        cards={}
        for r in allrows:
            if r['kind']=='Despesa' and ('cartão' in r['payment'].lower() or 'crédito' in r['payment'].lower()):
                group=cards.setdefault((r['period'],r['payment']),[0,0]); group[0]+=r['amount']; group[1]+=r['amount'] if not r['paid'] else 0
        self.fill(self.cards,[(i,[key[0],key[1],money(value[0]),money(value[1])]) for i,(key,value) in enumerate(sorted(cards.items()))])
        limits=self.store.db.execute('SELECT * FROM budgets WHERE period LIKE ?',(period+'%',)).fetchall()
        grouped={}
        for r in limits: grouped[r['category']]=grouped.get(r['category'],0)+r['amount']
        self.fill(self.budgets,[(i,[cat,money(limit),money(categories.get(cat,0)),money(limit-categories.get(cat,0)),'Acima do limite' if categories.get(cat,0)>limit else 'Dentro do limite']) for i,(cat,limit) in enumerate(grouped.items())])
        inv={r['name']:{'Aporte':0,'Retirada':0,'Saldo inicial':0} for r in self.store.catalog('categories') if r['section']=='Investimento'}
        for r in self.store.rows():
            if r['kind'] in ('Aporte','Retirada','Saldo inicial'):
                d=inv.setdefault(r['category'],{'Aporte':0,'Retirada':0,'Saldo inicial':0}); d[r['kind']]+=r['amount']
        self.fill(self.invest,[(i,[cat,money(d['Saldo inicial']),money(d['Aporte']),money(d['Retirada']),money(d['Saldo inicial']+d['Aporte']-d['Retirada'])]) for i,(cat,d) in enumerate(inv.items())])
        self.fill(self.tasks,[(r['id'],[r['period'],r['name'],'Sim' if r['done'] else 'Não']) for r in self.store.db.execute('SELECT * FROM tasks WHERE period LIKE ?',(period+'%',))])
        self.fill(self.goals,[(r['id'],[r['name'],money(r['target']),money(r['saved']),money(max(0,r['target']-r['saved'])),f"{r['saved']/r['target']*100:.0f}%" if r['target'] else '—',r['location']]) for r in self.store.db.execute('SELECT * FROM goals')])
    def form(self,title,fields,save):
        win=tk.Toplevel(self); win.configure(bg=PALETTES[self.mode.get()]['bg']); win.title(title); win.transient(self); win.grab_set(); win.resizable(False,False)
        values={}
        for i,(key,label,default,options) in enumerate(fields):
            ttk.Label(win,text=label).grid(row=i,column=0,padx=15,pady=7,sticky='w'); var=tk.StringVar(value=str(default)); values[key]=var
            widget=ttk.Combobox(win,textvariable=var,values=options,width=37) if options else ttk.Entry(win,textvariable=var,width=40)
            widget.grid(row=i,column=1,padx=15,pady=7)
            if key in ('date','period'):
                ttk.Button(win,text='Calendário',command=lambda v=var,k=key:CalendarPicker(win,v,k=='period')).grid(row=i,column=2,padx=(0,12))
        if title=='Novo lançamento' and 'date' in values:
            def sync_period(*args):
                try: values['period'].set(dt.date.fromisoformat(values['date'].get()).strftime('%Y-%m'))
                except ValueError: pass
            values['date'].trace_add('write',sync_period)
        def submit():
            try:
                save({k:v.get().strip() for k,v in values.items()}); self.store.db.commit(); self.refresh(); win.destroy()
            except Exception as e:
                self.store.db.rollback(); messagebox.showerror('Não foi possível salvar',str(e),parent=win)
        ttk.Button(win,text='Salvar',command=submit).grid(row=len(fields),column=1,pady=15,sticky='e',padx=15)
    def entry_dialog(self,row=None):
        r=dict(row) if row else {}; today=dt.date.today().isoformat()
        cats=[x['name'] for x in self.store.catalog('categories')]
        types=[x['name'] for x in self.store.catalog('types')]
        fields=[('date','Data (AAAA-MM-DD)',r.get('date',today),None),('period','Competência (AAAA-MM)',r.get('period',today[:7]),None),('kind','Tipo',r.get('kind','Despesa'),types),('category','Categoria / investimento',r.get('category','Alimentação'),cats or ['Alimentação','Moradia','Contas','Saúde','Reserva de emergência']),('description','Descrição',r.get('description',''),None),('amount','Valor (R$)',f"{r.get('amount',0)/100:.2f}",None),('payment','Forma de pagamento',r.get('payment','Pix'),['Pix','Débito','Crédito','Boleto','Dinheiro']),('paid','Situação','Pago' if r.get('paid',1) else 'Pendente',['Pago','Pendente']),('repeat','Repetir por quantos meses?','1',None),('detail','Observações / parcela',r.get('detail',''),None)]
        def save(v):
            date=dt.date.fromisoformat(v['date']); period=dt.date.fromisoformat(v['period']+'-01'); amount=cents(v['amount']); n=int(v['repeat'])
            if not 1<=n<=120: raise ValueError('Use de 1 a 120 meses.')
            if v['kind'] not in types: raise ValueError('Tipo inválido.')
            if not v['description'] or not v['category']: raise ValueError('Informe descrição e categoria.')
            if row: self.store.db.execute('DELETE FROM entries WHERE id=?',(r['id'],))
            for i in range(n):
                def shift(d):
                    y,m=divmod(d.year*12+d.month-1+i,12); m+=1
                    return d.replace(year=y,month=m,day=min(d.day,calendar.monthrange(y,m)[1]))
                self.store.add(shift(date).isoformat(),v['kind'],v['category'],v['description'],amount,v['payment'],v['paid']=='Pago',v['detail']+(f' | {i+1}/{n}' if n>1 else ''),shift(period).strftime('%Y-%m'))
        self.form('Editar lançamento' if row else 'Novo lançamento',fields,save)
    def selected(self,tree):
        ids=tree.selection(); return ids[0] if ids else None
    def edit(self):
        key=self.selected(self.entries)
        if key: self.entry_dialog(self.store.db.execute('SELECT * FROM entries WHERE id=?',(key,)).fetchone())
    def toggle(self):
        key=self.selected(self.entries)
        if key:
            self.store.db.execute('UPDATE entries SET paid=1-paid WHERE id=?',(key,)); self.store.db.commit(); self.refresh()
    def delete(self):
        key=self.selected(self.entries)
        if key and messagebox.askyesno('Excluir','Excluir este lançamento?'):
            self.store.db.execute('DELETE FROM entries WHERE id=?',(key,)); self.store.db.commit(); self.refresh()
    def budget_dialog(self):
        def save(v):
            dt.date.fromisoformat(v['period']+'-01'); amount=cents(v['amount'])
            if amount<0 or not v['category']: raise ValueError('Informe categoria e valor positivo.')
            self.store.db.execute('INSERT OR REPLACE INTO budgets VALUES(?,?,?)',(v['period'],v['category'],amount))
        self.form('Limite mensal',[('period','Mês (AAAA-MM)',self.period.get()[:7],None),('category','Categoria','Alimentação',[r['name'] for r in self.store.catalog('categories') if r['section']=='Categoria']),('amount','Limite (R$)','500,00',None)],save)
    def goal_dialog(self,edit=False):
        key=self.selected(self.goals) if edit else None
        r=dict(self.store.db.execute('SELECT * FROM goals WHERE id=?',(key,)).fetchone()) if key else {}
        def save(v):
            target,saved=cents(v['target']),cents(v['saved'])
            if not v['name'] or target<=0 or saved<0: raise ValueError('Informe nome, objetivo positivo e valor guardado não negativo.')
            if key: self.store.db.execute('UPDATE goals SET name=?,target=?,saved=?,location=? WHERE id=?',(v['name'],target,saved,v['location'],key))
            else: self.store.db.execute('INSERT INTO goals(name,target,saved,location) VALUES(?,?,?,?)',(v['name'],target,saved,v['location']))
        self.form('Meta financeira',[('name','Nome',r.get('name',''),None),('target','Objetivo (R$)',r.get('target',0)/100,None),('saved','Guardado (R$)',r.get('saved',0)/100,None),('location','Onde guardar',r.get('location',''),None)],save)
    def delete_goal(self):
        key=self.selected(self.goals)
        if key and messagebox.askyesno('Excluir meta','Excluir esta meta?'):
            self.store.db.execute('DELETE FROM goals WHERE id=?',(key,)); self.store.db.commit(); self.refresh()
    def task_dialog(self):
        def save(v):
            dt.date.fromisoformat(v['period']+'-01')
            if not v['name']: raise ValueError('Informe o objetivo.')
            self.store.db.execute('INSERT INTO tasks(period,name) VALUES(?,?)',(v['period'],v['name']))
        self.form('Objetivo do mês',[('period','Competência',dt.date.today().strftime('%Y-%m'),None),('name','Objetivo','',None)],save)
    def task_toggle(self):
        key=self.selected(self.tasks)
        if key:
            self.store.db.execute('UPDATE tasks SET done=1-done WHERE id=?',(key,)); self.store.db.commit(); self.refresh()
    def reserve_dialog(self):
        def calculate(v):
            total=cents(v['fixed'])+cents(v['essential'])
            if total<0: raise ValueError('Custos devem ser positivos.')
            messagebox.showinfo('Reserva sugerida',f'3 meses: {money(total*3)}\n6 meses: {money(total*6)}\n12 meses: {money(total*12)}')
        self.form('Calcular reserva ideal',[('fixed','Custo fixo mensal (R$)','0',None),('essential','Custo essencial mensal (R$)','0',None)],calculate)
    def import_file(self):
        path=filedialog.askopenfilename(filetypes=[('Planilha Excel','*.xlsx')])
        if not path: return
        if not messagebox.askyesno('Importar','Adicionar os registros desta planilha ao banco atual? Uma cópia idêntica não será importada duas vezes. Planilhas editadas podem repetir lançamentos.'): return
        try:
            self.store.backup(self.data_dir/'antes-da-importacao.db'); count,warnings=self.store.import_xlsx(Path(path)); self.refresh()
            messagebox.showinfo('Importação concluída',f'{count} movimentações importadas.\n\n'+'\n'.join(warnings))
        except Exception as e: messagebox.showerror('Importação',str(e))
    def export(self):
        path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')])
        if path:
            with open(path,'w',encoding='utf-8-sig',newline='') as f:
                writer=csv.writer(f,delimiter=';'); writer.writerow(['Data','Competência','Tipo','Categoria','Descrição','Valor','Pagamento','Pago','Observação'])
                for r in self.store.rows(self.period.get()):
                    values=[r['date'],r['period'],r['type_name'],r['category'],r['description'],f"{r['amount']/100:.2f}".replace('.',','),r['payment'],r['paid'],r['detail']]
                    writer.writerow(["'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v for v in values])
            messagebox.showinfo('Exportação','CSV salvo.')
    def backup(self):
        path=filedialog.asksaveasfilename(defaultextension='.db',initialfile='financas-backup.db')
        if path:
            self.store.backup(path); messagebox.showinfo('Backup','Backup salvo. Guarde uma cópia fora deste computador.')

def smoke_test():
    """Exercita também o aplicativo empacotado sem tocar nos dados do usuário."""
    with tempfile.TemporaryDirectory() as directory:
        app=App(directory,welcome=False)
        errors=[]
        app.report_callback_exception=lambda *error: errors.append(error)
        try:
            app.update()
            for mode in ('Escuro','Claro'):
                app.mode.set(mode); app.apply_theme(); app.update()
            if errors: raise RuntimeError('Falha em um callback da interface.')
        finally: app.close()

if __name__=='__main__':
    if '--smoke-test' in sys.argv: smoke_test()
    else: App().mainloop()
