import pygame
import sys
import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox

# Import compiler phases
from lexer import tokenize_sql
from parser import Parser
from semantic import SemanticAnalyzer

# Tree visualization
try:
    from graphviz import Digraph
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False
    print(" Install graphviz: pip install graphviz")

# Image loading
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Install Pillow: pip install Pillow")


# GRAPHVIZ TREE GENERATOR Layout - Enhanced

class GraphvizTreeGenerator:
    def __init__(self):
        self.counter = 0
        self.graph = None
        self.node_map = {}

    def _count_nodes(self, root):
        if not root:
            return 0
        count = 1
        for child in root.children:
            count += self._count_nodes(child)
        return count

    def _get_tree_stats(self, root):
        if not root:
            return 0, 0, 0, 0

        def get_max_width_at_level(node, level=0, max_level=50):
            if level > max_level or not node:
                return 0
            if not node.children:
                return 1
            return max(len(node.children), max(get_max_width_at_level(child, level+1, max_level) for child in node.children))

        def get_max_depth(node, depth=0, max_depth=50):
            if depth > max_depth or not node:
                return depth
            if not node.children:
                return depth
            return max(get_max_depth(child, depth+1, max_depth) for child in node.children)

        def get_avg_children_per_node(node):
            if not node:
                return 0
            total = len(node.children)
            count = 1 if node.children else 0
            for child in node.children:
                t, c = get_avg_children_per_node(child)
                total += t
                count += c
            return total, count

        total_nodes = self._count_nodes(root)
        max_depth = get_max_depth(root)
        max_width = get_max_width_at_level(root)
        t, c = get_avg_children_per_node(root)
        avg_children = t / max(1, c)
        return total_nodes, max_depth, max_width, avg_children

    def generate_tree_image(self, root, filename="parse_tree"):
        if not root:
            return None, {}

        total_nodes, max_depth, max_width, avg_children = self._get_tree_stats(root)
        nodesep = 0.5
        ranksep = 0.6
        if total_nodes > 20:
            nodesep = 0.7
            ranksep = 0.9
        if total_nodes > 50:
            nodesep = 1.0
            ranksep = 1.4
        if max_width > max_depth * 2:
            nodesep *= 1.5

        self.graph = Digraph(format='png')
        self.graph.attr(rankdir='TB')
        self.graph.attr(nodesep=str(nodesep))
        self.graph.attr(ranksep=str(ranksep))
        self.graph.attr(splines='ortho')
        self.graph.attr('node', shape='box', style='filled,rounded', fontname='Arial Bold', fontsize='14', margin='0.3,0.15', height='0.5', width='0')
        self.graph.attr('edge', color='#4A5568', penwidth='2', arrowsize='1.2')

        self.counter = 0
        self.node_map = {}
        self._add_node(root)

        try:
            output_path = self.graph.render(filename, cleanup=True)
            return output_path, self.node_map
        except Exception as e:
            print(f"Error rendering tree: {e}")
            return None, {}

    def _add_node(self, node, parent_id=None):
        node_id = f"node{self.counter}"
        self.counter += 1
        node.node_id = node_id
        self.node_map[node_id] = node

        label = node.rule
        fillcolor = "#E3F2FD"
        fontcolor = "#1565C0"
        border_color = "#1976D2"
        
        if label.endswith("Stmt"):
            fillcolor = "#BBDEFB"
            fontcolor = "#0D47A1"
            border_color = "#1565C0"
        elif label in ["CREATE", "TABLE", "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE"]:
            fillcolor = "#C8E6C9"
            fontcolor = "#1B5E20"
            border_color = "#2E7D32"
        elif label.startswith("Table:"):
            fillcolor = "#FFCDD2"
            fontcolor = "#B71C1C"
            border_color = "#C62828"
        elif label.startswith("Col:"):
            fillcolor = "#FFF9C4"
            fontcolor = "#F57F17"
            border_color = "#F9A825"
        elif label.startswith("Type:"):
            fillcolor = "#E1BEE7"
            fontcolor = "#4A148C"
            border_color = "#6A1B9A"
        elif label.startswith("Value:") or label.startswith("Val:"):
            fillcolor = "#C5E1A5"
            fontcolor = "#33691E"
            border_color = "#558B2F"
        elif label == "Comparison":
            fillcolor = "#FFE0B2"
            fontcolor = "#E65100"
            border_color = "#F57C00"
        elif label in ["AND", "OR", "NOT"]:
            fillcolor = "#FFCCBC"
            fontcolor = "#BF360C"
            border_color = "#D84315"
        elif label == "Query":
            fillcolor = "#263238"
            fontcolor = "#FFFFFF"
            border_color = "#37474F"

        self.graph.node(node_id, label, fillcolor=fillcolor, fontcolor=fontcolor, color=border_color, penwidth='2')
        if parent_id:
            self.graph.edge(parent_id, node_id)
        for child in node.children:
            self._add_node(child, node_id)


# SCROLLBAR WIDGET

class Scrollbar:
    def __init__(self, x, y, width, height, orientation='vertical'):
        self.rect = pygame.Rect(x, y, width, height)
        self.orientation = orientation
        self.handle_rect = None
        self.dragging = False
        self.scroll_pos = 0
        self.content_size = 1000
        self.visible_size = 100
        self.update_handle()

    def update_handle(self):
        if self.content_size <= self.visible_size:
            self.handle_rect = None
            return
        handle_ratio = self.visible_size / self.content_size
        if self.orientation == 'vertical':
            handle_height = max(30, self.rect.height * handle_ratio)
            handle_y = self.rect.y + (self.rect.height - handle_height) * self.scroll_pos
            self.handle_rect = pygame.Rect(self.rect.x, handle_y, self.rect.width, handle_height)
        else:
            handle_width = max(30, self.rect.width * handle_ratio)
            handle_x = self.rect.x + (self.rect.width - handle_width) * self.scroll_pos
            self.handle_rect = pygame.Rect(handle_x, self.rect.y, handle_width, self.rect.height)

    def handle_event(self, event, mouse_pos):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.handle_rect and self.handle_rect.collidepoint(mouse_pos):
                self.dragging = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            if self.orientation == 'vertical':
                total_range = self.rect.height - self.handle_rect.height
                if total_range > 0:
                    delta = event.rel[1]
                    self.scroll_pos += delta / total_range
                    self.scroll_pos = max(0, min(1, self.scroll_pos))
                    self.update_handle()
            else:
                total_range = self.rect.width - self.handle_rect.width
                if total_range > 0:
                    delta = event.rel[0]
                    self.scroll_pos += delta / total_range
                    self.scroll_pos = max(0, min(1, self.scroll_pos))
                    self.update_handle()
            return True
        return False

    def get_scroll_offset(self):
        max_scroll = max(0, self.content_size - self.visible_size)
        return int(self.scroll_pos * max_scroll)

    def draw(self, surface, palette):
        if self.handle_rect:
            pygame.draw.rect(surface, palette["DIVIDER"], self.rect, border_radius=8)
            shadow_rect = self.handle_rect.copy()
            shadow_rect.x += 2
            shadow_rect.y += 2
            pygame.draw.rect(surface, (0, 0, 0, 60), shadow_rect, border_radius=8)
            pygame.draw.rect(surface, palette["BUTTON"], self.handle_rect, border_radius=8)


# COLOR PALETTES

