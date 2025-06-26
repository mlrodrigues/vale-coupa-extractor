# 📎 Sistema de Download de Anexos

## Funcionalidades Implementadas

### ✅ **Download Automático de Arquivos**
- O sistema agora baixa automaticamente todos os arquivos anexados encontrados nas cotações
- Os arquivos são salvos na pasta `downloads_anexos/` 
- No CSV, a coluna "arquivos_anexados" conterá o **caminho local** dos arquivos baixados

### 🔍 **Detecção Inteligente de Anexos**
O sistema procura por links que contenham:
- `attachment` na URL
- `download` na URL  
- `file` na URL

### 💾 **Organização dos Downloads**
- **Pasta**: `downloads_anexos/` (criada automaticamente)
- **Nomes únicos**: Se um arquivo já existe, adiciona `_1`, `_2`, etc.
- **Nomes seguros**: Remove caracteres perigosos dos nomes de arquivo
- **Extensões automáticas**: Detecta tipo de arquivo pelo Content-Type

### 🏷️ **Tipos de Arquivo Suportados**
- PDF (`.pdf`)
- Word (`.doc`, `.docx`)
- Excel (`.xls`, `.xlsx`)
- Imagens (`.jpg`, `.png`, `.gif`)
- Texto (`.txt`)
- Compactados (`.zip`, `.rar`)
- E outros...

### 🔄 **Status em Tempo Real**
A interface mostra o progresso dos downloads:
- `📎 Encontrados X anexos para baixar`
- `📎 Baixando anexo 1/3: nome_arquivo.pdf`
- `📎 ✓ Anexo 1 baixado: arquivo.pdf`
- `📎 Downloads concluídos: 2/3`

### 🛡️ **Segurança e Autenticação**
- Copia cookies do navegador para manter autenticação
- Headers realísticos para evitar bloqueios
- Timeout de 30 segundos por arquivo
- Tratamento robusto de erros

## Como Usar

1. Execute o extrator normalmente
2. Os arquivos serão baixados automaticamente durante a extração
3. No CSV final, a coluna "arquivos_anexados" terá os caminhos como:
   ```
   downloads_anexos\especificacao_tecnica.pdf; downloads_anexos\desenho_tecnico_1.jpg
   ```

## Formato no CSV

### ✅ **Antes** (apenas nomes):
```
arquivos_anexados
especificacao_tecnica.pdf, desenho_tecnico.jpg
```

### 🎯 **Agora** (caminhos locais):
```
arquivos_anexados
downloads_anexos\especificacao_tecnica.pdf; downloads_anexos\desenho_tecnico.jpg
```

## Tratamento de Erros

Se um arquivo não puder ser baixado, aparecerá como:
```
ERRO_DOWNLOAD: nome_do_arquivo.pdf
```

## Vantagens

✅ **Acesso offline** aos arquivos anexados  
✅ **Links diretos** para abrir os arquivos  
✅ **Backup local** de todos os documentos  
✅ **Organização automática** em pasta dedicada  
✅ **Compatibilidade total** com Excel (colunas auto-ajustadas)  
✅ **Status visual** do progresso dos downloads 

## Funcionalidade de Downloads Organizados

O sistema agora organiza automaticamente todos os anexos baixados em pastas separadas por cotação, facilitando a localização e organização dos arquivos.

### Estrutura de Pastas

```
downloads_anexos/
├── cotacao_56984/
│   ├── especificacao_tecnica.pdf
│   ├── desenho_tecnico.dwg
│   └── planilha_precos.xlsx
├── cotacao_56988/
│   ├── documento_contrato.pdf
│   └── anexo_especificacao.docx
└── cotacao_57082/
    ├── catalogo_produto.pdf
    └── certificado_qualidade.pdf
```

### Como Funciona

1. **Identificação da Cotação**: Cada cotação é identificada pelo seu número de evento (ex: "56984", "56988")

2. **Criação de Pasta**: O sistema cria automaticamente uma pasta com o nome da cotação na pasta `downloads_anexos/`

3. **Sanitização de Nomes**: Os nomes das pastas são automaticamente sanitizados para remover caracteres inválidos:
   - Caracteres especiais são substituídos por underscore (_)
   - Espaços são convertidos para underscore
   - Nomes muito longos são truncados

4. **Download Direto**: Os arquivos são baixados diretamente na pasta da cotação correspondente

5. **Prevenção de Duplicatas**: Se um arquivo com o mesmo nome já existir, o sistema adiciona um número sequencial (ex: `arquivo_1.pdf`, `arquivo_2.pdf`)

### Informações na Planilha

A coluna "arquivos_anexados" na planilha CSV/Excel continua mostrando os caminhos completos dos arquivos baixados, permitindo fácil localização:

```
downloads_anexos/cotacao_56984/especificacao_tecnica.pdf; downloads_anexos/cotacao_56984/desenho_tecnico.dwg
```

### Vantagens da Organização

- **Facilita Localização**: Cada cotação tem sua própria pasta
- **Evita Conflitos**: Arquivos com nomes iguais de cotações diferentes não se sobrescrevem
- **Organização Automática**: Não é necessário organizar manualmente os arquivos
- **Rastreabilidade**: Fácil identificação de qual anexo pertence a qual cotação

### Tratamento de Erros

- Se um download falhar, a informação é mantida na planilha como "ERRO_DOWNLOAD: nome_arquivo"
- Arquivos vazios ou corrompidos são automaticamente detectados e não são salvos
- Logs detalhados são gerados para facilitar a identificação de problemas

### Compatibilidade

- Funciona com todos os tipos de arquivo suportados (PDF, DOC, XLS, imagens, etc.)
- Mantém compatibilidade com versões anteriores do sistema
- Não afeta o funcionamento da extração de dados 