# 📁 Exemplo de Estrutura de Pastas Organizadas por Cotação

## Estrutura Completa

```
webcrawler/
├── main_refactored.py
├── requirements.txt
├── README.md
├── README_DOWNLOADS.md
├── downloads_anexos/
│   ├── cotacao_12345/
│   │   ├── cotacao_12345_especificacao_tecnica_item01.pdf
│   │   ├── cotacao_12345_desenho_tecnico_item02.dwg
│   │   ├── cotacao_12345_catalogo_fornecedor_item03.pdf
│   │   ├── cotacao_12345_manual_operacao_item04.pdf
│   │   └── resumo_downloads_cotacao_12345.txt
│   ├── cotacao_67890/
│   │   ├── cotacao_67890_ficha_tecnica_item01.xlsx
│   │   ├── cotacao_67890_certificado_qualidade_item02.pdf
│   │   ├── cotacao_67890_foto_produto_item03.jpg
│   │   └── resumo_downloads_cotacao_67890.txt
│   ├── cotacao_11111/
│   │   ├── cotacao_11111_planilha_precos_item01.xlsx
│   │   ├── cotacao_11111_contrato_modelo_item02.docx
│   │   └── resumo_downloads_cotacao_11111.txt
│   └── cotacao_geral/
│       └── (arquivos sem cotação específica)
└── dados_cotacoes_20241225_143015.csv
```

## Exemplo de Conteúdo do CSV

```csv
evento,nome_evento,data_inicial,data_final,numero_item,descricao,descricao_estendida,quantidade,data_necessaria,detalhes,arquivos_anexados
12345,Fornecimento de Equipamentos,25/12/2024,30/12/2024,1/3,Bomba Centrífuga,Especificação técnica conforme anexo,2,15/01/2025,Pressão: 10 bar,downloads_anexos\cotacao_12345\cotacao_12345_especificacao_tecnica_item01.pdf
12345,Fornecimento de Equipamentos,25/12/2024,30/12/2024,2/3,Válvula de Controle,Desenho técnico em DWG,5,15/01/2025,Diâmetro: 2",downloads_anexos\cotacao_12345\cotacao_12345_desenho_tecnico_item02.dwg
12345,Fornecimento de Equipamentos,25/12/2024,30/12/2024,3/3,Motor Elétrico,Catálogo do fornecedor,2,15/01/2025,Potência: 15 HP,downloads_anexos\cotacao_12345\cotacao_12345_catalogo_fornecedor_item03.pdf
67890,Serviços de Manutenção,26/12/2024,31/12/2024,1/2,Manutenção Preventiva,Ficha técnica de serviços,1,20/01/2025,Equipamentos: 10 unidades,downloads_anexos\cotacao_67890\cotacao_67890_ficha_tecnica_item01.xlsx
67890,Serviços de Manutenção,26/12/2024,31/12/2024,2/2,Inspeção Técnica,Certificado de qualidade,1,20/01/2025,Padrão: ISO 9001,downloads_anexos\cotacao_67890\cotacao_67890_certificado_qualidade_item02.pdf
```

## Exemplo de Arquivo de Resumo

### `resumo_downloads_cotacao_12345.txt`

```
RESUMO DE DOWNLOADS - COTAÇÃO 12345
==================================================

Data/Hora: 25/12/2024 14:30:15
Pasta: downloads_anexos/cotacao_12345

Arquivos baixados (4):
------------------------------
• cotacao_12345_especificacao_tecnica_item01.pdf (1,245,678 bytes)
• cotacao_12345_desenho_tecnico_item02.dwg (2,345,678 bytes)
• cotacao_12345_catalogo_fornecedor_item03.pdf (3,456,789 bytes)
• cotacao_12345_manual_operacao_item04.pdf (987,654 bytes)

Informações da cotação:
• Evento: 12345
• Nome do evento: Fornecimento de Equipamentos
• Data inicial: 25/12/2024
• Data final: 30/12/2024
```

## Vantagens da Nova Organização

### ✅ **Organização Clara**
- Cada cotação tem sua própria pasta
- Fácil identificação por número da cotação
- Separação lógica dos documentos

### ✅ **Nomes Descritivos**
- Mantém o nome original do arquivo
- Adiciona contexto da cotação
- Identifica o item específico

### ✅ **Rastreabilidade**
- Arquivo de resumo por cotação
- Logs detalhados de cada download
- Estatísticas completas

### ✅ **Facilidade de Uso**
- Acesso direto aos arquivos por cotação
- Nomes intuitivos e organizados
- Compatibilidade total com sistemas de arquivo

### ✅ **Backup e Controle**
- Todos os anexos salvos localmente
- Estrutura replicável
- Fácil backup por cotação

## Como Usar

1. **Execute o extrator** normalmente
2. **Os arquivos serão organizados** automaticamente por cotação
3. **Acesse as pastas** `downloads_anexos/cotacao_XXXXX/`
4. **Consulte o resumo** `resumo_downloads_cotacao_XXXXX.txt`
5. **Use os caminhos** no CSV para referência direta

## Compatibilidade

- ✅ **Windows**: Caminhos com `\`
- ✅ **Linux/macOS**: Caminhos com `/`
- ✅ **Excel**: Colunas auto-ajustadas
- ✅ **Sistemas de arquivo**: Nomes seguros
- ✅ **Backup**: Estrutura preservada 