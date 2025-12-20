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
from typing import Optional, Protocol, List, Dict
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

    # --- Extensão para multiusuário (mantém compatibilidade com API antiga) ---
    def list_accounts(self) -> List[str]:
        """Lista usernames salvos"""
        ...

    def load_account(self, username: str) -> Optional[Credentials]:
        """Carrega credenciais de um usuário específico"""
        ...


# ==========================================
# ESTRATÉGIAS DE ARMAZENAMENTO
# ==========================================

class WindowsCredentialsRepository(ABC):
    """Repositório base usando Windows Credential Manager"""
    
    def __init__(self, service_name: str = "ValeCoupaCrawler"):
        self.service_name = service_name
        self.logger = logging.getLogger(self.__class__.__name__)
        # Keys reservadas (evita conflito com usernames reais)
        self._index_key = "__accounts_index__"
        self._default_key = "__default_account__"
        self._legacy_username_key = "username"
        self._legacy_password_key = "password"
        self._account_prefix = "acct:"

    def _account_key(self, username: str) -> str:
        return f"{self._account_prefix}{username}"

    def _load_index(self) -> List[str]:
        raw = keyring.get_password(self.service_name, self._index_key)
        if not raw:
            return []
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [str(x) for x in data if str(x).strip()]
            return []
        except Exception:
            return []

    def _save_index(self, accounts: List[str]) -> None:
        unique = sorted({a.strip() for a in accounts if a and a.strip()})
        keyring.set_password(self.service_name, self._index_key, json.dumps(unique))

    def _set_default(self, username: str) -> None:
        if username and username.strip():
            keyring.set_password(self.service_name, self._default_key, username.strip())

    def _get_default(self) -> Optional[str]:
        val = keyring.get_password(self.service_name, self._default_key)
        return val.strip() if val and val.strip() else None

    def _migrate_legacy_if_needed(self) -> None:
        """Migra armazenamento legado (username/password únicos) para multiusuário."""
        try:
            legacy_username = keyring.get_password(self.service_name, self._legacy_username_key)
            legacy_password = keyring.get_password(self.service_name, self._legacy_password_key)
            if not (legacy_username and legacy_password):
                return

            # Se já existe no formato novo, não migra novamente
            accounts = self._load_index()
            if legacy_username in accounts:
                # Remove legado para evitar confusão
                try:
                    keyring.delete_password(self.service_name, self._legacy_username_key)
                except Exception:
                    pass
                try:
                    keyring.delete_password(self.service_name, self._legacy_password_key)
                except Exception:
                    pass
                return

            keyring.set_password(self.service_name, self._account_key(legacy_username), legacy_password)
            accounts.append(legacy_username)
            self._save_index(accounts)
            self._set_default(legacy_username)

            # Limpa chaves antigas
            try:
                keyring.delete_password(self.service_name, self._legacy_username_key)
            except Exception:
                pass
            try:
                keyring.delete_password(self.service_name, self._legacy_password_key)
            except Exception:
                pass

            self.logger.info(f"Migração legado->multiusuário concluída para: {legacy_username}")
        except Exception as e:
            self.logger.debug(f"Falha ao migrar legado: {str(e)}")
    
    def save(self, credentials: Credentials) -> bool:
        """Salva credenciais no Windows Credential Manager (Keyring)"""
        try:
            if not credentials.is_valid():
                self.logger.warning("Credenciais inválidas não podem ser salvas")
                return False

            self._migrate_legacy_if_needed()

            username = credentials.username.strip()
            keyring.set_password(self.service_name, self._account_key(username), credentials.password)

            accounts = self._load_index()
            if username not in accounts:
                accounts.append(username)
            self._save_index(accounts)
            self._set_default(username)

            self.logger.info(f"Credenciais salvas com sucesso para: {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais: {str(e)}")
            return False
    
    def load(self) -> Optional[Credentials]:
        """Carrega credenciais do Windows Credential Manager"""
        try:
            self._migrate_legacy_if_needed()

            default_username = self._get_default()
            if default_username:
                cred = self.load_account(default_username)
                if cred:
                    return cred

            accounts = self._load_index()
            if accounts:
                cred = self.load_account(accounts[0])
                if cred:
                    return cred

            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais: {str(e)}")
            return None

    def load_account(self, username: str) -> Optional[Credentials]:
        """Carrega credenciais de um usuário específico"""
        try:
            self._migrate_legacy_if_needed()
            username = (username or "").strip()
            if not username:
                return None
            password = keyring.get_password(self.service_name, self._account_key(username))
            if password:
                return Credentials(username=username, password=password, service_name=self.service_name)
            return None
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais do usuário {username}: {str(e)}")
            return None

    def list_accounts(self) -> List[str]:
        """Lista usernames salvos"""
        try:
            self._migrate_legacy_if_needed()
            return self._load_index()
        except Exception:
            return []
    
    def delete(self) -> bool:
        """Deleta credenciais do Windows Credential Manager"""
        try:
            self._migrate_legacy_if_needed()

            accounts = self._load_index()
            for username in accounts:
                try:
                    keyring.delete_password(self.service_name, self._account_key(username))
                except Exception:
                    pass

            # Remove chaves auxiliares
            for key_name in [self._index_key, self._default_key, self._legacy_username_key, self._legacy_password_key]:
                try:
                    keyring.delete_password(self.service_name, key_name)
                except Exception:
                    pass

            self.logger.info("Credenciais (todas as contas) removidas com sucesso")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao deletar credenciais: {str(e)}")
            return False
    
    def exists(self) -> bool:
        """Verifica se existem credenciais salvas"""
        try:
            self._migrate_legacy_if_needed()
            return bool(self._load_index())
            
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
    
    def _load_payload(self) -> Dict:
        """Carrega payload criptografado (suporta migração do formato legado)."""
        if not self.config_file.exists():
            return {"accounts": {}, "default": None}

        cipher = self._get_cipher()
        encrypted_data = self.config_file.read_bytes()
        json_data = cipher.decrypt(encrypted_data).decode()
        data = json.loads(json_data) if json_data else {}

        # Migração de legado: {"username": "...", "password": "..."}
        if isinstance(data, dict) and data.get("username") and data.get("password") and "accounts" not in data:
            legacy_username = str(data["username"]).strip()
            legacy_password = str(data["password"])
            migrated = {"accounts": {legacy_username: legacy_password}, "default": legacy_username}
            # Persiste migração para não repetir
            self._save_payload(migrated)
            return migrated

        if not isinstance(data, dict):
            return {"accounts": {}, "default": None}
        if "accounts" not in data or not isinstance(data.get("accounts"), dict):
            data["accounts"] = {}
        if "default" not in data:
            data["default"] = None
        return data

    def _save_payload(self, data: Dict) -> None:
        cipher = self._get_cipher()
        json_data = json.dumps(data).encode()
        encrypted_data = cipher.encrypt(json_data)
        self.config_file.write_bytes(encrypted_data)
        try:
            os.chmod(self.config_file, 0o600)
        except Exception:
            pass

    def save(self, credentials: Credentials) -> bool:
        """Salva credenciais criptografadas localmente (multiusuário)"""
        try:
            if not credentials.is_valid():
                self.logger.warning("Credenciais inválidas não podem ser salvas")
                return False

            payload = self._load_payload()
            username = credentials.username.strip()
            payload["accounts"][username] = credentials.password
            payload["default"] = username
            self._save_payload(payload)

            self.logger.info(f"Credenciais criptografadas salvas para: {username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar credenciais criptografadas: {str(e)}")
            return False
    
    def load(self) -> Optional[Credentials]:
        """Carrega credenciais criptografadas"""
        try:
            payload = self._load_payload()
            accounts: Dict[str, str] = payload.get("accounts", {})
            if not accounts:
                return None

            default_username = payload.get("default")
            if default_username and default_username in accounts:
                return Credentials(username=default_username, password=accounts[default_username], service_name=self.service_name)

            # fallback: primeiro da lista
            first_username = sorted(accounts.keys())[0]
            return Credentials(username=first_username, password=accounts[first_username], service_name=self.service_name)
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar credenciais criptografadas: {str(e)}")
            return None

    def load_account(self, username: str) -> Optional[Credentials]:
        """Carrega credenciais de um usuário específico"""
        try:
            username = (username or "").strip()
            if not username:
                return None
            payload = self._load_payload()
            accounts: Dict[str, str] = payload.get("accounts", {})
            if username in accounts and accounts[username]:
                return Credentials(username=username, password=accounts[username], service_name=self.service_name)
            return None
        except Exception:
            return None

    def list_accounts(self) -> List[str]:
        """Lista usernames salvos"""
        try:
            payload = self._load_payload()
            accounts: Dict[str, str] = payload.get("accounts", {})
            return sorted([u for u in accounts.keys() if u and str(u).strip()])
        except Exception:
            return []
    
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

    def list_accounts(self) -> List[str]:
        """Lista contas salvas (multiusuário)."""
        repo_list = getattr(self.repository, "list_accounts", None)
        if callable(repo_list):
            return repo_list()
        # Compatibilidade: se não suportar multiusuário, retorna o username salvo (se houver)
        username = self.get_saved_username()
        return [username] if username else []

    def load_account(self, username: str) -> Optional[Credentials]:
        """Carrega uma conta específica (multiusuário)."""
        repo_load = getattr(self.repository, "load_account", None)
        if callable(repo_load):
            return repo_load(username)
        # Compatibilidade: retorna credencial default se bater com username
        cred = self.load_credentials()
        if cred and cred.username == username:
            return cred
        return None


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

