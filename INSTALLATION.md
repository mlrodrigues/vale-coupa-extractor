# 📦 Guia de Instalação e Setup

## Pré-requisitos

- Python 3.8+
- Windows 10 ou superior (para melhor compatibilidade com Keyring)
- pip (gerenciador de pacotes Python)

## Instalação de Dependências

### 1. Clonar ou baixar o projeto

```bash
cd vale-coupa-extractor
```

### 2. Instalar dependências Python

```bash
pip install -r requirements.txt
```

Isto instalará:
- `playwright` - Automação de navegador
- `keyring` - Acesso ao Windows Credential Manager
- `cryptography` - Encriptação de credenciais (fallback)
- `pydantic` - Validação de dados

### 3. Instalar browsers do Playwright

```bash
playwright install chromium
```

## Rodando a Aplicação

### Modo Desenvolvimento (Python puro)

```bash
python main_refactored.py
```

### Rodando Testes

```bash
# Testes do gerenciador de credenciais
python test_credentials_manager.py
```

## Compilando para Executável (Windows)

### Com PyInstaller

```bash
python build_exe.py
```

Ou para versão portátil:

```bash
python build_exe_portable.py
```

O executável será criado em `dist/ValeCoupaCrawler.exe`

## Estrutura do Projeto

```
vale-coupa-extractor/
├── main_refactored.py           # Aplicação principal
├── credentials_manager.py       # Gerenciador de credenciais
├── test_credentials_manager.py  # Testes unitários
├── build_exe.py                 # Script de compilação
├── build_exe_portable.py        # Script compilação portátil
├── requirements.txt             # Dependências
├── README.md                     # Documentação do usuário
├── INSTALLATION.md              # Este arquivo
├── CREDENTIALS_IMPLEMENTATION.md # Documentação técnica
└── BUILD.md                     # Instruções de build
```

## Troubleshooting

### Erro: "ModuleNotFoundError: No module named 'playwright'"

```bash
pip install playwright
playwright install chromium
```

### Erro: "ModuleNotFoundError: No module named 'keyring'"

```bash
pip install keyring
```

### Erro: "ModuleNotFoundError: No module named 'cryptography'"

```bash
pip install cryptography
```

### No Windows, as credenciais não salvam

Se o Windows Credential Manager não estiver acessível, o sistema fallback automaticamente para encriptação local (arquivo `.credentials/`).

Verifique permissões da pasta:
```bash
icacls .credentials /grant %username%:F
```

### Erro ao executar o .exe compilado

1. Desbloquear arquivo no Windows:
   - Clique direito > Propriedades
   - Marque "Desbloquear" se aparecer
   - Clique OK

2. Se não funcionar, tente rodar como Administrador:
   - Clique direito no .exe
   - "Executar como administrador"

## Primeiros Passos

1. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

2. **Rode testes para validar setup**
   ```bash
   python test_credentials_manager.py
   ```

3. **Execute a aplicação**
   ```bash
   python main_refactored.py
   ```

4. **Teste a funcionalidade de credenciais**
   - Digite suas credenciais
   - Marque "Lembrar credenciais nesta máquina"
   - Clique "EXTRAIR COTAÇÕES"
   - Feche e reabra a aplicação
   - As credenciais devem estar preenchidas

## Variáveis de Ambiente (Opcional)

Você pode configurar comportamento via variáveis:

```bash
# Usar encriptação local em vez de Keyring
set CREDMANAGER_USE_KEYRING=false

# Mudar diretório de armazenamento de credenciais
set CREDMANAGER_CONFIG_DIR=C:\MyCredentials
```

## Segurança

⚠️ **IMPORTANTE:**

- Nunca compartilhe o arquivo `.credentials/` ou qualquer arquivo `.key`
- Se usar computador compartilhado, sempre clique "Limpar credenciais salvas" depois
- Não commit credenciais para repositório Git
- Adicione `.credentials/` ao `.gitignore`

## Suporte

Se encontrar problemas:

1. Verifique o arquivo `crawler.log` para erros detalhados
2. Verifique o arquivo `credentials.log` para erros de credenciais
3. Execute testes: `python test_credentials_manager.py`
4. Consulte a documentação técnica: `CREDENTIALS_IMPLEMENTATION.md`

