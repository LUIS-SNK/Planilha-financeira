"""Calendário e gráficos sem dependências externas."""
import calendar
import datetime as dt
import os
import tkinter as tk
from tkinter import ttk
from core import MONTHS, money

PALETTES={
    'Claro':dict(bg='#f2f5fa',panel='#ffffff',text='#17283e',muted='#52637a',line='#dce3ee',accent='#536dce',green='#14856e',red='#ce5368',field='#ffffff',select='#dbe4ff'),
    'Escuro':dict(bg='#151d2c',panel='#202b3d',text='#edf2ff',muted='#b4c0d5',line='#35455e',accent='#9baaff',green='#61cfb4',red='#ff93a4',field='#29364b',select='#3e5279')}
FONT_FAMILY='Segoe UI' if os.name=='nt' else 'Helvetica'
MONTH_NAMES=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

class CalendarPicker(tk.Toplevel):
    def __init__(self,parent,variable,month_only=False):
        super().__init__(parent)
        self.title('Selecionar mês' if month_only else 'Selecionar data')
        self.transient(parent); self.resizable(False,False)
        self.variable=variable; self.month_only=month_only
        try: self.selected=dt.date.fromisoformat(variable.get()+('-01' if month_only else ''))
        except ValueError: self.selected=dt.date.today()
        self.year,self.month=self.selected.year,self.selected.month
        self.previous_grab=self.grab_current()
        self.grab_set(); self.protocol('WM_DELETE_WINDOW',self.close)
        self.bind('<Escape>',lambda e:self.close())
        self.body=ttk.Frame(self,padding=12); self.body.pack()
        self.draw()
    def close(self):
        previous=self.previous_grab; self.destroy()
        if previous is not None and previous.winfo_exists(): previous.grab_set()
    def move(self,delta):
        y,m=divmod(self.year*12+self.month-1+delta,12)
        if 1<=y<=9999: self.year,self.month=y,m+1; self.draw()
    def choose(self,day=1):
        date=dt.date(self.year,self.month,day)
        self.variable.set(date.strftime('%Y-%m') if self.month_only else date.isoformat())
        self.close()
    def draw(self):
        for w in self.body.winfo_children(): w.destroy()
        ttk.Button(self.body,text='‹',width=3,command=lambda:self.move(-1)).grid(row=0,column=0)
        ttk.Label(self.body,text=f'{MONTH_NAMES[self.month-1]} {self.year}',anchor='center').grid(row=0,column=1,columnspan=5,sticky='ew')
        ttk.Button(self.body,text='›',width=3,command=lambda:self.move(1)).grid(row=0,column=6)
        if self.month_only:
            for m,name in enumerate(MONTHS,1):
                def pick(month=m): self.month=month; self.choose()
                ttk.Button(self.body,text=name,width=8,command=pick).grid(row=1+(m-1)//3,column=((m-1)%3)*2,columnspan=2,padx=3,pady=5)
            return
        for col,label in enumerate(['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']): ttk.Label(self.body,text=label,anchor='center').grid(row=1,column=col,pady=8)
        for row,week in enumerate(calendar.monthcalendar(self.year,self.month),2):
            for col,day in enumerate(week):
                if day:
                    style='Selected.TButton' if (self.year,self.month,day)==(self.selected.year,self.selected.month,self.selected.day) else 'TButton'
                    ttk.Button(self.body,text=str(day),width=3,style=style,command=lambda d=day:self.choose(d)).grid(row=row,column=col,padx=2,pady=2)
        ttk.Button(self.body,text='Hoje',command=self.today).grid(row=9,column=0,columnspan=7,sticky='ew',pady=(8,0))
    def today(self):
        date=dt.date.today(); self.year,self.month=date.year,date.month; self.choose(date.day)

class Dashboard(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        self.palette=PALETTES['Claro']; self.rows=[]; self.year_rows=[]; self.history=[]; self.year='2026'
        self.canvases=[]
        for i in range(4):
            c=tk.Canvas(self,height=175,highlightthickness=0)
            c.grid(row=i//2,column=i%2,sticky='nsew',padx=5,pady=5); c.bind('<Configure>',lambda e:self.draw()); self.canvases.append(c)
        for i in range(2): self.columnconfigure(i,weight=1); self.rowconfigure(i,weight=1)
    def set_data(self,rows,year_rows,history,year):
        self.rows,self.year_rows,self.history,self.year=rows,year_rows,history,year; self.draw()
    def theme(self,palette): self.palette=palette; self.draw()
    def label(self,c,x,y,text,**kw): c.create_text(x,y,text=text,fill=self.palette['text'],font=(FONT_FAMILY,9),**kw)
    def prepare(self,index,title):
        c=self.canvases[index]; c.configure(bg=self.palette['panel']); c.delete('all')
        w,h=max(c.winfo_width(),300),max(c.winfo_height(),165)
        self.label(c,12,17,title,anchor='w'); return c,w,h
    def draw(self):
        p=self.palette
        c,w,h=self.prepare(0,'Maiores despesas por categoria | período selecionado')
        cats={}
        for r in self.rows:
            if r['kind']=='Despesa': cats[r['category']]=cats.get(r['category'],0)+r['amount']
        ranked=sorted(cats.items(),key=lambda x:x[1],reverse=True)[:5]; maximum=max(cats.values(),default=1)
        if not ranked: self.label(c,16,70,'Sem despesas neste período.',anchor='w')
        for i,(name,value) in enumerate(ranked):
            y=49+i*max(23,(h-65)/5)
            self.label(c,12,y,name[:22],anchor='w'); start=min(155,w*.35); end=w-108
            c.create_rectangle(start,y-6,start+max(1,(end-start)*value/maximum),y+6,fill=p['accent'],outline='')
            self.label(c,w-10,y,money(value),anchor='e')
        c,w,h=self.prepare(1,f'Entradas e despesas | {self.year}')
        incoming=[sum(r['amount'] for r in self.year_rows if r['period'].endswith(f'-{m:02d}') and r['kind']=='Receita') for m in range(1,13)]
        outgoing=[sum(r['amount'] for r in self.year_rows if r['period'].endswith(f'-{m:02d}') and r['kind']=='Despesa') for m in range(1,13)]
        self.lines(c,w,h,[(incoming,p['green'],'Entradas'),(outgoing,p['red'],'Despesas')])
        c,w,h=self.prepare(2,'Despesas pagas e pendentes | período selecionado')
        paid=sum(r['amount'] for r in self.rows if r['kind']=='Despesa' and r['paid'])
        pending=sum(r['amount'] for r in self.rows if r['kind']=='Despesa' and not r['paid'])
        size=min(h-55,w*.38,145); x=20; y=42
        if paid+pending:
            extent=360*paid/(paid+pending)
            for start,angle,color in [(90,extent,p['green']),(90+extent,360-extent,p['red'])]:
                if angle>0: c.create_arc(x,y,x+size,y+size,start=start,extent=angle,fill=color,outline=p['panel'])
            c.create_oval(x+size*.25,y+size*.25,x+size*.75,y+size*.75,fill=p['panel'],outline=p['panel'])
        else: c.create_oval(x,y,x+size,y+size,outline=p['line'],width=12)
        self.label(c,x+size+18,65,f'Pagas: {money(paid)}',anchor='w')
        self.label(c,x+size+18,98,f'Pendentes: {money(pending)}',anchor='w')
        c,w,h=self.prepare(3,f'Evolução dos investimentos | saldo acumulado em {self.year}')
        balances=[]
        for m in range(1,13):
            period=f'{self.year}-{m:02d}'
            balances.append(sum(r['amount']*(-1 if r['kind']=='Retirada' else 1) for r in self.history if r['period']<=period and r['kind'] in ('Aporte','Retirada','Saldo inicial')))
        self.lines(c,w,h,[(balances,p['accent'],'Saldo investido')])
    def lines(self,c,w,h,series):
        p=self.palette; left,right,top,bottom=88,w-16,57,h-28
        values=[v for data,_,_ in series for v in data]; low=min([0]+values); high=max([1]+values)
        for i in range(3):
            y=top+(bottom-top)*i/2
            c.create_line(left,y,right,y,fill=p['line'])
            self.label(c,left-5,y,money(round(high-(high-low)*i/2)),anchor='e')
        for i,label in enumerate(MONTHS): self.label(c,left+(right-left)*i/11,bottom+14,label,anchor='center')
        for index,(data,color,label) in enumerate(series):
            c.create_rectangle(left+index*125,34,left+10+index*125,41,fill=color,outline='')
            self.label(c,left+15+index*125,38,label,anchor='w')
            coords=[]
            for i,value in enumerate(data): coords.extend([left+(right-left)*i/11,bottom-(value-low)/(high-low)*(bottom-top)])
            c.create_line(*coords,fill=color,width=2)
            for x,y in zip(coords[::2],coords[1::2]): c.create_oval(x-2,y-2,x+2,y+2,fill=color,outline='')
