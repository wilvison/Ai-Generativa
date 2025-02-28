#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CodeDocGen: IA Generativa para Documentação Automática de Códigos
Este módulo contém a implementação principal do gerador de documentação.
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Optional, Union
import openai
from pathlib import Path
import tiktoken
import re

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
DEFAULT_MODEL = "gpt-4"
MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.2
SUPPORTED_LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".java": "Java",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".go": "Go",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".rs": "Rust"
}
OUTPUT_FORMATS = ["markdown", "html", "pdf"]

class DocGenerator:
    """
    Classe principal para geração de documentação a partir de código-fonte
    usando Large Language Models.
    """
    
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        api_key: Optional[str] = None,
        output_format: str = "markdown"
    ):
        """
        Inicializa o gerador de documentação.
        
        Args:
            model: Nome do modelo LLM a ser usado.
            temperature: Temperatura para geração (0.0-1.0).
            api_key: Chave de API para o serviço LLM.
            output_format: Formato de saída da documentação.
        """
        self.model = model
        self.temperature = temperature
        self.output_format = output_format.lower()
        
        if self.output_format not in OUTPUT_FORMATS:
            raise ValueError(f"Formato de saída '{output_format}' não suportado. Use um dos seguintes: {', '.join(OUTPUT_FORMATS)}")
        
        # Configura a API key
        if api_key:
            openai.api_key = api_key
        elif os.environ.get("OPENAI_API_KEY"):
            openai.api_key = os.environ.get("OPENAI_API_KEY")
        else:
            logger.warning("Nenhuma API key fornecida. Use api_key ou defina OPENAI_API_KEY no ambiente.")
        
        # Inicializa o codificador de tokens
        try:
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except:
            # Fallback para o codificador cl100k_base que é usado pelo GPT-4
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
        logger.info(f"DocGenerator inicializado com modelo {model} e temperatura {temperature}")
        
    def _get_language_from_extension(self, file_path: str) -> str:
        """
        Identifica a linguagem de programação com base na extensão do arquivo.
        
        Args:
            file_path: Caminho para o arquivo de código.
            
        Returns:
            Nome da linguagem de programação.
        """
        ext = os.path.splitext(file_path)[1].lower()
        return SUPPORTED_LANGUAGES.get(ext, "Desconhecido")
    
    def _count_tokens(self, text: str) -> int:
        """
        Conta o número de tokens em um texto.
        
        Args:
            text: Texto para contar tokens.
            
        Returns:
            Número de tokens.
        """
        return len(self.tokenizer.encode(text))
    
    def _truncate_code(self, code: str, max_tokens: int = MAX_TOKENS-1000) -> str:
        """
        Trunca o código se exceder o limite de tokens.
        
        Args:
            code: Código fonte a ser truncado.
            max_tokens: Número máximo de tokens permitidos.
            
        Returns:
            Código truncado se necessário.
        """
        tokens = self.tokenizer.encode(code)
        if len(tokens) <= max_tokens:
            return code
        
        logger.warning(f"Código excede o limite de tokens. Truncando de {len(tokens)} para {max_tokens} tokens.")
        truncated_tokens = tokens[:max_tokens]
        truncated_code = self.tokenizer.decode(truncated_tokens)
        return truncated_code + "\n\n# [Código truncado devido a limitações de tamanho]"
    
    def _create_prompt(self, code: str, language: str, file_name: str) -> str:
        """
        Cria um prompt especializado para o LLM com base no código e linguagem.
        
        Args:
            code: Código fonte a ser documentado.
            language: Linguagem de programação do código.
            file_name: Nome do arquivo de código.
            
        Returns:
            Prompt formatado para o LLM.
        """
        base_prompt = f"""
        # Tarefa: Gerar documentação técnica detalhada para o código abaixo
        
        ## Informações do Arquivo
        - Nome do arquivo: {file_name}
        - Linguagem: {language}
        
        ## Código a ser documentado:
        ```{language.lower()}
        {code}
        ```
        
        ## Instruções para Geração de Documentação
        
        1. Comece com uma visão geral explicando o propósito principal do código.
        2. Identifique e descreva as principais classes, funções, métodos e suas responsabilidades.
        3. Documente os parâmetros, tipos de retorno e exceções lançadas.
        4. Explique a lógica de negócio e algoritmos implementados.
        5. Identifique padrões de design ou arquiteturais utilizados.
        6. Inclua exemplos de uso, quando aplicável.
        7. Destaque quaisquer possíveis problemas, limitações ou considerações de performance.
        
        ## Formato da Documentação
        Gere a documentação no formato Markdown estruturado, incluindo cabeçalhos, listas, tabelas e blocos de código quando apropriado.
        
        ## Documentação:
        """
        
        return base_prompt
    
    def generate(self, file_path: str) -> str:
        """
        Gera documentação para um único arquivo de código.
        
        Args:
            file_path: Caminho para o arquivo de código.
            
        Returns:
            Documentação gerada.
        """
        try:
            # Lê o arquivo
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Obtém informações do arquivo
            file_name = os.path.basename(file_path)
            language = self._get_language_from_extension(file_path)
            
            if language == "Desconhecido":
                logger.warning(f"Linguagem desconhecida para o arquivo {file_path}. A documentação pode não ser ideal.")
            
            # Trunca o código se necessário
            code = self._truncate_code(code)
            
            # Cria o prompt
            prompt = self._create_prompt(code, language, file_name)
            
            logger.info(f"Gerando documentação para {file_path} ({language})")
            
            # Chama a API do LLM
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um assistente especializado em gerar documentação técnica de alta qualidade para código-fonte."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=MAX_TOKENS
            )
            
            # Extrai e retorna a documentação
            documentation = response.choices[0].message.content.strip()
            
            # Converte para o formato desejado, se necessário
            if self.output_format != "markdown":
                documentation = self._convert_format(documentation)
                
            return documentation
            
        except Exception as e:
            logger.error(f"Erro ao gerar documentação para {file_path}: {str(e)}")
            raise
    
    def generate_project(self, project_dir: str, exclude_dirs: List[str] = None) -> Dict[str, str]:
        """
        Gera documentação para um projeto inteiro.
        
        Args:
            project_dir: Diretório do projeto.
            exclude_dirs: Lista de diretórios a serem excluídos.
            
        Returns:
            Dicionário com caminhos de arquivo e suas documentações.
        """
        if exclude_dirs is None:
            exclude_dirs = ['.git', 'node_modules', 'venv', '__pycache__', 'dist', 'build']
            
        project_docs = {}
        
        for root, dirs, files in os.walk(project_dir):
            # Filtra diretórios a serem excluídos
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_path = os.path.join(root, file)
                extension = os.path.splitext(file)[1].lower()
                
                if extension in SUPPORTED_LANGUAGES:
                    try:
                        # Gera documentação para este arquivo
                        doc = self.generate(file_path)
                        
                        # Armazena a documentação
                        rel_path = os.path.relpath(file_path, project_dir)
                        project_docs[rel_path] = doc
                        
                        logger.info(f"Documentação gerada com sucesso para {rel_path}")
                        
                    except Exception as e:
                        logger.error(f"Falha ao gerar documentação para {file_path}: {str(e)}")
        
        return project_docs
    
    def _convert_format(self, markdown_doc: str) -> str:
        """
        Converte a documentação de Markdown para outros formatos.
        
        Args:
            markdown_doc: Documentação em formato Markdown.
            
        Returns:
            Documentação no formato de saída solicitado.
        """
        if self.output_format == "html":
            # Implementar conversão para HTML
            # Esta é uma implementação simplificada
            try:
                import markdown
                return markdown.markdown(markdown_doc)
            except ImportError:
                logger.warning("Biblioteca 'markdown' não encontrada. Instalando: pip install markdown")
                raise
        
        elif self.output_format == "pdf":
            # Implementar conversão para PDF
            # Esta é uma implementação simplificada
            try:
                import markdown
                from weasyprint import HTML
                
                html = markdown.markdown(markdown_doc)
                # Aqui você normalmente retornaria bytes do PDF, mas para simplicidade retornamos o HTML
                logger.warning("Conversão real para PDF requer implementação completa")
                return html
            except ImportError:
                logger.warning("Bibliotecas necessárias não encontradas. Instalando: pip install markdown weasyprint")
                raise
                
        # Formato padrão é markdown, retorna sem alterações
        return markdown_doc
    
    def save(self, documentation: str, output_path: str) -> None:
        """
        Salva a documentação em um arquivo.
        
        Args:
            documentation: Documentação gerada.
            output_path: Caminho para salvar o arquivo.
        """
        # Certifica-se de que o diretório existe
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # Determina a extensão correta com base no formato
        if self.output_format == "html" and not output_path.endswith(".html"):
            output_path = output_path.rsplit(".", 1)[0] + ".html"
        elif self.output_format == "pdf" and not output_path.endswith(".pdf"):
            output_path = output_path.rsplit(".", 1)[0] + ".pdf"
        elif self.output_format == "markdown" and not output_path.endswith((".md", ".markdown")):
            output_path = output_path + ".md"
        
        # Salva o arquivo
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(documentation)
            
        logger.info(f"Documentação salva em: {output_path}")
    
    def save_project(self, project_docs: Dict[str, str], output_dir: str) -> None:
        """
        Salva a documentação de um projeto inteiro.
        
        Args:
            project_docs: Dicionário com caminhos de arquivo e suas documentações.
            output_dir: Diretório para salvar a documentação.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Processa cada arquivo e sua documentação
        for rel_path, doc in project_docs.items():
            # Cria o caminho de saída correspondente
            output_path = os.path.join(output_dir, rel_path)
            
            # Adiciona a extensão correta
            if self.output_format == "html":
                output_path = output_path.rsplit(".", 1)[0] + ".html"
            elif self.output_format == "pdf":
                output_path = output_path.rsplit(".", 1)[0] + ".pdf"
            else:  # markdown
                output_path = output_path.rsplit(".", 1)[0] + ".md"
            
            # Cria o diretório para este arquivo, se necessário
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Salva a documentação
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(doc)
                
            logger.info(f"Documentação salva em: {output_path}")
        
        # Cria um índice
        self._create_index(project_docs, output_dir)
        
    def _create_index(self, project_docs: Dict[str, str], output_dir: str) -> None:
        """
        Cria um arquivo de índice para a documentação do projeto.
        
        Args:
            project_docs: Dicionário com caminhos de arquivo e suas documentações.
            output_dir: Diretório onde a documentação está salva.
        """
        # Define o nome do arquivo de índice baseado no formato
        if self.output_format == "html":
            index_file = os.path.join(output_dir, "index.html")
            header = "<!DOCTYPE html>\n<html>\n<head>\n<title>Documentação do Projeto</title>\n</head>\n<body>\n"
            footer = "</body>\n</html>"
            item_template = '<li><a href="{}">{}</a></li>\n'
            list_start = '<h1>Índice da Documentação</h1>\n<ul>\n'
            list_end = '</ul>\n'
        else:  # markdown e base para PDF
            index_file = os.path.join(output_dir, "index.md")
            header = "# Índice da Documentação\n\n"
            footer = ""
            item_template = "- [{}]({})\n"
            list_start = ""
            list_end = ""
        
        # Cria o conteúdo do índice
        content = header + list_start
        
        # Agrupa os arquivos por diretório para uma melhor organização
        grouped_files = {}
        for rel_path in project_docs.keys():
            dir_name = os.path.dirname(rel_path)
            if dir_name not in grouped_files:
                grouped_files[dir_name] = []
            grouped_files[dir_name].append(rel_path)
        
        # Adiciona cada grupo ao índice
        for dir_name, files in sorted(grouped_files.items()):
            if dir_name:
                if self.output_format == "html":
                    content += f'<h2>{dir_name}</h2>\n<ul>\n'
                else:
                    content += f"\n## {dir_name}\n\n"
            
            for file_path in sorted(files):
                # Determina o caminho para o link
                if self.output_format == "html":
                    link_path = file_path.rsplit(".", 1)[0] + ".html"
                elif self.output_format == "pdf":
                    link_path = file_path.rsplit(".", 1)[0] + ".pdf"
                else:  # markdown
                    link_path = file_path.rsplit(".", 1)[0] + ".md"
                
                # Adiciona o item ao índice
                content += item_template.format(link_path, os.path.basename(file_path))
            
            if dir_name and self.output_format == "html":
                content += '</ul>\n'
        
        content += list_end + footer
        
        # Salva o arquivo de índice
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        logger.info(f"Índice de documentação criado em: {index_file}")

def main():
    """
    Função principal para uso via linha de comando.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="CodeDocGen: Gerador de Documentação Automática usando IA")
    
    parser.add_argument("input", help="Caminho para o arquivo ou diretório de entrada")
    parser.add_argument("-o", "--output", help="Caminho para o arquivo ou diretório de saída")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"Modelo LLM a ser usado (padrão: {DEFAULT_MODEL})")
    parser.add_argument("-t", "--temperature", type=float, default=DEFAULT_TEMPERATURE, 
                        help=f"Temperatura para geração (0.0-1.0, padrão: {DEFAULT_TEMPERATURE})")
    parser.add_argument("-f", "--format", choices=OUTPUT_FORMATS, default="markdown",
                        help=f"Formato de saída (padrão: markdown)")
    parser.add_argument("-e", "--exclude", nargs="+", default=None,
                        help="Diretórios a serem excluídos (para projetos)")
    
    args = parser.parse_args()
    
    # Inicializa o gerador
    doc_gen = DocGenerator(
        model=args.model,
        temperature=args.temperature,
        output_format=args.format
    )
    
    # Verifica se é um arquivo ou diretório
    if os.path.isfile(args.input):
        # Gera documentação para um arquivo
        documentation = doc_gen.generate(args.input)
        
        # Define o caminho de saída se não fornecido
        if not args.output:
            base_name = os.path.splitext(args.input)[0]
            args.output = f"{base_name}_documentacao.{args.format if args.format != 'markdown' else 'md'}"
        
        # Salva a documentação
        doc_gen.save(documentation, args.output)
        
    elif os.path.isdir(args.input):
        # Gera documentação para um projeto
        project_docs = doc_gen.generate_project(args.input, args.exclude)
        
        # Define o diretório de saída se não fornecido
        if not args.output:
            args.output = os.path.join(os.path.dirname(args.input), "documentacao")
        
        # Salva a documentação do projeto
        doc_gen.save_project(project_docs, args.output)
        
    else:
        logger.error(f"Entrada inválida: {args.input}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
