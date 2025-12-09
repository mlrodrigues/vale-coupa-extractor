"""
Gerenciador de Credenciais - Vale Coupa Crawler
Sistema seguro para armazenamento e recuperação de credenciais do usuário

Arquitetura baseada em:
- Repository Pattern para abstração do armazenamento
- Strategy Pattern para diferentes estratégias de armazenamento
- SOLID Principles (Single Responsibility, Open/Closed, Liskov, Interface Segregation, Dependency Inversion)
- Criptografia para dados sensíveis
"""

import keyring
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Protocol
from cryptography.fernet import Fernet
import os

# ==========================================
# TIPOS E ESTRUTURAS
# ==========================================

@dataclass
class Credentials:
    """Estrutura de credenciais do usuário"""
    username: str
    password: str
    service_name: str = "ValeCoupaCrawler"
    
    def is_valid(self) -> bool:
        """Verifica se as credenciais são válidas"""
        return bool(self.username and self.password)


# ==========================================
# INTERFACES (PROTOCOLS)
# ==========================================

class CredentialsRepository(Protocol):
    """Interface para repositório de credenciais"""
    
    def save(self, credentials: Credentials) -> bool:
        """Salva as credenciais"""
        ...
    
    def load(self) -> Optional[Credentials]:
        """Carrega as credenciais salvas"""
        ...
    
    def delete(self) -> bool:
        """Deleta as credenciais salvas"""
        ...
    
    def exists(self) -> bool:
        """Verifica se existem credenciais salvas"""
        ...


# ==========================================
# ESTRATÉGIAS DE ARMAZENAMENTO
# ==========================================

class WindowsCredentialsRepository(ABC):
    """Repositório base usando Windows Credential Manager"""
    
    def __init__(self, service_name: str = "ValeCoupaCrawler"):
        self.service_name = service_name
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def save(self, credentials: Credentials) -> bool:
        """Salva credenciais no Windows Credential Manager (Keyring)"""
        try:
            if not credentials.is_valid():
                self.logger.warning("Credenciais inválidas não podem ser salvas")
                return False
            
            # Salva username como usuário do serviço
            keyring.set_password(self.service_name, "username", credentials.username)
            
            # Salva password
            keyring.set_password(self.service_name, "password", credentials.password)
            
            self.logger.info(f"Credenciais salvas com sucesso para: {credentials.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {str(e)}")
            return False
    
    def load(self) -> Optional[Credentials]:
        """Carrega credenciais do Windows Credential Manager"""
        try:
            username = keyring.get_password(self.service_name, "username")
            password = keyring.get_password(self.service_name, "password")
            
            if username and password:
                self.logger.info(f"Credenciais carregadas para: {username}")
                return Credentials(username=username, password=password, service_name=self.service_name)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais: {str(e)}")
            return None
    
    def delete(self) -> bool:
        """Deleta credenciais do Windows Credential Manager"""
        try:
            try:
                keyring.delete_password(self.service_name, "username")
            except keyring.errors.PasswordDeleteError:
                pass
            
            try:
                keyring.delete_password(self.service_name, "password")
            except keyring.errors.PasswordDeleteError:
                pass
            
            self.logger.info("Credenciais removidas com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao deletar credenciais: {str(e)}")
            return False
    
    def exists(self) -> bool:
        """Verifica se existem credenciais salvas"""
        try:
            username = keyring.get_password(self.service_name, "username")
            password = keyring.get_password(self.service_name, "password")
            
            return bool(username and password)
            
        except Exception:
            return False


