"""
==============================================
BOT ALMA - INTERFACE COMPLETA
==============================================
Interface moderna e profissional para o Bot WhatsApp
- Dashboard com status em tempo real
- Logs em tempo real
- Gerenciamento completo de grupos
- Configuracao de gatilhos
- Configuracao de voz (TTS)
- Configuracao de Whisper
- Configuracao da IA
- Gerenciamento de arquivos PDF
==============================================
"""

import sys
import os
import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QTableWidget, QTableWidgetItem, QPushButton, QLabel,
        QLineEdit, QTextEdit, QComboBox, QCheckBox, QGroupBox,
        QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
        QHeaderView, QSpinBox, QFormLayout, QPlainTextEdit, QFrame,
        QSplitter, QScrollArea, QGridLayout, QProgressBar, QSizePolicy,
        QStackedWidget, QToolButton, QStatusBar
    )
    from PyQt5.QtCore import Qt, QTimer, QSize
    from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QTextCursor
except ImportError:
    print("PyQt5 nao instalado. Execute: pip install PyQt5")
    sys.exit(1)

# Diretorios - Tudo na mesma pasta agora!
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Arquivos de configuracao (todos na pasta do bot baileys)
CONFIG_BOT_FILE = os.path.join(SCRIPT_DIR, 'config_bot.json')
GATILHOS_FILE = os.path.join(SCRIPT_DIR, 'gatilhos_arquivos.json')
IA_CONFIG_FILE = os.path.join(SCRIPT_DIR, 'ia_config.json')
ARQUIVOS_DIR = os.path.join(SCRIPT_DIR, 'arquivos')

# Cores do tema
COLORS = {
    'bg_dark': '#0d1117',
    'bg_card': '#161b22',
    'bg_input': '#21262d',
    'border': '#30363d',
    'text': '#c9d1d9',
    'text_secondary': '#8b949e',
    'accent': '#58a6ff',
    'success': '#3fb950',
    'warning': '#d29922',
    'error': '#f85149',
    'purple': '#a371f7'
}


