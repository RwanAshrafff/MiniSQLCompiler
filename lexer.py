# Lexical Analyzer

KEYWORDS = {
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES",
    "UPDATE", "SET", "DELETE", "CREATE", "TABLE",
    "INT", "FLOAT", "TEXT", "AND", "OR", "NOT"
}

OPERATORS = {"=", "<>", "!=", "<=", ">=", "<", ">", "+", "-", "*", "/"}
DELIMITERS = {"(", ")", ",", ";", "."}


def is_letter(ch):
    return ch.isalpha() or ch == "_"


def is_digit(ch):
    return ch.isdigit()


def is_whitespace(ch):
    return ch in " \t\r\n"


def tokenize_sql(code):
    """Tokenize SQL code"""
    tokens = []
    paren_stack = []
    i = 0
    line = 1
    column = 1
    length = len(code)

    while i < length:
        ch = code[i]

        if ch == '\n':
            line += 1
            column = 1
            i += 1
            continue

        if is_whitespace(ch):
            i += 1
            column += 1
            continue

        if i + 1 < length and code[i:i+2] == "--":
            while i < length and code[i] != '\n':
                i += 1
            continue

        if i + 1 < length and code[i:i+2] == "/*":
            start_line, start_col = line, column
            i += 2
            closed = False
            while i < length - 1:
                if code[i] == '\n':
                    line += 1
                    column = 1
                    i += 1
                    continue
                if code[i:i+2] == "/*":
                    tokens.append(("ERROR", f"nested comment detected", line, column))
                    return tokens
                if code[i:i+2] == "*/":
                    i += 2
                    closed = True
                    break
                i += 1
                column += 1
            if not closed:
                tokens.append(("ERROR", f"unclosed comment", line, column))
                return tokens
            continue

        if ch == "'":
            start_line, start_col = line, column
            i += 1
            value = ""
            closed = False
            while i < length:
                if code[i] == '\n':
                    tokens.append(("ERROR", f"unclosed string", line, column))
                    return tokens
                if code[i] == "'":
                    closed = True
                    i += 1
                    break
                value += code[i]
                i += 1
            if not closed:
                tokens.append(("ERROR", f"unclosed string", line, column))
                return tokens
            tokens.append(("STRING_LITERAL", "'" + value + "'", start_line, start_col))
            column += len(value) + 2
            continue

        if is_letter(ch):
            start = i
            start_col = column
            while i < length and (is_letter(code[i]) or is_digit(code[i])):
                i += 1
                column += 1
            word = code[start:i]
            if word.upper() in KEYWORDS:
                tokens.append(("KEYWORD", word.upper(), line, start_col))
            else:
                if len(word) > 63:
                    tokens.append(("ERROR", f"identifier too long", line, start_col))
                    return tokens
                tokens.append(("IDENTIFIER", word, line, start_col))
            continue

        if is_digit(ch):
            start = i
            start_col = column
            has_dot = False
            while i < length and (is_digit(code[i]) or (code[i] == '.' and not has_dot)):
                if code[i] == '.':
                    has_dot = True
                i += 1
                column += 1
            value = code[start:i]
            token_type = "FLOAT_LITERAL" if has_dot else "INTEGER_LITERAL"
            tokens.append((token_type, value, line, start_col))
            continue

        two_char = code[i:i+2]
        if two_char in OPERATORS:
            tokens.append(("OPERATOR", two_char, line, column))
            i += 2
            column += 2
            continue
        elif ch in OPERATORS:
            tokens.append(("OPERATOR", ch, line, column))
            i += 1
            column += 1
            continue

        if ch in DELIMITERS:
            if ch == '(':
                paren_stack.append((line, column))
            elif ch == ')':
                if not paren_stack:
                    tokens.append(("ERROR", f"unmatched ')'", line, column))
                    return tokens
                paren_stack.pop()
            tokens.append(("DELIMITER", ch, line, column))
            i += 1
            column += 1
            continue

        tokens.append(("ERROR", f"invalid character '{ch}'", line, column))
        return tokens

    if paren_stack:
        l, c = paren_stack[-1]
        tokens.append(("ERROR", f"unmatched '('", l, c))
        return tokens

    return tokens