class EncryptedLocalRepository:
    """Repositório com armazenamento local criptografado (fallback/alternativa)"""
    
    def __init__(self, config_dir: str = ".credentials", service_name: str = "ValeCoupaCrawler"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / f"{service_name}_credentials.enc"
        self.key_file = self.config_dir / f"{service_name}.key"
        self.service_name = service_name
        self.logger = logging.getLogger(self.__class__.__name__)
        self._ensure_key()
    
    def _ensure_key(self) -> None:
        """Garante que existe uma chave de criptografia"""
        if not self.key_file.exists():
            key = Fernet.generate_key()
            self.key_file.write_bytes(key)
            # Protege arquivo da chave
            os.chmod(self.key_file, 0o600)
    
    def _get_cipher(self) -> Fernet:
        """Retorna instância do cipher com a chave"""
        key = self.key_file.read_bytes()
        return Fernet(key)
    
    def save(self, credentials: Credentials) -> bool:
        """Salva credenciais criptografadas localmente"""
        try:
            if not credentials.is_valid():
                self.logger.warning("Credenciais inválidas não podem ser salvas")
                return False
            
            cipher = self._get_cipher()
            data = {
                "username": credentials.username,
                "password": credentials.password
            }
            
            json_data = json.dumps(data).encode()
            encrypted_data = cipher.encrypt(json_data)
            
            self.config_file.write_bytes(encrypted_data)
            
            # Protege arquivo de credenciais
            os.chmod(self.config_file, 0o600)
            
            self.logger.info(f"Credenciais criptografadas salvas para: {credentials.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais criptografadas: {str(e)}")
            return False
    
    def load(self) -> Optional[Credentials]:
        """Carrega credenciais criptografadas"""
        try:
            if not self.config_file.exists():
                return None
            
            cipher = self._get_cipher()
            encrypted_data = self.config_file.read_bytes()
            json_data = cipher.decrypt(encrypted_data).decode()
            data = json.loads(json_data)
            
            if data.get("username") and data.get("password"):
                self.logger.info(f"Credenciais descriptografadas para: {data['username']}")
                return Credentials(
                    username=data["username"],
                    password=data["password"],
                    service_name=self.service_name
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais criptografadas: {str(e)}")
            return None
    
    def delete(self) -> bool:
        """Deleta arquivo de credenciais"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            
            self.logger.info("Credenciais criptografadas removidas com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao deletar credenciais: {str(e)}")
            return False
    
    def exists(self) -> bool:
        """Verifica se arquivo de credenciais existe"""
        return self.config_file.exists()


# ==========================================
# SERVIÇO DE GERENCIAMENTO DE CREDENCIAIS
# ==========================================

class CredentialsManager:
    """Gerenciador centralizado de credenciais com Strategy Pattern"""
    
    def __init__(self, use_windows_keyring: bool = True):
        """
        Inicializa o gerenciador
        
        Args:
            use_windows_keyring: Se True, usa Windows Credential Manager; se False, usa encriptação local
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.use_windows_keyring = use_windows_keyring
        
        # Seleciona estratégia de armazenamento
        if use_windows_keyring:
            try:
                self.repository = WindowsCredentialsRepository()
                self.logger.info("Usando Windows Credential Manager")
            except Exception as e:
                self.logger.warning(f"Keyring não disponível: {str(e)}, usando criptografia local")
                self.repository = EncryptedLocalRepository()
        else:
            self.repository = EncryptedLocalRepository()
            self.logger.info("Usando armazenamento local criptografado")
    
    def save_credentials(self, username: str, password: str) -> bool:
        """Salva credenciais"""
        credentials = Credentials(username=username, password=password)
        return self.repository.save(credentials)
    
    def load_credentials(self) -> Optional[Credentials]:
        """Carrega credenciais salvas"""
        return self.repository.load()
    
    def delete_credentials(self) -> bool:
        """Deleta credenciais salvas"""
        return self.repository.delete()
    
    def has_saved_credentials(self) -> bool:
        """Verifica se existem credenciais salvas"""
        return self.repository.exists()
    
    def get_saved_username(self) -> Optional[str]:
        """Retorna nome de usuário salvo (se existir)"""
        credentials = self.load_credentials()
        return credentials.username if credentials else None


# ==========================================
# CONFIGURAÇÃO DE LOGGING
# ==========================================

def setup_credentials_logger(level: int = logging.INFO) -> logging.Logger:
    """Configura logger para o módulo de credenciais"""
    logger = logging.getLogger("CredentialsManager")
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.FileHandler("credentials.log", encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# Configura logger ao importar
setup_credentials_logger()

