===============================================================================
                        VALE COUPA EXTRATOR DE COTAÇÕES
===============================================================================

O QUE É ESTE APLICATIVO?
========================

O Vale Coupa Extrator de Cotações é um programa que automatiza a extração 
de dados de cotações da plataforma Vale Coupa. Em vez de você ter que copiar 
e colar cada item manualmente, o programa faz isso automaticamente e salva 
tudo em uma planilha Excel (arquivo CSV).

O QUE VOCÊ VAI PRECISAR
======================

- Computador com Windows (Windows 10 ou superior)
- Conexão com internet (para acessar a plataforma Vale Coupa)
- Suas credenciais de login da plataforma Vale Coupa (usuário e senha)
- Data das cotações que você quer extrair

COMO USAR O APLICATIVO
=====================

1. EXECUTAR O PROGRAMA
---------------------
- Localize o arquivo "ValeCoupaCrawler_Headless.exe" (ou nome similar)
- Dê um duplo-clique no arquivo para abrir o programa
- Aguarde alguns segundos para o programa carregar

2. PREENCHER OS DADOS DE LOGIN
-----------------------------
Na tela que abrir, você verá campos para:

CREDENCIAIS DE ACESSO:
- Usuário: Digite seu nome de usuário da plataforma Vale Coupa
- Senha: Digite sua senha (ficará oculta por segurança)

3. ESCOLHER A DATA
-----------------
DATA PARA EXTRAÇÃO:
- Digite a data das cotações que você quer extrair
- FORMATO: DD/MM/AA (exemplo: 25/12/24 para 25 de dezembro de 2024)
- O programa já vem com a data de hoje preenchida

4. INICIAR A EXTRAÇÃO
--------------------
- Clique no botão azul "EXTRAIR COTAÇÕES"
- O programa começará a trabalhar automaticamente

5. ACOMPANHAR O PROGRESSO
------------------------
Na parte inferior da tela, você verá mensagens mostrando o que está acontecendo:
- "Iniciando browser..." - O programa está abrindo o navegador
- "Fazendo login..." - Está fazendo login na plataforma
- "Buscando cotações..." - Está procurando cotações para a data escolhida
- "Processando cotação..." - Está extraindo dados de cada cotação
- "Salvando dados..." - Está salvando os dados no arquivo
- "X itens salvos!" - Terminou com sucesso!

RESULTADO FINAL
==============

Quando o programa terminar, você encontrará um arquivo CSV na MESMA PASTA 
DO PROGRAMA com nome parecido com:
dados_cotacoes_20241225_143022.csv

Este arquivo pode ser aberto no EXCEL ou GOOGLE SHEETS e contém todas as 
informações extraídas:
- Evento (número da cotação)
- Nome do evento
- Data inicial e final
- Número do item
- Descrição detalhada
- Quantidade
- Data necessária
- Detalhes adicionais
- Arquivos anexados

PROBLEMAS COMUNS E SOLUÇÕES
==========================

"FALHA NO LOGIN"
---------------
PROBLEMA: Suas credenciais estão incorretas
SOLUÇÃO: Verifique se você digitou o usuário e senha corretamente

"NENHUMA COTAÇÃO ENCONTRADA"
---------------------------
PROBLEMA: Não há cotações para a data escolhida
SOLUÇÃO: 
- Verifique se a data está correta (formato DD/MM/AA)
- Tente uma data diferente
- Confirme se existem cotações para aquela data na plataforma

"ERRO INESPERADO"
----------------
PROBLEMA: Algum erro técnico ocorreu
SOLUÇÃO:
- Feche o programa e tente novamente
- Verifique sua conexão com internet
- Certifique-se de que a plataforma Vale Coupa está funcionando

PROGRAMA NÃO ABRE
----------------
PROBLEMA: O Windows está bloqueando o arquivo
SOLUÇÃO:
- Clique com botão direito no arquivo .exe
- Escolha "Propriedades"
- Na aba "Geral", marque "Desbloquear" (se aparecer)
- Clique "OK" e tente novamente

SEGURANÇA
=========

- O programa NÃO SALVA suas credenciais
- Todas as senhas são mantidas apenas na memória durante o uso
- O programa se conecta diretamente com a plataforma Vale Coupa 
  (mesma que você usa no navegador)

TEMPO DE EXECUÇÃO
================

- Login: 10-30 segundos
- Por cotação: 30-60 segundos cada
- Total: Depende de quantas cotações existem para a data escolhida

DICAS IMPORTANTES
================

1. NÃO FECHE O PROGRAMA enquanto ele estiver trabalhando
2. AGUARDE até ver a mensagem de sucesso
3. MANTENHA INTERNET ESTÁVEL durante todo o processo
4. NÃO MEXA NO NAVEGADOR que o programa abre (ele pode ficar invisível)

EXEMPLO DE USO COMPLETO
======================

1. Duplo-clique no "ValeCoupaCrawler_Headless.exe"
2. Digite seu usuário: joao.silva@empresa.com
3. Digite sua senha: MinhaSenh@123
4. Digite a data: 15/01/25
5. Clique em "EXTRAIR COTAÇÕES"
6. Aguarde as mensagens de progresso
7. Quando aparecer "Extração concluída!", procure o arquivo CSV na pasta
8. Abra o arquivo no Excel para ver os dados

SUPORTE
=======

Se você encontrar problemas não listados acima:
1. Anote a mensagem de erro que apareceu
2. Verifique o arquivo "crawler.log" na pasta do programa 
   (contém detalhes técnicos)
3. Entre em contato com o suporte técnico

===============================================================================

Versão: 2.0 Refatorada
Compatibilidade: Windows 10/11
Última atualização: Junho 2025

=============================================================================== 