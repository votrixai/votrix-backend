"""Model manager — singleton for pre-loaded LLM models."""

import os
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI


class ModelManager:
    _instance: Optional["ModelManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.gemini_flash: Optional[ChatGoogleGenerativeAI] = None
        self.gemini_flash_backup: Optional[ChatGoogleGenerativeAI] = None
        self._init_models()

    def _init_models(self):
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        if not api_key:
            return
        self.gemini_flash = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-preview-05-20",
            google_api_key=api_key,
            temperature=0.7,
            convert_system_message_to_human=False,
        )
        self.gemini_flash_backup = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.7,
            convert_system_message_to_human=False,
        )

    def get_primary(self) -> ChatGoogleGenerativeAI:
        if not self.gemini_flash:
            self._init_models()
        return self.gemini_flash

    def get_backup(self) -> ChatGoogleGenerativeAI:
        if not self.gemini_flash_backup:
            self._init_models()
        return self.gemini_flash_backup


model_manager = ModelManager()
