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