# Semantic Analyzer (Phase 3)

class SemanticAnalyzer:
    def __init__(self):
        # Symbol Table: { table_name: { column_name: data_type } }
        self.symbol_table = {}
        self.errors = []
        self.annotated_tree = None

    def error(self, message, line=None, col=None):
        error_msg = f"[Semantic Error"
        if line is not None:
            error_msg += f" at Line {line}, Col {col}"
        error_msg += f"] {message}"
        self.errors.append(error_msg)

    def get_symbol_table_dump(self):
        """Format symbol table as a readable string."""
        if not self.symbol_table:
            return "Symbol Table: (empty)\n"
        
        lines = ["=" * 60]
        lines.append("SYMBOL TABLE")
        lines.append("=" * 60)
        
        for table_name, columns in self.symbol_table.items():
            lines.append(f"\nTable: {table_name}")
            lines.append("-" * 40)
            lines.append(f"{'Column Name':<20} {'Data Type':<15}")
            lines.append("-" * 40)
            for col_name, col_type in columns.items():
                lines.append(f"{col_name:<20} {col_type:<15}")
        
        lines.append("=" * 60)
        return "\n".join(lines)

    def annotate_node(self, node, table_context=None):
        """Annotate a single node with semantic information (non-destructive)."""
        annotations = {}
        
        # Annotate based on node type
        if node.rule.startswith("Type: "):
            type_val = node.rule.split(": ")[1]
            annotations['semantic_type'] = type_val
        
        elif node.rule.startswith("Col: "):
            col_name = node.rule.split(": ")[1]
            # Try to find column type in symbol table
            if table_context and table_context in self.symbol_table:
                if col_name in self.symbol_table[table_context]:
                    annotations['semantic_type'] = self.symbol_table[table_context][col_name]
                    annotations['symbol_ref'] = f"{table_context}.{col_name}"
            else:
                # Search all tables if no context
                for tbl_name, columns in self.symbol_table.items():
                    if col_name in columns:
                        annotations['semantic_type'] = columns[col_name]
                        annotations['symbol_ref'] = f"{tbl_name}.{col_name}"
                        break
        
        elif node.rule.startswith("Value: ") or node.rule.startswith("Val: "):
            val_text = node.rule.split(": ")[1]
            annotations['semantic_type'] = self.get_literal_type(val_text)
        
        elif node.rule.startswith("Table: "):
            table_name = node.rule.split(": ")[1]
            if table_name in self.symbol_table:
                annotations['symbol_ref'] = table_name
        
        return annotations

    def get_annotated_tree_string(self, node, indent=0, prefix="", table_context=None):
        """Generate a text representation of parse tree with semantic annotations."""
        if not node:
            return ""
        
        lines = []
        
        # Extract table context from current node if it's a table reference
        if node.rule.startswith("Table: "):
            table_context = node.rule.split(": ")[1]
        
        # Get annotations for this node
        annotations = self.annotate_node(node, table_context)
        
        # Build node information
        node_info = prefix + node.rule
        ann_parts = []
        
        if 'semantic_type' in annotations:
            ann_parts.append(f"Type: {annotations['semantic_type']}")
        if 'symbol_ref' in annotations:
            ann_parts.append(f"Ref: {annotations['symbol_ref']}")
        
        if ann_parts:
            node_info += f"  [{', '.join(ann_parts)}]"
        
        lines.append("  " * indent + node_info)
        
        # Recursively print children
        for i, child in enumerate(node.children):
            is_last = (i == len(node.children) - 1)
            child_prefix = "└─ " if is_last else "├─ "
            lines.append(self.get_annotated_tree_string(child, indent + 1, child_prefix, table_context))
        
        return "\n".join(lines)

    def analyze(self, root):
        """Perform semantic analysis and return structured results."""
        self.errors = []
        self.symbol_table = {}  # Reset for each analysis
        self.annotated_tree = root
        
        if not root:
            return {
                "success": False,
                "errors": ["No parse tree provided"],
                "symbol_table": "",
                "annotated_tree": "",
                "message": "✖ Semantic Analysis Failed. No parse tree."
            }

        # Phase 1: Build symbol table and check semantics
        for stmt in root.children:
            if stmt.rule == "CreateStmt":
                self.analyze_create(stmt)
            elif stmt.rule == "InsertStmt":
                self.analyze_insert(stmt)
            elif stmt.rule == "SelectStmt":
                self.analyze_select(stmt)
            elif stmt.rule == "UpdateStmt":
                self.analyze_update(stmt)
            elif stmt.rule == "DeleteStmt":
                self.analyze_delete(stmt)
        
        # Phase 2: Generate outputs
        success = len(self.errors) == 0
        symbol_table_dump = self.get_symbol_table_dump()
        annotated_tree_str = self.get_annotated_tree_string(root)
        
        result = {
            "success": success,
            "errors": self.errors,
            "symbol_table": symbol_table_dump,
            "annotated_tree": annotated_tree_str,
            "message": "✓ Semantic Analysis Successful. Query is valid." if success else "✖ Semantic Analysis Failed. Errors detected."
        }
        
        return result

    def analyze_create(self, node):
        table_name = None
        columns = {}

        for child in node.children:
            if child.rule.startswith("Table: "):
                table_name = child.rule.split(": ")[1]
                if table_name in self.symbol_table:
                    self.error(f"Table '{table_name}' already exists.", child.line, child.col)
            elif child.rule == "ColumnList":
                for col_node in child.children:
                    col_name = col_node.rule.split(": ")[1]
                    col_type = None
                    for type_node in col_node.children:
                        if type_node.rule.startswith("Type: "):
                            col_type = type_node.rule.split(": ")[1]

                    if col_name in columns:
                        self.error(f"Column '{col_name}' is redeclared in table '{table_name}'.", col_node.line, col_node.col)

                    if col_type not in ["INT", "FLOAT", "TEXT"]:
                        self.error(f"Invalid data type '{col_type}' for column '{col_name}'.", col_node.line, col_node.col)

                    columns[col_name] = col_type

        if table_name and table_name not in self.symbol_table:
            self.symbol_table[table_name] = columns

    def analyze_insert(self, node):
        table_name = None
        values = []

        for child in node.children:
            if child.rule.startswith("Table: "):
                table_name = child.rule.split(": ")[1]
                if table_name not in self.symbol_table:
                    self.error(f"Table '{table_name}' does not exist.", child.line, child.col)
                    return
            elif child.rule == "ValueList":
                for val_node in child.children:
                    val_text = val_node.rule.split(": ")[1]
                    # Determine type of literal
                    if val_text.startswith("'"):
                        val_type = "TEXT"
                    elif "." in val_text:
                        val_type = "FLOAT"
                    else:
                        val_type = "INT"
                    values.append((val_type, val_node.line, val_node.col))

        if table_name in self.symbol_table:
            expected_cols = self.symbol_table[table_name]
            if len(values) != len(expected_cols):
                self.error(f"INSERT into '{table_name}' expects {len(expected_cols)} values, but {len(values)} were provided.", node.line, node.col)
            else:
                col_types = list(expected_cols.values())
                for i, (val_type, v_line, v_col) in enumerate(values):
                    expected_type = col_types[i]
                    if not self.is_compatible(expected_type, val_type):
                        self.error(f"Type mismatch: Column {i+1} of '{table_name}' expects {expected_type}, but got {val_type}.", v_line, v_col)

    def analyze_select(self, node):
        table_name = None

        for child in node.children:
            if child.rule.startswith("Table: "):
                table_name = child.rule.split(": ")[1]
                if table_name not in self.symbol_table:
                    self.error(f"Table '{table_name}' does not exist.", child.line, child.col)
                    return

        if table_name in self.symbol_table:
            table_cols = self.symbol_table[table_name]
            for child in node.children:
                if child.rule == "SelectList":
                    for col_node in child.children:
                        if col_node.rule == "*":
                            continue
                        col_name = col_node.rule.split(": ")[1]
                        if col_name not in table_cols:
                            self.error(f"Column '{col_name}' does not exist in table '{table_name}'.", col_node.line, col_node.col)
                elif child.rule == "WhereClause":
                    self.analyze_where(child, table_name)

    def analyze_update(self, node):
        table_name = None
        for child in node.children:
            if child.rule.startswith("Table: "):
                table_name = child.rule.split(": ")[1]
                if table_name not in self.symbol_table:
                    self.error(f"Table '{table_name}' does not exist.", child.line, child.col)
                    return

        if table_name in self.symbol_table:
            table_cols = self.symbol_table[table_name]
            for child in node.children:
                if child.rule == "AssignmentList":
                    for assign in child.children:
                        col_node = assign.children[0]
                        val_node = assign.children[1]
                        col_name = col_node.rule.split(": ")[1]
                        val_text = val_node.rule.split(": ")[1]

                        if col_name not in table_cols:
                            self.error(f"Column '{col_name}' does not exist in table '{table_name}'.", col_node.line, col_node.col)
                        else:
                            expected_type = table_cols[col_name]
                            val_type = self.get_literal_type(val_text)
                            if not self.is_compatible(expected_type, val_type):
                                self.error(f"Type mismatch in UPDATE: Column '{col_name}' ({expected_type}) cannot be assigned {val_type}.", val_node.line, val_node.col)
                elif child.rule == "WhereClause":
                    self.analyze_where(child, table_name)

    def analyze_delete(self, node):
        table_name = None
        for child in node.children:
            if child.rule.startswith("Table: "):
                table_name = child.rule.split(": ")[1]
                if table_name not in self.symbol_table:
                    self.error(f"Table '{table_name}' does not exist.", child.line, child.col)
                    return

        if table_name in self.symbol_table:
            for child in node.children:
                if child.rule == "WhereClause":
                    self.analyze_where(child, table_name)

    def analyze_where(self, node, table_name):
        for child in node.children:
            if child.rule in ["AND", "OR", "NOT"]:
                self.analyze_where(child, table_name)
            elif child.rule == "Comparison":
                col_node = child.children[0]
                val_node = child.children[2]
                col_name = col_node.rule.split(": ")[1]
                val_text = val_node.rule.split(": ")[1]

                table_cols = self.symbol_table[table_name]
                if col_name not in table_cols:
                    self.error(f"Column '{col_name}' does not exist in table '{table_name}'.", col_node.line, col_node.col)
                else:
                    col_type = table_cols[col_name]
                    val_type = self.get_literal_type(val_text)
                    if not self.is_compatible(col_type, val_type):
                        self.error(f"Type mismatch in WHERE: Cannot compare {col_type} column '{col_name}' with {val_type} literal.", val_node.line, val_node.col)

    def get_literal_type(self, text):
        if text.startswith("'"):
            return "TEXT"
        if "." in text:
            return "FLOAT"
        return "INT"

    def is_compatible(self, type1, type2):
        if type1 == type2:
            return True
        if type1 in ["INT", "FLOAT"] and type2 in ["INT", "FLOAT"]:
            return True
        return False
