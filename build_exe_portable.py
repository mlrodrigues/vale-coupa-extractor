#!/usr/bin/env python3
"""
Script de Build para Vale Coupa Crawler - Versão Portátil
Gera um executável standalone com todas as dependências incluídas
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path
import json
from datetime import datetime

class PortableBuilder:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.dist_dir = self.project_dir / "dist"
        self.build_dir = self.project_dir / "build"
        self.spec_file = self.project_dir / "vale_crawler.spec"
        
    def clean_previous_builds(self):
        """Remove builds anteriores"""
        print("🧹 Limpando builds anteriores...")
        
        dirs_to_clean = [self.dist_dir, self.build_dir]
        for dir_path in dirs_to_clean:
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    print(f"   Removido: {dir_path}")
                except PermissionError:
                    print(f"   ⚠️ Não foi possível remover {dir_path} (arquivo em uso)")
                    # Tenta remover apenas arquivos individuais
                    try:
                        for file_path in dir_path.rglob('*'):
                            if file_path.is_file():
                                file_path.unlink()
                        dir_path.rmdir()
                        print(f"   ✓ Removido com sucesso: {dir_path}")
                    except Exception as e:
                        print(f"   ❌ Erro ao remover {dir_path}: {e}")
                        return False
                except Exception as e:
                    print(f"   ❌ Erro ao remover {dir_path}: {e}")
                    return False
        
        # Remove arquivo .spec se existir
        if self.spec_file.exists():
            try:
                self.spec_file.unlink()
                print(f"   Removido: {self.spec_file}")
            except Exception as e:
                print(f"   ⚠️ Não foi possível remover {self.spec_file}: {e}")
        
        return True
    
    def install_dependencies(self):
        """Instala dependências necessárias"""
        print("📦 Instalando dependências...")
        
        # Lista de dependências atualizadas para Python 3.13
        dependencies = [
            "pyinstaller",
            "playwright>=1.42.0",  # Versão mais recente que suporta Python 3.13
            "openpyxl==3.1.2", 
            "pandas==2.2.0",
            "requests==2.31.0"
        ]
        
        for dep in dependencies:
            print(f"   Instalando {dep}...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                             check=True, capture_output=True, text=True)
                print(f"   ✓ {dep} instalado")
            except subprocess.CalledProcessError as e:
                print(f"   ❌ Erro ao instalar {dep}: {e}")
                # Tenta instalar sem versão específica
                try:
                    dep_name = dep.split('==')[0].split('>=')[0]
                    print(f"   Tentando instalar {dep_name} sem versão específica...")
                    subprocess.run([sys.executable, "-m", "pip", "install", dep_name], 
                                 check=True, capture_output=True, text=True)
                    print(f"   ✓ {dep_name} instalado (versão mais recente)")
                except subprocess.CalledProcessError as e2:
                    print(f"   ❌ Falha total ao instalar {dep}: {e2}")
                    return False
        
        return True
    
    def install_playwright_browsers(self):
        """Instala browsers do Playwright"""
        print("🌐 Instalando browsers do Playwright...")
        
        try:
            # Instala browsers
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                         check=True, capture_output=True, text=True)
            print("   ✓ Chromium instalado")
            
            # Instala dependências do sistema
            subprocess.run([sys.executable, "-m", "playwright", "install-deps"], 
                         check=True, capture_output=True, text=True)
            print("   ✓ Dependências do sistema instaladas")
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Erro ao instalar browsers: {e}")
            return False
    
    def create_spec_file(self):
        """Cria arquivo de especificação do PyInstaller"""
        print("📝 Criando arquivo de especificação...")
        
        # Tenta localizar os browsers para incluir no spec
        browsers_data = []
        try:
            import playwright
            user_home = Path.home()
            possible_browser_paths = [
                user_home / "AppData" / "Local" / "ms-playwright",
                user_home / ".cache" / "ms-playwright",
                user_home / "ms-playwright"
            ]
            
            for path in possible_browser_paths:
                if path.exists() and (path / "chromium-1169").exists():
                    # Converte barras invertidas para barras normais para evitar erro de unicode
                    path_str = str(path).replace('\\', '/')
                    browsers_data.append(f"('{path_str}', 'ms-playwright')")
                    print(f"   ✓ Browsers encontrados para incluir: {path}")
                    break
        except:
            pass
        
        # Formata a lista de dados
        if browsers_data:
            data_list = "['requirements.txt', '.'], " + ", ".join(browsers_data)
        else:
            data_list = "['requirements.txt', '.']"
        
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Arquivos e pastas a serem incluídos
added_files = [
    {data_list}
]

# Configuração para Windows
a = Analysis(
    ['main_refactored.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'playwright.sync_api',
        'playwright.async_api', 
        'openpyxl',
        'pandas',
        'requests',
        'tkinter',
        'tkinter.ttk',
        'csv',
        'datetime',
        'pathlib',
        'hashlib',
        'urllib.parse',
        'threading',
        'logging',
        're',
        'time',
        'os',
        'sys',
        'json',
        'shutil',
        'subprocess',
        'platform'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Configuração para executável
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Vale_Coupa_Crawler_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False para aplicação GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Adicione ícone aqui se tiver
    version_file=None,
)
'''
        
        try:
            with open(self.spec_file, 'w', encoding='utf-8') as f:
                f.write(spec_content)
            
            print(f"   ✓ Arquivo de especificação criado: {self.spec_file}")
            return True
        except Exception as e:
            print(f"   ❌ Erro ao criar arquivo de especificação: {e}")
            return False
    
    def build_executable(self):
        """Executa o build do PyInstaller"""
        print("🔨 Iniciando build do executável...")
        
        try:
            # Comando PyInstaller
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--clean",  # Limpa cache
                "--noconfirm",  # Não pede confirmação
                str(self.spec_file)
            ]
            
            print(f"   Executando: {' '.join(cmd)}")
            
            # Executa o build
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            print("   ✓ Build concluído com sucesso!")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Erro no build: {e}")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            return False
    
    def copy_playwright_browsers(self):
        """Copia browsers do Playwright para o executável"""
        print("🌐 Copiando browsers do Playwright...")
        
        try:
            # Tenta diferentes caminhos para localizar os browsers
            possible_paths = []
            
            # Caminho padrão do usuário
            user_home = Path.home()
            possible_paths.extend([
                user_home / "AppData" / "Local" / "ms-playwright",
                user_home / ".cache" / "ms-playwright",
                user_home / "ms-playwright"
            ])
            
            # Caminhos do Python
            try:
                import playwright
                playwright_dir = Path(playwright.__file__).parent
                possible_paths.extend([
                    playwright_dir / ".venv" / "ms-playwright",
                    playwright_dir / "ms-playwright",
                    playwright_dir.parent / "ms-playwright"
                ])
            except:
                pass
            
            # Procura pelos browsers
            browsers_dir = None
            for path in possible_paths:
                if path.exists() and (path / "chromium-1169").exists():
                    browsers_dir = path
                    print(f"   ✓ Browsers encontrados em: {browsers_dir}")
                    break
            
            if not browsers_dir:
                print("   ⚠️ Browsers não encontrados nos caminhos padrão")
                print("   💡 Tentando instalar novamente...")
                
                # Tenta instalar novamente
                try:
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                                 check=True, capture_output=True, text=True)
                    
                    # Procura novamente após instalação
                    for path in possible_paths:
                        if path.exists() and (path / "chromium-1169").exists():
                            browsers_dir = path
                            print(f"   ✓ Browsers encontrados após reinstalação: {browsers_dir}")
                            break
                except:
                    pass
            
            if browsers_dir and browsers_dir.exists():
                # Copia para o executável - múltiplos locais possíveis
                exe_dir = self.dist_dir / "Vale_Coupa_Crawler_v2"
                
                # Local 1: Pasta ms-playwright na raiz do executável
                target_dir1 = exe_dir / "ms-playwright"
                if target_dir1.exists():
                    shutil.rmtree(target_dir1)
                shutil.copytree(browsers_dir, target_dir1)
                print(f"   ✓ Browsers copiados para: {target_dir1}")
                
                # Local 2: Pasta playwright/driver/package/.local-browsers (onde o PyInstaller procura)
                target_dir2 = exe_dir / "playwright" / "driver" / "package" / ".local-browsers"
                target_dir2.mkdir(parents=True, exist_ok=True)
                
                # Copia apenas o chromium para o local esperado
                chromium_source = browsers_dir / "chromium-1169"
                if chromium_source.exists():
                    chromium_target = target_dir2 / "chromium-1169"
                    if chromium_target.exists():
                        shutil.rmtree(chromium_target)
                    shutil.copytree(chromium_source, chromium_target)
                    print(f"   ✓ Chromium copiado para: {chromium_target}")
                
                return True
            else:
                print("   ⚠️ Não foi possível localizar os browsers")
                print("   💡 O aplicativo pode funcionar sem browsers embutidos")
                print("   💡 Execute manualmente: playwright install chromium")
                return True  # Retorna True mesmo sem browsers para continuar o build
                
        except Exception as e:
            print(f"   ⚠️ Erro ao copiar browsers: {e}")
            print("   💡 O aplicativo pode funcionar sem browsers embutidos")
            return True  # Retorna True para continuar o build
    
    def create_readme(self):
        """Cria arquivo README para o executável"""
        print("📖 Criando README...")
        
        # Garante que a pasta dist existe
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        
        readme_content = f"""# Vale Coupa Web Crawler - Versão Portátil

