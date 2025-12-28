# MiniSQLCompiler

A complete SQL compiler implementation with lexical analysis, syntax parsing, semantic analysis, and an interactive GUI for visualizing the compilation process.

## Overview

This project implements a compiler for a subset of SQL, featuring:

- **Lexical Analysis (Lexer)**: Tokenizes SQL code and identifies keywords, operators, delimiters, and identifiers
- **Syntax Parsing (Parser)**: Builds a parse tree from tokens and validates SQL grammar
- **Semantic Analysis**: Checks semantic correctness, maintains symbol tables, and validates data types
- **Interactive GUI**: Visual interface with real-time parsing, error highlighting, and parse tree visualization
- **Tree Visualization**: Generates parse tree diagrams using Graphviz

## Project Structure

```
MiniSQLCompiler/
   src/
      ├── lexer.py           # Lexical analyzer - tokenizes SQL input
      ├── parser.py          # Syntax parser - builds parse tree from tokens
      ├── semantic.py        # Semantic analyzer - validates semantics and maintains symbol table
      ├── gui.py             # Interactive GUI using Tkinter and Pygame
      ├── app.py             # Main entry point
      ├── input.sql          # Sample SQL input file
└── README.md          # This file
└── License          # MIT
```

## Features

### Lexical Analysis
- Tokenizes SQL statements (SELECT, INSERT, UPDATE, DELETE, CREATE, etc.)
- Recognizes keywords, identifiers, operators, and delimiters
- Handles comments and whitespace
- Provides token location information (line, column)

### Syntax Parsing
- Recursive descent parser
- Generates abstract syntax tree (AST)
- Validates SQL grammar according to defined rules
- Reports syntax errors with line and column numbers

### Semantic Analysis
- Symbol table management for database tables and columns
- Data type validation
- Semantic error detection
- Non-destructive tree annotation with semantic information

### GUI Features
- Text editor for SQL code input
- Real-time compilation and error reporting
- Parse tree visualization with collapsible nodes
- Symbol table display
- Error messages with line/column references
- File operations (open, save, new)
- Tree export to image formats

## Installation

### Requirements
- Python 3.7+
- tkinter (usually included with Python)
- pygame
- graphviz (optional, for tree visualization)
- Pillow (optional, for image display in GUI)

## Usage

### Run the Application

```bash
python app.py
```

This launches the interactive GUI where you can:

1. **Write SQL Code**: Type or paste SQL statements in the text editor
2. **Parse Code**: Click "Parse" to compile and analyze the code
3. **View Results**: 
   - See tokenization results in the Tokens tab
   - View parse tree in the Tree tab
   - Check symbol table in the Symbol Table tab
   - Review any errors in the Error tab

---

For questions or contributions, please refer to the project repository.
