"""
Script para compilar o Vale Coupa Crawler em um arquivo executável
Versão otimizada para Playwright
"""

import subprocess
import sys
import os

def install_pyinstaller():
    """Instala o PyInstaller se não estiver instalado"""
    try:
        import PyInstaller
        print("PyInstaller já está instalado.")
    except ImportError:
        print("Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("PyInstaller instalado com sucesso!")

def install_playwright_browsers():
    """Instala os browsers do Playwright"""
    print("Verificando browsers do Playwright...")
    try:
        # Instala apenas o Chromium (mais leve)
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("Browsers do Playwright instalados!")
    except Exception as e:
        print(f"Aviso: Não foi possível instalar browsers automaticamente: {e}")
        print("Você pode precisar executar 'playwright install chromium' manualmente.")

def build_executable():
    """Compila o aplicativo em um arquivo executável"""
    print("Iniciando compilação do Vale Coupa Crawler...")
    
    # Comando PyInstaller com configurações otimizadas para Playwright
    cmd = [
        "pyinstaller",
        "--onefile",  # Gera um único arquivo
        "--windowed",  # Remove a janela do console
        "--name=ValeCoupaCrawler",  # Nome do executável
        "--distpath=dist",  # Pasta de saída
        "--workpath=build",  # Pasta de trabalho temporária
        "--specpath=.",  # Pasta do arquivo .spec
        # Configurações específicas para Playwright
        "--collect-data=playwright",  # Inclui dados do Playwright
        "--collect-binaries=playwright",  # Inclui binários do Playwright
        "--hidden-import=playwright",
        "--hidden-import=playwright.sync_api",
        "--hidden-import=playwright._impl",
        "--hidden-import=greenlet",  # Dependência do Playwright
        # Configurações para tkinter
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.ttk",
        "--hidden-import=tkinter.messagebox",
        # Outras dependências
        "--hidden-import=csv",
        "--hidden-import=logging",
        "--hidden-import=datetime",
        "--hidden-import=re",
        "--hidden-import=time",
        "--hidden-import=os",
        "--hidden-import=typing",
        "--hidden-import=abc",
        "--hidden-import=dataclasses",
        "--hidden-import=enum",
        # Ignora avisos não críticos
        "--noconfirm",
        "main_refactored.py"  # Arquivo principal
    ]
    
    # Adiciona ícone se existir
    if os.path.exists("icon.ico"):
        cmd.insert(-1, "--icon=icon.ico")
    
    try:
        print(f"Executando: {' '.join(cmd[:5])} ... [comando completo]")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("\n" + "="*50)
        print("COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*50)
        print("O arquivo executável foi criado em: dist/ValeCoupaCrawler.exe")
        print("\n⚠️  IMPORTANTE:")
        print("• Este executável precisa que o Playwright esteja instalado")
        print("• Execute 'playwright install chromium' no PC de destino")
        print("• Ou distribua junto com uma pasta de browsers")
        print("="*50)
        
    except subprocess.CalledProcessError as e:
        print(f"Erro durante a compilação: {e}")
        if e.stderr:
            print(f"Detalhes do erro: {e.stderr}")
        return False
    except FileNotFoundError:
        print("PyInstaller não encontrado. Tentando instalar...")
        install_pyinstaller()
        return build_executable()
    
    return True

def create_portable_version():
    """Cria uma versão portátil com instruções"""
    instructions = """
INSTRUÇÕES PARA USO DO EXECUTÁVEL
================================

1. PRIMEIRA EXECUÇÃO:
   - Execute o arquivo ValeCoupaCrawler.exe
   - Se der erro de "browser não encontrado", faça:
     - Instale Python no PC de destino (python.org)
     - Abra o prompt de comando
     - Execute: pip install playwright
     - Execute: playwright install chromium

2. ALTERNATIVA (SEM INSTALAR PYTHON):
   - Copie a pasta de browsers do Playwright junto com o EXE
   - A pasta fica em: %USERPROFILE%\\AppData\\Local\\ms-playwright

3. DISTRIBUIÇÃO:
   - Arquivo principal: ValeCoupaCrawler.exe
   - Opcional: pasta ms-playwright (browsers)
   - Este arquivo: LEIA-ME.txt

4. REQUISITOS:
   - Windows 10/11
   - Conexão com internet (para acessar o site Vale Coupa)
   
Desenvolvido para automatizar extração de cotações Vale Coupa
================================
"""
    
    with open("dist/LEIA-ME.txt", "w", encoding="utf-8") as f:
        f.write(instructions)
    
    print("Arquivo de instruções criado: dist/LEIA-ME.txt")

def main():
    """Função principal"""
    print("Vale Coupa Crawler - Compilador de Executável v2.0")
    print("=" * 50)
    
    # Verifica se o arquivo principal existe
    if not os.path.exists("main_refactored.py"):
        print("ERRO: Arquivo 'main_refactored.py' não encontrado!")
        print("Certifique-se de que está na pasta correta.")
        return
    
    # Instala dependências
    install_pyinstaller()
    install_playwright_browsers()
    
    # Compila o executável
    if build_executable():
        create_portable_version()
        print("\nCompilação finalizada! Verifique a pasta 'dist'")
        print("\nPressione Enter para continuar...")
        input()

if __name__ == "__main__":
    main() 