## 📋 Descrição
Sistema automatizado para extração de dados de cotações da plataforma Vale Coupa com filtro de resposta configurável.

## 🚀 Como Usar

### 1. Execução
- Execute o arquivo `Vale_Coupa_Crawler.exe`
- Aguarde a interface gráfica carregar

### 2. Configuração
- **Usuário**: Seu nome de usuário na plataforma Vale Coupa
- **Senha**: Sua senha na plataforma Vale Coupa
- **Data**: Data das cotações no formato DD/MM/YY (ex: 25/12/24)
- **Filtro de Resposta**: 
  - `0` = Apenas cotações sem resposta (resposta = 0)
  - `1` = Apenas cotações com resposta (resposta ≠ 0)
  - `todas` = Todas as cotações

### 3. Extração
- Clique em "🔥 EXTRAIR COTAÇÕES"
- Aguarde o processo de extração
- O arquivo CSV será gerado na pasta do programa

## 📁 Arquivos Gerados
- `dados_cotacoes_YYYYMMDD_HHMMSS.csv` - Dados extraídos em formato CSV
- `dados_cotacoes_YYYYMMDD_HHMMSS.xlsx` - Dados extraídos em formato Excel (se disponível)
- `downloads_anexos/` - Pasta com anexos baixados das cotações

