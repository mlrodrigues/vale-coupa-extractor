"""
Script para compilar Vale Coupa Crawler em executável PORTÁTIL
Versão completamente standalone - não precisa de instalações no PC de destino

Configurações:
- Modo headless (browser invisível)
- Todos os browsers incluídos
- Todas as dependências empacotadas
- Funciona em qualquer Windows 10/11
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def install_pyinstaller():
    """Instala PyInstaller se não estiver presente"""
    try:
        import PyInstaller
        print("✅ PyInstaller já está instalado")
    except ImportError:
        print("📦 Instalando PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✅ PyInstaller instalado com sucesso")

def find_playwright_browsers():
    """Encontra o diretório dos browsers do Playwright"""
    possible_paths = [
        os.path.expanduser("~/.cache/ms-playwright"),
        os.path.expanduser("~/AppData/Local/ms-playwright"),
        os.path.join(os.getcwd(), ".venv", "Lib", "site-packages", "playwright", "driver"),
        os.path.join(sys.prefix, "Lib", "site-packages", "playwright", "driver")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Browsers encontrados em: {path}")
            return path
    
    print("❌ Browsers do Playwright não encontrados!")
    print("Execute: python -m playwright install")
    return None

def create_portable_spec():
    """Cria arquivo .spec otimizado para versão portátil"""
    browsers_path = find_playwright_browsers()
    if not browsers_path:
        return None
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Coleta todos os browsers do Playwright
datas = [(r'{browsers_path}', 'ms-playwright')]

# Coleta dados do Playwright
datas += collect_data_files('playwright')

# Coleta submódulos ocultos
hidden_imports = [
    'playwright',
    'playwright.sync_api', 
    'playwright._impl',
    'playwright._impl._browser',
    'playwright._impl._browser_context',
    'playwright._impl._page',
    'playwright._impl._element_handle',
    'playwright._impl._locator',
    'greenlet',
    'tkinter',
    'tkinter.ttk', 
    'tkinter.messagebox',
    'tkinter.filedialog',
    'csv',
    'logging',
    'datetime',
    'pathlib',
    'subprocess',
    'asyncio',
    'threading',
    'queue',
    'json',
    'base64',
    'urllib',
    'urllib.parse',
    'urllib.request',
    'ssl',
    'certifi'
]

# Adiciona submódulos do Playwright automaticamente
hidden_imports += collect_submodules('playwright')

a = Analysis(
    ['main_refactored.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'pandas',
        'numpy',
        'scipy',
        'PIL',
        'cv2',
        'tensorflow',
        'torch'
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ValeCoupaCrawler_Portable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Modo janela (sem console)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)
'''
    
    with open('ValeCoupaCrawler_Portable.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print("✅ Arquivo .spec portátil criado")
    return 'ValeCoupaCrawler_Portable.spec'

def build_portable_exe():
    """Compila o executável portátil"""
    print("🚀 Iniciando compilação PORTÁTIL...")
    
    # Instala PyInstaller
    install_pyinstaller()
    
    # Cria arquivo .spec
    spec_file = create_portable_spec()
    if not spec_file:
        print("❌ Falha ao criar arquivo .spec")
        return False
    
    # Limpa builds anteriores
    if os.path.exists('build'):
        shutil.rmtree('build')
        print("🧹 Pasta build anterior removida")
    
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        print("🧹 Pasta dist anterior removida")
    
    # Compila com PyInstaller
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',           # Limpa cache
        '--noconfirm',       # Não pede confirmação
        '--distpath', 'dist', # Pasta de saída
        '--workpath', 'build', # Pasta de trabalho
        spec_file
    ]
    
    print("⚙️ Executando PyInstaller...")
    print(f"Comando: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Compilação concluída com sucesso!")
        
        # Verifica se o arquivo foi criado
        exe_path = Path('dist') / 'ValeCoupaCrawler_Portable.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"📦 Executável criado: {exe_path}")
            print(f"📏 Tamanho: {size_mb:.1f} MB")
            
            # Cria README para a pasta dist
            create_dist_readme()
            
            return True
        else:
            print("❌ Arquivo executável não encontrado após compilação")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro na compilação: {e}")
        print(f"Saída do erro: {e.stderr}")
        return False

def create_dist_readme():
    """Cria README específico para a versão portátil"""
    readme_content = """🚀 VALECOUPACRAWLER PORTÁTIL

✅ VERSÃO COMPLETAMENTE AUTÔNOMA
- Não precisa instalar Python
- Não precisa instalar Playwright 
- Não precisa instalar browsers
- Funciona em qualquer Windows 10/11
- Browser pode rodar visível ou invisível conforme configuração

🎯 COMO USAR:
1. Copie o arquivo ValeCoupaCrawler_Portable.exe
2. Execute em qualquer computador Windows
3. Pronto! Não precisa instalar nada

📦 O QUE ESTÁ INCLUÍDO:
- Interface gráfica completa
- Chromium browser integrado
- Todas as bibliotecas Python necessárias
- Sistema de logging
- Exportação para CSV
- Configurações otimizadas

⚠️ IMPORTANTE:
- Arquivo maior (~500MB) pois inclui browser completo
- Primeira execução pode demorar mais (normal)
- Funciona offline para a interface (precisa internet para acessar Vale Coupa)
- Antivírus podem detectar falso positivo (normal com PyInstaller)

🎊 Desenvolvido para máxima portabilidade e compatibilidade!

---
Versão: 2.0 Portátil
Compatibilidade: Windows 10/11
"""
    
    dist_path = Path('dist')
    dist_path.mkdir(exist_ok=True)
    
    with open(dist_path / 'LEIA-ME_PORTABLE.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print("✅ README criado na pasta dist")

def main():
    """Função principal"""
    print("=" * 60)
    print("🔧 VALE COUPA CRAWLER - BUILD PORTÁTIL")
    print("=" * 60)
    print()
    
    # Verifica se o arquivo principal existe
    if not os.path.exists('main_refactored.py'):
        print("❌ Arquivo main_refactored.py não encontrado!")
        print("Certifique-se de estar na pasta correta do projeto.")
        return
    
    print("📋 Configuração:")
    print("   • Tipo: Executável Portátil")
    print("   • Browser: Chromium Integrado")
    print("   • Interface: GUI (sem console)")
    print("   • Compatibilidade: Windows 10/11")
    print()
    
    # Pergunta confirmação
    response = input("🚀 Iniciar compilação? (s/n): ").lower().strip()
    if response not in ['s', 'sim', 'y', 'yes']:
        print("❌ Compilação cancelada")
        return
    
    print()
    success = build_portable_exe()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 COMPILAÇÃO CONCLUÍDA COM SUCESSO!")
        print()
        print("📁 Arquivos gerados:")
        print("   • dist/ValeCoupaCrawler_Portable.exe")
        print("   • dist/LEIA-ME_PORTABLE.txt")
        print()
        print("💡 Você pode distribuir apenas o arquivo .exe")
        print("   Ele é completamente independente!")
    else:
        print("❌ FALHA NA COMPILAÇÃO")
        print()
        print("🔍 Verifique:")
        print("   • Se todas as dependências estão instaladas")
        print("   • Se os browsers do Playwright foram instalados")
        print("   • Se há espaço suficiente em disco")
    print("=" * 60)

if __name__ == "__main__":
    main() 