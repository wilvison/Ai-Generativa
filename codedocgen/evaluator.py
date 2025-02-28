#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Módulo de avaliação para o CodeDocGen.
Implementa métricas para avaliar a qualidade da documentação gerada.
"""

import os
import re
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import openai

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
DEFAULT_MODEL = "gpt-4"
MAX_TOKENS = 4096

# Ensure NLTK dependencies are downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class DocEvaluator:
    """
    Classe para avaliar a qualidade da documentação gerada.
    Implementa várias métricas de avaliação.
    """
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        api_key: Optional[str] = None
    ):
        """
        Inicializa o avaliador de documentação.
        
        Args:
            model: Nome do modelo LLM a ser usado para avaliações semânticas.
            api_key: Chave de API para o serviço LLM.
        """
        self.model = model
        
        # Configura a API key
        if api_key:
            openai.api_key = api_key
        elif os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
        else:
            logger.warning("Nenhuma API key fornecida. Use api_key ou defina OPENAI_API_KEY no ambiente.")
        
        logger.info(f"DocEvaluator inicializado com modelo {model}")
    
    def evaluate_completeness(self, code: str, documentation: str) -> float:
        """
        Avalia o quão completa é a documentação em relação ao código.
        
        Args:
            code: Código fonte.
            documentation: Documentação gerada.
            
        Returns:
            Pontuação de completude (0-1).
        """
        # Extrai funções, classes e métodos do código (implementação simplificada)
        code_elements = self._extract_code_elements(code)
        
        # Verifica quais elementos foram mencionados na documentação
        mentioned_count = 0
        for element in code_elements:
            if element.lower() in documentation.lower():
                mentioned_count += 1
        
        # Calcula a pontuação de completude
        if not code_elements:
            return 1.0  # Se não há elementos, a documentação é completa por definição
            
        completeness_score = mentioned_count / len(code_elements)
        return completeness_score
    
    def evaluate_clarity(self, documentation: str) -> float:
        """
        Avalia a clareza da documentação usando métricas de legibilidade.
        
        Args:
            documentation: Documentação gerada.
            
        Returns:
            Pontuação de clareza (0-1).
        """
        # Tokeniza a documentação em sentenças e palavras
        sentences = sent_tokenize(documentation)
        words = word_tokenize(documentation)
        
        if not sentences or not words:
            return 0.0
        
        # Calcula o comprimento médio das sentenças
        avg_sentence_length = len(words) / len(sentences)
        
        # Calcula a pontuação de clareza baseada no comprimento das sentenças
        # Sentenças muito longas podem ser difíceis de entender
        clarity_score = 1.0 - min(1.0, max(0.0, (avg_sentence_length - 15) / 25))
        
        return clarity_score
    
    def evaluate_accuracy(self, code: str, documentation: str) -> float:
        """
        Av