class ConfigManager:
    """Gerenciador de configuracoes"""

    @staticmethod
    def carregar_config_bot():
        if os.path.exists(CONFIG_BOT_FILE):
            with open(CONFIG_BOT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "nomeBot": "Alma",
            "ignorarGrupos": True,
            "gruposPermitidos": [],
            "voz": "pt-BR-ThalitaMultilingualNeural",
            "modeloWhisper": "large",
            "usarGPU": True
        }

    @staticmethod
    def salvar_config_bot(config):
        with open(CONFIG_BOT_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    @staticmethod
    def carregar_gatilhos():
        if os.path.exists(GATILHOS_FILE):
            with open(GATILHOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    @staticmethod
    def salvar_gatilhos(gatilhos):
        with open(GATILHOS_FILE, 'w', encoding='utf-8') as f:
            json.dump(gatilhos, f, ensure_ascii=False, indent=4)

    @staticmethod
    def carregar_ia_config():
        if os.path.exists(IA_CONFIG_FILE):
            with open(IA_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"ativo": True, "api_key": "", "modelo": "openai/gpt-4o-mini", "prompt_sistema": ""}

    @staticmethod
    def salvar_ia_config(config):
        with open(IA_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)


class CardWidget(QFrame):
    """Widget de card estilizado"""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(15)

        if title:
            self.title_label = QLabel(title)
            self.title_label.setObjectName("cardTitle")
            self.layout.addWidget(self.title_label)

    def addWidget(self, widget):
        self.layout.addWidget(widget)

    def addLayout(self, layout):
        self.layout.addLayout(layout)


class StatusIndicator(QWidget):
    """Indicador de status com LED"""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.led = QLabel()
        self.led.setFixedSize(12, 12)
        self.set_status("offline")
        layout.addWidget(self.led)

        self.label = QLabel(text)
        self.label.setObjectName("statusText")
        layout.addWidget(self.label)
        layout.addStretch()

    def set_status(self, status):
        colors = {
            "online": COLORS['success'],
            "offline": COLORS['error'],
            "connecting": COLORS['warning']
        }
        color = colors.get(status, COLORS['text_secondary'])
        self.led.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
        """)

    def set_text(self, text):
        self.label.setText(text)


class MainWindow(QMainWindow):
    """Janela principal"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bot Alma - Painel de Controle")
        self.setMinimumSize(1200, 800)

        # Carrega configuracoes
        self.config = ConfigManager.carregar_config_bot()
        self.gatilhos = ConfigManager.carregar_gatilhos()
        self.ia_config = ConfigManager.carregar_ia_config()

        # Setup UI
        self.setup_ui()
        self.aplicar_estilo()

        # Timer para atualizar estatisticas
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.atualizar_estatisticas)
        self.stats_timer.start(5000)

    def setup_ui(self):
        """Configura a interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = self.criar_sidebar()
        main_layout.addWidget(sidebar)

        # Conteudo principal
        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.criar_pagina_dashboard())
        self.content_stack.addWidget(self.criar_pagina_grupos())
        self.content_stack.addWidget(self.criar_pagina_gatilhos())
        self.content_stack.addWidget(self.criar_pagina_voz())
        self.content_stack.addWidget(self.criar_pagina_whisper())
        self.content_stack.addWidget(self.criar_pagina_ia())
        self.content_stack.addWidget(self.criar_pagina_arquivos())
        main_layout.addWidget(self.content_stack)

        # Status bar
        self.statusBar().showMessage("Pronto")
        self.statusBar().setStyleSheet(f"background-color: {COLORS['bg_card']}; color: {COLORS['text_secondary']};")

    def criar_sidebar(self):
        """Cria a barra lateral de navegacao"""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo/Titulo
        header = QFrame()
        header.setObjectName("sidebarHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 30, 20, 30)

        title = QLabel("Bot Alma")
        title.setObjectName("sidebarTitle")
        header_layout.addWidget(title)

        subtitle = QLabel("Painel de Controle")
        subtitle.setObjectName("sidebarSubtitle")
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        # Menu items
        menu_items = [
            ("Dashboard", 0),
            ("Grupos Permitidos", 1),
            ("Gatilhos", 2),
            ("Voz (TTS)", 3),
            ("Whisper", 4),
            ("IA / Prompt", 5),
            ("Arquivos PDF", 6)
        ]

        self.menu_buttons = []
        for text, index in menu_items:
            btn = QPushButton(text)
            btn.setObjectName("menuButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=index: self.mudar_pagina(i))
            layout.addWidget(btn)
            self.menu_buttons.append(btn)

        self.menu_buttons[0].setChecked(True)

        layout.addStretch()

        # Versao
        version = QLabel("v1.0.0 - Baileys")
        version.setObjectName("versionLabel")
        version.setAlignment(Qt.AlignCenter)
        layout.addWidget(version)

        return sidebar

    def mudar_pagina(self, index):
        """Muda a pagina ativa"""
        self.content_stack.setCurrentIndex(index)
        for i, btn in enumerate(self.menu_buttons):
            btn.setChecked(i == index)

    def criar_pagina_dashboard(self):
        """Pagina principal com controles do bot"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        # Botoes de controle
        self.btn_iniciar = QPushButton("Iniciar Bot")
        self.btn_iniciar.setObjectName("btnSuccess")
        self.btn_iniciar.setFixedSize(150, 45)
        self.btn_iniciar.clicked.connect(self.iniciar_bot)
        header.addWidget(self.btn_iniciar)

        self.btn_parar = QPushButton("Parar Bot")
        self.btn_parar.setObjectName("btnDanger")
        self.btn_parar.setFixedSize(150, 45)
        self.btn_parar.clicked.connect(self.parar_bot)
        self.btn_parar.setEnabled(False)
        header.addWidget(self.btn_parar)

        layout.addLayout(header)

        # Cards de status
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(20)

        # Card Status
        card_status = CardWidget("Status do Bot")
        self.status_indicator = StatusIndicator("Desconectado")
        card_status.addWidget(self.status_indicator)
        cards_layout.addWidget(card_status)

        # Card Configuracao
        card_config = CardWidget("Configuracao")
        config_info = QLabel(f"Voz: {self.config.get('voz', 'N/A')[:20]}...\nWhisper: {self.config.get('modeloWhisper', 'N/A')}")
        config_info.setObjectName("cardInfo")
        card_config.addWidget(config_info)
        cards_layout.addWidget(card_config)

        # Card Gatilhos
        card_gatilhos = CardWidget("Gatilhos")
        gatilhos_count = QLabel(f"{len(self.gatilhos)} gatilhos configurados")
        gatilhos_count.setObjectName("cardInfo")
        card_gatilhos.addWidget(gatilhos_count)
        cards_layout.addWidget(card_gatilhos)

        layout.addLayout(cards_layout)

        # Logs em tempo real
        logs_card = CardWidget("Logs em Tempo Real")
        self.logs_text = QPlainTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setObjectName("logsArea")
        self.logs_text.setMinimumHeight(400)
        logs_card.addWidget(self.logs_text)

        # Botao limpar logs
        btn_limpar = QPushButton("Limpar Logs")
        btn_limpar.setObjectName("btnSecondary")
        btn_limpar.clicked.connect(lambda: self.logs_text.clear())
        logs_card.addWidget(btn_limpar)

        layout.addWidget(logs_card)

        return page

    def criar_pagina_grupos(self):
        """Pagina de grupos permitidos"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        title = QLabel("Grupos Permitidos")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Instrucoes
        instrucoes = QLabel(
            "Adicione os IDs dos grupos onde o bot deve responder.\n"
            "Para descobrir o ID, veja os logs quando alguem mandar mensagem no grupo."
        )
        instrucoes.setObjectName("instructions")
        layout.addWidget(instrucoes)

        # Card principal
        card = CardWidget()

        # Lista de grupos
        self.lista_grupos = QListWidget()
        self.lista_grupos.setObjectName("listWidget")
        self.lista_grupos.setMinimumHeight(300)
        for grupo in self.config.get('gruposPermitidos', []):
            self.lista_grupos.addItem(grupo)
        card.addWidget(self.lista_grupos)

        # Adicionar grupo
        add_layout = QHBoxLayout()
        self.input_grupo = QLineEdit()
        self.input_grupo.setPlaceholderText("ID do grupo (ex: 120363123456789@g.us)")
        self.input_grupo.setObjectName("inputField")
        add_layout.addWidget(self.input_grupo)

        btn_adicionar = QPushButton("Adicionar")
        btn_adicionar.setObjectName("btnPrimary")
        btn_adicionar.clicked.connect(self.adicionar_grupo)
        add_layout.addWidget(btn_adicionar)

        btn_remover = QPushButton("Remover")
        btn_remover.setObjectName("btnDanger")
        btn_remover.clicked.connect(self.remover_grupo)
        add_layout.addWidget(btn_remover)

        card.addLayout(add_layout)

        # Checkbox
        self.check_ignorar_grupos = QCheckBox("Ignorar grupos que nao estao na lista")
        self.check_ignorar_grupos.setChecked(self.config.get('ignorarGrupos', True))
        self.check_ignorar_grupos.setObjectName("checkbox")
        card.addWidget(self.check_ignorar_grupos)

        layout.addWidget(card)

        # Botao salvar
        btn_salvar = QPushButton("Salvar Configuracoes")
        btn_salvar.setObjectName("btnSuccess")
        btn_salvar.setFixedHeight(50)
        btn_salvar.clicked.connect(self.salvar_grupos)
        layout.addWidget(btn_salvar)

        layout.addStretch()

        return page

    def criar_pagina_gatilhos(self):
        """Pagina de gatilhos"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Header
        title = QLabel("Gatilhos")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Card tabela
        card = CardWidget()

        # Tabela de gatilhos
        self.tabela_gatilhos = QTableWidget()
        self.tabela_gatilhos.setColumnCount(4)
        self.tabela_gatilhos.setHorizontalHeaderLabels(["Palavra-chave", "Arquivo", "Ativo", "Acoes"])
        self.tabela_gatilhos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabela_gatilhos.setObjectName("tableWidget")
        self.tabela_gatilhos.setMinimumHeight(300)
        self.atualizar_tabela_gatilhos()
        card.addWidget(self.tabela_gatilhos)

        layout.addWidget(card)

        # Card novo gatilho
        form_card = CardWidget("Adicionar Novo Gatilho")
        form_layout = QFormLayout()

        self.input_gatilho_palavra = QLineEdit()
        self.input_gatilho_palavra.setPlaceholderText("Ex: CHECKLIST")
        self.input_gatilho_palavra.setObjectName("inputField")
        form_layout.addRow("Palavra-chave:", self.input_gatilho_palavra)

        arquivo_layout = QHBoxLayout()
        self.input_gatilho_arquivo = QLineEdit()
        self.input_gatilho_arquivo.setPlaceholderText("Nome do arquivo PDF")
        self.input_gatilho_arquivo.setObjectName("inputField")
        arquivo_layout.addWidget(self.input_gatilho_arquivo)

        btn_buscar = QPushButton("Buscar")
        btn_buscar.setObjectName("btnSecondary")
        btn_buscar.clicked.connect(self.buscar_arquivo_gatilho)
        arquivo_layout.addWidget(btn_buscar)
        form_layout.addRow("Arquivo:", arquivo_layout)

        form_card.addLayout(form_layout)

        btn_add_gatilho = QPushButton("Adicionar Gatilho")
        btn_add_gatilho.setObjectName("btnPrimary")
        btn_add_gatilho.clicked.connect(self.salvar_gatilho)
        form_card.addWidget(btn_add_gatilho)

        layout.addWidget(form_card)

        return page

    def criar_pagina_voz(self):
        """Pagina de configuracao de voz"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Configuracao de Voz (Edge TTS)")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        card = CardWidget()

        # Combo voz
        form = QFormLayout()

        self.combo_voz = QComboBox()
        self.combo_voz.setObjectName("comboBox")
        vozes = [
            ("Thalita (PT-BR Multilingual)", "pt-BR-ThalitaMultilingualNeural"),
            ("Ava (EN-US Multilingual)", "en-US-AvaMultilingualNeural"),
            ("Emma (EN-US Multilingual)", "en-US-EmmaMultilingualNeural"),
            ("Seraphina (DE Multilingual)", "de-DE-SeraphinaMultilingualNeural"),
            ("Vivienne (FR Multilingual)", "fr-FR-VivienneMultilingualNeural")
        ]

        for nome, valor in vozes:
            self.combo_voz.addItem(nome, valor)

        voz_atual = self.config.get('voz', 'pt-BR-ThalitaMultilingualNeural')
        for i, (_, valor) in enumerate(vozes):
            if valor == voz_atual:
                self.combo_voz.setCurrentIndex(i)
                break

        form.addRow("Voz:", self.combo_voz)
        card.addLayout(form)

        # Botoes
        btns_layout = QHBoxLayout()

        btn_testar = QPushButton("Testar Voz")
        btn_testar.setObjectName("btnSecondary")
        btn_testar.clicked.connect(self.testar_voz)
        btns_layout.addWidget(btn_testar)

        btn_salvar = QPushButton("Salvar")
        btn_salvar.setObjectName("btnSuccess")
        btn_salvar.clicked.connect(self.salvar_voz)
        btns_layout.addWidget(btn_salvar)

        card.addLayout(btns_layout)

        layout.addWidget(card)

        # Info
        info_card = CardWidget("Sobre as Vozes Multilinguais")
        info_text = QLabel(
            "As vozes multilinguais podem falar qualquer idioma automaticamente.\n"
            "A voz detecta o idioma do texto e ajusta a pronuncia.\n\n"
            "Recomendado: Thalita (PT-BR) - otima qualidade em todos os idiomas."
        )
        info_text.setObjectName("instructions")
        info_text.setWordWrap(True)
        info_card.addWidget(info_text)
        layout.addWidget(info_card)

        layout.addStretch()

        return page

    def criar_pagina_whisper(self):
        """Pagina de configuracao do Whisper"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Configuracao do Whisper")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        card = CardWidget()
        form = QFormLayout()

        # Modelo
        self.combo_modelo = QComboBox()
        self.combo_modelo.setObjectName("comboBox")
        modelos = [
            ("Tiny (mais rapido)", "tiny"),
            ("Base", "base"),
            ("Small", "small"),
            ("Medium", "medium"),
            ("Large (mais preciso)", "large")
        ]

        for nome, valor in modelos:
            self.combo_modelo.addItem(nome, valor)

        modelo_atual = self.config.get('modeloWhisper', 'large')
        for i, (_, valor) in enumerate(modelos):
            if valor == modelo_atual:
                self.combo_modelo.setCurrentIndex(i)
                break

        form.addRow("Modelo:", self.combo_modelo)

        # GPU
        self.check_gpu = QCheckBox("Usar GPU (CUDA) - Muito mais rapido!")
        self.check_gpu.setChecked(self.config.get('usarGPU', True))
        self.check_gpu.setObjectName("checkbox")
        form.addRow("", self.check_gpu)

        card.addLayout(form)

        btn_salvar = QPushButton("Salvar Configuracoes")
        btn_salvar.setObjectName("btnSuccess")
        btn_salvar.clicked.connect(self.salvar_whisper)
        card.addWidget(btn_salvar)

        layout.addWidget(card)

        # Info
        info_card = CardWidget("Informacoes")
        info = QLabel(
            "O Whisper transcreve audios para texto.\n\n"
            "Modelos:\n"
            "- Tiny/Base: Rapido, menor precisao\n"
            "- Small/Medium: Equilibrado\n"
            "- Large: Melhor precisao (recomendado)\n\n"
            "Com GPU (RTX 4060): transcricao em 2-5 segundos\n"
            "Sem GPU: pode demorar 30+ segundos"
        )
        info.setObjectName("instructions")
        info.setWordWrap(True)
        info_card.addWidget(info)
        layout.addWidget(info_card)

        layout.addStretch()

        return page

    def criar_pagina_ia(self):
        """Pagina de configuracao da IA"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Configuracao da IA")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Card API
        api_card = CardWidget("API OpenRouter")
        api_form = QFormLayout()

        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.Password)
        self.input_api_key.setText(self.ia_config.get('api_key', ''))
        self.input_api_key.setObjectName("inputField")
        api_form.addRow("API Key:", self.input_api_key)

        self.input_modelo = QLineEdit()
        self.input_modelo.setText(self.ia_config.get('modelo', 'openai/gpt-4o-mini'))
        self.input_modelo.setObjectName("inputField")
        api_form.addRow("Modelo:", self.input_modelo)

        api_card.addLayout(api_form)
        layout.addWidget(api_card)

        # Card Prompt
        prompt_card = CardWidget("Prompt do Sistema")
        self.texto_prompt = QPlainTextEdit()
        self.texto_prompt.setPlainText(self.ia_config.get('prompt_sistema', ''))
        self.texto_prompt.setObjectName("promptArea")
        self.texto_prompt.setMinimumHeight(300)
        prompt_card.addWidget(self.texto_prompt)
        layout.addWidget(prompt_card)

        # Botao salvar
        btn_salvar = QPushButton("Salvar Configuracoes da IA")
        btn_salvar.setObjectName("btnSuccess")
        btn_salvar.setFixedHeight(50)
        btn_salvar.clicked.connect(self.salvar_ia)
        layout.addWidget(btn_salvar)

        return page

    def criar_pagina_arquivos(self):
        """Pagina de gerenciamento de arquivos PDF"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title = QLabel("Arquivos PDF")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        card = CardWidget()

        # Lista de arquivos
        self.lista_arquivos = QListWidget()
        self.lista_arquivos.setObjectName("listWidget")
        self.lista_arquivos.setMinimumHeight(400)
        self.atualizar_lista_arquivos()
        card.addWidget(self.lista_arquivos)

        # Botoes
        btns = QHBoxLayout()

        btn_add = QPushButton("Adicionar PDF")
        btn_add.setObjectName("btnPrimary")
        btn_add.clicked.connect(self.adicionar_pdf)
        btns.addWidget(btn_add)

        btn_abrir_pasta = QPushButton("Abrir Pasta")
        btn_abrir_pasta.setObjectName("btnSecondary")
        btn_abrir_pasta.clicked.connect(lambda: os.startfile(ARQUIVOS_DIR))
        btns.addWidget(btn_abrir_pasta)

        btn_atualizar = QPushButton("Atualizar Lista")
        btn_atualizar.setObjectName("btnSecondary")
        btn_atualizar.clicked.connect(self.atualizar_lista_arquivos)
        btns.addWidget(btn_atualizar)

        card.addLayout(btns)

        layout.addWidget(card)
        layout.addStretch()

        return page

    def aplicar_estilo(self):
        """Aplica estilo moderno"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['bg_dark']};
            }}

            QWidget {{
                color: {COLORS['text']};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }}

            #sidebar {{
                background-color: {COLORS['bg_card']};
                border-right: 1px solid {COLORS['border']};
            }}

            #sidebarHeader {{
                border-bottom: 1px solid {COLORS['border']};
            }}

            #sidebarTitle {{
                font-size: 24px;
                font-weight: bold;
                color: {COLORS['accent']};
            }}

            #sidebarSubtitle {{
                color: {COLORS['text_secondary']};
                font-size: 12px;
            }}

            #menuButton {{
                text-align: left;
                padding: 15px 25px;
                border: none;
                background-color: transparent;
                color: {COLORS['text_secondary']};
                font-size: 14px;
            }}

            #menuButton:hover {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
            }}

            #menuButton:checked {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['accent']};
                border-left: 3px solid {COLORS['accent']};
            }}

            #versionLabel {{
                color: {COLORS['text_secondary']};
                padding: 20px;
                font-size: 11px;
            }}

            #pageTitle {{
                font-size: 28px;
                font-weight: bold;
                color: {COLORS['text']};
                margin-bottom: 10px;
            }}

            #card {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
            }}

            #cardTitle {{
                font-size: 16px;
                font-weight: bold;
                color: {COLORS['text']};
                margin-bottom: 10px;
            }}

            #cardInfo {{
                color: {COLORS['text_secondary']};
                font-size: 14px;
            }}

            #instructions {{
                color: {COLORS['text_secondary']};
                line-height: 1.6;
            }}

            #inputField {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
                color: {COLORS['text']};
            }}

            #inputField:focus {{
                border-color: {COLORS['accent']};
            }}

            #comboBox {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 10px;
                color: {COLORS['text']};
            }}

            #comboBox::drop-down {{
                border: none;
            }}

            #comboBox QAbstractItemView {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['accent']};
            }}

            #checkbox {{
                color: {COLORS['text']};
                spacing: 10px;
            }}

            #checkbox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['bg_input']};
            }}

            #checkbox::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}

            #listWidget {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 5px;
            }}

            #listWidget::item {{
                padding: 12px;
                border-radius: 6px;
                margin: 2px;
            }}

            #listWidget::item:selected {{
                background-color: {COLORS['accent']};
            }}

            #tableWidget {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                gridline-color: {COLORS['border']};
            }}

            #tableWidget::item {{
                padding: 10px;
            }}

            #tableWidget::item:selected {{
                background-color: {COLORS['accent']};
            }}

            QHeaderView::section {{
                background-color: {COLORS['bg_card']};
                padding: 12px;
                border: none;
                border-bottom: 1px solid {COLORS['border']};
                font-weight: bold;
            }}

            #logsArea, #promptArea {{
                background-color: {COLORS['bg_input']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 15px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 12px;
                color: {COLORS['text']};
            }}

            #btnPrimary {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
            }}

            #btnPrimary:hover {{
                background-color: #4393e4;
            }}

            #btnSuccess {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
            }}

            #btnSuccess:hover {{
                background-color: #2ea043;
            }}

            #btnDanger {{
                background-color: {COLORS['error']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
            }}

            #btnDanger:hover {{
                background-color: #da3633;
            }}

            #btnSecondary {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px 24px;
            }}

            #btnSecondary:hover {{
                background-color: {COLORS['border']};
            }}

            QScrollBar:vertical {{
                background-color: {COLORS['bg_dark']};
                width: 12px;
                border-radius: 6px;
            }}

            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                border-radius: 6px;
                min-height: 30px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['text_secondary']};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

    # ========== ACOES ==========

    def iniciar_bot(self):
        """Inicia o bot em uma janela CMD separada (como dar 2 cliques no .bat)"""
        # Abre o bot em uma nova janela CMD
        bat_file = os.path.join(SCRIPT_DIR, "Iniciar Bot Alma.bat")

        if os.path.exists(bat_file):
            # Abre o .bat em nova janela CMD (como dar 2 cliques)
            subprocess.Popen(f'start cmd /k "{bat_file}"', shell=True, cwd=SCRIPT_DIR)
            self.adicionar_log("[BOT] Janela CMD aberta! O bot esta rodando em outra janela.")
            self.status_indicator.set_status("online")
            self.status_indicator.set_text("Rodando (CMD externo)")
        else:
            # Se nao tiver o .bat, roda direto o node
            subprocess.Popen('start cmd /k node index.js', shell=True, cwd=SCRIPT_DIR)
            self.adicionar_log("[BOT] Janela CMD aberta com node index.js")
            self.status_indicator.set_status("online")
            self.status_indicator.set_text("Rodando (CMD externo)")

    def parar_bot(self):
        """Para o bot - instrui usuario a fechar a janela CMD"""
        QMessageBox.information(
            self,
            "Parar Bot",
            "Para parar o bot, feche a janela CMD onde ele esta rodando.\n\n"
            "Ou pressione Ctrl+C na janela do bot."
        )
        self.status_indicator.set_status("offline")
        self.status_indicator.set_text("Desconectado")

    def adicionar_log(self, texto):
        """Adiciona texto ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs_text.appendPlainText(f"[{timestamp}] {texto}")
        self.logs_text.moveCursor(QTextCursor.End)

    def atualizar_status(self, status):
        """Atualiza o status do bot"""
        if status == "starting":
            self.status_indicator.set_status("connecting")
            self.status_indicator.set_text("Iniciando...")
        elif status == "running":
            self.status_indicator.set_status("online")
            self.status_indicator.set_text("Conectado")
        else:
            self.status_indicator.set_status("offline")
            self.status_indicator.set_text("Desconectado")

    def atualizar_estatisticas(self):
        """Atualiza estatisticas periodicamente"""
        pass  # Implementar se necessario

    def adicionar_grupo(self):
        """Adiciona grupo"""
        grupo = self.input_grupo.text().strip()
        if grupo and '@g.us' in grupo:
            self.lista_grupos.addItem(grupo)
            self.input_grupo.clear()
        else:
            QMessageBox.warning(self, "Aviso", "ID invalido. Deve conter @g.us")

    def remover_grupo(self):
        """Remove grupo"""
        item = self.lista_grupos.currentItem()
        if item:
            self.lista_grupos.takeItem(self.lista_grupos.row(item))

    def salvar_grupos(self):
        """Salva grupos"""
        grupos = [self.lista_grupos.item(i).text() for i in range(self.lista_grupos.count())]
        self.config['gruposPermitidos'] = grupos
        self.config['ignorarGrupos'] = self.check_ignorar_grupos.isChecked()
        ConfigManager.salvar_config_bot(self.config)
        QMessageBox.information(self, "Salvo", "Configuracoes salvas!")
        self.adicionar_log("[CONFIG] Grupos atualizados")

    def atualizar_tabela_gatilhos(self):
        """Atualiza tabela"""
        self.tabela_gatilhos.setRowCount(len(self.gatilhos))
        for i, (palavra, config) in enumerate(self.gatilhos.items()):
            self.tabela_gatilhos.setItem(i, 0, QTableWidgetItem(palavra))
            arquivos = ', '.join(config.get('arquivos', []))
            self.tabela_gatilhos.setItem(i, 1, QTableWidgetItem(arquivos))
            ativo = "Sim" if config.get('ativo', True) else "Nao"
            self.tabela_gatilhos.setItem(i, 2, QTableWidgetItem(ativo))

    def buscar_arquivo_gatilho(self):
        """Busca arquivo"""
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar", ARQUIVOS_DIR, "PDF (*.pdf)")
        if arquivo:
            self.input_gatilho_arquivo.setText(os.path.basename(arquivo))

    def salvar_gatilho(self):
        """Salva gatilho"""
        palavra = self.input_gatilho_palavra.text().strip().upper()
        arquivo = self.input_gatilho_arquivo.text().strip()

        if not palavra:
            QMessageBox.warning(self, "Aviso", "Digite a palavra-chave")
            return

        self.gatilhos[palavra] = {
            "tipo": "simples",
            "mensagem": "",
            "arquivos": [arquivo] if arquivo else [],
            "audio": "",
            "ativo": True
        }

        ConfigManager.salvar_gatilhos(self.gatilhos)
        self.atualizar_tabela_gatilhos()
        self.input_gatilho_palavra.clear()
        self.input_gatilho_arquivo.clear()
        QMessageBox.information(self, "Salvo", f"Gatilho '{palavra}' salvo!")
        self.adicionar_log(f"[GATILHO] Adicionado: {palavra}")

    def testar_voz(self):
        """Testa voz"""
        voz = self.combo_voz.currentData()
        texto = "Ola amor, como voce esta? Estou aqui para te ajudar."
        arquivo = os.path.join(SCRIPT_DIR, "teste_voz.mp3")

        try:
            subprocess.run(['edge-tts', '--voice', voz, '--text', texto, '--write-media', arquivo], check=True)
            os.startfile(arquivo)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro: {e}")

    def salvar_voz(self):
        """Salva voz"""
        self.config['voz'] = self.combo_voz.currentData()
        ConfigManager.salvar_config_bot(self.config)
        QMessageBox.information(self, "Salvo", "Voz salva!")
        self.adicionar_log(f"[CONFIG] Voz alterada: {self.config['voz']}")

    def salvar_whisper(self):
        """Salva whisper"""
        self.config['modeloWhisper'] = self.combo_modelo.currentData()
        self.config['usarGPU'] = self.check_gpu.isChecked()
        ConfigManager.salvar_config_bot(self.config)
        QMessageBox.information(self, "Salvo", "Configuracoes do Whisper salvas!")
        self.adicionar_log(f"[CONFIG] Whisper: {self.config['modeloWhisper']}, GPU: {self.config['usarGPU']}")

    def salvar_ia(self):
        """Salva IA"""
        self.ia_config['api_key'] = self.input_api_key.text()
        self.ia_config['modelo'] = self.input_modelo.text()
        self.ia_config['prompt_sistema'] = self.texto_prompt.toPlainText()
        self.ia_config['ativo'] = True
        ConfigManager.salvar_ia_config(self.ia_config)
        QMessageBox.information(self, "Salvo", "Configuracoes da IA salvas!")
        self.adicionar_log("[CONFIG] IA atualizada")

    def atualizar_lista_arquivos(self):
        """Atualiza lista de PDFs"""
        self.lista_arquivos.clear()
        if os.path.exists(ARQUIVOS_DIR):
            for arquivo in os.listdir(ARQUIVOS_DIR):
                if arquivo.endswith('.pdf'):
                    self.lista_arquivos.addItem(arquivo)

    def adicionar_pdf(self):
        """Adiciona PDF"""
        arquivos, _ = QFileDialog.getOpenFileNames(self, "Selecionar PDFs", "", "PDF (*.pdf)")
        for arquivo in arquivos:
            import shutil
            destino = os.path.join(ARQUIVOS_DIR, os.path.basename(arquivo))
            shutil.copy(arquivo, destino)
        self.atualizar_lista_arquivos()
        if arquivos:
            QMessageBox.information(self, "Sucesso", f"{len(arquivos)} arquivo(s) adicionado(s)!")

    def closeEvent(self, event):
        """Ao fechar"""
        reply = QMessageBox.question(
            self, 'Confirmar',
            'Deseja fechar o painel de controle?\n\n'
            'Nota: Se o bot estiver rodando em uma janela CMD,\n'
            'ele continuara funcionando.',
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
