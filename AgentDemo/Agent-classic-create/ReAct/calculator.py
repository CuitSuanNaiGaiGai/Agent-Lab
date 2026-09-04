import ast
import operator

# ast.literal_eval 支持的运算符白名单
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def _safe_eval(node):
    """递归求值 ast 节点，超出白名单抛出异常。"""
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        return op(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        return op(_safe_eval(node.operand))
    raise ValueError(f"不支持的表达式节点: {type(node).__name__}")

def calculator(expression: str) -> str:
    """
    一个安全的算术表达式计算器工具。
    支持 + - * / // % ** 和括号，例如: (3 + 4) * 2 - 10 / 5
    """
    expr = expression.strip()
    if not expr:
        return "错误: 表达式为空"
    try:
        tree = ast.parse(expr, mode="eval")
        result = _safe_eval(tree)
        return f"{expr} = {result}"
    except Exception as e:
        return f"计算错误: {e}。请输入合法的算术表达式，例如: 3 * (2 + 4)"
