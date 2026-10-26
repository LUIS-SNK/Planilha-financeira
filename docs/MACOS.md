# Aplicativo para macOS

O workflow **Aplicativo macOS** compila e testa dois pacotes nativos: Apple Silicon (`arm64`, M1 ou posterior) e Intel (`x86_64`), em macOS 15. Cada pacote inclui Python, Tk e as dependências: o usuário não precisa instalar Python nem usar o terminal.

Os testes do código e da interface rodam antes do empacotamento. O próprio executável dentro do `.app` é iniciado com `--smoke-test`, usando um banco temporário e os dois temas. Isso não equivale a um teste manual em todas as versões de macOS; a compatibilidade validada pelo CI é macOS 15 na arquitetura correspondente.

## Abertura sem contornar o Gatekeeper

Para distribuir fora da App Store sem exigir uma exceção nas configurações de segurança, o `.app` precisa de assinatura **Developer ID Application**, hardened runtime e notarização aceita pela Apple. O ticket é anexado ao aplicativo (stapling) e validado antes da publicação.

Isso exige inscrição paga no [Apple Developer Program](https://developer.apple.com/programs/) e um certificado Developer ID Application com sua chave privada. Uma conta gratuita ou a assinatura ad hoc usada em testes não substituem esses requisitos. A confirmação normal de primeira abertura de um arquivo baixado da internet ainda pode aparecer; não é possível prometer ausência de todo aviso do sistema.

Sem os requisitos Apple, o workflow compila e testa internamente, registra a distribuição bloqueada no resumo e **não publica um pacote sem notarização**. Uma execução verde nessa situação significa apenas que a compilação e os testes passaram. Não há comandos para remover quarentena ou desligar o Gatekeeper neste projeto.

## Configuração segura no GitHub

Depois de obter a conta e o certificado, configure estes **Repository secrets** em **Settings → Secrets and variables → Actions**:

| Nome | Conteúdo |
| --- | --- |
| `MACOS_CERTIFICATE_P12_BASE64` | Certificado Developer ID Application exportado com a chave privada em `.p12`, codificado em Base64. Base64 não é criptografia: use somente o campo de secret. |
| `MACOS_CERTIFICATE_PASSWORD` | Senha de exportação do `.p12`. |
| `MACOS_SIGNING_IDENTITY` | Nome exato da identidade, começando por `Developer ID Application:`. |
| `APPLE_ID` | Apple ID associado à equipe de desenvolvimento. |
| `APPLE_TEAM_ID` | Identificador da equipe Apple Developer. |
| `APPLE_APP_PASSWORD` | Senha específica de aplicativo criada para a notarização. |

Não envie esses valores em chat, issues ou arquivos do repositório. O certificado é importado em um keychain temporário do runner, removido ao final. A configuração parcial falha explicitamente para evitar uma distribuição incompleta.

Execute novamente o workflow por **Actions → Aplicativo macOS → Run workflow**. Só após a Apple aceitar a notarização e `codesign`, `stapler` e `spctl` validarem o aplicativo, os artefatos `MinhasFinancas-macOS-arm64-notarizado` e `MinhasFinancas-macOS-x86_64-notarizado` serão disponibilizados.

O caminho de assinatura/notarização só pode ser validado com as credenciais reais. A configuração do pipeline não significa que um pacote já foi assinado ou aceito pela Apple.

## Instalar e preservar os dados

Baixe o artefato da arquitetura correta e extraia o ZIP interno, que preserva a estrutura do `.app`. Arraste `MinhasFinancas.app` para Aplicativos e abra com dois cliques. Python e Excel não são necessários. Dados pessoais não são incluídos no aplicativo.

No Mac, o banco e os backups ficam em `~/Library/Application Support/FinancasGeovana/`. Para continuar o histórico de outro computador, faça Backup no aplicativo antigo, feche o aplicativo no Mac, preserve qualquer banco atual e copie o backup para esse diretório com o nome `financas.db`. Na primeira abertura sem banco, também é possível importar a planilha pelo botão Importar Excel.

Referência: [Notarizing macOS software before distribution](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
