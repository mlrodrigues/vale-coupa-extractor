#!/usr/bin/env python3
"""
Script de Build Simplificado para Vale Coupa Crawler
Tenta diferentes abordagens para resolver problemas de compatibilidade
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path

def check_python_version():
    """Verifica a versão do Python e sugere soluções"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor >= 13:
        print("⚠️  Python 3.13+ detectado - pode haver problemas de compatibilidade")
        print("💡 Sugestões:")
        print("   1. Use Python 3.10, 3.11 ou 3.12 para melhor compatibilidade")
        print("   2. Ou tente instalar dependências manualmente primeiro")
        return False
    elif version.major == 3 and version.minor >= 10:
        print("✅ Versão do Python compatível")
        return True
    else:
        print("❌ Versão do Python muito antiga")
        return False

def install_dependencies_simple():
    """Instala dependências com abordagem simplificada"""
    print("📦 Instalando dependências...")
    
    # Primeiro tenta atualizar o pip
    try:
        print("   Atualizando pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True, text=True)
        print("   ✓ Pip atualizado")
    except:
        print("   ⚠️ Não foi possível atualizar o pip")
    
    # Lista de dependências básicas
    basic_deps = ["pyinstaller", "requests", "openpyxl", "pandas"]
    
    for dep in basic_deps:
        try:
            print(f"   Instalando {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                         check=True, capture_output=True, text=True)
            print(f"   ✓ {dep} instalado")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Erro ao instalar {dep}: {e}")
            return False
    
    # Tenta instalar Playwright de diferentes formas
    playwright_installed = False
    
    # Tentativa 1: Versão mais recente
    try:
        print("   Tentando instalar playwright (versão mais recente)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], 
                      check=True, capture_output=True, text=True)
        print("   ✓ Playwright instalado (versão mais recente)")
        playwright_installed = True
    except:
        print("   ❌ Falha na tentativa 1")
    
    # Tentativa 2: Versão específica mais antiga
    if not playwright_installed:
        try:
            print("   Tentando instalar playwright==1.40.0...")
            subprocess.run([sys.executable, "-m", "pip", "install", "playwright==1.40.0"], 
                          check=True, capture_output=True, text=True)
            print("   ✓ Playwright instalado (versão 1.40.0)")
            playwright_installed = True
        except:
            print("   ❌ Falha na tentativa 2")
    
    # Tentativa 3: Instalação manual
    if not playwright_installed:
        print("   ⚠️ Instalação automática do Playwright falhou")
        print("   💡 Tente instalar manualmente:")
        print("      pip install playwright")
        print("      playwright install chromium")
        return False
    
    # Instala browsers
    try:
        print("   Instalando browsers do Playwright...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                      check=True, capture_output=True, text=True)
        print("   ✓ Browsers instalados")
    except:
        print("   ⚠️ Não foi possível instalar browsers automaticamente")
        print("   💡 Execute manualmente: playwright install chromium")
    
    return True

def create_simple_spec():
    """Cria arquivo .spec simplificado"""
    print("📝 Criando arquivo de especificação...")
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main_refactored.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'playwright.sync_api',
        'openpyxl',
        'pandas',
        'requests',
        'tkinter',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Vale_Coupa_Crawler_Simple',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    version_file=None,
)
'''
    
    spec_file = Path("vale_crawler_simple.spec")
    with open(spec_file, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    
    print(f"   ✓ Arquivo de especificação criado: {spec_file}")
    return spec_file

def build_executable_simple(spec_file):
    """Executa build simplificado"""
    print("🔨 Iniciando build...")
    
    try:
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            str(spec_file)
        ]
        
        print(f"   Executando: {' '.join(cmd)}")
        
        # Executa sem capturar output para ver progresso
        result = subprocess.run(cmd, check=True)
        
        print("   ✓ Build concluído com sucesso!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro no build: {e}")
        return False

def main():
    """Função principal"""
    print("🚀 Build Simplificado - Vale Coupa Crawler")
    print("=" * 50)
    
    # Verifica versão do Python
    if not check_python_version():
        print("\n💡 Recomendação: Use Python 3.10, 3.11 ou 3.12")
        print("   Ou continue se quiser tentar mesmo assim...")
        input("   Pressione Enter para continuar...")
    
    # Instala dependências
    if not install_dependencies_simple():
        print("\n❌ Falha na instalação de dependências")
        print("💡 Tente instalar manualmente:")
        print("   pip install pyinstaller playwright openpyxl pandas requests")
        print("   playwright install chromium")
        return
    
    # Cria arquivo .spec
    spec_file = create_simple_spec()
    
    # Executa build
    if build_executable_simple(spec_file):
        print("\n✅ BUILD CONCLUÍDO!")
        print("📁 Executável disponível em: dist/Vale_Coupa_Crawler_Simple.exe")
        print("🎉 Teste o aplicativo!")
    else:
        print("\n❌ Build falhou")
        print("💡 Verifique os erros acima")

if __name__ == "__main__":
    main() 