PALETTE_DARK = {
    "BG": (20, 24, 32),
    "PANEL": (32, 38, 48),
    "FONT": (230, 235, 245),
    "TITLE": (100, 180, 255),
    "SUBTITLE": (150, 160, 180),
    "HIGHLIGHT": (70, 130, 80),
    "HIGHLIGHT_TREE": (255, 215, 0, 150),
    "LINE_NUM": (100, 120, 160),
    "DIVIDER": (60, 70, 85),
    "BUTTON": (65, 75, 95),
    "BUTTON_HOVER": (85, 95, 115),
    "BUTTON_ACTIVE": (110, 150, 200),
    "SCROLLBAR": (75, 85, 100),
    "CARD_BG": (40, 46, 58),
    "CARD_BORDER": (70, 80, 100),
    "TOKEN_CODE": {
        "KEYWORD": (220, 130, 240),
        "IDENTIFIER": (240, 210, 140),
        "STRING_LITERAL": (160, 210, 130),
        "INTEGER_LITERAL": (220, 170, 110),
        "FLOAT_LITERAL": (220, 170, 110),
        "OPERATOR": (100, 200, 240),
        "DELIMITER": (180, 190, 210),
    },
    "TOKEN_LIST": {"ERROR": (255, 100, 100)},
    "SUCCESS": (100, 220, 140),
    "INFO": (100, 180, 255),
}
PALETTE_DARK["TOKEN_LIST"].update(PALETTE_DARK["TOKEN_CODE"])

PALETTE_LIGHT = {
    "BG": (248, 248, 246),  # Warm off-white background
    "PANEL": (255, 255, 254),  # Very soft white
    "FONT": (33, 36, 44),  # Warm dark gray (less harsh)
    "TITLE": (25, 95, 175),  # Softer blue
    "SUBTITLE": (105, 115, 130),  # Warmer gray
    "HIGHLIGHT": (255, 150, 100),  # Warm orange
    "HIGHLIGHT_TREE": (255, 235, 150, 120),  # Warmer highlight
    "LINE_NUM": (160, 165, 175),
    "DIVIDER": (225, 228, 235),  # Softer borders
    "BUTTON": (240, 242, 248),  # Very soft button bg
    "BUTTON_HOVER": (225, 230, 245),  # Soft hover
    "BUTTON_ACTIVE": (180, 210, 245),  # Softer blue
    "SCROLLBAR": (205, 210, 220),  # Softer scrollbar
    "CARD_BG": (252, 254, 255),  # Very pale blue
    "CARD_BORDER": (210, 220, 230),  # Softer borders
    "TOKEN_CODE": {
        "KEYWORD": (120, 40, 160),  # Softer purple
        "IDENTIFIER": (30, 100, 180),  # Softer blue
        "STRING_LITERAL": (50, 140, 50),  # Softer green
        "INTEGER_LITERAL": (180, 100, 30),  # Softer orange
        "FLOAT_LITERAL": (180, 100, 30),  # Softer orange
        "OPERATOR": (100, 50, 100),  # Softer purple
        "DELIMITER": (110, 115, 125),  # Softer gray
    },
    "TOKEN_LIST": {"ERROR": (200, 30, 30)},  # Softer red
    "SUCCESS": (40, 150, 60),  # Softer green
    "INFO": (30, 100, 180),  # Softer blue
}
PALETTE_LIGHT["TOKEN_LIST"].update(PALETTE_LIGHT["TOKEN_CODE"])

DEFAULT_WIDTH, DEFAULT_HEIGHT = 1800, 1000
DIVIDER_WIDTH = 10


# UTILITY FUNCTIONS