## 🔧 Funcionalidades
- ✅ Autenticação automática na plataforma
- ✅ Filtro configurável por tipo de resposta
- ✅ Extração de dados de itens e serviços
- ✅ Download automático de anexos
- ✅ Remoção automática de duplicatas
- ✅ Exportação para CSV e Excel
- ✅ Interface gráfica moderna
- ✅ Logs detalhados de execução

## 📝 Notas Importantes
- O sistema filtra automaticamente as cotações baseado no critério de resposta selecionado
- Apenas cotações da data especificada são processadas
- Os anexos são organizados em pastas por cotação
- O arquivo de log `crawler.log` contém informações detalhadas da execução

## 🆘 Suporte
Em caso de problemas, verifique:
1. Se as credenciais estão corretas
2. Se há cotações para a data especificada
3. Se há cotações com o tipo de resposta selecionado
4. O arquivo de log para detalhes técnicos

---
**Versão**: Portátil com todas as dependências incluídas
**Data**: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
"""
        
        readme_file = self.dist_dir / "README.txt"
        try:
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            print(f"   ✓ README criado: {readme_file}")
            return True
        except Exception as e:
            print(f"   ❌ Erro ao criar README: {e}")
            return False
    
    def create_batch_launcher(self):
        """Cria arquivo .bat para facilitar execução"""
        print("🚀 Criando launcher...")
        
        # Garante que a pasta dist existe
        self.dist_dir.mkdir(parents=True, exist_ok=True)
        
        batch_content = """@echo off
