"""
graph_builder.py - Xây dựng đồ thị ngữ nghĩa từ code Python.

Sử dụng AST (Abstract Syntax Tree) của Python để phân tích code và xây dựng
đồ thị ngữ nghĩa thể hiện luồng thực thi và các phép tính.
"""

import ast
from typing import Any, Optional


class SemanticGraphBuilder:
    """Xây dựng đồ thị ngữ nghĩa từ code Python."""

    def __init__(self):
        self._node_counter = 0
        self._variables: dict[str, str] = {}  # tên biến -> node_id

    def _new_id(self) -> str:
        self._node_counter += 1
        return f"n{self._node_counter}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_graph(self, code: str) -> dict:
        """
        Xây dựng đồ thị ngữ nghĩa từ code Python.

        Args:
            code: Chuỗi code Python cần phân tích.

        Returns:
            dict có các khóa: nodes, edges, metadata.
        """
        self._node_counter = 0
        self._variables = {}

        # Kiểm tra lỗi cú pháp trước
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return {
                "nodes": [],
                "edges": [],
                "metadata": {
                    "has_syntax_error": True,
                    "syntax_error": str(exc),
                    "error_line": exc.lineno,
                    "error_msg": exc.msg,
                },
            }

        nodes: list[dict] = []
        node_order: list[str] = []  # for sequential control-flow edges

        # Duyệt qua từng statement ở cấp module
        for stmt in tree.body:
            node = self._process_statement(stmt)
            if node is not None:
                nodes.append(node)
                node_order.append(node["id"])

        # Xây dựng data-flow edges
        edges: list[dict] = []
        node_by_id = {n["id"]: n for n in nodes}
        for node in nodes:
            for src_var in node.get("source_vars", []):
                if src_var in self._variables:
                    src_id = self._variables[src_var]
                    if src_id != node["id"] and src_id in node_by_id:
                        edges.append(
                            {
                                "from": src_id,
                                "to": node["id"],
                                "type": "data_flow",
                                "variable": src_var,
                            }
                        )

        # Control-flow edges (sequential)
        for i in range(len(node_order) - 1):
            edges.append(
                {
                    "from": node_order[i],
                    "to": node_order[i + 1],
                    "type": "control_flow",
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "has_syntax_error": False,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "variables": list(self._variables.keys()),
            },
        }

    # ------------------------------------------------------------------
    # Statement processors
    # ------------------------------------------------------------------

    def _process_statement(self, stmt: ast.stmt) -> Optional[dict]:
        if isinstance(stmt, ast.Import):
            return self._handle_import(stmt)
        if isinstance(stmt, ast.ImportFrom):
            return self._handle_import_from(stmt)
        if isinstance(stmt, ast.Assign):
            return self._handle_assign(stmt)
        if isinstance(stmt, ast.AugAssign):
            return self._handle_aug_assign(stmt)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            return self._handle_expr_call(stmt)
        return None

    def _handle_import(self, stmt: ast.Import) -> dict:
        names = [alias.asname or alias.name for alias in stmt.names]
        node_id = self._new_id()
        return {
            "id": node_id,
            "type": "import",
            "label": f"import {', '.join(alias.name for alias in stmt.names)}",
            "operation": "import",
            "target_var": "",
            "source_vars": [],
            "line": stmt.lineno,
            "extra": {"modules": names},
        }

    def _handle_import_from(self, stmt: ast.ImportFrom) -> dict:
        names = [alias.name for alias in stmt.names]
        node_id = self._new_id()
        return {
            "id": node_id,
            "type": "import",
            "label": f"from {stmt.module} import {', '.join(names)}",
            "operation": "import_from",
            "target_var": "",
            "source_vars": [],
            "line": stmt.lineno,
            "extra": {"module": stmt.module, "names": names},
        }

    def _handle_assign(self, stmt: ast.Assign) -> dict:
        # Lấy tên biến đích
        target_var = ""
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                target_var = target.id
                break
            if isinstance(target, ast.Subscript) and isinstance(
                target.value, ast.Name
            ):
                obj = target.value.id
                if isinstance(target.slice, ast.Constant):
                    target_var = f"{obj}['{target.slice.value}']"
                else:
                    target_var = f"{obj}[...]"
                break

        node_type, operation, source_vars, extra = self._analyze_value(stmt.value)
        node_id = self._new_id()

        # Cập nhật variable map (chỉ cho biến đơn giản)
        if target_var and "[" not in target_var:
            self._variables[target_var] = node_id

        label = f"{target_var} = {operation}" if target_var else operation
        return {
            "id": node_id,
            "type": node_type,
            "label": label,
            "operation": operation,
            "target_var": target_var,
            "source_vars": source_vars,
            "line": stmt.lineno,
            "extra": extra,
        }

    def _handle_aug_assign(self, stmt: ast.AugAssign) -> dict:
        target_var = stmt.target.id if isinstance(stmt.target, ast.Name) else ""
        node_type, operation, source_vars, extra = self._analyze_value(stmt.value)
        op_sym = self._op_symbol(stmt.op)
        node_id = self._new_id()
        return {
            "id": node_id,
            "type": "aug_assign",
            "label": f"{target_var} {op_sym}= {operation}",
            "operation": f"aug_{op_sym}",
            "target_var": target_var,
            "source_vars": ([target_var] if target_var else []) + source_vars,
            "line": stmt.lineno,
            "extra": extra,
        }

    def _handle_expr_call(self, stmt: ast.Expr) -> dict:
        node_type, operation, source_vars, extra = self._analyze_call(stmt.value)
        node_id = self._new_id()
        return {
            "id": node_id,
            "type": node_type,
            "label": operation,
            "operation": operation,
            "target_var": "",
            "source_vars": source_vars,
            "line": stmt.lineno,
            "extra": extra,
        }

    # ------------------------------------------------------------------
    # Expression analyzers
    # ------------------------------------------------------------------

    def _analyze_value(self, node: ast.expr) -> tuple:
        """Trả về (type, operation, source_vars, extra)."""
        if isinstance(node, ast.Call):
            return self._analyze_call(node)
        if isinstance(node, ast.BinOp):
            return self._analyze_binop(node)
        if isinstance(node, ast.Compare):
            return self._analyze_compare(node)
        if isinstance(node, ast.BoolOp):
            return self._analyze_boolop(node)
        if isinstance(node, ast.Subscript):
            return self._analyze_subscript(node)
        if isinstance(node, ast.Attribute):
            obj = self._get_func_name(node.value)
            return "attr_access", f"{obj}.{node.attr}", [obj] if obj else [], {}
        if isinstance(node, ast.Name):
            return "variable_ref", node.id, [node.id], {}
        if isinstance(node, ast.Constant):
            return "constant", str(node.value), [], {"value": node.value}
        if isinstance(node, ast.List):
            elts = [self._get_ast_value(e) for e in node.elts]
            is_2d = elts and isinstance(elts[0], list)
            ntype = "matrix_literal" if is_2d else "list_literal"
            return ntype, repr(elts[:2]) + ("..." if len(elts) > 2 else ""), [], {"elements": elts}
        if isinstance(node, ast.Dict):
            keys = [self._get_ast_value(k) for k in node.keys]
            return "dict_literal", f"dict(keys={keys[:3]})", [], {"keys": keys}
        if isinstance(node, ast.UnaryOp):
            _, op_str, src_vars, _ = self._analyze_value(node.operand)
            sym = "not " if isinstance(node.op, ast.Not) else "-"
            return "unary_op", f"{sym}{op_str}", src_vars, {}
        return "unknown", "unknown", [], {}

    def _analyze_call(self, node: ast.Call) -> tuple:
        func_name = self._get_func_name(node.func)
        args_vals = []
        source_vars: list[str] = []
        extra: dict[str, Any] = {"func": func_name, "args": [], "kwargs": {}}

        for arg in node.args:
            v = self._get_ast_value(arg)
            args_vals.append(str(v))
            self._collect_vars(arg, source_vars)

        for kw in node.keywords:
            v = self._get_ast_value(kw.value)
            extra["kwargs"][kw.arg] = v
            self._collect_vars(kw.value, source_vars)

        extra["args"] = args_vals
        node_type = self._classify_call(func_name, node)
        # Xây dựng label ngắn gọn
        parts = args_vals[:2]
        for k, v in list(extra["kwargs"].items())[:2]:
            parts.append(f"{k}={v}")
        operation = f"{func_name}({', '.join(parts)})"
        return node_type, operation, source_vars, extra

    def _analyze_binop(self, node: ast.BinOp) -> tuple:
        _, l_op, l_vars, _ = self._analyze_value(node.left)
        _, r_op, r_vars, _ = self._analyze_value(node.right)
        sym = self._op_symbol(node.op)
        operation = f"({l_op} {sym} {r_op})"
        extra = {"op": sym, "left": l_op, "right": r_op}
        return "arithmetic_op", operation, l_vars + r_vars, extra

    def _analyze_compare(self, node: ast.Compare) -> tuple:
        _, l_op, l_vars, _ = self._analyze_value(node.left)
        comp_vars: list[str] = []
        ops = [self._cmp_symbol(op) for op in node.ops]
        comps = []
        for c in node.comparators:
            comps.append(str(self._get_ast_value(c)))
            self._collect_vars(c, comp_vars)
        operation = f"{l_op} {ops[0]} {comps[0]}"
        extra = {"op": ops[0], "left": l_op, "right": comps[0] if comps else ""}
        return "comparison_op", operation, l_vars + comp_vars, extra

    def _analyze_boolop(self, node: ast.BoolOp) -> tuple:
        op_str = "and" if isinstance(node.op, ast.And) else "or"
        parts, src_vars = [], []
        for val in node.values:
            _, v_op, v_vars, _ = self._analyze_value(val)
            parts.append(v_op)
            src_vars.extend(v_vars)
        operation = f" {op_str} ".join(parts)
        return "bool_op", operation, src_vars, {"op": op_str}

    def _analyze_subscript(self, node: ast.Subscript) -> tuple:
        # Handle df[condition].shape[0] and similar chained patterns
        if isinstance(node.value, ast.Attribute):
            attr_name = node.value.attr
            inner = node.value.value
            slice_val = self._get_ast_value(node.slice)
            if attr_name == "shape" and isinstance(inner, ast.Subscript):
                # df[condition].shape[0] → shape_access with embedded filter
                inner_type, inner_op, inner_vars, inner_extra = self._analyze_subscript(inner)
                op = f"({inner_op}).shape[{slice_val}]"
                return (
                    "shape_access",
                    op,
                    inner_vars,
                    {
                        "filter": inner_extra.get("filter", ""),
                        "filter_raw": inner_extra.get("filter_raw", ""),
                        "shape_index": slice_val,
                    },
                )
            # Generic attribute subscript
            inner_type, inner_op, inner_vars, inner_extra = self._analyze_value(node.value)
            return "indexing", f"({inner_op})[{slice_val}]", inner_vars, {}

        if isinstance(node.value, ast.Name):
            obj = node.value.id
            sl = node.slice
            # Boolean indexing (filter)
            if isinstance(sl, (ast.Compare, ast.BoolOp)):
                _, cond_op, cond_vars, cond_extra = self._analyze_value(sl)
                # Also store the raw filter string for text-based comparisons
                try:
                    filter_raw = ast.unparse(sl)
                except Exception:
                    filter_raw = cond_op
                return (
                    "boolean_indexing",
                    f"{obj}[{cond_op}]",
                    [obj] + cond_vars,
                    {"filter": cond_op, "filter_raw": filter_raw, "filter_extra": cond_extra},
                )
            # Slice indexing like arr[:, 0]
            if isinstance(sl, ast.Tuple):
                slice_str = ", ".join(str(self._get_ast_value(s)) for s in sl.elts)
                return "slice_indexing", f"{obj}[{slice_str}]", [obj], {"slice": slice_str}
            slice_val = self._get_ast_value(sl)
            return "indexing", f"{obj}[{slice_val}]", [obj], {"key": str(slice_val)}
        return "indexing", "subscript", [], {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _classify_call(self, func_name: str, node: ast.Call) -> str:
        fn = func_name.lower()
        if fn == "print":
            return "print_output"
        if fn in ("np.array", "numpy.array"):
            if node.args and isinstance(node.args[0], ast.List):
                if node.args[0].elts and isinstance(node.args[0].elts[0], ast.List):
                    return "matrix_creation"
            return "array_creation"
        if fn in (
            "np.sum", "numpy.sum",
            "np.mean", "numpy.mean",
            "np.max", "numpy.max",
            "np.min", "numpy.min",
            "np.argmax", "numpy.argmax",
            "np.argmin", "numpy.argmin",
            "np.std", "numpy.std",
            "np.var", "numpy.var",
            "np.median", "numpy.median",
            "np.round", "numpy.round",
        ):
            return "numpy_reduction"
        if fn in (
            "np.zeros", "numpy.zeros",
            "np.ones", "numpy.ones",
            "np.arange", "numpy.arange",
            "np.linspace", "numpy.linspace",
        ):
            return "numpy_creation"
        if fn in ("pd.dataframe", "pandas.dataframe"):
            return "dataframe_creation"
        if ".sort_values" in fn:
            return "pandas_sort"
        if ".groupby" in fn:
            return "pandas_groupby"
        if ".shape" in fn or fn.endswith(".shape"):
            return "shape_access"
        if ".mean" in fn or ".sum" in fn or ".max" in fn or ".min" in fn:
            return "series_reduction"
        if ".fillna" in fn or ".dropna" in fn:
            return "pandas_na_handling"
        return "function_call"

    def _collect_vars(self, node: ast.expr, out: list) -> None:
        """Thêm tên biến từ AST node vào list out."""
        if isinstance(node, ast.Name):
            out.append(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            out.append(node.value.id)

    def _get_func_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_func_name(node.value)}.{node.attr}"
        return "unknown"

    def _get_ast_value(self, node) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.List):
            return [self._get_ast_value(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._get_ast_value(e) for e in node.elts)
        if isinstance(node, ast.Dict):
            return {
                self._get_ast_value(k): self._get_ast_value(v)
                for k, v in zip(node.keys, node.values)
            }
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            v = self._get_ast_value(node.operand)
            return -v if isinstance(v, (int, float)) else f"-{v}"
        if isinstance(node, ast.Attribute):
            return f"{self._get_ast_value(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return f"{self._get_func_name(node.func)}(...)"
        if isinstance(node, ast.Subscript):
            obj = self._get_ast_value(node.value)
            sl = self._get_ast_value(node.slice)
            return f"{obj}[{sl}]"
        if isinstance(node, ast.BinOp):
            l = self._get_ast_value(node.left)
            r = self._get_ast_value(node.right)
            return f"({l} {self._op_symbol(node.op)} {r})"
        if isinstance(node, ast.Compare):
            l = self._get_ast_value(node.left)
            ops = [self._cmp_symbol(op) for op in node.ops]
            comps = [self._get_ast_value(c) for c in node.comparators]
            return f"{l} {ops[0]} {comps[0]}"
        if isinstance(node, ast.BoolOp):
            op_str = "and" if isinstance(node.op, ast.And) else "or"
            vals = [str(self._get_ast_value(v)) for v in node.values]
            return f" {op_str} ".join(vals)
        if isinstance(node, ast.Slice):
            lo = self._get_ast_value(node.lower) if node.lower else ""
            hi = self._get_ast_value(node.upper) if node.upper else ""
            return f"{lo}:{hi}"
        if isinstance(node, ast.Tuple):
            elts = [str(self._get_ast_value(e)) for e in node.elts]
            return ", ".join(elts)
        return "?"

    def _op_symbol(self, op) -> str:
        return {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/",
            ast.FloorDiv: "//", ast.Mod: "%", ast.Pow: "**",
            ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^",
        }.get(type(op), "?")

    def _cmp_symbol(self, op) -> str:
        return {
            ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
            ast.Gt: ">", ast.GtE: ">=", ast.Is: "is", ast.IsNot: "is not",
            ast.In: "in", ast.NotIn: "not in",
        }.get(type(op), "?")


def build_graph(code: str) -> dict:
    """
    Hàm tiện ích - xây dựng đồ thị ngữ nghĩa từ code Python.

    Args:
        code: Chuỗi code Python.

    Returns:
        dict chứa nodes, edges, metadata.
    """
    return SemanticGraphBuilder().build_graph(code)
