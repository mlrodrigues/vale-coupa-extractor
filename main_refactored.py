"""
Vale Coupa Web Crawler - Versão Refatorada
Sistema para extração automatizada de cotações da plataforma Vale Coupa

MUDANÇAS IMPLEMENTADAS:
- Browser visível (headless=False) para acompanhar o processo
- Ordenação automática da tabela pela coluna "Data inicial" em ordem decrescente
- Verificação inteligente da ordenação usando múltiplos atributos (aria-sort e data-dir)
- Tratamento robusto de inconsistências nos atributos de ordenação
- Download automático de anexos com indicação clara na tabela
- Extração robusta de anexos com múltiplas estratégias de detecção

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

# ==========================================
# FUNÇÕES UTILITÁRIAS GLOBAIS
# ==========================================

def convert_to_number(value: str) -> str:
    """Converte string para formato número, removendo caracteres não numéricos"""
    if not value:
        return ""
    try:
        # Remove caracteres não numéricos exceto ponto e vírgula
        numero_limpo = re.sub(r'[^\d,\.]', '', value.strip())
        # Converte vírgula para ponto se necessário
        numero_limpo = numero_limpo.replace(',', '.')
        # Verifica se é um número válido
        float(numero_limpo)
        return numero_limpo
    except (ValueError, AttributeError):
        # Se não conseguiu converter, retorna o valor original limpo com vírgula convertida
        numero_limpo = re.sub(r'[^\d,\.]', '', value.strip())
        return numero_limpo.replace(',', '.')

def convert_to_date_format(date_str: str) -> str:
    """Converte string de data para formato padrão DD/MM/YYYY"""
    if not date_str:
        return ""
    try:
        # Remove espaços extras
        date_str = date_str.strip()
        
        # Padrões comuns de data
        patterns = [
            (r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$', 'DMY'),  # DD/MM/YY ou DD/MM/YYYY
            (r'^(\d{1,2})-(\d{1,2})-(\d{2,4})$', 'DMY'),  # DD-MM-YY ou DD-MM-YYYY
            (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', 'YMD'),    # YYYY-MM-DD
        ]
        
        for pattern, fmt in patterns:
            match = re.match(pattern, date_str)
            if match:
                groups = match.groups()
                if fmt == 'DMY':
                    day = groups[0].zfill(2)
                    month = groups[1].zfill(2)
                    year = groups[2]
                elif fmt == 'YMD':
                    year = groups[0]
                    month = groups[1].zfill(2)
                    day = groups[2].zfill(2)
                # Corrige ano com 2 dígitos
                if len(year) == 2:
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                return f"{day}/{month}/{year}"
        
        return date_str
    except Exception:
        return date_str

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
    codigo_item: str  # Novo campo para o código extraído
    descricao: str
    descricao_estendida: str
    quantidade: str
    data_necessaria: str
    detalhes: str
    arquivos_anexados: str
    ncm: str  # Novo campo NCM
    numero_planta: str  # Novo campo número da planta
    estado_planta: str  # Novo campo estado da planta

class QuoteData(TypedDict):
    """Estrutura dos dados de uma cotação"""
    evento: str
    numero_evento: str  # Novo campo para o número extraído
    nome_evento: str
    data_inicial: str
    data_final: str
    resposta: str  # Adicionado campo resposta

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
    def setup_logger(name: str, level: LogLevel = LogLevel.DEBUG) -> logging.Logger:
        """Configura e retorna um logger"""
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
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
    
    def __init__(self, page: Page, numero_evento: str = None):
        self.page = page
        self.logger = LoggerConfig.setup_logger(self.__class__.__name__)
        self.numero_evento = numero_evento or "sem_numero"
        self.anexos_dir = Path("anexos") / str(self.numero_evento)
        self.anexos_dir.mkdir(parents=True, exist_ok=True)
    
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
            self.logger.debug(f"[COTAÇÃO] Itens detectados: {item_count}")
            
            items = []
            for i in range(item_count):
                item_data = self._extract_single_item(i, item_count)
                self.logger.debug(f"[COTAÇÃO] Extraindo item {i+1}/{item_count}: {item_data}")
                if self._is_valid_item(item_data):
                    items.append(item_data)
            
            self.logger.debug(f"[COTAÇÃO] Total de itens extraídos: {len(items)}")
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
        """Conta itens válidos na página (apenas forms visíveis e com descrição preenchida)"""
        return self.page.evaluate("""
            () => {
                const forms = Array.from(document.querySelectorAll('form.s-itemsAndServicesFieldGrid'));
                return forms.filter(form => {
                    // Verifica se o form está visível
                    const rect = form.getBoundingClientRect();
                    if (rect.height < 10 || rect.width < 10) return false;
                    // Verifica se tem texto de descrição
                    const desc = form.querySelector('div.s-description p.s-textField');
                    return desc && desc.textContent && desc.textContent.trim().length > 0;
                }).length;
            }
        """)
    
    def _extract_single_item(self, index: int, total: int) -> ExtractedItemData:
        """Extrai dados de um item específico"""
        try:
            # Obtém o formulário específico do item usando índice
            form = self.page.locator("form.s-itemsAndServicesFieldGrid").nth(index)
            
            # Extrai descrição completa (incluindo inglês e espanhol)
            raw_desc = self._extract_field("div.s-description p.s-textField", index)
            codigo_item, descricao_sem_codigo = self._split_codigo_descricao(raw_desc)
            
            # Extrai descrição estendida completa (sem filtrar apenas português)
            descricao_estendida_completa = self._extract_complete_extended_description(index)
            
            # Extrai quantidade e converte para número
            quantidade_raw = self._extract_field("div.s-quantity span.s-value", index)
            quantidade = convert_to_number(quantidade_raw)
            
            # Extrai data e converte para formato data
            data_necessaria_raw = self._extract_field("div.s-need_by_date p.s-textField", index)
            data_necessaria = convert_to_date_format(data_necessaria_raw)
            
            # Extrai detalhes e processa número da planta e estado
            detalhes_raw = self._extract_field("div.s-details li span", index)
            numero_planta, estado_planta = self._extract_planta_info(detalhes_raw)
            
            # Extrai NCM
            ncm = self._extract_ncm(index)
            
            # Extrai anexos de forma mais específica
            arquivos_anexados = self._extract_attachments_specific(form, index)
            
            # Se tem anexos, tenta fazer o download
            if arquivos_anexados.strip():
                self._download_attachments_for_item(form, index)
            
            return ExtractedItemData(
                numero_item=f"{index + 1}/{total}",
                codigo_item=convert_to_number(codigo_item),
                descricao=descricao_sem_codigo,
                descricao_estendida=descricao_estendida_completa,
                quantidade=quantidade,
                data_necessaria=data_necessaria,
                detalhes=detalhes_raw,
                arquivos_anexados=arquivos_anexados,
                ncm=ncm,
                numero_planta=numero_planta,
                estado_planta=estado_planta
            )
        except Exception as e:
            self.logger.warning(f"Erro ao extrair item {index + 1}: {str(e)}")
            return self._create_empty_item(index, total)
    
    def _extract_field(self, selector: str, index: int) -> str:
        """Extrai um campo específico usando seletor CSS"""
        try:
            elements = self.page.locator(selector)
            if elements.count() > index:
                raw_text = elements.nth(index).text_content().strip()
                # Remove quebras de linha e normaliza espaços
                clean_text = re.sub(r'\s+', ' ', raw_text)
                return clean_text
        except Exception as e:
            self.logger.warning(f"Erro ao extrair campo '{selector}': {str(e)}")
        return ""
    
    def _extract_complete_extended_description(self, index: int) -> str:
        """Extrai descrição estendida completa (incluindo inglês e espanhol) sem quebras de linha"""
        try:
            selector = "div.s-extended_description p.s-textField"
            raw_text = self._extract_field(selector, index)
            if not raw_text:
                return ""
            
            # Remove quebras de linha e normaliza espaços
            text_limpo = re.sub(r'\s+', ' ', raw_text.strip())
            return text_limpo
        except Exception as e:
            self.logger.warning(f"Erro ao extrair descrição estendida completa: {str(e)}")
            return ""
    
    def _extract_extended_description(self, index: int) -> str:
        """Extrai e processa descrição estendida (método legado para compatibilidade)"""
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
    
    def _extract_attachments_specific(self, form, index: int) -> str:
        """Extrai anexos de forma robusta, garantindo que pertencem ao item correto e cobrindo mais casos de links"""
        try:
            attachments = set()
            self.logger.info(f"Tentando extrair anexos do item {index + 1}")
            
            # Estratégia 1: Busca anexos na estrutura específica do Vale Coupa
            attachment_lists = form.locator("ul.attachments__list.s-attachmentList").all()
            self.logger.info(f"Encontradas {len(attachment_lists)} listas de anexos específicas")
            
            for attachment_list in attachment_lists:
                try:
                    # Busca links dentro da lista de anexos
                    file_links = attachment_list.locator("li.attachment.attachmentFile.s-attachmentFile a").all()
                    self.logger.info(f"Encontrados {len(file_links)} links de anexos específicos")
                    
                    for link in file_links:
                        try:
                            if not link.is_visible():
                                continue
                            href = link.get_attribute("href")
                            if not href:
                                continue
                            text = (link.text_content() or "").strip()
                            filename = text or Path(href).name
                            filename = filename.strip()
                            if not filename:
                                continue
                            # Normaliza nome
                            filename = re.sub(r'\s+', ' ', filename)
                            attachments.add(filename)
                            self.logger.info(f"Anexo específico encontrado: {filename}")
                        except Exception as e:
                            self.logger.warning(f"Erro ao processar anexo da lista: {str(e)}")
                            continue
                except Exception as e:
                    self.logger.warning(f"Erro ao processar lista de anexos: {str(e)}")
                    continue
            
            # Estratégia 2: Busca anexos com seletores genéricos se não encontrou específicos
            if not attachments:
                self.logger.info("Nenhum anexo encontrado na estrutura específica, tentando seletores genéricos")
                attachment_selectors = [
                    "a[href*='attachment']",
                    "a[href*='download']",
                    "a[href*='file']",
                    "a[href*='document']",
                    "a[href*='.pdf']",
                    "a[href*='.doc']",
                    "a[href*='.docx']",
                    "a[href*='.xls']",
                    "a[href*='.xlsx']",
                    "a[href*='.zip']",
                    "a[href*='.rar']",
                    "a[download]",
                    "a[target='_blank']"
                ]
                
                for selector in attachment_selectors:
                    try:
                        links = form.locator(selector).all()
                        if links:
                            self.logger.info(f"Seletor '{selector}' encontrou {len(links)} links")
                        
                        for link in links:
                            try:
                                if not link.is_visible():
                                    continue
                                href = link.get_attribute("href")
                                if not href:
                                    continue
                                text = (link.text_content() or "").strip()
                                filename = text or Path(href).name
                                filename = filename.strip()
                                if not filename:
                                    continue
                                
                                # Ignora textos genéricos
                                generic_texts = ["anexos", "chment", "download", "arquivo", "file", "documento", "clique aqui", "open", "abrir"]
                                if filename.lower() in generic_texts:
                                    continue
                                
                                # Normaliza nome
                                filename = re.sub(r'\s+', ' ', filename)
                                attachments.add(filename)
                                self.logger.info(f"Anexo genérico encontrado: {filename}")
                            except Exception as e:
                                self.logger.warning(f"Erro ao processar anexo individual: {str(e)}")
                                continue
                    except Exception as e:
                        self.logger.warning(f"Erro ao buscar anexos com seletor {selector}: {str(e)}")
                        continue
            
            # Estratégia 3: Busca por qualquer link que pareça ser um anexo
            if not attachments:
                self.logger.info("Tentando busca por qualquer link que pareça anexo")
                try:
                    all_links = form.locator("a").all()
                    self.logger.info(f"Total de links encontrados no formulário: {len(all_links)}")
                    
                    for link in all_links:
                        try:
                            if not link.is_visible():
                                continue
                            href = link.get_attribute("href")
                            if not href:
                                continue
                            
                            # Verifica se o href parece ser um arquivo
                            if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar', '.txt']):
                                text = (link.text_content() or "").strip()
                                filename = text or Path(href).name
                                filename = filename.strip()
                                if filename and filename.lower() not in ["anexos", "chment", "download", "arquivo", "file", "documento", "clique aqui", "open", "abrir"]:
                                    filename = re.sub(r'\s+', ' ', filename)
                                    attachments.add(filename)
                                    self.logger.info(f"Anexo por extensão encontrado: {filename}")
                        except Exception as e:
                            continue
                except Exception as e:
                    self.logger.warning(f"Erro na busca por extensões: {str(e)}")
            
            result = ", ".join(sorted(attachments)) if attachments else ""
            self.logger.info(f"Total de anexos extraídos para item {index + 1}: {len(attachments)} - Resultado: '{result}'")
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao extrair anexos específicos do item {index + 1}: {str(e)}")
            return ""
    
    def _download_attachments_for_item(self, form, index: int) -> None:
        """Faz download dos anexos de um item específico"""
        try:
            self.logger.info(f"Tentando fazer download dos anexos do item {index + 1}")
            
            # Busca anexos na estrutura específica do Vale Coupa
            attachment_lists = form.locator("ul.attachments__list.s-attachmentList").all()
            for attachment_list in attachment_lists:
                try:
                    # Busca links dentro da lista de anexos
                    file_links = attachment_list.locator("li.attachment.attachmentFile.s-attachmentFile a").all()
                    for link in file_links:
                        try:
                            if not link.is_visible():
                                continue
                            href = link.get_attribute("href")
                            if not href:
                                continue
                            text = (link.text_content() or "").strip()
                            filename = text or Path(href).name
                            filename = filename.strip()
                            if not filename:
                                continue
                            
                            # Normaliza nome
                            filename = re.sub(r'\s+', ' ', filename)
                            
                            # Faz o download
                            if self._download_file(href, filename):
                                self.logger.info(f"Anexo baixado com sucesso: {filename}")
                            else:
                                self.logger.warning(f"Falha ao baixar anexo: {filename}")
                                
                        except Exception as e:
                            self.logger.warning(f"Erro ao processar anexo para download: {str(e)}")
                            continue
                except Exception as e:
                    self.logger.warning(f"Erro ao processar lista de anexos para download: {str(e)}")
                    continue
            
            # Se não encontrou anexos na estrutura específica, busca com seletores genéricos
            if not attachment_lists:
                attachment_selectors = [
                    "a[href*='attachment']",
                    "a[href*='download']",
                    "a[href*='file']",
                    "a[href*='document']",
                    "a[href*='.pdf']",
                    "a[href*='.doc']",
                    "a[href*='.docx']",
                    "a[href*='.xls']",
                    "a[href*='.xlsx']",
                    "a[href*='.zip']",
                    "a[href*='.rar']",
                    "a[download]",
                    "a[target='_blank']"
                ]
                for selector in attachment_selectors:
                    try:
                        links = form.locator(selector).all()
                        for link in links:
                            try:
                                if not link.is_visible():
                                    continue
                                href = link.get_attribute("href")
                                if not href:
                                    continue
                                text = (link.text_content() or "").strip()
                                filename = text or Path(href).name
                                filename = filename.strip()
                                if not filename:
                                    continue
                                
                                # Ignora textos genéricos
                                generic_texts = ["anexos", "chment", "download", "arquivo", "file", "documento", "clique aqui", "open", "abrir"]
                                if filename.lower() in generic_texts:
                                    continue
                                
                                # Normaliza nome
                                filename = re.sub(r'\s+', ' ', filename)
                                
                                # Faz o download
                                if self._download_file(href, filename):
                                    self.logger.info(f"Anexo baixado com sucesso: {filename}")
                                else:
                                    self.logger.warning(f"Falha ao baixar anexo: {filename}")
                                    
                            except Exception as e:
                                self.logger.warning(f"Erro ao processar anexo individual para download: {str(e)}")
                                continue
                    except Exception as e:
                        self.logger.warning(f"Erro ao buscar anexos com seletor {selector} para download: {str(e)}")
                        continue
                        
        except Exception as e:
            self.logger.error(f"Erro ao fazer download dos anexos do item {index + 1}: {str(e)}")
    
    def _download_file(self, url: str, filename: str) -> Path:
        """Baixa o arquivo do anexo e salva na pasta da cotação"""
        try:
            # Se a URL for relativa, torna absoluta
            if url.startswith('/'):
                url = f"https://vale.coupahost.com{url}"
            
            self.logger.info(f"Fazendo download de: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            safe_filename = self._sanitize_filename(filename)
            file_path = self.anexos_dir / safe_filename
            
            # Cria diretório se não existir
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"Arquivo salvo em: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.warning(f"Erro ao baixar arquivo {url}: {str(e)}")
            return None
    def _sanitize_filename(self, filename: str) -> str:
        """Remove caracteres inválidos do nome do arquivo"""
        return re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    def _is_valid_item(self, item: ExtractedItemData) -> bool:
        """Verifica se o item tem dados válidos"""
        return bool(item["descricao"] or item["quantidade"] or item["descricao_estendida"])
    
    def _split_codigo_descricao(self, raw_desc: str) -> (str, str):
        """Separa o código do início da descrição (antes do primeiro '||')"""
        if not raw_desc:
            return "", ""
        
        # Remove quebras de linha e normaliza espaços
        raw_desc = re.sub(r'\s+', ' ', raw_desc.strip())
        
        partes = raw_desc.split('||', 1)
        if len(partes) == 2:
            codigo = partes[0].strip()
            descricao = partes[1].strip()
            return codigo, descricao
        return "", raw_desc
    
    def _extract_planta_info(self, detalhes: str) -> tuple[str, str]:
        """Extrai número da planta e estado da planta dos detalhes"""
        if not detalhes:
            return "", ""
        
        try:
            # Padrão para extrair número da planta após "Local de entrega:"
            numero_match = re.search(r'Local de entrega:\s*(\d+)', detalhes)
            numero_planta = numero_match.group(1) if numero_match else ""
            
            # Padrão para extrair estado (2 letras antes de "- BR")
            estado_match = re.search(r'-\s*([A-Z]{2})\s*-\s*BR', detalhes)
            estado_planta = estado_match.group(1) if estado_match else ""
            
            return numero_planta, estado_planta
        except Exception:
            return "", ""
    
    def _extract_ncm(self, index: int) -> str:
        """Extrai código NCM do campo próprio do item"""
        try:
            # Seletor específico baseado no HTML fornecido
            ncm_selectors = [
                "div.s-classification_of_goods p.s-textField",  # Seletor específico do NCM
                "div.s-showField.s-classification_of_goods p.s-textField",  # Seletor mais específico
                "div[class*=classification_of_goods] p.s-textField",  # Seletor alternativo
                "div.s-ncm span.s-value",  # Fallback para outros possíveis seletores
                "div.s-ncm p.s-textField",
                "div[data-field='ncm'] span",
                "div[data-field='ncm'] p",
                "td[data-field='ncm']",
                "span[data-field='ncm]"
            ]
            
            for selector in ncm_selectors:
                ncm = self._extract_field(selector, index)
                if ncm and ncm.strip():
                    return ncm.strip()
            
            return ""
        except Exception as e:
            self.logger.warning(f"Erro ao extrair NCM: {str(e)}")
            return ""
    
    def _create_empty_item(self, index: int, total: int) -> ExtractedItemData:
        """Cria item vazio em caso de erro"""
        return ExtractedItemData(
            numero_item=f"{index + 1}/{total}",
            codigo_item="",
            descricao="",
            descricao_estendida="",
            quantidade="",
            data_necessaria="",
            detalhes="",
            arquivos_anexados="",
            ncm="",
            numero_planta="",
            estado_planta=""
        )

    def _is_attachment_belongs_to_item(self, link, form) -> bool:
        """Verifica se o anexo realmente pertence ao item específico"""
        try:
            # Verifica se o link está visível
            if not link.is_visible():
                return False
            
            # Verifica se o link tem um href válido
            href = link.get_attribute("href")
            if not href:
                return False
            
            # Verifica se o link está dentro do formulário do item
            # Como já estamos buscando dentro do form.locator(), isso deve ser suficiente
            # Apenas verifica se o link está realmente dentro do contexto do formulário
            try:
                # Verifica se conseguimos encontrar o link dentro do formulário
                # Se conseguirmos, significa que pertence ao item
                form.locator(f"a[href={href}]").count() > 0
                return True
            except:
                # Se não conseguir encontrar, pode ser que o href tenha parâmetros
                # Nesse caso, verifica apenas se está visível e tem href
                return True
                
        except Exception:
            return False

    def _extract_attachments(self, form) -> str:
        """Extrai e baixa arquivos anexados, salvando na pasta da cotação (método legado)"""
        # Chama o método específico sem índice para compatibilidade
        return self._extract_attachments_specific(form, -1)

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

    def export_to_excel(self, data: List[Dict[str, str]], filename: str) -> bool:
        """Exporta dados para Excel (.xlsx) usando openpyxl puro com formatação adequada"""
        if not data:
            return False
        try:
            from openpyxl import Workbook
            from openpyxl.styles import NamedStyle, Font, PatternFill, Border, Side
            from openpyxl.utils import get_column_letter
            
            # NÃO remove duplicatas!
            filtered_data = data
            # Cria workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "Cotações"
            
            # Cabeçalho
            headers = list(filtered_data[0].keys())
            ws.append(headers)
            
            # Estilo para cabeçalho
            header_style = NamedStyle(name="header_style")
            header_style.font = Font(bold=True, color="FFFFFF")
            header_style.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            header_style.border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Aplica estilo ao cabeçalho
            for cell in ws[1]:
                cell.style = header_style
            
            # Dados com formatação
            for row_idx, row_data in enumerate(filtered_data, start=2):
                for col_idx, header in enumerate(headers, start=1):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    value = row_data.get(header, "")
                    
                    # Aplica formatação baseada no tipo de campo
                    if self._is_numeric_field(header, value):
                        cell.value = self._convert_to_excel_number(value)
                        cell.number_format = '#,##0'  # Sem casas decimais
                    elif self._is_date_field(header, value):
                        cell.value = self._convert_to_excel_date(value)
                        cell.number_format = 'dd/mm/yyyy'
                    else:
                        cell.value = value
                        cell.number_format = '@'  # Formato texto
                    
                    # Aplica bordas
                    cell.border = Border(
                        left=Side(style='thin'),
                        right=Side(style='thin'),
                        top=Side(style='thin'),
                        bottom=Side(style='thin')
                    )
            
            # Ajusta largura das colunas
            for col in ws.columns:
                max_length = 0
                col_letter = col[0].column_letter
                for cell in col:
                    try:
                        if cell.value:
                            max_length = max(max_length, len(str(cell.value)))
                    except:
                        pass
                ws.column_dimensions[col_letter].width = min(max(max_length + 2, 10), 80)
            
            # Salva arquivo
            excel_filename = filename.replace('.csv', '.xlsx') if filename.endswith('.csv') else filename + '.xlsx'
            wb.save(excel_filename)
            self.logger.info(f"Arquivo Excel criado: {excel_filename}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao exportar Excel: {str(e)}")
            return False
    
    def _is_numeric_field(self, header: str, value: str) -> bool:
        """Verifica se o campo deve ser tratado como numérico"""
        numeric_headers = [
            'evento', 'numero_evento', 'codigo_item', 'quantidade',
            'numero_planta', 'ncm'
        ]
        return header.lower() in numeric_headers and value.strip()
    
    def _is_date_field(self, header: str, value: str) -> bool:
        """Verifica se o campo deve ser tratado como data"""
        date_headers = [
            'data_inicial', 'data_final', 'data_necessaria'
        ]
        return header.lower() in date_headers and value.strip()
    
    def _convert_to_excel_number(self, value: str):
        """Converte string para número do Excel, incluindo NCM como inteiro"""
        try:
            # Se for NCM (formato 0000.00.00), remove pontos e converte para inteiro
            if re.match(r'^\d{4}\.\d{2}\.\d{2}$', value.strip()):
                return int(value.replace('.', ''))
            # Para outros números, remove caracteres não numéricos exceto ponto
            clean_value = re.sub(r'[^\d\.]', '', value.strip())
            if clean_value:
                return float(clean_value)
            return None
        except:
            return None
    
    def _convert_to_excel_date(self, value: str):
        """Converte string de data para data do Excel"""
        try:
            # Converte para formato DD/MM/YYYY se necessário
            formatted_date = convert_to_date_format(value)
            if formatted_date:
                # Converte para objeto datetime
                day, month, year = formatted_date.split('/')
                from datetime import datetime
                return datetime(int(year), int(month), int(day))
            return None
        except:
            return None
    
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
            login_url = f"{self.config.base_url}{self.config.login_path}"
            page.goto(login_url)
            time.sleep(2)
            if not self._is_login_page(page):
                self.logger.error("Não foi possível acessar a página de login")
                return False
            self._fill_credentials(page, username, password)
            self._submit_login_form(page)
            # Verifica sucesso
            if not self._verify_authentication(page):
                self.logger.error("Usuário ou senha incorretos!")
                return "login_error"
            return True
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
    
    def crawl_quotes(self, username: str, password: str, target_date: str, resposta_filtro: str = "todas") -> bool:
        """Executa o processo completo de crawling"""
        try:
            self._update_status("🌐 Iniciando browser...")
            with sync_playwright() as playwright:
                browser = self._create_browser(playwright)
                page = self._create_page(browser)
                self._update_status("🔐 Fazendo login...")
                auth_result = self.auth_service.authenticate(page, username, password)
                if auth_result == "login_error":
                    self._update_status("❌ Usuário ou senha incorretos!")
                    return "login_error"
                if not auth_result:
                    self._update_status("❌ Falha no login")
                    return False
                self._update_status("📋 Buscando cotações...")
                quotes_data = self._extract_quotes_for_date(page, target_date, resposta_filtro)
                if quotes_data and len(quotes_data) > 0:
                    self._update_status("💾 Salvando dados...")
                    filename = self._generate_filename()
                    success = self.data_exporter.export_to_excel(quotes_data, filename)
                    if success:
                        self._update_status(f"✅ Dados salvos em Excel!")
                        return True
                    else:
                        self._update_status("❌ Erro na exportação")
                        return False
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
    
    def _extract_quotes_for_date(self, page: Page, target_date: str, resposta_filtro: str) -> List[Dict[str, str]]:
        """Extrai cotações para data específica"""
        quotes_url = f"{self.config.base_url}{self.config.quotes_path}"
        page.goto(quotes_url)
        
        # Configura visualização
        self._configure_page_view(page)
        
        # Extrai cotações
        return self._process_quote_rows(page, target_date, resposta_filtro)
    
    def _configure_page_view(self, page: Page) -> None:
        """Configura visualização da página (items per page, etc.)"""
        try:
            # Tenta configurar para mostrar mais itens por página
            items_selector = f"text='{self.config.items_per_page}'"
            if page.locator(items_selector).count() > 0:
                page.locator(items_selector).click()
                time.sleep(1)
            
            # Verifica e ordena a tabela pela coluna "Data inicial" em ordem decrescente
            self._ensure_table_sorted_by_start_time(page)
            
        except Exception as e:
            self.logger.warning(f"Não foi possível configurar visualização: {str(e)}")
    
    def _ensure_table_sorted_by_start_time(self, page: Page) -> None:
        """Verifica se a tabela está ordenada pela coluna 'Data inicial' em ordem decrescente"""
        try:
            # Aguarda a tabela carregar
            page.wait_for_selector("table", timeout=10000)
            
            # Procura pelo cabeçalho da coluna "Data inicial"
            start_time_header = page.locator("#th_start_time")
            if start_time_header.count() == 0:
                self.logger.warning("Cabeçalho 'Data inicial' não encontrado")
                return
            
            # Verifica ambos os atributos para determinar o estado real da ordenação
            aria_sort = start_time_header.get_attribute("aria-sort")
            data_dir = start_time_header.get_attribute("data-dir")
            
            self.logger.info(f"Estado da ordenação - aria-sort: '{aria_sort}', data-dir: '{data_dir}'")
            
            # Determina se está em ordem decrescente
            is_descending = self._is_descending_order(aria_sort, data_dir)
            
            if not is_descending:
                self.logger.info("Ordenando tabela por 'Data inicial' em ordem decrescente...")
                
                # Clica no cabeçalho para ordenar
                start_time_header.click()
                time.sleep(2)
                
                # Aguarda um pouco mais para a ordenação ser aplicada
                time.sleep(1)
                
                # Verifica se a ordenação foi aplicada
                new_aria_sort = start_time_header.get_attribute("aria-sort")
                new_data_dir = start_time_header.get_attribute("data-dir")
                
                self.logger.info(f"Após ordenação - aria-sort: '{new_aria_sort}', data-dir: '{new_data_dir}'")
                
                if self._is_descending_order(new_aria_sort, new_data_dir):
                    self.logger.info("Tabela ordenada com sucesso em ordem decrescente")
                else:
                    self.logger.warning("Não foi possível confirmar se a ordenação foi aplicada corretamente")
                    # Tenta clicar novamente se necessário
                    if not self._is_descending_order(new_aria_sort, new_data_dir):
                        self.logger.info("Tentando clicar novamente para garantir ordenação decrescente...")
                        start_time_header.click()
                        time.sleep(2)
            else:
                self.logger.info("Tabela já está ordenada por 'Data inicial' em ordem decrescente")
                
        except Exception as e:
            self.logger.warning(f"Erro ao verificar/ordenar tabela: {str(e)}")
    
    def _is_descending_order(self, aria_sort: str, data_dir: str) -> bool:
        """Determina se a tabela está em ordem decrescente baseado nos atributos"""
        # Verifica aria-sort primeiro
        if aria_sort:
            if aria_sort.lower() == "decrescente":
                return True
            elif aria_sort.lower() == "crescente":
                return False
        
        # Verifica data-dir como fallback
        if data_dir:
            if data_dir.upper() == "DESC":
                return True
            elif data_dir.upper() == "ASC":
                return False
        
        # Se não conseguir determinar, assume que não está em ordem decrescente
        return False
    
    def _process_quote_rows(self, page: Page, target_date: str, resposta_filtro: str) -> List[Dict[str, str]]:
        """Processa as linhas de cotações na tabela, aplicando filtro de resposta"""
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
                        
                        # Filtro de data
                        if target_date not in quote_data["data_inicial"]:
                            continue
                        
                        # Filtro de resposta (coluna 6)
                        resposta_valor = self._extract_resposta_coluna(row)
                        quote_data["resposta"] = resposta_valor
                        if resposta_filtro == "0" and resposta_valor != "0":
                            continue
                        if resposta_filtro == "1" and resposta_valor == "0":
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
            if cells.count() < 7:
                return None
                
            evento_link = cells.nth(0).locator("a")
            if evento_link.count() == 0:
                return None
                
            evento = evento_link.text_content(timeout=3000).strip()
            raw_nome_evento = cells.nth(1).text_content(timeout=3000).strip()
            numero_evento, nome_evento_limpo = self._split_numero_nome_evento(raw_nome_evento)
            data_inicial = cells.nth(2).text_content(timeout=3000).strip()
            data_final = cells.nth(3).text_content(timeout=3000).strip()
            resposta = cells.nth(6).text_content(timeout=3000).strip()
            
            # Remove quebras de linha dos textos
            evento = re.sub(r'\s+', ' ', evento)
            nome_evento_limpo = re.sub(r'\s+', ' ', nome_evento_limpo)
            data_inicial = re.sub(r'\s+', ' ', data_inicial)
            data_final = re.sub(r'\s+', ' ', data_final)
            resposta = re.sub(r'\s+', ' ', resposta)
            
            return QuoteData(
                evento=evento,
                numero_evento=numero_evento,
                nome_evento=nome_evento_limpo,
                data_inicial=data_inicial,
                data_final=data_final,
                resposta=resposta
            )
        except Exception as e:
            self.logger.warning(f"Erro ao extrair dados da linha: {str(e)}")
            return None
    def _split_numero_nome_evento(self, raw_nome_evento: str) -> (str, str):
        """Separa o número do nome do evento (após o '#')"""
        if not raw_nome_evento:
            return "", ""
        match = re.search(r'#(\d+)', raw_nome_evento)
        if match:
            numero = match.group(1)
            nome_limpo = re.sub(r'#\d+', '', raw_nome_evento).strip()
            return numero, nome_limpo
        return "", raw_nome_evento.strip()
    
    def _extract_quote_info(self, row) -> QuoteData:
        """Extrai informações básicas da cotação da linha da tabela (método original para compatibilidade)"""
        cells = row.locator("td")
        
        return QuoteData(
            evento=cells.nth(0).locator("a").text_content().strip(),
            nome_evento=cells.nth(1).text_content().strip(),
            data_inicial=cells.nth(2).text_content().strip(),
            data_final=cells.nth(3).text_content().strip()
        )
    
    def _extract_resposta_coluna(self, row) -> str:
        """Extrai o valor da coluna de resposta (índice 6) da linha da tabela"""
        try:
            cells = row.locator("td")
            if cells.count() >= 7:
                return cells.nth(6).text_content(timeout=3000).strip()
            return ""
        except Exception:
            return ""
    
    def _cotacao_ja_processada(self, evento: str, dados_processados: List[Dict[str, str]]) -> bool:
        """Verifica se uma cotação já foi processada"""
        return any(item.get("evento") == evento for item in dados_processados)
    
    def _processar_cotacao_individual(self, page: Page, row, quote_data: QuoteData, all_quotes_data: List[Dict[str, str]]) -> bool:
        """Processa uma cotação individual"""
        try:
            # Atualiza status
            self._update_status(f"📄 Processando cotação {quote_data['evento']}...")
            
            # Extrai o href do link da cotação
            link_element = row.locator("td").nth(0).locator("a")
            if link_element.count() == 0:
                self.logger.error(f"Link da cotação {quote_data['evento']} não encontrado")
                return False
            
            # Extrai o href do link
            href = link_element.get_attribute("href")
            if not href:
                self.logger.error(f"Href da cotação {quote_data['evento']} não encontrado")
                return False
            
            self.logger.info(f"Link da cotação {quote_data['evento']}: {href}")
            
            # Se o href for relativo, torna absoluto
            if href.startswith('/'):
                full_url = f"{self.config.base_url}{href}"
            else:
                full_url = href
            
            # Navega diretamente para a URL da cotação
            self.logger.info(f"Navegando para: {full_url}")
            page.goto(full_url, timeout=10000)
            time.sleep(3)  # Aguarda carregamento
            
            # Verifica se navegou corretamente
            current_url = page.url
            self.logger.info(f"URL atual após navegação: {current_url}")
            
            # Verifica se está na página correta (deve conter 'external_responses' ou 'quotes')
            if "external_responses" not in current_url and "quotes" not in current_url:
                self.logger.error(f"Falha na navegação para cotação {quote_data['evento']}. URL atual: {current_url}")
                return False

            # Verifica se é uma página de lista de respostas e navega para a primeira resposta
            if self._is_quote_with_responses_page(page):
                self.logger.info(f"Cotação {quote_data['evento']} é do tipo 'com respostas' - navegando para primeira resposta")
                if not self._navigate_to_first_response(page):
                    self.logger.error(f"Falha ao navegar para primeira resposta da cotação {quote_data['evento']}")
                    return False
                # Aguarda carregamento da página da resposta
                time.sleep(3)

            # Atualiza status
            self._update_status(f"🔍 Extraindo itens da cotação {quote_data['evento']}...")
            
            # Extrai itens da cotação
            # Passa o numero_evento para o extrator
            extractor = ItemDataExtractor(page, quote_data.get('numero_evento', None))
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
            # Converte campos numéricos da cotação
            quote_data_processed = {
                "evento": convert_to_number(quote_data.get("evento", "")),
                "numero_evento": convert_to_number(quote_data.get("numero_evento", "")),
                "nome_evento": quote_data.get("nome_evento", ""),
                "data_inicial": convert_to_date_format(quote_data.get("data_inicial", "")),
                "data_final": convert_to_date_format(quote_data.get("data_final", "")),
                "resposta": quote_data.get("resposta", "")
            }
            
            combined_item = {
                **quote_data_processed,  # Dados da cotação processados
                **item                   # Dados do item
            }
            combined_data.append(combined_item)
        
        return combined_data
    
    def _is_quote_with_responses_page(self, page: Page) -> bool:
        """Detecta se a página é uma lista de respostas de cotação"""
        try:
            # Indicadores de página de respostas
            indicators = [
                "img.sprite-application_form",  # Ícone de exibir
                "a[href*='response_id']",       # Links com response_id
                "td:has-text('Exibir')",        # Coluna com ação Exibir
            ]
            for indicator in indicators:
                if page.locator(indicator).count() > 0:
                    self.logger.info(f"Página detectada como 'com respostas' - encontrado: {indicator}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Erro ao detectar tipo de página: {str(e)}")
            return False

    def _navigate_to_first_response(self, page: Page) -> bool:
        """Navega para a primeira resposta disponível na lista"""
        try:
            # Tenta clicar no ícone Exibir
            view_buttons = page.locator("img.sprite-application_form")
            if view_buttons.count() > 0:
                self.logger.info("Clicando no primeiro botão 'Exibir'")
                view_buttons.first.click()
                time.sleep(3)
                return True
            # Ou tenta clicar no link com response_id
            response_links = page.locator("a[href*='response_id']")
            if response_links.count() > 0:
                href = response_links.first.get_attribute("href")
                if href:
                    self.logger.info(f"Navegando para primeira resposta: {href}")
                    page.goto(href, timeout=10000)
                    time.sleep(3)
                    return True
            self.logger.error("Nenhum botão 'Exibir' ou link de resposta encontrado")
            return False
        except Exception as e:
            self.logger.error(f"Erro ao navegar para primeira resposta: {str(e)}")
            return False
    
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
        resposta_legivel = self.resposta_var.get().strip()
        resposta_filtro = self.resposta_map.get(resposta_legivel, "todas")
        if not self._validate_inputs(username, password, date):
            return
        self.extract_button.config(state="disabled")
        self.status_var.set("🔄 Processando...")
        self.root.update()
        import threading
        thread = threading.Thread(
            target=self._execute_extraction,
            args=(username, password, date, resposta_filtro),
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
    
    def _execute_extraction(self, username: str, password: str, date: str, resposta_filtro: str) -> None:
        """Executa a extração em thread separada"""
        try:
            self.root.after(0, lambda: self.status_var.set("🔐 Conectando..."))
            crawler = QuoteCrawler(self.config)
            def update_status(message):
                self.root.after(0, lambda: self.status_var.set(message))
            crawler.status_callback = update_status
            result = crawler.crawl_quotes(username, password, date, resposta_filtro)
            if result == "login_error":
                self.root.after(0, lambda: self.status_var.set("❌ Usuário ou senha incorretos!"))
                self.root.after(0, lambda: messagebox.showerror("Erro de Login", "Usuário ou senha incorretos! Por favor, tente novamente."))
                self.root.after(0, lambda: self.extract_button.config(state="normal"))
                return
            if result:
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