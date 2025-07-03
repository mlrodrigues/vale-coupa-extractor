"""
Vale Coupa Web Crawler - Versão Refatorada
Sistema para extração automatizada de cotações da plataforma Vale Coupa

Arquitetura baseada em:
- Strategy Pattern para diferentes estratégias de expansão
- Factory Pattern para criação de extractors
- Observer Pattern para logging
- Dependency Injection para configurações
- Clean Code principles
- SOLID principles
"""

import csv
import time
import re
import os
import logging
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Protocol, TypedDict
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from playwright.sync_api import Page, sync_playwright, TimeoutError as PlaywrightTimeoutError
import sys
from pathlib import Path
import requests
from urllib.parse import urljoin, urlparse
import hashlib

# Adicionar import do openpyxl
try:
    from openpyxl import Workbook
    from openpyxl.utils.dataframe import dataframe_to_rows
    import pandas as pd
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

# ==========================================
# CONFIGURAÇÕES E TIPOS
# ==========================================

def get_executable_dir():
    """Retorna o diretório do executável ou script"""
    if getattr(sys, 'frozen', False):
        # Rodando como executável PyInstaller
        return Path(sys._MEIPASS)
    else:
        # Rodando como script Python
        return Path(__file__).parent

def setup_playwright_environment():
    """Configura ambiente do Playwright para executável"""
    if getattr(sys, 'frozen', False):
        # Rodando como executável - configura caminhos dos browsers
        exe_dir = get_executable_dir()
        
        # Procura pasta de browsers no executável
        browser_paths = [
            exe_dir / "ms-playwright",
            exe_dir / "playwright" / "browsers",
            exe_dir / "_internal" / "ms-playwright"
        ]
        
        for browser_path in browser_paths:
            if browser_path.exists():
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_path)
                break
        
        # Força download de browsers se necessário
        os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"

# Configura ambiente antes de importar o Playwright
setup_playwright_environment()

class LogLevel(Enum):
    """Níveis de log disponíveis"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

@dataclass
class CrawlerConfig:
    """Configurações do crawler"""
    base_url: str = "https://vale.coupahost.com"
    login_path: str = "/sessions/supplier_login"
    quotes_path: str = "/quote_supplier_land"
    timeout_ms: int = 60000
    headless: bool = True
    items_per_page: int = 90
    max_retries: int = 3
    resposta_filter: str = "0"  # "0", "1", ou "todas"
    
class ExtractedItemData(TypedDict):
    """Estrutura dos dados extraídos de um item"""
    numero_item: str
    descricao: str
    descricao_estendida: str
    quantidade: str
    data_necessaria: str
    detalhes: str
    arquivos_anexados: str

class QuoteData(TypedDict):
    """Estrutura dos dados de uma cotação"""
    evento: str
    nome_evento: str
    data_inicial: str
    data_final: str
    resposta: str  # Novo campo para filtrar cotações

# ==========================================
# INTERFACES E PROTOCOLOS
# ==========================================

class PageInteractionStrategy(Protocol):
    """Interface para estratégias de interação com página"""
    
    def execute(self, page: Page) -> bool:
        """Executa a estratégia na página"""
        ...

class DataExtractor(Protocol):
    """Interface para extratores de dados"""
    
    def extract(self, page: Page) -> List[ExtractedItemData]:
        """Extrai dados da página"""
        ...

class DataProcessor(Protocol):
    """Interface para processadores de dados"""
    
    def process(self, data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Processa os dados extraídos"""
        ...

# ==========================================
# CONFIGURAÇÃO DE LOGGING
# ==========================================