def load_sql_file(file_path=None):
    """Load SQL file from path, or try default locations"""
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read(), None, file_path
        except Exception as e:
            return None, f"Error: {str(e)}", None
    
    possible_paths = [
        "input.sql",
        os.path.join(os.getcwd(), "input.sql"),
        os.path.join(os.path.dirname(__file__), "input.sql"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read(), None, path
            except Exception as e:
                return None, f"Error: {str(e)}", None

    default_sql = """CREATE TABLE users (
    id INT,
    name TEXT,
    age INT
);
"""
    return default_sql, "Using sample code", None


def open_file_dialog():
    """Open file dialog to select SQL file"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.update()
    file_path = filedialog.askopenfilename(
        title="Select SQL File",
        filetypes=[("SQL files", "*.sql"), ("All files", "*.*")]
    )
    root.destroy()
    return file_path if file_path else None


def load_tree_image(image_path):
    if not os.path.exists(image_path):
        return None
    try:
        if PIL_AVAILABLE:
            pil_image = Image.open(image_path)
            return pygame.image.fromstring(pil_image.tobytes(), pil_image.size, pil_image.mode)
        else:
            return pygame.image.load(image_path)
    except Exception as e:
        print(f"Error loading image: {e}")
        return None




#  FILE COUNTER 

def get_next_tree_filename(base_name="parse_tree", extension=".png"):
    counter = 1
    while os.path.exists(f"{base_name}_{counter:03d}{extension}"):
        counter += 1
    return f"{base_name}_{counter:03d}{extension}"


def save_file_dialog(default_filename):
    """Open save file dialog for tree downloads"""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    root.update()

    file_path = filedialog.asksaveasfilename(
        title="Save Parse Tree",
        defaultextension=".png",
        filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
        initialfile=default_filename,
        initialdir="./"
    )

    root.destroy()
    return file_path if file_path else None


#  HIGHLIGHTING FUNCTIONS

def create_code_token_mapping(tokens, code_lines):
    mapping = {}  # {(line, col_start, col_end): [token_indices]}
    token_type_map = {}  # {(line, col_start, col_end): token_type}
    valid_tokens = [(ttype, tval, tline, tcol) for ttype, tval, tline, tcol in tokens if ttype != "ERROR"]

    for token_idx, (ttype, tval, tline, tcol) in enumerate(valid_tokens):
        if tline and tcol:
            col_end = tcol + len(tval) - 1
            key = (tline, tcol, col_end)
            if key not in mapping:
                mapping[key] = []
            mapping[key].append(token_idx)
            token_type_map[key] = ttype

    return mapping, valid_tokens, token_type_map


def find_statement_tokens(line_num, word_start_col, word_end_col, code_lines, valid_tokens):
    statement_tokens = set()

    # Find statement start (look backwards for SQL keywords)
    statement_start_line = line_num
    for i in range(line_num - 1, max(0, line_num - 10), -1):
        line = code_lines[i] if i < len(code_lines) else ""
        if any(keyword in line.upper() for keyword in ["CREATE", "SELECT", "INSERT", "UPDATE", "DELETE"]):
            statement_start_line = i + 1
            break

    # Find statement end (look forwards for semicolon)
    statement_end_line = line_num
    for i in range(line_num - 1, min(len(code_lines), line_num + 10)):
        line = code_lines[i] if i < len(code_lines) else ""
        if ';' in line:
            statement_end_line = i + 1
            break

    # Get all tokens in this statement range
    for token_idx, (ttype, tval, tline, tcol) in enumerate(valid_tokens):
        if tline and statement_start_line <= tline <= statement_end_line:
            statement_tokens.add(token_idx)

    return statement_tokens


def find_node_by_position(root, line, text):
    if not root:
        return None
    def search(node):
        if node.line == line and node.text and text == node.text:
            return node
        for child in node.children:
            result = search(child)
            if result:
                return result
        return None
    return search(root)


def draw_card(surface, rect, palette, title="", content_lines=None, icon="", border_color=None):
    """Draw a fancy card with title and content"""
    border_color = border_color or palette["CARD_BORDER"]
    # Card shadow
    shadow_rect = rect.copy()
    shadow_rect.x += 4
    shadow_rect.y += 4
    shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surface, (0, 0, 0, 40), shadow_surface.get_rect(), border_radius=12)
    surface.blit(shadow_surface, shadow_rect.topleft)
    
    # Card background
    pygame.draw.rect(surface, palette["CARD_BG"], rect, border_radius=12)
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=12)


# MAIN GUI

def main():
    pygame.init()
    # drag and drop
    try:
        pygame.event.set_allowed([pygame.QUIT, pygame.VIDEORESIZE, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.DROPFILE])
    except:
        pass
    screen = pygame.display.set_mode((DEFAULT_WIDTH, DEFAULT_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("SQL Compiler - Enhanced GUI (Phase 3 Semantic Analyzer)")
    clock = pygame.time.Clock()

    # fonts sizing
    try:
        code_font = pygame.font.SysFont("Consolas", 16)
        title_font = pygame.font.SysFont("Segoe UI", 32, bold=True)
        subtitle_font = pygame.font.SysFont("Segoe UI", 18)
        button_font = pygame.font.SysFont("Segoe UI", 17, bold=True)
        small_font = pygame.font.SysFont("Segoe UI", 15)
        card_title_font = pygame.font.SysFont("Segoe UI", 20, bold=True)
        card_content_font = pygame.font.SysFont("Consolas", 14)
    except:
        code_font = pygame.font.SysFont("monospace", 16)
        title_font = pygame.font.SysFont("sans", 32, bold=True)
        subtitle_font = pygame.font.SysFont("sans", 18)
        button_font = pygame.font.SysFont("sans", 17, bold=True)
        small_font = pygame.font.SysFont("sans", 15)
        card_title_font = pygame.font.SysFont("sans", 20, bold=True)
        card_content_font = pygame.font.SysFont("monospace", 14)

    char_width, line_height = code_font.size(" ")

    sql_code, file_error, current_file_path = load_sql_file()
    status_text = f"Loaded: {os.path.basename(current_file_path)}" if current_file_path else "Using sample code"
    drag_drop_active = False
    drag_drop_file = None

    def run_compiler(code):
        tokens = tokenize_sql(code)
        lex_errors = [t for t in tokens if t[0] == 'ERROR']
        parser = Parser(tokens)
        parse_tree = parser.parse_query()
        parse_errors = parser.error_messages
        analyzer = SemanticAnalyzer()
        semantic_result = analyzer.analyze(parse_tree)
        return tokens, parse_tree, lex_errors, parse_errors, semantic_result

    tokens, parse_tree, lex_errors, parse_errors, semantic_result = run_compiler(sql_code)
    code_lines = sql_code.splitlines()

    # mapping from SQL code positions to tokens 
    code_token_mapping, valid_tokens, token_type_map = create_code_token_mapping(tokens, code_lines)

    # hovered word/statement 
    hovered_word_info = None  # (line, word, word_start_col, word_end_col)
    highlighted_token_indices = set()

    tree_image = None
    tree_image_path = None
    node_map = {}

    def generate_tree(tree):
        nonlocal tree_image, tree_image_path, node_map
        if GRAPHVIZ_AVAILABLE and tree and tree.children:
            print("Generating enhanced tree layout...")
            tree_gen = GraphvizTreeGenerator()
            tree_image_path, node_map = tree_gen.generate_tree_image(tree)
            if tree_image_path:
                tree_image = load_tree_image(tree_image_path)
                print(f"Tree generated")
        else:
            tree_image = None

    generate_tree(parse_tree)

    current_palette_name = "dark"
    PALETTE = PALETTE_DARK
    current_mode = "lexer"
    padding = 25
    vertical_divider_x_frac = 0.5
    horizontal_divider_y_frac = 0.6
    dragging_vertical = False
    dragging_horizontal = False
    scroll_y_code = 0
    scroll_y_token = 0
    scroll_y_error = 0
    scroll_y_semantic = 0

    tree_zoom = 1.0
    tree_scroll_x = 0
    tree_scroll_y = 0
    tree_pan_start = None
    tree_auto_fit = True

    tree_vscrollbar = None
    tree_hscrollbar = None

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        current_width, current_height = screen.get_size()

        min_panel_width = 350
        min_panel_height = 200
        button_height = 50
        button_y = padding

        lexer_button_rect = pygame.Rect(padding, button_y, 140, button_height)
        parser_button_rect = pygame.Rect(padding + 150, button_y, 140, button_height)
        semantic_button_rect = pygame.Rect(padding + 300, button_y, 160, button_height)
        theme_button_rect = pygame.Rect(current_width - padding - 60, button_y, 60, button_height)
        file_button_rect = pygame.Rect(padding + 470, button_y, 200, button_height)

        zoom_in_button_rect = None
        zoom_out_button_rect = None
        fit_button_rect = None
        download_tree_button_rect = None

        if current_mode == "parser" and GRAPHVIZ_AVAILABLE:
            zoom_in_button_rect = pygame.Rect(padding + 680, button_y, 60, button_height)
            zoom_out_button_rect = pygame.Rect(padding + 750, button_y, 60, button_height)
            fit_button_rect = pygame.Rect(padding + 820, button_y, 100, button_height)
            download_tree_button_rect = pygame.Rect(padding + 930, button_y, 180, button_height)

        panel_top = button_y + button_height + padding + 10

        vertical_divider_x = max(min_panel_width,
            min(current_width - min_panel_width,
            vertical_divider_x_frac * current_width))
        vertical_divider_x_frac = vertical_divider_x / current_width

        code_panel_rect = pygame.Rect(
            padding, panel_top,
            vertical_divider_x - padding - (DIVIDER_WIDTH // 2),
            current_height - panel_top - padding
        )

        right_panel_x = vertical_divider_x + (DIVIDER_WIDTH // 2)
        right_panel_width = current_width - right_panel_x - padding

        token_panel_rect = None
        error_panel_rect = None
        semantic_panel_rect = None
        tree_panel_rect = None
        vertical_divider_rect = None
        horizontal_divider_rect = None

        if current_mode == "lexer":
            horizontal_divider_y = max(panel_top + min_panel_height,
                min(current_height - padding - min_panel_height,
                horizontal_divider_y_frac * current_height))
            horizontal_divider_y_frac = horizontal_divider_y / current_height

            token_panel_rect = pygame.Rect(
                right_panel_x, panel_top,
                right_panel_width,
                horizontal_divider_y - panel_top - (DIVIDER_WIDTH // 2)
            )

            error_panel_rect = pygame.Rect(
                right_panel_x, horizontal_divider_y + (DIVIDER_WIDTH // 2),
                right_panel_width,
                (current_height - padding) - (horizontal_divider_y + (DIVIDER_WIDTH // 2))
            )

            vertical_divider_rect = pygame.Rect(
                code_panel_rect.right, code_panel_rect.top,
                DIVIDER_WIDTH, code_panel_rect.height
            )

            horizontal_divider_rect = pygame.Rect(
                token_panel_rect.left, token_panel_rect.bottom,
                token_panel_rect.width, DIVIDER_WIDTH
            )
        elif current_mode == "semantic":
            semantic_panel_rect = pygame.Rect(
                right_panel_x, panel_top,
                right_panel_width,
                current_height - panel_top - padding
            )
            vertical_divider_rect = pygame.Rect(
                code_panel_rect.right, code_panel_rect.top,
                DIVIDER_WIDTH, code_panel_rect.height
            )
        else:  # Parser mode
            tree_panel_rect = pygame.Rect(
                0, panel_top,
                current_width,
                current_height - panel_top
            )
            scrollbar_width = 20
            if tree_image:
                tree_content_rect = tree_panel_rect.inflate(-15, -60)
                img_w, img_h = tree_image.get_size()

                if tree_auto_fit:
                    scale_w = tree_content_rect.width / img_w
                    scale_h = tree_content_rect.height / img_h
                    tree_zoom = min(scale_w, scale_h) * 0.9
                    scaled_w = int(img_w * tree_zoom)
                    scaled_h = int(img_h * tree_zoom)
                    tree_scroll_x = -(tree_content_rect.width - scaled_w) // 2
                    tree_scroll_y = -(tree_content_rect.height - scaled_h) // 2
                    tree_auto_fit = False

                scaled_w = int(img_w * tree_zoom)
                scaled_h = int(img_h * tree_zoom)

                tree_vscrollbar = Scrollbar(tree_content_rect.right + 5, tree_content_rect.top, scrollbar_width, tree_content_rect.height, 'vertical')
                tree_vscrollbar.content_size = scaled_h
                tree_vscrollbar.visible_size = tree_content_rect.height
                if scaled_h > tree_content_rect.height:
                    tree_vscrollbar.scroll_pos = (tree_scroll_y + max(0, tree_content_rect.height - scaled_h) // 2) / max(1, scaled_h - tree_content_rect.height)
                tree_vscrollbar.update_handle()

                tree_hscrollbar = Scrollbar(tree_content_rect.left, tree_content_rect.bottom + 5, tree_content_rect.width, scrollbar_width, 'horizontal')
                tree_hscrollbar.content_size = scaled_w
                tree_hscrollbar.visible_size = tree_content_rect.width
                if scaled_w > tree_content_rect.width:
                    tree_hscrollbar.scroll_pos = (tree_scroll_x + max(0, tree_content_rect.width - scaled_w) // 2) / max(1, scaled_w - tree_content_rect.width)
                tree_hscrollbar.update_handle()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                tree_auto_fit = True
            elif event.type == pygame.DROPFILE:
                # Handle drag and drop
                dropped_file = event.file
                if dropped_file.lower().endswith('.sql'):
                    sql_code, file_error, current_file_path = load_sql_file(dropped_file)
                    if file_error is None:
                        status_text = f"Loaded: {os.path.basename(current_file_path)}"
                        tokens, parse_tree, lex_errors, parse_errors, semantic_result = run_compiler(sql_code)
                        code_lines = sql_code.splitlines()
                        # Recreate token mappings for new file
                        code_token_mapping, valid_tokens, token_type_map = create_code_token_mapping(tokens, code_lines)
                        generate_tree(parse_tree)
                        tree_auto_fit = True
                        # Reset scroll positions
                        scroll_y_code = 0
                        scroll_y_token = 0
                        scroll_y_error = 0
                        scroll_y_semantic = 0
                    else:
                        status_text = f"Error: {file_error}"
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    if lexer_button_rect.collidepoint(event.pos):
                        current_mode = "lexer"
                    elif parser_button_rect.collidepoint(event.pos):
                        current_mode = "parser"
                        tree_auto_fit = True
                    elif semantic_button_rect.collidepoint(event.pos):
                        current_mode = "semantic"
                    elif theme_button_rect.collidepoint(event.pos):
                        current_palette_name = "light" if current_palette_name == "dark" else "dark"
                        PALETTE = PALETTE_LIGHT if current_palette_name == "light" else PALETTE_DARK
                    elif file_button_rect.collidepoint(event.pos):
                        file_path = open_file_dialog()
                        if file_path:
                            sql_code, file_error, current_file_path = load_sql_file(file_path)
                            if file_error is None:
                                status_text = f"Loaded: {os.path.basename(current_file_path)}"
                                tokens, parse_tree, lex_errors, parse_errors, semantic_result = run_compiler(sql_code)
                                code_lines = sql_code.splitlines()
                                # Recreate token mappings for new file
                                code_token_mapping, valid_tokens, token_type_map = create_code_token_mapping(tokens, code_lines)
                                generate_tree(parse_tree)
                                tree_auto_fit = True
                                # Reset scroll positions
                                scroll_y_code = 0
                                scroll_y_token = 0
                                scroll_y_error = 0
                                scroll_y_semantic = 0
                            else:
                                status_text = f"Error: {file_error}"
                    elif zoom_in_button_rect and zoom_in_button_rect.collidepoint(event.pos):
                        tree_zoom *= 1.2
                    elif zoom_out_button_rect and zoom_out_button_rect.collidepoint(event.pos):
                        tree_zoom /= 1.2
                    elif fit_button_rect and fit_button_rect.collidepoint(event.pos):
                        tree_auto_fit = True
                    elif download_tree_button_rect and download_tree_button_rect.collidepoint(event.pos):
                        if tree_image_path and os.path.exists(tree_image_path):
                            save_path = save_file_dialog("parse_tree.png")
                            if save_path:
                                try:
                                    shutil.copy2(tree_image_path, save_path)
                                    # Show success message
                                    root = tk.Tk()
                                    root.withdraw()
                                    messagebox.showinfo("Success", f"Parse tree saved to:\n{save_path}")
                                    root.destroy()
                                except Exception as e:
                                    root = tk.Tk()
                                    root.withdraw()
                                    messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
                                    root.destroy()
                        else:
                            root = tk.Tk()
                            root.withdraw()
                            messagebox.showwarning("Warning", "No parse tree available to save.")
                            root.destroy()
                    elif vertical_divider_rect and vertical_divider_rect.collidepoint(event.pos):
                        dragging_vertical = True
                    elif horizontal_divider_rect and horizontal_divider_rect.collidepoint(event.pos):
                        dragging_horizontal = True
                    elif tree_panel_rect and tree_panel_rect.collidepoint(event.pos):
                        tree_pan_start = event.pos
                if event.button == 4:
                    if current_mode == "lexer":
                        if code_panel_rect.collidepoint(event.pos): scroll_y_code = max(0, scroll_y_code - 30)
                        elif token_panel_rect and token_panel_rect.collidepoint(event.pos): scroll_y_token = max(0, scroll_y_token - 30)
                        elif error_panel_rect and error_panel_rect.collidepoint(event.pos): scroll_y_error = max(0, scroll_y_error - 30)
                    elif current_mode == "semantic":
                        if code_panel_rect.collidepoint(event.pos): scroll_y_code = max(0, scroll_y_code - 30)
                        elif semantic_panel_rect.collidepoint(event.pos): scroll_y_semantic = max(0, scroll_y_semantic - 30)
                    else:
                        tree_zoom *= 1.1
                elif event.button == 5:
                    if current_mode == "lexer":
                        if code_panel_rect.collidepoint(event.pos): scroll_y_code += 30
                        elif token_panel_rect and token_panel_rect.collidepoint(event.pos): scroll_y_token += 30
                        elif error_panel_rect and error_panel_rect.collidepoint(event.pos): scroll_y_error += 30
                    elif current_mode == "semantic":
                        if code_panel_rect.collidepoint(event.pos): scroll_y_code += 30
                        elif semantic_panel_rect.collidepoint(event.pos): scroll_y_semantic += 30
                    else:
                        tree_zoom /= 1.1
            elif event.type == pygame.MOUSEBUTTONUP:
                dragging_vertical = False
                dragging_horizontal = False
                tree_pan_start = None
            elif event.type == pygame.MOUSEMOTION:
                if dragging_vertical:
                    vertical_divider_x_frac = event.pos[0] / current_width
                if dragging_horizontal:
                    horizontal_divider_y_frac = event.pos[1] / current_height
                if tree_pan_start:
                    dx = tree_pan_start[0] - event.pos[0]
                    dy = tree_pan_start[1] - event.pos[1]
                    tree_scroll_x += dx
                    tree_scroll_y += dy
                    tree_pan_start = event.pos

        screen.fill(PALETTE["BG"])

        # Enhanced buttons with hover effects
        mouse_hover_lex = lexer_button_rect.collidepoint(mouse_pos)
        mouse_hover_par = parser_button_rect.collidepoint(mouse_pos)
        mouse_hover_sem = semantic_button_rect.collidepoint(mouse_pos)
        mouse_hover_file = file_button_rect.collidepoint(mouse_pos)

        lex_color = PALETTE["BUTTON_ACTIVE"] if current_mode == "lexer" else (PALETTE["BUTTON_HOVER"] if mouse_hover_lex else PALETTE["BUTTON"])
        par_color = PALETTE["BUTTON_ACTIVE"] if current_mode == "parser" else (PALETTE["BUTTON_HOVER"] if mouse_hover_par else PALETTE["BUTTON"])
        sem_color = PALETTE["BUTTON_ACTIVE"] if current_mode == "semantic" else (PALETTE["BUTTON_HOVER"] if mouse_hover_sem else PALETTE["BUTTON"])
        file_color = PALETTE["BUTTON_HOVER"] if mouse_hover_file else PALETTE["BUTTON"]

        pygame.draw.rect(screen, lex_color, lexer_button_rect, border_radius=14)
        pygame.draw.rect(screen, par_color, parser_button_rect, border_radius=14)
        pygame.draw.rect(screen, sem_color, semantic_button_rect, border_radius=14)
        pygame.draw.rect(screen, file_color, file_button_rect, border_radius=14)
        pygame.draw.rect(screen, PALETTE["BUTTON"], theme_button_rect, border_radius=14)

        # Icons for buttons
        icon_size = 20
        try:
            icon_font = pygame.font.SysFont("Segoe UI Emoji", icon_size)
        except:
            try:
                icon_font = pygame.font.SysFont("Arial Unicode MS", icon_size)
            except:
                icon_font = small_font
        
        # Lexer button with icon
        lexer_icon = "🔍" if current_mode == "lexer" else "🔎"
        screen.blit(icon_font.render(lexer_icon, True, PALETTE["FONT"]), (lexer_button_rect.x + 15, lexer_button_rect.y + 15))
        screen.blit(button_font.render("Lexer", True, PALETTE["FONT"]), (lexer_button_rect.x + 40, lexer_button_rect.y + 14))
        
        # Parser button with icon
        parser_icon = "🌳" if current_mode == "parser" else "🌲"
        screen.blit(icon_font.render(parser_icon, True, PALETTE["FONT"]), (parser_button_rect.x + 15, parser_button_rect.y + 15))
        screen.blit(button_font.render("Parser", True, PALETTE["FONT"]), (parser_button_rect.x + 40, parser_button_rect.y + 14))
        
        # Semantic button with icon
        semantic_icon = "✨" if current_mode == "semantic" else "⭐"
        screen.blit(icon_font.render(semantic_icon, True, PALETTE["FONT"]), (semantic_button_rect.x + 15, semantic_button_rect.y + 15))
        screen.blit(button_font.render("Semantic", True, PALETTE["FONT"]), (semantic_button_rect.x + 40, semantic_button_rect.y + 14))
        
        # File button with icon
        screen.blit(icon_font.render("📁", True, PALETTE["FONT"]), (file_button_rect.x + 15, file_button_rect.y + 15))
        screen.blit(button_font.render("Open File", True, PALETTE["FONT"]), (file_button_rect.x + 40, file_button_rect.y + 14))
        
        # Theme button with icon
        theme_icon = "🌙" if current_palette_name == "dark" else "☀️"
        screen.blit(icon_font.render(theme_icon, True, PALETTE["FONT"]), (theme_button_rect.x + 20, theme_button_rect.y + 15))
        
        screen.blit(subtitle_font.render(f"Status: {status_text}", True, PALETTE["SUBTITLE"]), (file_button_rect.right + 25, button_y + 16))
        screen.blit(small_font.render("💡 Drag & drop SQL files here", True, PALETTE["INFO"]), (file_button_rect.right + 25, button_y + 40))

        if zoom_in_button_rect:
            mouse_hover_zoom_in = zoom_in_button_rect.collidepoint(mouse_pos)
            zoom_in_color = PALETTE["BUTTON_HOVER"] if mouse_hover_zoom_in else PALETTE["BUTTON"]
            pygame.draw.rect(screen, zoom_in_color, zoom_in_button_rect, border_radius=14)
            screen.blit(icon_font.render("➕", True, PALETTE["FONT"]), (zoom_in_button_rect.x + 20, zoom_in_button_rect.y + 15))
        if zoom_out_button_rect:
            mouse_hover_zoom_out = zoom_out_button_rect.collidepoint(mouse_pos)
            zoom_out_color = PALETTE["BUTTON_HOVER"] if mouse_hover_zoom_out else PALETTE["BUTTON"]
            pygame.draw.rect(screen, zoom_out_color, zoom_out_button_rect, border_radius=14)
            screen.blit(icon_font.render("➖", True, PALETTE["FONT"]), (zoom_out_button_rect.x + 20, zoom_out_button_rect.y + 15))
        if fit_button_rect:
            mouse_hover_fit = fit_button_rect.collidepoint(mouse_pos)
            fit_color = PALETTE["BUTTON_HOVER"] if mouse_hover_fit else PALETTE["BUTTON"]
            pygame.draw.rect(screen, fit_color, fit_button_rect, border_radius=14)
            screen.blit(icon_font.render("🔍", True, PALETTE["FONT"]), (fit_button_rect.x + 15, fit_button_rect.y + 15))
            screen.blit(button_font.render("Fit", True, PALETTE["FONT"]), (fit_button_rect.x + 40, fit_button_rect.y + 14))
        if download_tree_button_rect:
            mouse_hover_download = download_tree_button_rect.collidepoint(mouse_pos)
            download_color = PALETTE["BUTTON_HOVER"] if mouse_hover_download else PALETTE["BUTTON"]
            pygame.draw.rect(screen, download_color, download_tree_button_rect, border_radius=14)
            screen.blit(icon_font.render("💾", True, PALETTE["FONT"]), (download_tree_button_rect.x + 15, download_tree_button_rect.y + 15))
            screen.blit(button_font.render("Download Tree", True, PALETTE["FONT"]), (download_tree_button_rect.x + 40, download_tree_button_rect.y + 14))

        if current_mode in ["lexer", "semantic"]:
            if code_panel_rect:
                pygame.draw.rect(screen, PALETTE["PANEL"], code_panel_rect, border_radius=18)
                # Title with gradient effect
                title_surface = title_font.render("SQL Code", True, PALETTE["TITLE"])
                screen.blit(title_surface, (code_panel_rect.x + 25, code_panel_rect.y + 20))
                code_clip = code_panel_rect.inflate(-50, -100)
                code_clip.y += 30
                screen.set_clip(code_clip)
                
                # Tokenize and highlight code with hover effects and cross-tab highlighting
                code_hovered = code_panel_rect.collidepoint(mouse_pos) if code_panel_rect else False
                
                # Track if we found a hovered word in this frame
                found_hovered_word = False
                
                # Clear previous highlights, will be set again if hovering over a word
                if code_hovered:
                    highlighted_token_indices.clear()
                else:
                    # Reset hover info if mouse is not in code panel
                    hovered_word_info = None
                    highlighted_token_indices.clear()
                
                for i, line in enumerate(code_lines):
                    y = code_clip.y + i * (line_height + 2) - scroll_y_code
                    if y >= code_clip.y - line_height and y <= code_clip.bottom:
                        screen.blit(code_font.render(f"{i+1:>4}", True, PALETTE["LINE_NUM"]), (code_clip.x, y))
                        
                        # Render line with word-by-word hover highlighting
                        x_offset = code_clip.x + 50
                        line_num = i + 1
                        col_pos = 1
                        
                        # Split line
                        parts = re.split(r'(\s+)', line)
                        
                        for part in parts:
                            if not part:
                                continue
                            
                            if part.isspace():
                                # Render spaces
                                space_width = code_font.size(part)[0]
                                col_pos += len(part)
                                x_offset += space_width
                            else:
                                # mouse hovering word
                                word_width = code_font.size(part)[0]
                                word_rect = pygame.Rect(x_offset, y, word_width, line_height)
                                is_hovered = word_rect.collidepoint(mouse_pos)
                                
                                # Store hovered word info for cross-tab highlighting
                                if is_hovered and code_hovered:
                                    found_hovered_word = True
                                    hovered_word_info = (line_num, part, col_pos, col_pos + len(part) - 1)
                                    #matching tokens by position
                                    for (tline, tcol_start, tcol_end), token_indices in code_token_mapping.items():
                                        if tline == line_num:
                                            # Check if token overlaps with hovered word
                                            if not (tcol_end < col_pos or tcol_start > col_pos + len(part) - 1):
                                                highlighted_token_indices.update(token_indices)
                                    # Also find tokens by matching value
                                    part_clean = part.strip('(),;')
                                    for token_idx, (ttype, tval, tline, tcol) in enumerate(valid_tokens):
                                        if tline == line_num:
                                            tval_clean = tval.strip('(),;')
                                            if tval_clean.upper() == part_clean.upper() or part_clean.upper() == tval_clean.upper():
                                                highlighted_token_indices.add(token_idx)
                                    
                                    # Find all tokens in the same statement
                                    statement_tokens = find_statement_tokens(line_num, col_pos, col_pos + len(part) - 1, code_lines, valid_tokens)
                                    highlighted_token_indices.update(statement_tokens)
                                
                                # Determine color based on actual token type from TOKEN_LIST
                                word_color = PALETTE["FONT"]
                                # Try to find matching token by position
                                token_type = None
                                for (tline, tcol_start, tcol_end), token_indices in code_token_mapping.items():
                                    if tline == line_num:
                                        # Check if token overlaps with current word
                                        if not (tcol_end < col_pos or tcol_start > col_pos + len(part) - 1):
                                            token_type = token_type_map.get((tline, tcol_start, tcol_end))
                                            if token_type:
                                                break
                                
                                # If no exact match, try to match by value
                                if not token_type:
                                    part_clean = part.strip('(),;')
                                    for (ttype, tval, tline, tcol) in valid_tokens:
                                        if tline == line_num:
                                            tval_clean = tval.strip('(),;')
                                            if tval_clean.upper() == part_clean.upper():
                                                token_type = ttype
                                                break
                                
                                # Use token type color from TOKEN_LIST
                                if token_type and token_type in PALETTE["TOKEN_LIST"]:
                                    word_color = PALETTE["TOKEN_LIST"][token_type]
                                else:
                                    # Fallback to simplified detection
                                    word_upper = part.upper().strip('(),;')
                                    if word_upper in ["SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "CREATE", "TABLE", "UPDATE", "SET", "DELETE", "INT", "FLOAT", "TEXT", "AND", "OR", "NOT"]:
                                        word_color = PALETTE["TOKEN_CODE"]["KEYWORD"]
                                    elif part.startswith("'") and part.endswith("'"):
                                        word_color = PALETTE["TOKEN_CODE"]["STRING_LITERAL"]
                                    elif part.replace('.', '').replace('-', '').isdigit():
                                        word_color = PALETTE["TOKEN_CODE"]["INTEGER_LITERAL"]
                                    elif part in ['(', ')', ',', ';', '.']:
                                        word_color = PALETTE["TOKEN_CODE"]["DELIMITER"]
                                    elif part in ['=', '<>', '!=', '<=', '>=', '<', '>', '+', '-', '*', '/']:
                                        word_color = PALETTE["TOKEN_CODE"]["OPERATOR"]
                                
                                # Highlight on hover
                                if is_hovered:
                                    highlight_rect = word_rect.inflate(2, 2)
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], highlight_rect, border_radius=3)
                                
                                screen.blit(code_font.render(part, True, word_color), (x_offset, y))
                                x_offset += word_width
                                col_pos += len(part)
                
                # Clear hover info if no word was hovered in this frame (but mouse is still in code panel)
                if code_hovered and not found_hovered_word:
                    hovered_word_info = None
                
                screen.set_clip(None)

            if current_mode == "lexer":
                if token_panel_rect:
                    pygame.draw.rect(screen, PALETTE["PANEL"], token_panel_rect, border_radius=18)
                    screen.blit(title_font.render("Tokens", True, PALETTE["TITLE"]), (token_panel_rect.x + 25, token_panel_rect.y + 20))
                    token_clip = token_panel_rect.inflate(-50, -100)
                    token_clip.y += 30
                    
                    # Column headers
                    header_y = token_clip.y - 25
                    col1_x = token_clip.x
                    col2_x = token_clip.x + 200
                    col3_x = token_clip.x + 350
                    col4_x = token_clip.x + 450
                    
                    screen.blit(card_title_font.render("Type", True, PALETTE["TITLE"]), (col1_x, header_y))
                    screen.blit(card_title_font.render("Value", True, PALETTE["TITLE"]), (col2_x, header_y))
                    screen.blit(card_title_font.render("Line", True, PALETTE["TITLE"]), (col3_x, header_y))
                    screen.blit(card_title_font.render("Column", True, PALETTE["TITLE"]), (col4_x, header_y))
                    
                    # Draw separator line
                    pygame.draw.line(screen, PALETTE["DIVIDER"], 
                                   (token_clip.x, header_y + 20), 
                                   (token_clip.right, header_y + 20), 2)
                    
                    screen.set_clip(token_clip)
                    for i, (ttype, tval, tline, tcol) in enumerate(valid_tokens):
                        y = token_clip.y + i * 28 - scroll_y_token
                        if y >= token_clip.y - 28 and y <= token_clip.bottom:
                            color = PALETTE["TOKEN_LIST"].get(ttype, PALETTE["FONT"])
                            
                            # Check if this token should be highlighted from SQL code hover
                            is_highlighted_from_code = i in highlighted_token_indices
                            
                            # Check hover for each column
                            type_rect = pygame.Rect(col1_x, y, 180, 25)
                            val_rect = pygame.Rect(col2_x, y, 140, 25)
                            line_rect = pygame.Rect(col3_x, y, 90, 25)
                            col_rect = pygame.Rect(col4_x, y, 90, 25)
                            
                            # Highlight entire row if hovered from SQL code or if mouse hovers
                            if is_highlighted_from_code:
                                row_rect = pygame.Rect(col1_x, y, col4_x + 90 - col1_x, 25)
                                pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], row_rect, border_radius=3)
                            else:
                                if type_rect.collidepoint(mouse_pos):
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], type_rect, border_radius=3)
                                if val_rect.collidepoint(mouse_pos):
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], val_rect, border_radius=3)
                                if line_rect.collidepoint(mouse_pos):
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], line_rect, border_radius=3)
                                if col_rect.collidepoint(mouse_pos):
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], col_rect, border_radius=3)
                            
                            screen.blit(card_content_font.render(ttype, True, color), (col1_x, y))
                            screen.blit(card_content_font.render(tval, True, color), (col2_x, y))
                            screen.blit(card_content_font.render(str(tline), True, PALETTE["LINE_NUM"]), (col3_x, y))
                            screen.blit(card_content_font.render(str(tcol), True, PALETTE["LINE_NUM"]), (col4_x, y))
                    screen.set_clip(None)

                if error_panel_rect:
                    pygame.draw.rect(screen, PALETTE["PANEL"], error_panel_rect, border_radius=18)
                    screen.blit(title_font.render("Lexer/Parser Errors", True, PALETTE["TITLE"]), (error_panel_rect.x + 25, error_panel_rect.y + 20))
                    error_clip = error_panel_rect.inflate(-50, -100)
                    error_clip.y += 30
                    screen.set_clip(error_clip)
                    all_errors = lex_errors + [(None, msg, None, None) for msg in parse_errors]
                    for i, err in enumerate(all_errors):
                        y = error_clip.y + i * 28 - scroll_y_error
                        if y >= error_clip.y - 28 and y <= error_clip.bottom:
                            msg = err[1] if isinstance(err, tuple) else err
                            error_text = f"❌ {str(msg)}"
                            
                            # Check if error should be highlighted from SQL code hover
                            is_highlighted = False
                            if hovered_word_info:
                                hovered_line, hovered_word, _, _ = hovered_word_info
                                # Check if error mentions the hovered line or word
                                if f"Line {hovered_line}" in str(msg) or hovered_word.upper() in str(msg).upper():
                                    is_highlighted = True
                            
                            # Word-by-word hover highlighting for errors
                            words = str(msg).split()
                            x_offset = error_clip.x
                            
                            # Highlight entire error row if matched from SQL code
                            if is_highlighted:
                                error_row_rect = pygame.Rect(error_clip.x - 20, y, error_clip.width + 20, 25)
                                pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], error_row_rect, border_radius=3)
                            
                            for word in words:
                                word_surface = card_content_font.render(word, True, PALETTE["TOKEN_LIST"]["ERROR"])
                                word_rect = pygame.Rect(x_offset, y, word_surface.get_width(), 25)
                                
                                if word_rect.collidepoint(mouse_pos) and not is_highlighted:
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], word_rect, border_radius=3)
                                
                                screen.blit(word_surface, (x_offset, y))
                                x_offset += word_surface.get_width() + card_content_font.size(' ')[0]
                            
                            # Draw error icon
                            icon_surface = card_content_font.render("❌", True, PALETTE["TOKEN_LIST"]["ERROR"])
                            screen.blit(icon_surface, (error_clip.x - 20, y))
                    if not all_errors:
                        screen.blit(subtitle_font.render(" No lexical or syntax errors found.", True, PALETTE["SUCCESS"]), (error_clip.x, error_clip.y))
                    screen.set_clip(None)
                if horizontal_divider_rect:
                    pygame.draw.rect(screen, PALETTE["DIVIDER"], horizontal_divider_rect, border_radius=5)

            elif current_mode == "semantic":
                if semantic_panel_rect:
                    pygame.draw.rect(screen, PALETTE["PANEL"], semantic_panel_rect, border_radius=18)
                    
                    # Enhanced semantic analysis display
                    title_y = semantic_panel_rect.y + 25
                    screen.blit(title_font.render("Semantic Analysis", True, PALETTE["TITLE"]), (semantic_panel_rect.x + 25, title_y))
                    
                    # Status card
                    status_card_y = title_y + 50
                    status_card_rect = pygame.Rect(semantic_panel_rect.x + 25, status_card_y, semantic_panel_rect.width - 50, 80)
                    status_color = PALETTE["SUCCESS"] if semantic_result["success"] else PALETTE["TOKEN_LIST"]["ERROR"]
                    border_status = (status_color[0]//2, status_color[1]//2, status_color[2]//2) if len(status_color) == 3 else status_color
                    draw_card(screen, status_card_rect, PALETTE, border_color=status_color)
                    
                    icon_text = "✓" if semantic_result["success"] else "✖"
                    status_text_display = semantic_result["message"]
                    screen.blit(card_title_font.render(f"{icon_text} {status_text_display}", True, status_color), (status_card_rect.x + 20, status_card_rect.y + 25))
                    
                    sem_clip = semantic_panel_rect.inflate(-30, -120)
                    sem_clip.y = status_card_y + 100
                    available_height = semantic_panel_rect.bottom - sem_clip.y - 30
                    
                    screen.set_clip(sem_clip)
                    
                    y_offset = 0
                    line_height_error = 28
                    line_height_symbol = 22
                    line_height_tree = 20
                    card_padding = 20
                    card_title_height = 45
                    card_spacing = 20
                    
                    # Errors card 
                    if semantic_result["errors"]:
                        # Calculate required height for each error 
                        max_width = sem_clip.width - 50
                        total_error_height = card_title_height
                        for err in semantic_result["errors"]:
                            err_text = str(err)
                            # Word wrap calculation
                            words = err_text.split()
                            lines_needed = 1
                            current_line_width = 0
                            for word in words:
                                word_width = card_content_font.size(word + ' ')[0]
                                if current_line_width + word_width > max_width and current_line_width > 0:
                                    lines_needed += 1
                                    current_line_width = word_width
                                else:
                                    current_line_width += word_width
                            total_error_height += max(line_height_error, lines_needed * line_height_error)
                        
                        error_card_height = total_error_height
                        error_card_rect = pygame.Rect(sem_clip.x, sem_clip.y + y_offset - scroll_y_semantic, sem_clip.width, error_card_height)
                        draw_card(screen, error_card_rect, PALETTE, border_color=PALETTE["TOKEN_LIST"]["ERROR"])
                        screen.blit(card_title_font.render("Errors Found", True, PALETTE["TOKEN_LIST"]["ERROR"]), (error_card_rect.x + 20, error_card_rect.y + 15))
                        
                        error_content_y = error_card_rect.y + card_title_height
                        error_content_x = error_card_rect.x + 25
                        current_y = error_content_y
                        for err in semantic_result["errors"]:
                            err_text = str(err)
                            
                            # Check if this error should be highlighted from SQL code hover
                            is_highlighted = False
                            if hovered_word_info:
                                hovered_line, hovered_word, _, _ = hovered_word_info
                                # Check if error mentions the hovered line or word
                                if f"Line {hovered_line}" in err_text or hovered_word.upper() in err_text.upper():
                                    is_highlighted = True
                            
                            # Word wrap and render with hover
                            words = err_text.split()
                            line_x = error_content_x
                            line_y = current_y
                            
                            # Highlight entire error if matched
                            if is_highlighted:
                                error_highlight_rect = pygame.Rect(error_content_x - 5, line_y, error_card_rect.width - 40, line_height_error)
                                pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], error_highlight_rect, border_radius=3)
                            
                            for word in words:
                                word_surface = card_content_font.render(word, True, PALETTE["TOKEN_LIST"]["ERROR"])
                                word_width = word_surface.get_width()
                                
                                # Check if word fits on current line
                                if line_x + word_width > error_card_rect.right - 25:
                                    line_y += line_height_error
                                    line_x = error_content_x
                                    if is_highlighted:
                                        error_highlight_rect = pygame.Rect(error_content_x - 5, line_y, error_card_rect.width - 40, line_height_error)
                                        pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], error_highlight_rect, border_radius=3)
                                
                                word_rect = pygame.Rect(line_x, line_y, word_width, line_height_error)
                                if word_rect.collidepoint(mouse_pos) and not is_highlighted:
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], word_rect, border_radius=3)
                                
                                screen.blit(word_surface, (line_x, line_y))
                                line_x += word_width + card_content_font.size(' ')[0]
                            
                            current_y = line_y + line_height_error + 5
                        y_offset += error_card_rect.height + card_spacing
                    
                    # Symbol table card 
                    if semantic_result["symbol_table"]:
                        symbol_lines = [line for line in semantic_result["symbol_table"].split('\n') if line.strip()]
                        symbol_card_height = len(symbol_lines) * line_height_symbol + card_title_height
                        symbol_card_rect = pygame.Rect(sem_clip.x, sem_clip.y + y_offset - scroll_y_semantic, sem_clip.width, symbol_card_height)
                        draw_card(screen, symbol_card_rect, PALETTE, border_color=PALETTE["INFO"])
                        screen.blit(card_title_font.render("📊 Symbol Table", True, PALETTE["INFO"]), (symbol_card_rect.x + 20, symbol_card_rect.y + 15))
                        symbol_content_y = symbol_card_rect.y + card_title_height
                        for i, line in enumerate(symbol_lines):
                            if symbol_content_y + i * line_height_symbol > symbol_card_rect.bottom - 10:
                                break
                            
                            # line highlighted from SQL code hover
                            is_highlighted = False
                            if hovered_word_info:
                                hovered_line, hovered_word, _, _ = hovered_word_info
                                hovered_word_clean = hovered_word.strip('(),;').upper()
                                # Check if line contains the hovered word (table or column name)
                                if hovered_word_clean in line.upper():
                                    is_highlighted = True
                            
                            color = PALETTE["TITLE"] if "=" in line or "SYMBOL" in line.upper() or "Table:" in line else PALETTE["FONT"]
                            
                            # Highlight line if matched
                            if is_highlighted:
                                line_highlight_rect = pygame.Rect(symbol_card_rect.x + 20, symbol_content_y + i * line_height_symbol, symbol_card_rect.width - 40, line_height_symbol)
                                pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], line_highlight_rect, border_radius=3)
                            
                            # Word hover for symbol table
                            words = line.split()
                            line_x = symbol_card_rect.x + 25
                            for word in words:
                                word_surface = card_content_font.render(word, True, color)
                                word_rect = pygame.Rect(line_x, symbol_content_y + i * line_height_symbol, word_surface.get_width(), line_height_symbol)
                                if word_rect.collidepoint(mouse_pos) and not is_highlighted:
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], word_rect, border_radius=3)
                                screen.blit(word_surface, (line_x, symbol_content_y + i * line_height_symbol))
                                line_x += word_surface.get_width() + card_content_font.size(' ')[0]
                        y_offset += symbol_card_rect.height + card_spacing
                    
                    # Annotated tree card 
                    if semantic_result["annotated_tree"]:
                        tree_lines = [line for line in semantic_result["annotated_tree"].split('\n') if line.strip()]
                        tree_card_height = len(tree_lines) * line_height_tree + card_title_height
                        tree_card_rect = pygame.Rect(sem_clip.x, sem_clip.y + y_offset - scroll_y_semantic, sem_clip.width, tree_card_height)
                        draw_card(screen, tree_card_rect, PALETTE, border_color=PALETTE["HIGHLIGHT"])
                        screen.blit(card_title_font.render("🌳 Annotated Parse Tree", True, PALETTE["HIGHLIGHT"]), (tree_card_rect.x + 20, tree_card_rect.y + 15))
                        tree_content_y = tree_card_rect.y + card_title_height
                        for i, line in enumerate(tree_lines):
                            if tree_content_y + i * line_height_tree > tree_card_rect.bottom - 10:
                                break
                            
                            # Check if this line should be highlighted from SQL code hover
                            is_highlighted = False
                            if hovered_word_info:
                                hovered_line, hovered_word, _, _ = hovered_word_info
                                hovered_word_clean = hovered_word.strip('(),;').upper()
                                # Check if line contains the hovered word
                                if hovered_word_clean in line.upper() or f"Line {hovered_line}" in line:
                                    is_highlighted = True
                            
                            # Color code tree elements
                            color = PALETTE["FONT"]
                            if "Type:" in line:
                                color = PALETTE["INFO"]
                            elif "Ref:" in line:
                                color = PALETTE["SUCCESS"]
                            elif line.strip().startswith("Query") or line.strip().endswith("Stmt"):
                                color = PALETTE["TITLE"]
                            
                            # Highlight entire line if matched
                            if is_highlighted:
                                line_highlight_rect = pygame.Rect(tree_card_rect.x + 20, tree_content_y + i * line_height_tree, tree_card_rect.width - 40, line_height_tree)
                                pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], line_highlight_rect, border_radius=3)
                            
                            # Word hover for tree
                            words = line.split()
                            line_x = tree_card_rect.x + 25
                            for word in words:
                                word_surface = card_content_font.render(word, True, color)
                                word_rect = pygame.Rect(line_x, tree_content_y + i * line_height_tree, word_surface.get_width(), line_height_tree)
                                if word_rect.collidepoint(mouse_pos) and not is_highlighted:
                                    pygame.draw.rect(screen, PALETTE["HIGHLIGHT"], word_rect, border_radius=3)
                                screen.blit(word_surface, (line_x, tree_content_y + i * line_height_tree))
                                line_x += word_surface.get_width() + card_content_font.size(' ')[0]
                        y_offset += tree_card_rect.height + card_spacing
                    
                    screen.set_clip(None)
            if vertical_divider_rect:
                pygame.draw.rect(screen, PALETTE["DIVIDER"], vertical_divider_rect, border_radius=5)
        else:
            if tree_panel_rect:
                pygame.draw.rect(screen, PALETTE["PANEL"], tree_panel_rect, border_radius=18)
                if tree_image:
                    tree_title_y = tree_panel_rect.y + 20
                    screen.blit(title_font.render("Parse Tree Visualization", True, PALETTE["TITLE"]), (tree_panel_rect.x + 25, tree_title_y))
                    tree_clip = tree_panel_rect.inflate(-15, -80)
                    tree_clip.y = tree_title_y + 50
                    screen.set_clip(tree_clip)
                    scaled_img = pygame.transform.scale(tree_image, (int(tree_image.get_width() * tree_zoom), int(tree_image.get_height() * tree_zoom)))
                    screen.blit(scaled_img, (tree_clip.x - tree_scroll_x, tree_clip.y - tree_scroll_y))
                    screen.set_clip(None)
                    if tree_vscrollbar:
                        tree_vscrollbar.draw(screen, PALETTE)
                    if tree_hscrollbar:
                        tree_hscrollbar.draw(screen, PALETTE)
                else:
                    screen.blit(title_font.render("No Parse Tree Available", True, PALETTE["TOKEN_LIST"]["ERROR"]), (tree_panel_rect.centerx - 200, tree_panel_rect.centery))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
