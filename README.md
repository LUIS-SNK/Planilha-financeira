# Minhas Finanças

Aplicativo local para Windows: receitas, despesas, contas pagas e pendentes, repetições e parcelas, orçamento por categoria, gráficos, investimentos, reserva e metas. Valores armazenados em centavos, em SQLite. Sem login, servidor ou conexão bancária.

## Baixar para Windows

No GitHub, abra **Actions → Aplicativo Windows → execução mais recente concluída → Artifacts → MinhasFinancas-Windows**. Extraia o ZIP e abra `MinhasFinancas.exe`. O download de artefatos pode exigir login no GitHub. O executável ainda não tem assinatura digital.

No primeiro uso, clique em **Importar Excel** e selecione sua planilha original. Dados financeiros não são distribuídos com o aplicativo nem publicados neste repositório.

## Uso

- Use Novo lançamento para receitas, despesas, aportes, retiradas e saldo inicial de investimentos. Informe valor por parcela e quantidade de meses para gerar parcelas; para contas recorrentes, informe a quantidade de meses desejada.
- Período aceita `2026-07` ou `2026`. O resumo usa a competência e inclui despesas pagas e pendentes: o saldo exibido é previsto, não um extrato bancário conciliado.
- Clique duas vezes em um lançamento para editar; alterar uma parcela não altera as demais.
- Investimentos mostra os saldos de todo o histórico. Metas são controles manuais independentes dos investimentos; clique duas vezes para atualizar.
- Limites são definidos por categoria e mês. Salvar novamente substitui o limite.
- Exporte o período em CSV ou use Backup para copiar o banco.

O banco fica em `%LOCALAPPDATA%\FinancasGeovana\financas.db`, com backups diários em `backups`. Para restaurar, feche o programa, preserve o banco atual e substitua-o pela cópia `.db`. Backups contêm dados pessoais e não são criptografados.

## Importação do modelo 2026

Importa as abas Jan–Dez, investimentos e metas nomeadas. Ignora a aba Exemplo, fórmulas e elementos visuais. Calcula os relatórios a partir dos lançamentos. Preserva competência da aba, data, categoria, descrição, pagamento, situação e detalhes da coluna N (que varia entre parcela e data de pagamento). Categorias são preservadas como digitadas. O ano deste importador é 2026.

Saldos iniciais, depósitos e retiradas de investimentos são importados separadamente. Metas com nomes de exemplo não são importadas. A mesma planilha é bloqueada por SHA-256; uma versão modificada é considerada outra importação e pode duplicar registros. Faça backup e confira totais após importar. Não use o resumo em cache do Excel como fonte definitiva: ele pode estar desatualizado.

## Desenvolvimento

Python 3.12+ com Tkinter. Sem dependências externas em execução:

```sh
python app.py
python -m unittest discover -s tests -v
```

Linux precisa de uma sessão gráfica e Tk. Para empacotar, em Windows:

```sh
python -m pip install pyinstaller==6.16.0
python -m PyInstaller --onefile --windowed --name MinhasFinancas app.py
```

A compilação Windows é feita pelo GitHub Actions. Ainda requer teste de execução em Windows. Não há pacote macOS nesta versão.