class LoggerConfig:
    """Configurador de logger centralizado"""
    
    @staticmethod
    def setup_logger(name: str, level: LogLevel = LogLevel.INFO) -> logging.Logger:
        """Configura e retorna um logger"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.value))
        
        if not logger.handlers:
            # Apenas file handler, sem console handler para não mostrar logs na tela
            file_handler = logging.FileHandler("crawler.log", encoding='utf-8')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            
            logger.addHandler(file_handler)
        
        return logger

# ==========================================
# ESTRATÉGIAS DE EXPANSÃO DE PAINEL
# ==========================================

class PanelExpansionStrategy(ABC):
    """Classe base para estratégias de expansão de painéis"""
    
    def __init__(self, page: Page):
        self.page = page
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
    
    @abstractmethod
    def expand_panels(self) -> bool:
        """Executa a estratégia de expansão"""
        pass
    
    def _count_expanded_forms(self) -> int:
        """Conta formulários expandidos"""
        return self.page.locator("form.s-itemsAndServicesFieldGrid[aria-expanded='true']").count()
    
    def _count_total_forms(self) -> int:
        """Conta total de formulários"""
        return self.page.locator("form.s-itemsAndServicesFieldGrid").count()

class DefaultPanelExpansionStrategy(PanelExpansionStrategy):
    """Estratégia padrão de expansão usando seletores comuns"""
    
    def expand_panels(self) -> bool:
        try:
            total_forms = self._count_total_forms()
            expanded_forms = self._count_expanded_forms()
            
            self.logger.info(f"Formulários encontrados: {total_forms}, expandidos: {expanded_forms}")
            
            if expanded_forms == total_forms and total_forms > 0:
                self.logger.info("Todos os painéis já estão expandidos")
                return True
            
            success_count = 0
            forms = self.page.locator("form.s-itemsAndServicesFieldGrid")
            
            for i in range(total_forms):
                if self._expand_single_form(forms.nth(i), i):
                    success_count += 1
            
            final_expanded = self._count_expanded_forms()
            self.logger.info(f"Expansão concluída: {final_expanded}/{total_forms} painéis expandidos")
            
            return final_expanded > expanded_forms
            
        except Exception as e:
            self.logger.error(f"Erro na estratégia padrão: {str(e)}")
            return False
    
    def _expand_single_form(self, form, index: int) -> bool:
        """Expande um formulário específico"""
        try:
            if form.get_attribute("aria-expanded") == "true":
                return True
            
            expand_button = form.locator("div.s-expandSidebar.-clickable")
            if expand_button.count() > 0 and expand_button.is_visible():
                expand_button.click()
                
                # Aguarda expansão
                start_time = time.time()
                while form.get_attribute("aria-expanded") != "true":
                    if time.time() - start_time > 2:
                        break
                    time.sleep(0.2)
                
                return form.get_attribute("aria-expanded") == "true"
            
        except Exception as e:
            self.logger.warning(f"Erro ao expandir formulário {index}: {str(e)}")
        
        return False

class JavaScriptExpansionStrategy(PanelExpansionStrategy):
    """Estratégia de expansão via JavaScript"""
    
    def expand_panels(self) -> bool:
        try:
            self.logger.info("Executando expansão via JavaScript")
            
            result = self.page.evaluate("""
                () => {
                    let expanded = 0;
                    const forms = document.querySelectorAll('form.s-itemsAndServicesFieldGrid');
                    
                    forms.forEach((form, index) => {
                        if (form.getAttribute('aria-expanded') !== 'true') {
                            // Tenta múltiplas abordagens
                            const expandButton = form.querySelector('div.s-expandSidebar.-clickable');
                            if (expandButton) {
                                expandButton.click();
                                expanded++;
                            }
                            
                            const expandIcon = form.querySelector('img.sprite-collapsed_section');
                            if (expandIcon) {
                                expandIcon.click();
                            }
                            
                            // Força atributo se necessário
                            form.setAttribute('aria-expanded', 'true');
                        }
                    });
                    
                    return expanded;
                }
            """)
            
            self.logger.info(f"JavaScript expandiu {result} formulários")
            time.sleep(1)
            
            final_expanded = self._count_expanded_forms()
            return final_expanded > 0
            
        except Exception as e:
            self.logger.error(f"Erro na estratégia JavaScript: {str(e)}")
            return False

class IconClickExpansionStrategy(PanelExpansionStrategy):
    """Estratégia de expansão clicando em ícones"""
    
    def expand_panels(self) -> bool:
        try:
            icon_selectors = [
                "img.sprite-collapsed_section",
                "img.icon_cmpt.icon.icon_button",
                ".s-expandLines"
            ]
            
            clicks_performed = 0
            
            for selector in icon_selectors:
                icons = self.page.locator(selector).all()
                self.logger.info(f"Encontrados {len(icons)} ícones com seletor '{selector}'")
                
                for icon in icons:
                    try:
                        if icon.is_visible():
                            icon.click()
                            clicks_performed += 1
                            time.sleep(0.3)
                    except Exception as e:
                        self.logger.warning(f"Erro ao clicar no ícone: {str(e)}")
            
            self.logger.info(f"Total de cliques realizados: {clicks_performed}")
            time.sleep(1)
            
            return self._count_expanded_forms() > 0
            
        except Exception as e:
            self.logger.error(f"Erro na estratégia de ícones: {str(e)}")
            return False

# ==========================================
# FACTORY DE ESTRATÉGIAS
# ==========================================

class ExpansionStrategyFactory:
    """Factory para criar estratégias de expansão"""
    
    @staticmethod
    def create_strategies(page: Page) -> List[PanelExpansionStrategy]:
        """Cria lista de estratégias ordenadas por eficácia"""
        return [
            DefaultPanelExpansionStrategy(page),
            IconClickExpansionStrategy(page),
            JavaScriptExpansionStrategy(page)
        ]

# ==========================================
# ORQUESTRADOR DE EXPANSÃO
# ==========================================

class PanelExpansionOrchestrator:
    """Orquestra múltiplas estratégias de expansão"""
    
    def __init__(self, page: Page):
        self.page = page
        self.strategies = ExpansionStrategyFactory.create_strategies(page)
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
    
    def expand_all_panels(self) -> bool:
        """Executa estratégias até conseguir expandir os painéis"""
        initial_expanded = self._count_expanded_forms()
        total_forms = self._count_total_forms()
        
        self.logger.info(f"Iniciando expansão: {initial_expanded}/{total_forms} painéis expandidos")
        
        if initial_expanded == total_forms and total_forms > 0:
            return True
        
        for i, strategy in enumerate(self.strategies, 1):
            self.logger.info(f"Tentando estratégia {i}/{len(self.strategies)}: {strategy.__class__.__name__}")
            
            if strategy.expand_panels():
                current_expanded = self._count_expanded_forms()
                if current_expanded >= total_forms or current_expanded > initial_expanded:
                    self.logger.info(f"Estratégia {i} bem-sucedida: {current_expanded}/{total_forms} expandidos")
                    return True
        
        self.logger.warning("Todas as estratégias falharam")
        return False
    
    def _count_expanded_forms(self) -> int:
        return self.page.locator("form.s-itemsAndServicesFieldGrid[aria-expanded='true']").count()
    
    def _count_total_forms(self) -> int:
        return self.page.locator("form.s-itemsAndServicesFieldGrid").count()

# ==========================================
# EXTRATOR DE DADOS
# ==========================================

class ItemDataExtractor:
    """Extrator especializado em dados de itens"""
    
    def __init__(self, page: Page, quote_id: str = None):
        self.page = page
        self.quote_id = quote_id or "cotacao_geral"
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
        self.downloads_dir = Path("downloads_anexos")
        self.downloads_dir.mkdir(exist_ok=True)
        
        # Cria pasta específica para esta cotação
        self.quote_dir = self.downloads_dir / self._sanitize_folder_name(self.quote_id)
        self.quote_dir.mkdir(exist_ok=True)
        
        self.session = requests.Session()
        self.download_status_callback = None  # Callback para atualizar status de download
        self._setup_session_headers()
    
    def _sanitize_folder_name(self, folder_name: str) -> str:
        """Sanitiza nome da pasta removendo caracteres inválidos"""
        # Remove caracteres inválidos para nomes de pasta
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        sanitized = folder_name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove espaços extras e substitui por underscore
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        
        # Limita o tamanho do nome
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized
    
    def _setup_session_headers(self):
        """Configura headers para sessão de download"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin'
        })
    
    def extract_all_items(self) -> List[ExtractedItemData]:
        """Extrai dados de todos os itens da página"""
        try:
            # Primeiro verifica se existe botão "inserir resposta" e clica nele
            self._click_insert_response_button()
            
            # Aguarda um pouco para a página carregar após clicar
            time.sleep(2)
            
            # Copia cookies do navegador para a sessão de download
            self._copy_browser_cookies()
            
            # Depois expande os painéis
            orchestrator = PanelExpansionOrchestrator(self.page)
            orchestrator.expand_all_panels()
            
            # Conta itens válidos
            item_count = self._count_valid_items()
            self.logger.info(f"Extraindo dados de {item_count} itens")
            
            items = []
            for i in range(item_count):
                item_data = self._extract_single_item(i, item_count)
                if self._is_valid_item(item_data):
                    items.append(item_data)
            
            self.logger.info(f"Extração concluída: {len(items)} itens válidos")
            return items
            
        except Exception as e:
            self.logger.error(f"Erro na extração: {str(e)}")
            return []
    
    def _copy_browser_cookies(self):
        """Copia cookies do navegador para a sessão de download"""
        try:
            cookies = self.page.context.cookies()
            for cookie in cookies:
                self.session.cookies.set(
                    name=cookie['name'],
                    value=cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )
            self.logger.info(f"Copiados {len(cookies)} cookies para sessão de download")
        except Exception as e:
            self.logger.warning(f"Erro ao copiar cookies: {str(e)}")
    
    def _click_insert_response_button(self) -> bool:
        """Verifica se existe botão 'inserir resposta' e clica nele se encontrar"""
        try:
            # Diferentes seletores possíveis para o botão "inserir resposta"
            button_selectors = [
                "button:has-text('inserir resposta')",
                "button:has-text('Inserir Resposta')",
                "input[value*='inserir resposta']",
                "input[value*='Inserir Resposta']",
                "a:has-text('inserir resposta')",
                "a:has-text('Inserir Resposta')",
                ".button:has-text('inserir resposta')",
                ".btn:has-text('inserir resposta')"
            ]
            
            for selector in button_selectors:
                try:
                    button = self.page.locator(selector)
                    if button.count() > 0 and button.is_visible():
                        self.logger.info(f"Botão 'inserir resposta' encontrado com seletor: {selector}")
                        button.click()
                        self.logger.info("Botão 'inserir resposta' clicado com sucesso")
                        return True
                except Exception as e:
                    continue
            
            # Se não encontrou pelos seletores específicos, tenta busca mais genérica
            try:
                # Busca por qualquer elemento que contenha "inserir resposta" (case insensitive)
                generic_button = self.page.locator("*:has-text('inserir resposta')").first
                if generic_button.count() > 0 and generic_button.is_visible():
                    self.logger.info("Botão 'inserir resposta' encontrado com busca genérica")
                    generic_button.click()
                    self.logger.info("Botão 'inserir resposta' clicado com sucesso")
                    return True
            except Exception:
                pass
            
            self.logger.info("Botão 'inserir resposta' não encontrado na página")
            return False
            
        except Exception as e:
            self.logger.warning(f"Erro ao procurar botão 'inserir resposta': {str(e)}")
            return False
    
    def _count_valid_items(self) -> int:
        """Conta itens válidos na página"""
        return self.page.evaluate("""
            () => {
                const forms = Array.from(document.querySelectorAll('form.s-itemsAndServicesFieldGrid'));
                const validForms = forms.filter(form => {
                    const rect = form.getBoundingClientRect();
                    return rect.height > 10 && rect.width > 10;
                });
                return validForms.length;
            }
        """)
    
    def _extract_single_item(self, index: int, total: int) -> ExtractedItemData:
        """Extrai dados de um item específico"""
        try:
            form = self.page.locator("form.s-itemsAndServicesFieldGrid").nth(index)
            
            return ExtractedItemData(
                numero_item=f"{index + 1}/{total}",
                descricao=self._extract_field("div.s-description p.s-textField", index),
                descricao_estendida=self._extract_extended_description(index),
                quantidade=self._extract_field("div.s-quantity span.s-value", index),
                data_necessaria=self._extract_field("div.s-need_by_date p.s-textField", index),
                detalhes=self._extract_field("div.s-details li span", index),
                arquivos_anexados=self._extract_attachments(form)
            )
            
        except Exception as e:
            self.logger.warning(f"Erro ao extrair item {index + 1}: {str(e)}")
            return self._create_empty_item(index, total)
    
    def _extract_field(self, selector: str, index: int) -> str:
        """Extrai um campo específico usando seletor CSS"""
        try:
            elements = self.page.locator(selector)
            if elements.count() > index:
                return elements.nth(index).text_content().strip()
        except Exception as e:
            self.logger.warning(f"Erro ao extrair campo '{selector}': {str(e)}")
        return ""
    
    def _extract_extended_description(self, index: int) -> str:
        """Extrai e processa descrição estendida"""
        try:
            selector = "div.s-extended_description p.s-textField"
            raw_text = self._extract_field(selector, index)
            return self._extract_portuguese_text(raw_text)
        except Exception as e:
            self.logger.warning(f"Erro ao extrair descrição estendida: {str(e)}")
            return ""
    
    def _extract_portuguese_text(self, text: str) -> str:
        """Extrai texto em português de uma descrição multilíngue"""
        if not text:
            return ""
        
        # Padrões para detectar texto em português
        patterns = [
            re.compile(r'\*{3,}\s*PT\s*(.*?)\s*\*{3,}', re.DOTALL),
            re.compile(r'PT \|\|(.*?)(?:\*{3,}|EN \|\||$)', re.DOTALL),
            re.compile(r'(?:PT:|Português:)\s*(.*?)(?:\*{3,}|EN:|English:|$)', re.DOTALL | re.IGNORECASE),
            re.compile(r'\[PT\](.*?)(?:\[EN\]|$)', re.DOTALL | re.IGNORECASE)
        ]
        
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        
        # Se não encontrar padrão específico, verifica características do português
        portuguese_indicators = ["conforme", "descrição", "fornecimento", "material", "especificação"]
        if any(indicator in text.lower() for indicator in portuguese_indicators):
            return text
        
        return text
    
    def _extract_attachments(self, form) -> str:
        """Extrai e baixa arquivos anexados, retornando caminhos locais"""
        try:
            attachment_links = form.locator("a[href*='attachment'], a[href*='download'], a[href*='file']").all()
            
            if not attachment_links:
                return ""
            
            # Atualiza status se callback disponível
            if self.download_status_callback:
                self.download_status_callback(f"Encontrados {len(attachment_links)} anexos para baixar")
            
            downloaded_files = []
            
            for i, link in enumerate(attachment_links, 1):
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    # Obter nome do arquivo
                    link_text = link.text_content().strip()
                    
                    # Atualiza status do download atual
                    if self.download_status_callback:
                        self.download_status_callback(f"Baixando anexo {i}/{len(attachment_links)}: {link_text}")
                    
                    # Se o href é relativo, torna absoluto
                    if href.startswith('/'):
                        full_url = urljoin(self.page.url, href)
                    else:
                        full_url = href
                    
                    # Baixa o arquivo na pasta da cotação
                    local_path = self._download_file(full_url, link_text)
                    
                    if local_path:
                        downloaded_files.append(str(local_path))
                        self.logger.info(f"Arquivo baixado: {link_text} -> {local_path}")
                        if self.download_status_callback:
                            self.download_status_callback(f"✓ Anexo {i} baixado: {local_path.name}")
                    else:
                        # Se não conseguiu baixar, mantém informação do link
                        downloaded_files.append(f"ERRO_DOWNLOAD: {link_text}")
                        if self.download_status_callback:
                            self.download_status_callback(f"✗ Erro ao baixar anexo {i}: {link_text}")
                        
                except Exception as e:
                    self.logger.warning(f"Erro ao processar anexo: {str(e)}")
                    if self.download_status_callback:
                        self.download_status_callback(f"✗ Erro no anexo {i}: {str(e)}")
                    continue
            
            if self.download_status_callback and downloaded_files:
                self.download_status_callback(f"Downloads concluídos: {len([f for f in downloaded_files if not f.startswith('ERRO_DOWNLOAD')])}/{len(attachment_links)}")
            
            return "; ".join(downloaded_files)
            
        except Exception as e:
            self.logger.warning(f"Erro ao extrair anexos: {str(e)}")
            return ""
    
    def _download_file(self, url: str, suggested_name: str) -> Optional[Path]:
        """Baixa um arquivo da URL e retorna o caminho local"""
        try:
            # Limita tempo de download
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Determina nome do arquivo
            filename = self._get_safe_filename(url, suggested_name, response)
            
            # Cria nome único se arquivo já existe na pasta da cotação
            file_path = self.quote_dir / filename
            counter = 1
            original_stem = file_path.stem
            original_suffix = file_path.suffix
            
            while file_path.exists():
                file_path = self.quote_dir / f"{original_stem}_{counter}{original_suffix}"
                counter += 1
            
            # Baixa o arquivo diretamente na pasta da cotação
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Verifica se o arquivo foi criado e tem conteúdo
            if file_path.exists() and file_path.stat().st_size > 0:
                return file_path
            else:
                self.logger.warning(f"Arquivo baixado está vazio: {file_path}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Erro de rede ao baixar {url}: {str(e)}")
            return None
        except Exception as e:
            self.logger.warning(f"Erro ao baixar arquivo {url}: {str(e)}")
            return None
    
    def _get_safe_filename(self, url: str, suggested_name: str, response) -> str:
        """Gera nome de arquivo seguro"""
        # Tenta obter nome do cabeçalho Content-Disposition
        content_disposition = response.headers.get('content-disposition', '')
        if 'filename=' in content_disposition:
            try:
                filename = content_disposition.split('filename=')[1].strip('"')
                if filename and self._is_safe_filename(filename):
                    return filename
            except:
                pass
        
        # Usa nome sugerido se válido
        if suggested_name and self._is_safe_filename(suggested_name):
            # Adiciona extensão se não tiver
            if '.' not in suggested_name:
                content_type = response.headers.get('content-type', '')
                extension = self._get_extension_from_content_type(content_type)
                if extension:
                    suggested_name += extension
            return suggested_name
        
        # Tenta extrair nome da URL
        parsed_url = urlparse(url)
        url_filename = Path(parsed_url.path).name
        if url_filename and self._is_safe_filename(url_filename):
            return url_filename
        
        # Gera nome baseado no hash da URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        content_type = response.headers.get('content-type', '')
        extension = self._get_extension_from_content_type(content_type)
        
        return f"anexo_{url_hash}{extension}"
    
    def _is_safe_filename(self, filename: str) -> bool:
        """Verifica se o nome do arquivo é seguro"""
        if not filename:
            return False
        
        # Remove caracteres perigosos
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        return not any(char in filename for char in dangerous_chars)
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Retorna extensão baseada no Content-Type"""
        content_type_map = {
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'text/plain': '.txt',
            'application/zip': '.zip',
            'application/x-rar-compressed': '.rar'
        }
        
        return content_type_map.get(content_type.lower(), '.dat')
    
    def _is_valid_item(self, item: ExtractedItemData) -> bool:
        """Verifica se o item tem dados válidos"""
        return bool(item["descricao"] or item["quantidade"] or item["descricao_estendida"])
    
    def _create_empty_item(self, index: int, total: int) -> ExtractedItemData:
        """Cria item vazio em caso de erro"""
        return ExtractedItemData(
            numero_item=f"{index + 1}/{total}",
            descricao="",
            descricao_estendida="",
            quantidade="",
            data_necessaria="",
            detalhes="",
            arquivos_anexados=""
        )

# ==========================================
# PROCESSADOR DE DUPLICATAS
# ==========================================

class DuplicateProcessor:
    """Processador especializado em remoção de duplicatas"""
    
    def __init__(self):
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
    
    def remove_duplicates(self, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove duplicatas dos dados extraídos"""
        if not items:
            return items
        
        unique_items = []
        seen_signatures = set()
        duplicates_removed = 0
        
        for i, item in enumerate(items):
            signature = self._create_item_signature(item)
            
            if self._is_empty_item(signature):
                unique_items.append(item)
                continue
            
            if signature in seen_signatures:
                duplicates_removed += 1
                continue
            
            seen_signatures.add(signature)
            unique_items.append(item)
        
        return unique_items
    
    def _create_item_signature(self, item: Dict[str, str]) -> tuple:
        """Cria assinatura única para o item"""
        primary_fields = ["descricao", "quantidade", "data_necessaria"]
        
        signature_parts = []
        for field in primary_fields:
            value = item.get(field, "").strip()
            if field == "descricao":
                value = self._extract_main_code(value)
            signature_parts.append(self._normalize_text(value))
        
        return tuple(signature_parts)
    
    def _extract_main_code(self, description: str) -> str:
        """Extrai código principal da descrição"""
        if not description:
            return ""
        
        # Procura padrão como "15422864 || PASTILHA TORN"
        match = re.search(r'(\d{8})\s*\|\|', description)
        if match:
            return match.group(1)
        
        # Fallback para primeiras palavras
        words = description.strip().split()
        return " ".join(words[:3]) if len(words) >= 3 else description
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto para comparação"""
        if not text:
            return ""
        
        text = text.strip().lower()
        text = re.sub(r'[;,\.\|\-\s]+', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _is_empty_item(self, signature: tuple) -> bool:
        """Verifica se o item está vazio"""
        return all(not part for part in signature)
    
    def _get_item_summary(self, item: Dict[str, str]) -> str:
        """Gera resumo do item para log"""
        desc = item.get("descricao", "")[:50]
        qty = item.get("quantidade", "")
        return f"Desc: '{desc}...', Qty: '{qty}'"

# ==========================================
# EXPORTADOR DE DADOS
# ==========================================

class DataExporter:
    """Responsável por exportar dados para diferentes formatos"""
    
    def __init__(self):
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
        self.duplicate_processor = DuplicateProcessor()
    
    def export_to_csv(self, data: List[Dict[str, str]], filename: str) -> bool:
        """Exporta dados para CSV com remoção automática de duplicatas"""
        if not data:
            return False
        
        try:
            # Remove duplicatas
            filtered_data = self.duplicate_processor.remove_duplicates(data)
            
            # Exporta para CSV
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                if filtered_data:
                    fieldnames = filtered_data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(filtered_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao exportar CSV: {str(e)}")
            return False
    
    def export_to_excel(self, data: List[Dict[str, str]], filename: str) -> bool:
        """Exporta dados para Excel com largura automática das colunas"""
        if not data:
            return False
        
        if not EXCEL_SUPPORT:
            self.logger.warning("Bibliotecas Excel não instaladas. Salvando apenas CSV.")
            return False
        
        try:
            # Remove duplicatas
            filtered_data = self.duplicate_processor.remove_duplicates(data)
            
            if not filtered_data:
                return False
            
            # Converte para DataFrame
            df = pd.DataFrame(filtered_data)
            
            # Cria o arquivo Excel
            excel_filename = filename.replace('.csv', '.xlsx')
            
            with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Cotações', index=False)
                
                # Obtém a planilha para ajuste de colunas
                worksheet = writer.sheets['Cotações']
                
                # Ajusta largura das colunas baseado no conteúdo
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            # Considera o conteúdo da célula
                            if cell.value:
                                cell_length = len(str(cell.value))
                                if cell_length > max_length:
                                    max_length = cell_length
                        except:
                            pass
                    
                    # Define largura mínima e máxima
                    adjusted_width = min(max(max_length + 2, 10), 80)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            self.logger.info(f"Arquivo Excel criado: {excel_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao exportar Excel: {str(e)}")
            return False
    
    def export_data(self, data: List[Dict[str, str]], base_filename: str) -> bool:
        """Exporta dados em múltiplos formatos (CSV e Excel se disponível)"""
        if not data:
            return False
        
        try:
            success_csv = self.export_to_csv(data, base_filename)
            
            # Tenta exportar para Excel também
            success_excel = False
            if EXCEL_SUPPORT:
                success_excel = self.export_to_excel(data, base_filename)
            
            # Retorna True se pelo menos um formato foi exportado com sucesso
            return success_csv or success_excel
            
        except Exception as e:
            self.logger.error(f"Erro na exportação: {str(e)}")
            return False
    
    def get_export_summary(self, original_count: int, final_count: int, filename: str) -> str:
        """Gera resumo da exportação"""
        duplicates = original_count - final_count
        
        # Verifica quais arquivos foram criados
        csv_file = filename
        excel_file = filename.replace('.csv', '.xlsx')
        
        files_created = []
        if os.path.exists(csv_file):
            files_created.append("CSV")
        if os.path.exists(excel_file):
            files_created.append("Excel")
        
        files_text = " e ".join(files_created) if files_created else "CSV"
        
        if duplicates > 0:
            return (f"Exportação concluída!\n\n"
                   f"• {original_count} itens extraídos\n"
                   f"• {duplicates} duplicatas removidas\n"
                   f"• {final_count} itens únicos salvos\n"
                   f"• Formatos: {files_text}")
        else:
            return (f"Exportação concluída!\n\n"
                   f"• {final_count} itens únicos salvos\n"
                   f"• Formatos: {files_text}\n"
                   f"• Nenhuma duplicata detectada")

# ==========================================
# AUTENTICADOR
# ==========================================

class AuthenticationService:
    """Serviço de autenticação na plataforma"""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
    
    def authenticate(self, page: Page, username: str, password: str) -> bool:
        """Realiza autenticação na plataforma"""
        try:
            # Navega para página de login
            login_url = f"{self.config.base_url}{self.config.login_path}"
            self.logger.info(f"Navegando para página de login: {login_url}")
            
            page.goto(login_url, wait_until='networkidle', timeout=30000)
            time.sleep(3)
            
            # Verifica se está na página de login
            if not self._is_login_page(page):
                self.logger.error("Não foi possível acessar a página de login")
                self.logger.info(f"URL atual: {page.url}")
                return False
            
            self.logger.info("✅ Página de login carregada com sucesso")
            
            # Preenche credenciais
            self.logger.info("Preenchendo credenciais...")
            self._fill_credentials(page, username, password)
            
            # Submete formulário
            self.logger.info("Submetendo formulário de login...")
            self._submit_login_form(page)
            
            # Verifica sucesso
            return self._verify_authentication(page)
            
        except Exception as e:
            self.logger.error(f"Erro na autenticação: {str(e)}")
            return False
    
    def _is_login_page(self, page: Page) -> bool:
        """Verifica se está na página de login"""
        return ("supplier_login" in page.url or 
                page.get_by_role("button", name="Signin").count() > 0)
    
    def _fill_credentials(self, page: Page, username: str, password: str) -> None:
        """Preenche as credenciais de login"""
        page.get_by_role("textbox", name="Nome de usuário ou endereço").fill(username)
        page.get_by_role("textbox", name="Senha").fill(password)
    
    def _submit_login_form(self, page: Page) -> None:
        """Submete o formulário de login"""
        page.get_by_role("button", name="Signin").click()
        time.sleep(3)
    
    def _verify_authentication(self, page: Page) -> bool:
        """Verifica se a autenticação foi bem-sucedida"""
        try:
            # Verifica se ainda está na página de login
            if "supplier_login" in page.url:
                self.logger.error("Login falhou - ainda na página de login")
                return False
            
            # Aguarda um pouco para garantir que a página carregou
            time.sleep(3)
            
            # Log da URL atual para debug
            current_url = page.url
            self.logger.info(f"URL atual após login: {current_url}")
            
            # Verifica se está em uma página de erro ou redirecionamento
            if "error" in current_url.lower() or "login" in current_url.lower():
                self.logger.error(f"Login falhou - redirecionado para: {current_url}")
                return False
            
            # Tenta acessar página de cotações
            quotes_url = f"{self.config.base_url}{self.config.quotes_path}"
            self.logger.info(f"Tentando acessar: {quotes_url}")
            
            try:
                page.goto(quotes_url, wait_until='networkidle', timeout=30000)
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"Erro ao navegar para página de cotações: {str(e)}")
                return False
            
            # Verifica se conseguiu acessar a página
            final_url = page.url
            self.logger.info(f"URL final após navegação: {final_url}")
            
            # Verifica se está na página correta
            success = "quote_supplier_land" in final_url
            
            if not success:
                self.logger.error(f"Falha ao acessar página de cotações. URL final: {final_url}")
                
                # Tenta verificar se há mensagem de erro na página
                try:
                    error_elements = page.locator("text=error, text=Error, text=erro, text=Erro").all()
                    if error_elements:
                        for elem in error_elements[:3]:  # Primeiros 3 elementos de erro
                            error_text = elem.text_content()
                            if error_text:
                                self.logger.error(f"Erro encontrado na página: {error_text}")
                except:
                    pass
                
                return False
            
            self.logger.info("✅ Autenticação bem-sucedida - página de cotações acessada")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na verificação de autenticação: {str(e)}")
            return False

# ==========================================
# CRAWLER PRINCIPAL
# ==========================================

class QuoteCrawler:
    """Crawler principal para extração de cotações"""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
        self.auth_service = AuthenticationService(config)
        self.data_exporter = DataExporter()
        self.status_callback = None  # Callback para atualizar status na UI
    
    def _update_status(self, message: str):
        """Atualiza status na interface se callback estiver definido"""
        if self.status_callback:
            self.status_callback(message)
    
    def crawl_quotes(self, username: str, password: str, target_date: str, resposta_filter: str = "0") -> bool:
        """Executa o processo completo de crawling"""
        try:
            # Configura o filtro de resposta
            self.config.resposta_filter = resposta_filter
            
            self._update_status("🌐 Iniciando browser...")
            
            with sync_playwright() as playwright:
                browser = self._create_browser(playwright)
                page = self._create_page(browser)
                
                # Autenticação
                self._update_status("🔐 Fazendo login...")
                if not self.auth_service.authenticate(page, username, password):
                    self._update_status("❌ Falha no login - Credenciais inválidas")
                    return False
                
                self._update_status("📋 Buscando cotações...")
                
                # Extração de cotações
                quotes_data = self._extract_quotes_for_date(page, target_date)
                
                # Se extraiu qualquer dado, considera sucesso
                if quotes_data and len(quotes_data) > 0:
                    self._update_status("💾 Salvando dados...")
                    
                    # Exportação
                    filename = self._generate_filename()
                    original_count = len(quotes_data)
                    success = self.data_exporter.export_data(quotes_data, filename)
                    
                    if success:
                        # Verifica se o arquivo foi criado e tem conteúdo
                        try:
                            with open(filename, 'r', encoding='utf-8') as f:
                                final_count = sum(1 for line in f) - 1  # -1 para descontar o cabeçalho
                            
                            # Se tem pelo menos 1 linha de dados, é sucesso
                            if final_count > 0:
                                self._update_status(f"✅ {final_count} itens salvos!")
                                return True
                            else:
                                self.logger.error("Arquivo CSV criado mas está vazio!")
                                self._update_status("❌ Nenhum dado extraído")
                                return False
                        except Exception:
                            # Se não conseguir ler o arquivo, assume que deu erro
                            self._update_status("❌ Erro ao salvar arquivo")
                            return False
                    else:
                        self._update_status("❌ Erro na exportação")
                        return False
                else:
                    # Nenhum dado extraído - pode ser que não há cotações para a data
                    if resposta_filter == "0":
                        self._update_status("❌ Nenhuma cotação com resposta = 0 encontrada")
                    elif resposta_filter == "1":
                        self._update_status("❌ Nenhuma cotação com resposta ≠ 0 encontrada")
                    else:
                        self._update_status("❌ Nenhuma cotação encontrada")
                    return False
                
        except Exception as e:
            self.logger.error(f"Erro no crawling: {str(e)}")
            self._update_status("❌ Erro inesperado")
            return False
    
    def _create_browser(self, playwright):
        """Cria instância do browser"""
        launch_args = [
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding'
        ]
        
        # Configurações especiais para executável portátil
        if getattr(sys, 'frozen', False):
            # Rodando como executável PyInstaller
            launch_args.extend([
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-plugins'
            ])
            
            # Tenta diferentes abordagens para encontrar o browser
            exe_dir = get_executable_dir()
            possible_browser_paths = [
                exe_dir / "ms-playwright" / "chromium-1169" / "chrome-win" / "chrome.exe",
                exe_dir / "_internal" / "ms-playwright" / "chromium-1169" / "chrome-win" / "chrome.exe",
                exe_dir / "playwright" / "chromium-1169" / "chrome-win" / "chrome.exe"
            ]
            
            # Procura por um executável do Chrome válido
            for browser_path in possible_browser_paths:
                if browser_path.exists():
                    self.logger.info(f"Usando browser em: {browser_path}")
                    return playwright.chromium.launch(
                        headless=self.config.headless,
                        args=launch_args,
                        executable_path=str(browser_path)
                    )
            
            # Se não encontrou, tenta sem caminho específico
            self.logger.warning("Browser não encontrado nos caminhos esperados, tentando padrão")
        
        return playwright.chromium.launch(
            headless=self.config.headless,
            args=launch_args
        )
    
    def _create_page(self, browser):
        """Cria página com configurações otimizadas"""
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            timezone_id='America/Sao_Paulo',
            locale='pt-BR',
            ignore_https_errors=True
        )
        
        context.set_default_timeout(self.config.timeout_ms)
        page = context.new_page()
        page.set_extra_http_headers({'DNT': '1'})
        
        return page
    
    def _extract_quotes_for_date(self, page: Page, target_date: str) -> List[Dict[str, str]]:
        """Extrai cotações para data específica"""
        quotes_url = f"{self.config.base_url}{self.config.quotes_path}"
        page.goto(quotes_url)
        
        # Configura visualização
        self._configure_page_view(page)
        
        # Detecta posição da coluna resposta
        resposta_column_index = self._find_resposta_column_index(page)
        
        # Extrai cotações
        return self._process_quote_rows(page, target_date, resposta_column_index)
    
    def _configure_page_view(self, page: Page) -> None:
        """Configura visualização da página (items per page, etc.)"""
        try:
            # Tenta configurar para mostrar mais itens por página
            items_selector = f"text='{self.config.items_per_page}'"
            if page.locator(items_selector).count() > 0:
                page.locator(items_selector).click()
                time.sleep(1)
        except Exception as e:
            self.logger.warning(f"Não foi possível configurar visualização: {str(e)}")
    
    def _process_quote_rows(self, page: Page, target_date: str, resposta_column_index: int) -> List[Dict[str, str]]:
        """Processa as linhas de cotações na tabela"""
        all_quotes_data = []
        eventos_processados = set()
        
        quotes_processed = 0
        quotes_found_for_date = 0
        quotes_filtered_by_response = 0  # Contador para cotações filtradas por resposta
        total_rows_checked = 0
        
        # Log da data que estamos procurando
        self.logger.info(f"Procurando cotações para a data: '{target_date}'")
        
        # Log do filtro aplicado
        if self.config.resposta_filter == "0":
            self.logger.info(f"Filtrando apenas cotações com resposta = 0 (coluna {resposta_column_index})")
        elif self.config.resposta_filter == "1":
            self.logger.info(f"Filtrando apenas cotações com resposta ≠ 0 (coluna {resposta_column_index})")
        else:
            self.logger.info(f"Processando todas as cotações (coluna {resposta_column_index})")
        
        # Configura timeout menor para detectar problemas rapidamente
        page.set_default_timeout(10000)  # 10 segundos em vez de 60
        
        # Loop principal - recarrega a página a cada iteração para garantir estado consistente
        while True:  # Remove limitação - processa até não encontrar mais cotações
            try:
                # Recarrega a tabela para garantir estado fresco
                if quotes_processed > 0:
                    quotes_url = f"{self.config.base_url}{self.config.quotes_path}"
                    page.goto(quotes_url)
                    time.sleep(2)
                
                # Aguarda a tabela carregar
                page.wait_for_selector("table tbody tr", timeout=10000)
                rows = page.locator("table tbody tr").all()
                
                if not rows:
                    self.logger.warning("Nenhuma linha encontrada na tabela")
                    break
                
                self.logger.info(f"Encontradas {len(rows)} linhas na tabela para verificar")
                
                # Procura uma cotação não processada ainda
                cotacao_encontrada = False
                datas_encontradas = []  # Para log das datas que encontramos
                
                for i, row in enumerate(rows):
                    total_rows_checked += 1
                    
                    try:
                        # Verifica se a linha existe e está visível com timeout reduzido
                        if not row.is_visible(timeout=2000):
                            continue
                        
                        # Extrai dados da cotação com timeout reduzido
                        quote_data = self._extract_quote_info_safe(row, resposta_column_index)
                        if not quote_data:
                            # Verifica se foi filtrado por resposta ou erro
                            try:
                                cells = row.locator("td")
                                if cells.count() >= resposta_column_index + 1:
                                    resposta_value = cells.nth(resposta_column_index).text_content(timeout=1000).strip()
                                    if resposta_value:
                                        if self.config.resposta_filter == "0" and resposta_value != "0":
                                            quotes_filtered_by_response += 1
                                        elif self.config.resposta_filter == "1" and resposta_value == "0":
                                            quotes_filtered_by_response += 1
                            except:
                                pass
                            self.logger.warning(f"Não foi possível extrair dados da linha {i+1}")
                            continue
                        
                        # Log da data encontrada para diagnóstico
                        data_inicial = quote_data["data_inicial"]
                        datas_encontradas.append(data_inicial)
                        self.logger.info(f"Linha {i+1}: Evento '{quote_data['evento']}', Data inicial: '{data_inicial}', Resposta: '{quote_data['resposta']}'")
                        
                        # Verifica se a data corresponde usando múltiplas abordagens
                        data_match = self._compare_dates(target_date, data_inicial)
                        
                        if not data_match:
                            self.logger.info(f"Data '{data_inicial}' não corresponde à data alvo '{target_date}'")
                            continue
                        
                        self.logger.info(f"✓ Data correspondente encontrada: '{data_inicial}' para evento '{quote_data['evento']}'")
                        
                        # Verifica se já processamos esta cotação
                        if quote_data['evento'] in eventos_processados:
                            self.logger.info(f"Cotação '{quote_data['evento']}' já foi processada, pulando...")
                            continue
                        
                        quotes_found_for_date += 1
                        cotacao_encontrada = True
                        
                        # Processa esta cotação
                        sucesso = self._processar_cotacao_individual(page, row, quote_data, all_quotes_data)
                        eventos_processados.add(quote_data['evento'])
                        
                        if sucesso:
                            quotes_processed += 1
                        else:
                            # Marca como processada mesmo se houve erro, para evitar loop infinito
                            quotes_processed += 1
                        
                        # Sai do loop for para recarregar a página
                        break
                        
                    except Exception as row_error:
                        self.logger.warning(f"Erro ao processar linha {i+1}: {str(row_error)}")
                        continue
                
                # Log das datas encontradas nesta iteração
                if datas_encontradas:
                    self.logger.info(f"Datas encontradas nesta página: {datas_encontradas}")
                else:
                    self.logger.warning("Nenhuma data foi extraída das linhas da tabela")
                
                # Se não encontrou nenhuma cotação nova, para o processamento
                if not cotacao_encontrada:
                    self.logger.info("Nenhuma nova cotação encontrada, finalizando processamento")
                    break
                    
            except Exception as page_error:
                self.logger.error(f"Erro ao recarregar página: {str(page_error)}")
                break
        
        # Restaura timeout original
        page.set_default_timeout(self.config.timeout_ms)
        
        # Log final detalhado
        self.logger.info(f"Processamento finalizado:")
        self.logger.info(f"- Total de linhas verificadas: {total_rows_checked}")
        self.logger.info(f"- Cotações filtradas por resposta ≠ 0: {quotes_filtered_by_response}")
        self.logger.info(f"- Cotações encontradas para a data '{target_date}' (resposta = 0): {quotes_found_for_date}")
        self.logger.info(f"- Cotações processadas com sucesso: {quotes_processed}")
        self.logger.info(f"- Total de itens extraídos: {len(all_quotes_data)}")
        
        # Log final apenas se não encontrou cotações
        if quotes_found_for_date == 0:
            if quotes_filtered_by_response > 0:
                if self.config.resposta_filter == "0":
                    self.logger.warning(f"NENHUMA cotação encontrada para a data '{target_date}' com resposta = 0")
                    self.logger.info(f"Encontradas {quotes_filtered_by_response} cotações com resposta ≠ 0 que foram filtradas")
                    self._update_status(f"⚠️ Nenhuma cotação com resposta = 0 encontrada para {target_date}")
                    self._update_status(f"📊 {quotes_filtered_by_response} cotações com resposta ≠ 0 foram filtradas")
                elif self.config.resposta_filter == "1":
                    self.logger.warning(f"NENHUMA cotação encontrada para a data '{target_date}' com resposta ≠ 0")
                    self.logger.info(f"Encontradas {quotes_filtered_by_response} cotações com resposta = 0 que foram filtradas")
                    self._update_status(f"⚠️ Nenhuma cotação com resposta ≠ 0 encontrada para {target_date}")
                    self._update_status(f"📊 {quotes_filtered_by_response} cotações com resposta = 0 foram filtradas")
                else:
                    self.logger.warning(f"NENHUMA cotação encontrada para a data '{target_date}'")
                    self._update_status(f"⚠️ Nenhuma cotação encontrada para {target_date}")
            else:
                self.logger.warning(f"NENHUMA cotação encontrada para a data '{target_date}'")
                self._update_status(f"❌ Nenhuma cotação encontrada para {target_date}")
        else:
            if self.config.resposta_filter == "0":
                self._update_status(f"✅ {quotes_found_for_date} cotações com resposta = 0 encontradas")
            elif self.config.resposta_filter == "1":
                self._update_status(f"✅ {quotes_found_for_date} cotações com resposta ≠ 0 encontradas")
            else:
                self._update_status(f"✅ {quotes_found_for_date} cotações encontradas")
        
        return all_quotes_data
    
    def _compare_dates(self, target_date: str, page_date: str) -> bool:
        """Compara datas usando múltiplas abordagens para máxima compatibilidade"""
        if not target_date or not page_date:
            return False
        
        # Normaliza as strings
        target_clean = target_date.strip()
        page_clean = page_date.strip()
        
        # Abordagem 1: Comparação direta
        if target_clean == page_clean:
            return True
        
        # Abordagem 2: Substring (método original)
        if target_clean in page_clean:
            return True
        
        # Abordagem 3: Converte ambas para formato padrão DD/MM/YY
        try:
            target_normalized = self._normalize_date_format(target_clean)
            page_normalized = self._normalize_date_format(page_clean)
            
            if target_normalized and page_normalized:
                return target_normalized == page_normalized
        except Exception as e:
            self.logger.warning(f"Erro ao normalizar datas: {str(e)}")
        
        # Abordagem 4: Extrai apenas números e compara
        target_numbers = re.findall(r'\d+', target_clean)
        page_numbers = re.findall(r'\d+', page_clean)
        
        if len(target_numbers) >= 3 and len(page_numbers) >= 3:
            # Compara dia, mês e ano
            target_day, target_month, target_year = target_numbers[:3]
            page_day, page_month, page_year = page_numbers[:3]
            
            # Normaliza anos (2 dígitos vs 4 dígitos)
            if len(target_year) == 2:
                target_year = "20" + target_year
            if len(page_year) == 2:
                page_year = "20" + page_year
            
            return (target_day == page_day and 
                    target_month == page_month and 
                    target_year == page_year)
        
        return False
    
    def _normalize_date_format(self, date_str: str) -> Optional[str]:
        """Normaliza formato de data para DD/MM/YY"""
        if not date_str:
            return None
        
        # Remove espaços e caracteres especiais
        clean_date = re.sub(r'[^\d/]', '', date_str)
        
        # Padrões suportados
        patterns = [
            r'^(\d{1,2})/(\d{1,2})/(\d{2})$',        # DD/MM/YY
            r'^(\d{1,2})/(\d{1,2})/(\d{4})$',        # DD/MM/YYYY
            r'^(\d{1,2})-(\d{1,2})-(\d{2})$',        # DD-MM-YY
            r'^(\d{1,2})-(\d{1,2})-(\d{4})$',        # DD-MM-YYYY
        ]
        
        for pattern in patterns:
            match = re.match(pattern, clean_date)
            if match:
                day, month, year = match.groups()
                
                # Normaliza para 2 dígitos
                day = day.zfill(2)
                month = month.zfill(2)
                
                # Converte ano para 2 dígitos se necessário
                if len(year) == 4:
                    year = year[-2:]
                
                return f"{day}/{month}/{year}"
        
        return None
    
    def _extract_quote_info_safe(self, row, resposta_column_index: int) -> Optional[QuoteData]:
        """Extrai informações da cotação com tratamento de erro robusto"""
        try:
            cells = row.locator("td")
            total_cells = cells.count()
            
            self.logger.info(f"Extraindo dados da linha - Total de células: {total_cells}, Coluna resposta: {resposta_column_index}")
            
            # Verifica se há células suficientes (precisamos pelo menos da posição da coluna resposta + 1)
            min_cells = max(5, resposta_column_index + 1)
            if total_cells < min_cells:
                self.logger.warning(f"Células insuficientes: {total_cells} < {min_cells}")
                return None
            
            # Extrai com timeout reduzido
            evento_link = cells.nth(0).locator("a")
            if evento_link.count() == 0:
                self.logger.warning("Link do evento não encontrado")
                return None
            
            evento = evento_link.text_content(timeout=3000).strip()
            nome_evento = cells.nth(1).text_content(timeout=3000).strip()
            data_inicial = cells.nth(2).text_content(timeout=3000).strip()
            data_final = cells.nth(3).text_content(timeout=3000).strip()
            
            # Extrai campo resposta usando o índice detectado
            resposta = cells.nth(resposta_column_index).text_content(timeout=3000).strip()
            
            self.logger.info(f"Dados extraídos - Evento: '{evento}', Data: '{data_inicial}', Resposta: '{resposta}'")
            
            # Aplica filtro baseado na configuração
            if self.config.resposta_filter == "0":
                # Filtra apenas cotações com resposta = 0
                if resposta != "0":
                    self.logger.info(f"Cotação '{evento}' ignorada - resposta = '{resposta}' (não é 0)")
                    return None
            elif self.config.resposta_filter == "1":
                # Filtra apenas cotações com resposta ≠ 0
                if resposta == "0":
                    self.logger.info(f"Cotação '{evento}' ignorada - resposta = '{resposta}' (é 0)")
                    return None
            # Se resposta_filter == "todas", não filtra nada
            
            self.logger.info(f"Cotação '{evento}' aceita - resposta = '{resposta}'")
            
            return QuoteData(
                evento=evento,
                nome_evento=nome_evento,
                data_inicial=data_inicial,
                data_final=data_final,
                resposta=resposta
            )
            
        except Exception as e:
            self.logger.warning(f"Erro ao extrair dados da linha: {str(e)}")
            return None
    
    def _extract_quote_info(self, row) -> QuoteData:
        """Extrai informações básicas da cotação da linha da tabela (método original para compatibilidade)"""
        cells = row.locator("td")
        
        return QuoteData(
            evento=cells.nth(0).locator("a").text_content().strip(),
            nome_evento=cells.nth(1).text_content().strip(),
            data_inicial=cells.nth(2).text_content().strip(),
            data_final=cells.nth(3).text_content().strip(),
            resposta=cells.nth(6).text_content().strip()
        )
    
    def _cotacao_ja_processada(self, evento: str, dados_processados: List[Dict[str, str]]) -> bool:
        """Verifica se uma cotação já foi processada"""
        return any(item.get("evento") == evento for item in dados_processados)
    
    def _processar_cotacao_individual(self, page: Page, row, quote_data: QuoteData, all_quotes_data: List[Dict[str, str]]) -> bool:
        """Processa uma cotação individual"""
        try:
            # Atualiza status
            self._update_status(f"📄 Processando cotação {quote_data['evento']}...")
            
            # Navega para a cotação
            link = row.locator("td").nth(0).locator("a")
            
            link.click(timeout=5000)
            time.sleep(3)  # Aguarda um pouco mais para garantir carregamento
            
            # Verifica se navegou corretamente
            current_url = page.url
            if "quote_supplier_land" in current_url:
                return False
            
            # Atualiza status
            self._update_status(f"🔍 Extraindo itens da cotação {quote_data['evento']}...")
            
            # Extrai itens da cotação
            extractor = ItemDataExtractor(page, quote_data['evento'])
            
            # Configura callback para atualizar status durante downloads
            def download_status_callback(message):
                self._update_status(f"📎 {message}")
            
            extractor.download_status_callback = download_status_callback
            items = extractor.extract_all_items()
            
            if items:
                # Combina dados da cotação com dados dos itens
                quote_items = self._combine_quote_and_items_data(quote_data, items)
                all_quotes_data.extend(quote_items)
                
                self._update_status(f"✅ {len(items)} itens extraídos da cotação {quote_data['evento']}")
                return True
            else:
                self._update_status(f"⚠️ Nenhum item encontrado na cotação {quote_data['evento']}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao processar cotação {quote_data['evento']}: {str(e)}")
            self._update_status(f"❌ Erro na cotação {quote_data['evento']}")
            return False
    
    def _combine_quote_and_items_data(self, quote_data: QuoteData, items: List[ExtractedItemData]) -> List[Dict[str, str]]:
        """Combina dados da cotação com dados dos itens"""
        combined_data = []
        
        for item in items:
            combined_item = {
                **quote_data,  # Dados da cotação
                **item         # Dados do item
            }
            combined_data.append(combined_item)
        
        return combined_data
    
    def _generate_filename(self) -> str:
        """Gera nome do arquivo com timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"dados_cotacoes_{timestamp}.csv"

    def _find_resposta_column_index(self, page: Page) -> int:
        # Força o índice da coluna resposta para 6
        return 6

