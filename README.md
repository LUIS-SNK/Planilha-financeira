# Minhas Finanças

Aplicativo local para Windows: receitas, despesas, contas pagas e pendentes, repetições e parcelas, orçamento por categoria, gráficos, investimentos, reserva, metas, objetivos mensais, calculadora de reserva e resumo anual. Valores armazenados em centavos, em SQLite. Sem login, servidor ou conexão bancária.

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

Importa as abas Jan–Dez, investimentos e metas nomeadas. Ignora a aba Exemplo, fórmulas e elementos visuais. Calcula os relatórios a partir dos lançamentos. Preserva competência da aba, data, categoria, descrição, pagamento, situação e detalhes da coluna N (que varia entre parcela e data de pagamento). Categorias são preservadas como digitadas. Objetivos mensais são importados com suas marcações. Compras variáveis sem coluna de situação são consideradas pagas, exceto compras em cartões reconhecidos, cuja situação vem do quadro de faturas. O ano deste importador é 2026.

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

## Cadastros, calendário e aparência

- A aba **Cadastros** permite adicionar, editar e excluir tipos, categorias e investimentos.
- Cada tipo personalizado tem comportamento de Receita, Despesa, Aporte, Retirada ou Saldo inicial. Exemplo: Salário → Receita. Os relatórios usam o comportamento e os lançamentos exibem o nome cadastrado.
- Tipos padrão são preservados. Tipos já utilizados podem ser renomeados, mas seu comportamento não pode mudar; crie outro tipo para outro comportamento. Cadastros utilizados não podem ser excluídos. Renomear uma categoria atualiza seus lançamentos e orçamentos.
- Categorias de grupo Investimento aparecem na lista de investimentos mesmo antes de receber aportes.
- O botão **Calendário** escolhe datas ou competência mensal. Em novos lançamentos, mudar a data atualiza a competência; ela ainda pode ser ajustada manualmente.
- **Aparência: Claro / Escuro**, no topo, troca o tema e salva a preferência no banco local.
- A visão geral mostra quatro gráficos: despesas por categoria (até cinco maiores), entradas e despesas mensais do ano, despesas pagas e pendentes do período e saldo acumulado dos investimentos. O gráfico de investimentos inclui saldos anteriores ao ano selecionado. O gráfico anual acompanha o ano do período selecionado.

## Atualizar sem perder os dados

Faça um backup pelo aplicativo, feche a versão anterior e abra o novo executável. O banco continua no mesmo diretório e recebe as novas tabelas automaticamente. Não é necessário importar a planilha novamente. Mantenha a cópia de segurança para voltar à versão anterior.

## Validação desta versão

Dez testes automatizados cobrem cadastros, tipos personalizados nos cálculos, renomeação, migração de banco anterior, persistência de tema, calendário (incluindo ano bissexto), abertura dos formulários e renderização de gráficos nos dois temas, além de arredondamento monetário, backup, importação com fórmulas e bloqueio de duplicatas, além de rejeição de valores inválidos. A planilha fornecida foi exercitada localmente, sem incluí-la no Git: 313 movimentações, com receitas e reserva conciliadas. A interface foi exercitada em uma sessão gráfica Linux com dados sintéticos. O workflow Windows também executa os testes gráficos antes de gerar o executável; o uso manual do executável continua dependendo de validação em Windows.
