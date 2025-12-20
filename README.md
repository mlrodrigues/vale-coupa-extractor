# 🔍 Vale Coupa Extrator de Cotações

## O que é este aplicativo?

O **Vale Coupa Extrator de Cotações** é um programa que automatiza a extração de dados de cotações da plataforma Vale Coupa. Em vez de você ter que copiar e colar cada item manualmente, o programa faz isso automaticamente e salva tudo em uma planilha Excel (`.xlsx`).

## 📋 O que você vai precisar

- **Computador com Windows** (Windows 10 ou superior)
- **Conexão com internet** (para acessar a plataforma Vale Coupa)
- **Suas credenciais de login** da plataforma Vale Coupa (usuário e senha)
- **Data das cotações** que você quer extrair

## 🚀 Como usar o aplicativo

### 1. Executar o programa
- Localize o arquivo `ValeCoupaCrawler_Portable.exe` (ou nome similar)
- **Dê um duplo-clique** no arquivo para abrir o programa
- Aguarde alguns segundos para o programa carregar

### 2. Preencher os dados de login
Na tela que abrir, você verá campos para:

**🔐 Credenciais de Acesso**
- **Usuário**: Digite seu nome de usuário da plataforma Vale Coupa
- **Senha**: Digite sua senha (ficará oculta por segurança)
- **Lembrar credenciais**: 
  - ✅ Marque esta opção se deseja que o programa salve suas credenciais
  - Na próxima vez que abrir o programa, seus dados já estarão preenchidos automaticamente
  - As credenciais são armazenadas de forma criptografada e segura
  - Se deseja remover as credenciais salvas, clique no botão "🗑️ Limpar credenciais salvas"

### 3. Escolher a data
**📅 Data para Extração**
- Digite a data das cotações que você quer extrair
- **Formato**: DD/MM/AA (exemplo: 25/12/24 para 25 de dezembro de 2024)
- O programa já vem com a data de hoje preenchida

### 4. Iniciar a extração
- Clique no botão azul **"🔥 EXTRAIR COTAÇÕES"**
- O programa começará a trabalhar automaticamente

### 5. Acompanhar o progresso
Na parte inferior da tela, você verá mensagens mostrando o que está acontecendo:
- 🌐 "Iniciando browser..." - O programa está abrindo o navegador
- 🔐 "Fazendo login..." - Está fazendo login na plataforma
- 📋 "Buscando cotações..." - Está procurando cotações para a data escolhida
- 📄 "Processando cotação..." - Está extraindo dados de cada cotação
- 💾 "Salvando dados..." - Está salvando os dados no arquivo
- ✅ "X itens salvos!" - Terminou com sucesso!

## 📊 Resultado final

Quando o programa terminar, você encontrará um arquivo Excel (`.xlsx`) na **mesma pasta do programa** com nome parecido com:
`dados_cotacoes_FERROSOS_kennedy.correa_20251216_195341.xlsx`

Este arquivo pode ser aberto no **Excel** ou **Google Sheets** e contém todas as informações extraídas:
- Evento (número da cotação)
- Nome do evento
- Data inicial e final
- Número do item
- Descrição detalhada
- Quantidade
- Data necessária
- Detalhes adicionais
- Arquivos anexados

## ⚠️ Problemas comuns e soluções

### "❌ Falha no login"
**Problema**: Suas credenciais estão incorretas
**Solução**: Verifique se você digitou o usuário e senha corretamente

### "❌ Nenhuma cotação encontrada"
**Problema**: Não há cotações para a data escolhida
**Solução**: 
- Verifique se a data está correta (formato DD/MM/AA)
- Tente uma data diferente
- Confirme se existem cotações para aquela data na plataforma

### "❌ Erro inesperado"
**Problema**: Algum erro técnico ocorreu
**Solução**:
- Feche o programa e tente novamente
- Verifique sua conexão com internet
- Certifique-se de que a plataforma Vale Coupa está funcionando

### Programa não abre
**Problema**: O Windows está bloqueando o arquivo
**Solução**:
- Clique com botão direito no arquivo .exe
- Escolha "Propriedades"
- Na aba "Geral", marque "Desbloquear" (se aparecer)
- Clique "OK" e tente novamente

### Dúvidas sobre credenciais salvas

**P: As minhas credenciais são seguras?**
R: Sim! As credenciais são armazenadas usando criptografia e o Windows Credential Manager. São tão seguras quanto as senhas salvas no seu navegador.

**P: Como removo as credenciais salvas?**
R: Clique no botão "🗑️ Limpar credenciais salvas" na tela de login. Você pode confirmar a exclusão.

**P: E se eu estou usando um computador compartilhado?**
R: ⚠️ **Não recomendamos salvar credenciais em computadores compartilhados**. Clique em "Limpar credenciais salvas" depois de usar.

**P: Posso desativar a opção de salvar credenciais?**
R: Sim! Basta **desmarcar** a opção "Lembrar credenciais nesta máquina" e suas credenciais não serão salvas naquele login.

## 🛡️ Segurança

- ✅ O programa agora pode **salvar suas credenciais de forma segura** (opcional)
- 🔒 As senhas são criptografadas usando o Windows Credential Manager ou encriptação local
- 🔑 Você pode optar por não salvar as credenciais (marcando/desmarcando a opção)
- 🗑️ Existe botão para **limpar credenciais salvas** a qualquer momento
- 📱 O programa se conecta diretamente com a plataforma Vale Coupa (mesma que você usa no navegador)
- 🚫 As credenciais são armazenadas de forma segura no seu computador (Windows Credential Manager)

## ⏱️ Tempo de execução

- **Login**: 10-30 segundos
- **Por cotação**: 30-60 segundos cada
- **Total**: Depende de quantas cotações existem para a data escolhida

## 💡 Dicas importantes

1. **Não feche o programa** enquanto ele estiver trabalhando
2. **Aguarde** até ver a mensagem de sucesso
3. **Mantenha internet estável** durante todo o processo
4. **Não mexa no navegador** que o programa abre (ele pode ficar invisível)

## 📝 Exemplo de uso completo

1. Duplo-clique no `ValeCoupaCrawler_Portable.exe`
2. Digite seu usuário: `joao.silva@empresa.com`
3. Digite sua senha: `MinhaSenh@123`
4. Digite a data: `15/01/25`
5. Clique em "🔥 EXTRAIR COTAÇÕES"
6. Aguarde as mensagens de progresso
7. Quando aparecer "✅ Extração concluída!", procure o arquivo Excel (`.xlsx`) na pasta
8. Abra o arquivo no Excel para ver os dados

## 🆘 Suporte

Se você encontrar problemas não listados acima:
1. Anote a mensagem de erro que apareceu
2. Verifique o arquivo `crawler.log` na pasta do programa (contém detalhes técnicos)
3. Entre em contato com o suporte técnico

---

**Versão**: 2.0 Refatorada  
**Compatibilidade**: Windows 10/11  
**Última atualização**: Junho 2025