# ==========================================
# INTERFACE GRÁFICA
# ==========================================

class CrawlerGUI:
    """Interface gráfica moderna para o crawler"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.config = CrawlerConfig()
        self.crawler = QuoteCrawler(self.config)
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        self.root.title("Extrator de Cotações Vale Coupa")
        self.root.minsize(700, 600)
        self.root.configure(bg="#fff")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Card.TFrame", background="#fff", relief="flat", borderwidth=0)
        style.configure("Card.TLabelframe", background="#fff", borderwidth=0)
        style.configure("Card.TLabelframe.Label", background="#fff", font=("Segoe UI", 12, "bold"), foreground="#222")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground="#1a73e8", background="#fff")
        style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground="#222", background="#fff")
        style.configure("TEntry", font=("Segoe UI", 11), fieldbackground="#fff", background="#fff", relief="flat")
        style.configure("TCombobox", font=("Segoe UI", 11), fieldbackground="#fff", background="#fff", relief="flat")
        style.configure("Accent.TButton", font=("Segoe UI", 12, "bold"), foreground="#fff", background="#22bb55", padding=8)
        style.map("Accent.TButton",
            background=[("active", "#1e9c47"), ("!active", "#22bb55")],
            foreground=[("disabled", "#ccc"), ("!disabled", "#fff")]
        )

        # Cabeçalho
        header = ttk.Frame(self.root, style="Card.TFrame")
        header.pack(pady=(20, 10), padx=20, fill="x")
        ttk.Label(header, text="📝 Extrator de Cotações Vale Coupa", style="Title.TLabel").pack(anchor="center")
        ttk.Label(header, text="Sistema automatizado para extração de dados de cotações", font=("Segoe UI", 10), background="#fff").pack(anchor="center")

        # Card principal (inputs lado a lado)
        main_card = ttk.Frame(self.root, style="Card.TFrame")
        main_card.pack(padx=20, pady=10, fill="x")

        # Inputs em grid
        # Coluna 1: Credenciais
        cred_frame = ttk.Labelframe(main_card, text="🔐 Credenciais de Acesso", style="Card.TLabelframe")
        cred_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        cred_frame.columnconfigure(0, weight=1)
        ttk.Label(cred_frame, text="Usuário (e-mail):", style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 0))
        self.username_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.username_var, style="TEntry").grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        ttk.Label(cred_frame, text="Senha:", style="Section.TLabel").grid(row=2, column=0, sticky="w", padx=8, pady=(0, 0))
        self.password_var = tk.StringVar()
        ttk.Entry(cred_frame, textvariable=self.password_var, show="*", style="TEntry").grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 8))

        # Coluna 2: Configurações
        config_frame = ttk.Labelframe(main_card, text="⚙️ Configurações de Extração", style="Card.TLabelframe")
        config_frame.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        config_frame.columnconfigure(1, weight=1)
        ttk.Label(config_frame, text="Data para Extração:", style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 0))
        self.date_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%y"))
        ttk.Entry(config_frame, textvariable=self.date_var, width=14, style="TEntry").grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        ttk.Label(config_frame, text="Filtro de Resposta:", style="Section.TLabel").grid(row=2, column=0, sticky="w", padx=8, pady=(0, 0))
        self.resposta_var = tk.StringVar(value="Sem resposta")
        self.resposta_map = {"Sem resposta": "0", "Com resposta": "1", "Todas": "todas"}
        ttk.Combobox(config_frame, textvariable=self.resposta_var, values=["Sem resposta", "Com resposta", "Todas"], width=16, state="readonly", style="TCombobox").grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))
        ttk.Label(config_frame, text="Escolha o tipo de cotação a extrair", font=("Segoe UI", 8), background="#fff").grid(row=4, column=0, sticky="w", padx=8, pady=(0, 8))

        main_card.columnconfigure(0, weight=1)
        main_card.columnconfigure(1, weight=1)

        # Card de ação
        action_card = ttk.Frame(self.root, style="Card.TFrame")
        action_card.pack(padx=20, pady=(10, 0), fill="x")
        ttk.Label(action_card, text="Iniciar Extração de Dados", style="Section.TLabel").pack(anchor="center", pady=(10, 5))
        self.extract_button = ttk.Button(action_card, text="🚀 Extrair Cotações", style="Accent.TButton", command=self._start_extraction)
        self.extract_button.pack(pady=(0, 10))
        ttk.Label(action_card, text="Clique no botão acima para iniciar a extração automática", font=("Segoe UI", 9), background="#fff").pack(anchor="center", pady=(0, 10))

        # Card de status/logs
        status_card = ttk.Labelframe(self.root, text="📊 Status e Logs", style="Card.TLabelframe")
        status_card.pack(padx=20, pady=10, fill="x")
        self.status_var = tk.StringVar(value="Pronto para extrair cotações")
        ttk.Label(status_card, textvariable=self.status_var, foreground="#22bb55", font=("Segoe UI", 11, "bold"), background="#fff").pack(anchor="w", padx=8, pady=(8, 5))
        ttk.Label(status_card, text="Os dados serão salvos em CSV na pasta do programa. Anexos em 'downloads_anexos'.", font=("Segoe UI", 8), background="#fff").pack(anchor="w", padx=8, pady=(0, 8))
    
    def _start_extraction(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        date = self.date_var.get().strip()
        resposta_legivel = self.resposta_var.get().strip()
        resposta = self.resposta_map.get(resposta_legivel, "0")

        if not self._validate_inputs(username, password, date, resposta):
            return

        self.extract_button.config(state="disabled")
        self.status_var.set("🔄 Processando...")
        self.root.update()

        import threading
        thread = threading.Thread(
            target=self._execute_extraction,
            args=(username, password, date, resposta),
            daemon=True
        )
        thread.start()
    
    def _validate_inputs(self, username: str, password: str, date: str, resposta: str) -> bool:
        """Valida entradas do usuário"""
        if not username or not password:
            messagebox.showerror("Erro", "Por favor, informe usuário e senha.")
            return False
        
        if not re.match(r'^\d{2}/\d{2}/\d{2}$', date):
            messagebox.showerror("Erro", "Formato de data inválido. Use DD/MM/YY")
            return False
        
        if resposta not in ["0", "1", "todas"]:
            messagebox.showerror("Erro", "Resposta inválida. Use 0, 1 ou 'todas'.")
            return False
        
        return True
    
    def _execute_extraction(self, username: str, password: str, date: str, resposta: str) -> None:
        """Executa a extração em thread separada"""
        try:
            # Atualiza status inicial
            self.root.after(0, lambda: self.status_var.set("🔐 Conectando..."))
            
            # Cria um crawler com callback de status
            crawler = QuoteCrawler(self.config)
            
            # Define callback para atualizações de status
            def update_status(message):
                self.root.after(0, lambda: self.status_var.set(message))
            
            # Adiciona callback ao crawler
            crawler.status_callback = update_status
            
            # Executa extração
            success = crawler.crawl_quotes(username, password, date, resposta)
            
            if success:
                self.root.after(0, lambda: self.status_var.set("✅ Extração concluída! (apenas resposta = 0)"))
                self.root.after(0, lambda: self._show_success_and_close())
            else:
                # Verifica se o problema foi de login
                if "❌ Falha no login" in self.status_var.get() or "Credenciais inválidas" in self.status_var.get():
                    error_msg = "🔐 Erro de Autenticação!\n\nSuas credenciais de login estão incorretas ou sua conta pode estar bloqueada.\n\nPor favor, verifique:\n• Se o usuário está correto\n• Se a senha está correta\n• Se sua conta não está bloqueada\n• Se você tem acesso à plataforma Vale Coupa\n\nTente novamente com credenciais válidas."
                    self.root.after(0, lambda: self.status_var.set("❌ Credenciais inválidas"))
                else:
                    self.root.after(0, lambda: self.status_var.set("❌ Falha na extração"))
                    
                    # Mensagem de erro dinâmica baseada no filtro
                    resposta_filter = self.resposta_var.get()
                    if resposta_filter == "0":
                        error_msg = "Falha na extração. Verifique se há cotações sem resposta (resposta = 0) para a data informada."
                    elif resposta_filter == "1":
                        error_msg = "Falha na extração. Verifique se há cotações com resposta (resposta ≠ 0) para a data informada."
                    else:
                        error_msg = "Falha na extração. Verifique se há cotações para a data informada."
                
                self.root.after(0, lambda: messagebox.showerror("Erro", error_msg))
            
        except Exception as e:
            self.logger.error(f"Erro na thread de extração: {str(e)}")
            self.root.after(0, lambda: self.status_var.set("❌ Erro inesperado"))
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro inesperado: {str(e)}"))
        
        finally:
            self.root.after(0, lambda: self.extract_button.config(state="normal"))
    
    def _show_success_and_close(self) -> None:
        """Mostra mensagem de sucesso e fecha a aplicação"""
        resposta_filter = self.resposta_var.get()
        
        if resposta_filter == "0":
            filter_text = "apenas cotações sem resposta (resposta = 0)"
        elif resposta_filter == "1":
            filter_text = "apenas cotações com resposta (resposta ≠ 0)"
        else:
            filter_text = "todas as cotações"
        
        result = messagebox.showinfo("Sucesso", f"Extração realizada com sucesso!\n\nO arquivo CSV foi gerado na pasta do programa.\n\nNota: {filter_text} foram extraídas.")
        # Fecha a aplicação após o usuário clicar OK
        self.root.quit()
        self.root.destroy()
    
    def run(self) -> None:
        """Executa a aplicação"""
        self.root.mainloop()

# ==========================================
# PONTO DE ENTRADA
# ==========================================

def main():
    """Função principal da aplicação"""
    try:
        app = CrawlerGUI()
        app.run()
    except Exception as e:
        print(f"Erro crítico: {str(e)}")

if __name__ == "__main__":
    main() 