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
    def setup_logger(name: str, level: LogLevel = LogLevel.WARNING) -> logging.Logger:
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
    
    def __init__(self, page: Page):
        self.page = page
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
    
    def extract_all_items(self) -> List[ExtractedItemData]:
        """Extrai dados de todos os itens da página"""
        try:
            # Primeiro verifica se existe botão "inserir resposta" e clica nele
            self._click_insert_response_button()
            
            # Aguarda um pouco para a página carregar após clicar
            time.sleep(2)
            
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
        """Extrai arquivos anexados"""
        try:
            attachment_links = form.locator("a[href*='attachment'], a[href*='download']").all()
            attachments = []
            
            for link in attachment_links:
                try:
                    text = link.text_content().strip()
                    href = link.get_attribute("href")
                    attachments.append(text or href)
                except Exception:
                    continue
            
            return ", ".join(attachments)
            
        except Exception as e:
            self.logger.warning(f"Erro ao extrair anexos: {str(e)}")
            return ""
    
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
            original_count = len(data)
            filtered_data = self.duplicate_processor.remove_duplicates(data)
            final_count = len(filtered_data)
            
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
    
    def get_export_summary(self, original_count: int, final_count: int, filename: str) -> str:
        """Gera resumo da exportação"""
        duplicates = original_count - final_count
        
        if duplicates > 0:
            return (f"Exportação concluída!\n\n"
                   f"• {original_count} itens extraídos\n"
                   f"• {duplicates} duplicatas removidas\n"
                   f"• {final_count} itens únicos salvos em {filename}")
        else:
            return (f"Exportação concluída!\n\n"
                   f"• {final_count} itens únicos salvos em {filename}\n"
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
            page.goto(login_url)
            time.sleep(2)
            
            # Verifica se está na página de login
            if not self._is_login_page(page):
                self.logger.error("Não foi possível acessar a página de login")
                return False
            
            # Preenche credenciais
            self._fill_credentials(page, username, password)
            
            # Submete formulário
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
        if "supplier_login" in page.url:
            self.logger.error("Login falhou")
            return False
        
        # Tenta acessar página de cotações
        quotes_url = f"{self.config.base_url}{self.config.quotes_path}"
        page.goto(quotes_url)
        time.sleep(2)
        
        success = "quote_supplier_land" in page.url
        if not success:
            self.logger.error("Falha ao acessar página de cotações")
        
        return success

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
    
    def crawl_quotes(self, username: str, password: str, target_date: str) -> bool:
        """Executa o processo completo de crawling"""
        try:
            self._update_status("🌐 Iniciando browser...")
            
            with sync_playwright() as playwright:
                browser = self._create_browser(playwright)
                page = self._create_page(browser)
                
                # Autenticação
                self._update_status("🔐 Fazendo login...")
                if not self.auth_service.authenticate(page, username, password):
                    self._update_status("❌ Falha no login")
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
                    success = self.data_exporter.export_to_csv(quotes_data, filename)
                    
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
        
        # Extrai cotações
        return self._process_quote_rows(page, target_date)
    
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
    
    def _process_quote_rows(self, page: Page, target_date: str) -> List[Dict[str, str]]:
        """Processa as linhas de cotações na tabela"""
        all_quotes_data = []
        
        quotes_processed = 0
        quotes_found_for_date = 0
        total_rows_checked = 0
        
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
                    break
                
                # Procura uma cotação não processada ainda
                cotacao_encontrada = False
                
                for i, row in enumerate(rows):
                    total_rows_checked += 1
                    
                    try:
                        # Verifica se a linha existe e está visível com timeout reduzido
                        if not row.is_visible(timeout=2000):
                            continue
                        
                        # Extrai dados da cotação com timeout reduzido
                        quote_data = self._extract_quote_info_safe(row)
                        if not quote_data:
                            continue
                        
                        # Verifica se a data corresponde
                        if target_date not in quote_data["data_inicial"]:
                            continue
                        
                        # Verifica se já processamos esta cotação
                        if self._cotacao_ja_processada(quote_data['evento'], all_quotes_data):
                            continue
                        
                        quotes_found_for_date += 1
                        cotacao_encontrada = True
                        
                        # Processa esta cotação
                        sucesso = self._processar_cotacao_individual(page, row, quote_data, all_quotes_data)
                        
                        if sucesso:
                            quotes_processed += 1
                        else:
                            # Marca como processada mesmo se houve erro, para evitar loop infinito
                            quotes_processed += 1
                        
                        # Sai do loop for para recarregar a página
                        break
                        
                    except Exception as row_error:
                        continue
                
                # Se não encontrou nenhuma cotação nova, para o processamento
                if not cotacao_encontrada:
                    break
                    
            except Exception as page_error:
                self.logger.error(f"Erro ao recarregar página: {str(page_error)}")
                break
        
        # Restaura timeout original
        page.set_default_timeout(self.config.timeout_ms)
        
        # Log final apenas se não encontrou cotações
        if quotes_found_for_date == 0:
            self.logger.warning(f"Nenhuma cotação encontrada para a data '{target_date}'")
        
        return all_quotes_data
    
    def _extract_quote_info_safe(self, row) -> Optional[QuoteData]:
        """Extrai informações da cotação com tratamento de erro robusto"""
        try:
            cells = row.locator("td")
            
            # Verifica se há células suficientes
            if cells.count() < 4:
                return None
            
            # Extrai com timeout reduzido
            evento_link = cells.nth(0).locator("a")
            if evento_link.count() == 0:
                return None
            
            evento = evento_link.text_content(timeout=3000).strip()
            nome_evento = cells.nth(1).text_content(timeout=3000).strip()
            data_inicial = cells.nth(2).text_content(timeout=3000).strip()
            data_final = cells.nth(3).text_content(timeout=3000).strip()
            
            return QuoteData(
                evento=evento,
                nome_evento=nome_evento,
                data_inicial=data_inicial,
                data_final=data_final
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
            data_final=cells.nth(3).text_content().strip()
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
            extractor = ItemDataExtractor(page)
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
        """Configura a interface do usuário"""
        self.root.title("Vale Coupa Crawler - Versão Refatorada")
        self.root.geometry("600x600")
        self.root.configure(bg="#f8f9fa")
        
        # Estilo
        self._configure_styles()
        
        # Container principal
        main_frame = ttk.Frame(self.root, style="Card.TFrame")
        main_frame.pack(padx=30, pady=30, fill="both", expand=True)
        
        # Componentes
        self._create_header(main_frame)
        self._create_login_section(main_frame)
        self._create_date_section(main_frame)
        self._create_action_section(main_frame)
        self._create_status_section(main_frame)
    
    def _configure_styles(self) -> None:
        """Configura estilos da interface"""
        style = ttk.Style()
        
        # Cores modernas
        style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        style.configure("Header.TLabel", background="#ffffff", font=("Segoe UI", 16, "bold"), foreground="#2c3e50")
        style.configure("Section.TLabel", background="#ffffff", font=("Segoe UI", 11, "bold"), foreground="#34495e")
        style.configure("Info.TLabel", background="#ffffff", font=("Segoe UI", 9), foreground="#7f8c8d")
        style.configure("Status.TLabel", background="#ffffff", font=("Segoe UI", 10), foreground="#27ae60")
    
    def _create_header(self, parent) -> None:
        """Cria cabeçalho da aplicação"""
        header_frame = ttk.Frame(parent, style="Card.TFrame")
        header_frame.pack(fill="x", pady=(0, 30))
        
        title = ttk.Label(header_frame, text="🔍 Extrator de Cotações Vale Coupa", style="Header.TLabel")
        title.pack(pady=10)
        
        subtitle = ttk.Label(header_frame, text="Sistema automatizado para extração de dados de cotações", style="Info.TLabel")
        subtitle.pack()
    
    def _create_login_section(self, parent) -> None:
        """Cria seção de login"""
        login_frame = ttk.LabelFrame(parent, text="🔐 Credenciais de Acesso", style="Card.TFrame")
        login_frame.pack(fill="x", pady=(0, 20))
        
        # Grid interno
        grid_frame = ttk.Frame(login_frame)
        grid_frame.pack(padx=20, pady=20, fill="x")
        
        # Usuário
        ttk.Label(grid_frame, text="Usuário:", style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.username_var = tk.StringVar()
        username_entry = ttk.Entry(grid_frame, textvariable=self.username_var, width=30, font=("Segoe UI", 10))
        username_entry.grid(row=0, column=1, sticky="ew", pady=5)
        
        # Senha
        ttk.Label(grid_frame, text="Senha:", style="Section.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(grid_frame, textvariable=self.password_var, show="*", width=30, font=("Segoe UI", 10))
        password_entry.grid(row=1, column=1, sticky="ew", pady=5)
        
        grid_frame.columnconfigure(1, weight=1)
    
    def _create_date_section(self, parent) -> None:
        """Cria seção de seleção de data"""
        date_frame = ttk.LabelFrame(parent, text="📅 Data para Extração", style="Card.TFrame")
        date_frame.pack(fill="x", pady=(0, 20))
        
        inner_frame = ttk.Frame(date_frame)
        inner_frame.pack(padx=20, pady=20, fill="x")
        
        ttk.Label(inner_frame, text="Data (DD/MM/YY):", style="Section.TLabel").pack(anchor="w")
        
        date_input_frame = ttk.Frame(inner_frame)
        date_input_frame.pack(anchor="w", pady=(5, 0))
        
        self.date_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%y"))
        date_entry = ttk.Entry(date_input_frame, textvariable=self.date_var, width=15, font=("Segoe UI", 10))
        date_entry.pack(side="left")
        
        ttk.Label(date_input_frame, text="  Exemplo: 25/12/24", style="Info.TLabel").pack(side="left")
    
    def _create_action_section(self, parent) -> None:
        """Cria seção de ações"""
        action_frame = ttk.Frame(parent, style="Card.TFrame")
        action_frame.pack(fill="x", pady=(0, 20))
        
        # Usando Button padrão do tkinter para melhor controle de aparência
        self.extract_button = tk.Button(
            action_frame, 
            text="🔥 EXTRAIR COTAÇÕES", 
            command=self._start_extraction,
            bg="#007acc",  # Fundo azul
            fg="white",    # Texto branco
            font=("Segoe UI", 12, "bold"),
            relief="flat", # Sem borda 3D
            borderwidth=0, # Sem borda
            padx=30,      # Padding horizontal
            pady=15,      # Padding vertical
            cursor="hand2", # Cursor de mão
            activebackground="#005499", # Cor quando clicado
            activeforeground="white"    # Texto quando clicado
        )
        self.extract_button.pack(pady=30)
    
    def _create_status_section(self, parent) -> None:
        """Cria seção de status"""
        status_frame = ttk.LabelFrame(parent, text="📊 Status", style="Card.TFrame")
        status_frame.pack(fill="both", expand=True)
        
        self.status_var = tk.StringVar(value="Pronto para extrair cotações")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, style="Status.TLabel")
        status_label.pack(padx=20, pady=20, anchor="w")
    
    def _start_extraction(self) -> None:
        """Inicia processo de extração"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        date = self.date_var.get().strip()
        
        # Validações
        if not self._validate_inputs(username, password, date):
            return
        
        # Atualiza UI
        self.extract_button.config(state="disabled")
        self.status_var.set("🔄 Processando...")
        self.root.update()
        
        # Executa em thread separada
        import threading
        thread = threading.Thread(
            target=self._execute_extraction,
            args=(username, password, date),
            daemon=True
        )
        thread.start()
    
    def _validate_inputs(self, username: str, password: str, date: str) -> bool:
        """Valida entradas do usuário"""
        if not username or not password:
            messagebox.showerror("Erro", "Por favor, informe usuário e senha.")
            return False
        
        if not re.match(r'^\d{2}/\d{2}/\d{2}$', date):
            messagebox.showerror("Erro", "Formato de data inválido. Use DD/MM/YY")
            return False
        
        return True
    
    def _execute_extraction(self, username: str, password: str, date: str) -> None:
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
            success = crawler.crawl_quotes(username, password, date)
            
            if success:
                self.root.after(0, lambda: self.status_var.set("✅ Extração concluída!"))
                self.root.after(0, lambda: self._show_success_and_close())
            else:
                self.root.after(0, lambda: self.status_var.set("❌ Falha na extração"))
                self.root.after(0, lambda: messagebox.showerror("Erro", "Falha na extração. Verifique se há cotações para a data informada."))
            
        except Exception as e:
            self.logger.error(f"Erro na thread de extração: {str(e)}")
            self.root.after(0, lambda: self.status_var.set("❌ Erro inesperado"))
            self.root.after(0, lambda: messagebox.showerror("Erro", f"Erro inesperado: {str(e)}"))
        
        finally:
            self.root.after(0, lambda: self.extract_button.config(state="normal"))
    
    def _show_success_and_close(self) -> None:
        """Mostra mensagem de sucesso e fecha a aplicação"""
        result = messagebox.showinfo("Sucesso", "Extração realizada com sucesso!\n\nO arquivo CSV foi gerado na pasta do programa.")
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