echo ========================================
echo    Vale Coupa Crawler v2 - Portatil
echo ========================================
echo.
echo Iniciando aplicacao...
echo.

REM Executa o aplicativo
start "" "Vale_Coupa_Crawler_v2.exe"

REM Aguarda um pouco e fecha a janela
timeout /t 3 /nobreak >nul
exit
"""
        
        batch_file = self.dist_dir / "Executar_Crawler_v2.bat"
        try:
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write(batch_content)
            
            print(f"   ✓ Launcher criado: {batch_file}")
            return True
        except Exception as e:
            print(f"   ❌ Erro ao criar launcher: {e}")
            return False
    
    def optimize_size(self):
        """Otimiza tamanho do executável"""
        print("📦 Otimizando tamanho...")
        
        exe_dir = self.dist_dir / "Vale_Coupa_Crawler_v2"
        
        if exe_dir.exists():
            try:
                # Remove arquivos desnecessários
                files_to_remove = [
                    "VCRUNTIME140.dll",  # Já incluído no Windows
                    "python*.dll",       # DLLs do Python desnecessárias
                ]
                
                for file_pattern in files_to_remove:
                    for file_path in exe_dir.glob(file_pattern):
                        try:
                            file_path.unlink()
                            print(f"   Removido: {file_path.name}")
                        except:
                            pass
                
                # Calcula tamanho final
                total_size = sum(f.stat().st_size for f in exe_dir.rglob('*') if f.is_file())
                size_mb = total_size / (1024 * 1024)
                print(f"   ✓ Tamanho final: {size_mb:.1f} MB")
                return True
            except Exception as e:
                print(f"   ⚠️ Erro na otimização: {e}")
                return True  # Retorna True mesmo com erro para não falhar o build
        else:
            print("   ⚠️ Pasta do executável não encontrada")
            return True  # Retorna True para não falhar o build
    
    def build(self):
        """Executa o processo completo de build"""
        print("🚀 Iniciando build do Vale Coupa Crawler v2 Portátil")
        print("=" * 60)
        
        # Verifica se estamos no Windows
        if platform.system() != "Windows":
            print("❌ Este build é específico para Windows")
            return False
        
        # Passos do build
        steps = [
            ("Limpando builds anteriores", self.clean_previous_builds),
            ("Instalando dependências", self.install_dependencies),
            ("Instalando browsers", self.install_playwright_browsers),
            ("Criando especificação", self.create_spec_file),
            ("Executando build", self.build_executable),
            ("Copiando browsers", self.copy_playwright_browsers),
            ("Criando README", self.create_readme),
            ("Criando launcher", self.create_batch_launcher),
            ("Otimizando tamanho", self.optimize_size),
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 {step_name}...")
            if not step_func():
                print(f"❌ Falha no passo: {step_name}")
                return False
        
        print("\n" + "=" * 60)
        print("✅ BUILD CONCLUÍDO COM SUCESSO!")
        print(f"📁 Executável disponível em: {self.dist_dir}")
        print("🎉 O aplicativo v2 está pronto para uso!")
        
        return True

def main():
    """Função principal"""
    builder = PortableBuilder()
    success = builder.build()
    
    if success:
        print("\n🎯 Para usar o aplicativo:")
        print("1. Vá para a pasta 'dist'")
        print("2. Execute 'Vale_Coupa_Crawler_v2.exe' ou 'Executar_Crawler_v2.bat'")
        print("3. O aplicativo é totalmente portátil!")
        print("4. Agora filtra automaticamente apenas cotações com resposta = 0")
    else:
        print("\n❌ Build falhou. Verifique os erros acima.")
        sys.exit(1)

if __name__ == "__main__":
    main() 