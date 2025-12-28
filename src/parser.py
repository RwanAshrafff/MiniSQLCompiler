# Syntax Parser

class ParseTreeNode:
    def __init__(self, value, line=None, col=None, text=None):
        self.children = []
        self.rule = value
        self.node_id = None
        self.line = line
        self.col = col
        self.text = text

    def add_child(self, node):
        self.children.append(node)

    def __repr__(self):
        return self.rule


class Parser:
    def __init__(self, tokens):
        self.tokens = [t for t in tokens if t[0] != 'ERROR']
        self.current = 0
        self.had_error = False
        self.error_messages = []

    def peek(self):
        if self.current >= len(self.tokens):
            return None
        return self.tokens[self.current]

    def advance(self):
        if self.current < len(self.tokens):
            self.current += 1
            return self.tokens[self.current - 1]
        return None

    def error(self, message):
        self.had_error = True
        token = self.peek()
        if token:
            error_msg = f"[Line {token[2]}, Col {token[3]}] {message}"
            self.error_messages.append(error_msg)
        else:
            error_msg = f"[End of Input] {message}"
            self.error_messages.append(error_msg)

    def synchronize(self):
        self.advance()
        while self.peek():
            if self.tokens[self.current - 1][1] == ";":
                return
            if self.peek()[1].upper() in ["CREATE", "SELECT", "INSERT", "UPDATE", "DELETE"]:
                return
            self.advance()

    def match(self, expected_type, expected_lexeme=None):
        cur = self.peek()
        if cur is None:
            return False
        if cur[0] != expected_type:
            return False
        if expected_lexeme is not None and cur[1] != expected_lexeme:
            return False
        self.advance()
        return True

    def create_node(self, value):
        token = self.peek()
        if token:
            return ParseTreeNode(value, token[2], token[3], token[1])
        return ParseTreeNode(value)

    def parse_query(self):
        root = ParseTreeNode('Query')
        while self.peek():
            stmt_node = self.parse_statement()
            if stmt_node:
                root.add_child(stmt_node)
            else:
                self.synchronize()
        return root

    def parse_statement(self):
        token = self.peek()
        if not token:
            return None
        lexeme = token[1].upper()
        if lexeme == "CREATE":
            return self.parse_CreateStmt()
        elif lexeme == "SELECT":
            return self.parse_SelectStmt()
        elif lexeme == "INSERT":
            return self.parse_InsertStmt()
        elif lexeme == "UPDATE":
            return self.parse_UpdateStmt()
        elif lexeme == "DELETE":
            return self.parse_DeleteStmt()
        else:
            self.error(f"Unexpected token '{lexeme}'")
            return None

    def parse_CreateStmt(self):
        node = ParseTreeNode("CreateStmt")
        if not self.match("KEYWORD", "CREATE"):
            return None
        node.add_child(self.create_node("CREATE"))
        if not self.match("KEYWORD", "TABLE"):
            self.error("Expected 'TABLE'")
            return None
        node.add_child(self.create_node("TABLE"))
        table_token = self.peek()
        if not self.match("IDENTIFIER"):
            self.error("Expected table name")
            return None
        node.add_child(ParseTreeNode(f"Table: {table_token[1]}", table_token[2], table_token[3], table_token[1]))
        if not self.match("DELIMITER", "("):
            self.error("Expected '('")
            return None
        col_list = self.parse_ColumnList()
        if not col_list:
            return None
        node.add_child(col_list)
        if not self.match("DELIMITER", ")"):
            self.error("Expected ')'")
            return None
        if not self.match("DELIMITER", ";"):
            self.error("Expected ';'")
            return None
        return node

    def parse_ColumnList(self):
        node = ParseTreeNode("ColumnList")
        while True:
            col_token = self.peek()
            if not self.match("IDENTIFIER"):
                self.error("Expected column name")
                return None
            col_node = ParseTreeNode(f"Col: {col_token[1]}", col_token[2], col_token[3], col_token[1])
            type_token = self.peek()
            if type_token and type_token[1] in ["INT", "FLOAT", "TEXT"]:
                self.advance()
                col_node.add_child(ParseTreeNode(f"Type: {type_token[1]}", type_token[2], type_token[3], type_token[1]))
            else:
                self.error("Expected data type")
                return None
            node.add_child(col_node)
            if not self.match("DELIMITER", ","):
                break
        return node

    def parse_InsertStmt(self):
        node = ParseTreeNode("InsertStmt")
        if not self.match("KEYWORD", "INSERT"):
            return None
        node.add_child(self.create_node("INSERT"))
        if not self.match("KEYWORD", "INTO"):
            self.error("Expected 'INTO'")
            return None
        node.add_child(self.create_node("INTO"))
        tbl_token = self.peek()
        if not self.match("IDENTIFIER"):
            self.error("Expected table name")
            return None
        node.add_child(ParseTreeNode(f"Table: {tbl_token[1]}", tbl_token[2], tbl_token[3], tbl_token[1]))
        if not self.match("KEYWORD", "VALUES"):
            self.error("Expected 'VALUES'")
            return None
        node.add_child(self.create_node("VALUES"))
        if not self.match("DELIMITER", "("):
            self.error("Expected '('")
            return None
        val_list = self.parse_ValueList()
        if not val_list:
            return None
        node.add_child(val_list)
        if not self.match("DELIMITER", ")"):
            self.error("Expected ')'")
            return None
        if not self.match("DELIMITER", ";"):
            self.error("Expected ';'")
            return None
        return node

    def parse_ValueList(self):
        node = ParseTreeNode("ValueList")
        while True:
            token = self.peek()
            if not token:
                break
            if token[0] in ["INTEGER_LITERAL", "FLOAT_LITERAL", "STRING_LITERAL"]:
                self.advance()
                node.add_child(ParseTreeNode(f"Value: {token[1]}", token[2], token[3], token[1]))
            else:
                self.error("Expected value")
                return None
            if not self.match("DELIMITER", ","):
                break
        return node

    def parse_SelectStmt(self):
        node = ParseTreeNode("SelectStmt")
        if not self.match("KEYWORD", "SELECT"):
            return None
        node.add_child(self.create_node("SELECT"))
        sl_node = self.parse_SelectList()
        if not sl_node:
            return None
        node.add_child(sl_node)
        if not self.match("KEYWORD", "FROM"):
            self.error("Expected 'FROM'")
            return None
        node.add_child(self.create_node("FROM"))
        tbl = self.peek()
        if not self.match("IDENTIFIER"):
            self.error("Expected table name")
            return None
        node.add_child(ParseTreeNode(f"Table: {tbl[1]}", tbl[2], tbl[3], tbl[1]))
        next_tok = self.peek()
        if next_tok and next_tok[1].upper() == "WHERE":
            where_node = self.parse_WhereClause()
            if where_node:
                node.add_child(where_node)
        if not self.match("DELIMITER", ";"):
            self.error("Expected ';'")
            return None
        return node

    def parse_SelectList(self):
        node = ParseTreeNode("SelectList")
        if self.match("OPERATOR", "*"):
            node.add_child(ParseTreeNode("*"))
            return node
        while True:
            token = self.peek()
            if not self.match("IDENTIFIER"):
                self.error("Expected column")
                return None
            node.add_child(ParseTreeNode(f"Col: {token[1]}", token[2], token[3], token[1]))
            if not self.match("DELIMITER", ","):
                break
        return node

    def parse_WhereClause(self):
        if not self.match("KEYWORD", "WHERE"):
            return None
        node = ParseTreeNode("WhereClause")
        node.add_child(self.create_node("WHERE"))
        cond_node = self.parse_Condition()
        if cond_node:
            node.add_child(cond_node)
        return node

    def parse_Condition(self):
        left = self.parse_AndTerm()
        if not left:
            return None
        while self.match("KEYWORD", "OR"):
            parent = ParseTreeNode("OR")
            parent.add_child(left)
            right = self.parse_AndTerm()
            if not right:
                return None
            parent.add_child(right)
            left = parent
        return left

    def parse_AndTerm(self):
        left = self.parse_BaseCondition()
        if not left:
            return None
        while self.match("KEYWORD", "AND"):
            parent = ParseTreeNode("AND")
            parent.add_child(left)
            right = self.parse_BaseCondition()
            if not right:
                return None
            parent.add_child(right)
            left = parent
        return left

    def parse_BaseCondition(self):
        if self.match("KEYWORD", "NOT"):
            node = ParseTreeNode("NOT")
            child = self.parse_BaseCondition()
            if child:
                node.add_child(child)
            return node
        if self.match("DELIMITER", "("):
            node = self.parse_Condition()
            if not node:
                return None
            if not self.match("DELIMITER", ")"):
                self.error("Expected ')'")
            return node
        id_tok = self.peek()
        if not self.match("IDENTIFIER"):
            self.error("Expected identifier")
            return None
        comp_node = ParseTreeNode("Comparison")
        comp_node.add_child(ParseTreeNode(f"Col: {id_tok[1]}", id_tok[2], id_tok[3], id_tok[1]))
        op_tok = self.peek()
        if op_tok and op_tok[0] == "OPERATOR":
            self.advance()
            comp_node.add_child(ParseTreeNode(f"Op: {op_tok[1]}", op_tok[2], op_tok[3], op_tok[1]))
        else:
            self.error("Expected operator")
            return None
        val_tok = self.peek()
        if val_tok and val_tok[0] in ["INTEGER_LITERAL", "FLOAT_LITERAL", "STRING_LITERAL"]:
            self.advance()
            comp_node.add_child(ParseTreeNode(f"Val: {val_tok[1]}", val_tok[2], val_tok[3], val_tok[1]))
        else:
            self.error("Expected value")
            return None
        return comp_node

    def parse_UpdateStmt(self):
        node = ParseTreeNode("UpdateStmt")
        if not self.match("KEYWORD", "UPDATE"):
            return None
        node.add_child(self.create_node("UPDATE"))
        tbl = self.peek()
        if not self.match("IDENTIFIER"):
            self.error("Expected table")
            return None
        node.add_child(ParseTreeNode(f"Table: {tbl[1]}", tbl[2], tbl[3], tbl[1]))
        if not self.match("KEYWORD", "SET"):
            self.error("Expected 'SET'")
            return None
        node.add_child(self.create_node("SET"))
        assign_node = self.parse_AssignmentList()
        if assign_node:
            node.add_child(assign_node)
        if self.peek() and self.peek()[1].upper() == "WHERE":
            where_node = self.parse_WhereClause()
            if where_node:
                node.add_child(where_node)
        if not self.match("DELIMITER", ";"):
            self.error("Expected ';'")
        return node

    def parse_AssignmentList(self):
        node = ParseTreeNode("AssignmentList")
        while True:
            col = self.peek()
            if not self.match("IDENTIFIER"):
                self.error("Expected column")
                return None
            assign = ParseTreeNode("Assignment")
            assign.add_child(ParseTreeNode(f"Col: {col[1]}", col[2], col[3], col[1]))
            if not self.match("OPERATOR", "="):
                self.error("Expected '='")
                return None
            val = self.peek()
            if val and val[0] in ["INTEGER_LITERAL", "FLOAT_LITERAL", "STRING_LITERAL"]:
                self.advance()
                assign.add_child(ParseTreeNode(f"Val: {val[1]}", val[2], val[3], val[1]))
            else:
                self.error("Expected value")
                return None
            node.add_child(assign)
            if not self.match("DELIMITER", ","):
                break
        return node

    def parse_DeleteStmt(self):
        node = ParseTreeNode("DeleteStmt")
        if not self.match("KEYWORD", "DELETE"):
            return None
        node.add_child(self.create_node("DELETE"))
        if not self.match("KEYWORD", "FROM"):
            self.error("Expected 'FROM'")
            return None
        node.add_child(self.create_node("FROM"))
        tbl = self.peek()
        if not self.match("IDENTIFIER"):
            self.error("Expected table")
            return None
        node.add_child(ParseTreeNode(f"Table: {tbl[1]}", tbl[2], tbl[3], tbl[1]))
        if self.peek() and self.peek()[1].upper() == "WHERE":
            where_node = self.parse_WhereClause()
            if where_node:
                node.add_child(where_node)
        if not self.match("DELIMITER", ";"):
            self.error("Expected ';'")
        return node
