# 🔧 Instruções de Build

## Para Desenvolvedores

Este documento contém instruções para compilar o projeto em um executável standalone.

## 📋 Pré-requisitos

1. **Python 3.8+** instalado
2. **Git** para clonar o repositório

## 🚀 Setup do Ambiente

### 1. Clonar o repositório
```bash
git clone <url-do-repositorio>
cd webcrawler
```

### 2. Criar ambiente virtual
```bash
python -m venv .venv
```

### 3. Ativar ambiente virtual
**Windows:**
```bash
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 4. Instalar dependências
```bash
pip install -r requirements.txt
```

### 5. Instalar browsers do Playwright
```bash
python -m playwright install
```

## 🔨 Opções de Compilação

Este projeto oferece **duas versões** de build:

### 🏆 **Build Portátil (RECOMENDADO)**
**Arquivo:** `build_exe_portable.py`

```bash
python build_exe_portable.py
```

**Características:**
- ✅ **Completamente independente**
- ✅ **Não precisa de instalações no PC de destino**
- ✅ **Inclui todos os browsers**
- ✅ **Máxima compatibilidade**
- ✅ **Pronto para distribuição**

**Resultado:**
- Arquivo: `dist/ValeCoupaCrawler_Portable.exe`
- Tamanho: ~500MB
- Funciona em qualquer Windows 10/11

### 🔧 **Build Padrão**
**Arquivo:** `build_exe.py`

```bash
python build_exe.py
```

**Características:**
- ⚡ Arquivo menor
- 🔧 Pode requerer configurações adicionais
- 🎯 Para desenvolvimento/teste

## 🧪 Testar Antes de Compilar

Para testar o código antes de compilar:
```bash
python main_refactored.py
```

## 📁 Estrutura do Projeto

```
webcrawler/
├── main_refactored.py         # Código principal
├── build_exe_portable.py      # Build PORTÁTIL (recomendado)
├── build_exe.py              # Build padrão
├── requirements.txt          # Dependências Python
├── README.md                # Manual do usuário
├── README.txt               # Manual em texto simples
├── BUILD.md                 # Este arquivo
└── .gitignore              # Arquivos ignorados pelo Git
```

## ⚠️ Notas Importantes

### 🏆 **Versão Portátil (build_exe_portable.py)**
1. **Tamanho**: ~500MB (inclui browser completo)
2. **Compatibilidade**: Máxima - funciona em qualquer Windows
3. **Instalação**: Zero - usuário só precisa do .exe
4. **Distribuição**: Ideal para usuários finais

### 🔧 **Versão Padrão (build_exe.py)**
1. **Tamanho**: Menor
2. **Compatibilidade**: Pode precisar de ajustes
3. **Uso**: Desenvolvimento e teste

### 📝 **Geral**
- **Antivírus**: Podem detectar falsos positivos (normal com PyInstaller)
- **Primeira execução**: Pode demorar mais para iniciar
- **Sistema**: Apenas Windows 10/11

## 🐛 Solução de Problemas

### Erro de "browser não encontrado"
```bash
python -m playwright install chromium
```

### Erro de dependências
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

### Build falha
1. Verifique se todos os browsers estão instalados
2. Certifique-se de ter espaço em disco (~2GB livres)
3. Execute como administrador se necessário

### Executável muito lento
- Normal na primeira execução
- Executáveis PyInstaller são mais lentos que Python direto

## 📦 Distribuição Recomendada

### Para Usuários Finais:
1. Use **`python build_exe_portable.py`**
2. Distribua apenas o arquivo `.exe` gerado
3. Inclua os arquivos `README.md` e `README.txt`
4. O executável é 100% standalone

### Para Desenvolvedores:
1. Use **`python build_exe.py`** para testes rápidos
2. Use **`python build_exe_portable.py`** para distribuição final

## 🎯 Exemplo de Uso

```bash
# 1. Setup inicial
git clone <repositorio>
cd webcrawler
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install

# 2. Teste o código
python main_refactored.py

# 3. Build para distribuição
python build_exe_portable.py

# 4. Resultado
# dist/ValeCoupaCrawler_Portable.exe (pronto para usar!)
```

---

**Versão**: 2.0 Refatorada  
**Última atualização**: Junho 2025 