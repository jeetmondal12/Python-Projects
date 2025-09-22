"""
Advanced Calculator
File: main.py

Features:
- Modern Tkinter UI with light/dark theme toggle
- Safe expression evaluator using ast parsing and math functions
- History panel, memory buttons (M+, M-, MR, MC)
- Keyboard bindings, copy/paste, backspace, clear

Run: python main.py
"""
from __future__ import annotations

import ast
import math
import operator
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox


class SafeEvaluator:
	"""Evaluate math expressions safely using AST.

	Supports +, -, *, /, %, **, unary +/-, parentheses, numbers,
	and math functions/constants from the allowed list.
	"""

	# allowed binary operators
	_binops = {
		ast.Add: operator.add,
		ast.Sub: operator.sub,
		ast.Mult: operator.mul,
		ast.Div: operator.truediv,
		ast.Mod: operator.mod,
		ast.Pow: operator.pow,
		ast.FloorDiv: operator.floordiv,
	}

	# allowed unary ops
	_unaryops = {ast.UAdd: operator.pos, ast.USub: operator.neg}

	# allowed names -> functions/constants
	_names = {k: getattr(math, k) for k in dir(math) if not k.startswith("__")}
	# add some builtins
	_names.update({
		"abs": abs,
		"round": round,
		"min": min,
		"max": max,
		"pi": math.pi,
		"e": math.e,
	})

	def eval(self, expression: str) -> float:
		try:
			node = ast.parse(expression, mode="eval")
			return self._eval(node.body)
		except Exception as e:
			raise ValueError(f"Invalid expression: {e}")

	def _eval(self, node):
		if isinstance(node, ast.BinOp):
			op_type = type(node.op)
			if op_type in self._binops:
				left = self._eval(node.left)
				right = self._eval(node.right)
				return self._binops[op_type](left, right)
			raise ValueError(f"Unsupported binary operator: {op_type}")
		if isinstance(node, ast.UnaryOp):
			op_type = type(node.op)
			if op_type in self._unaryops:
				return self._unaryops[op_type](self._eval(node.operand))
			raise ValueError(f"Unsupported unary operator: {op_type}")
		if isinstance(node, ast.Num):
			return node.n
		if isinstance(node, ast.Constant):
			if isinstance(node.value, (int, float)):
				return node.value
			raise ValueError("Only numeric constants are allowed")
		if isinstance(node, ast.Call):
			# func(args...)
			if isinstance(node.func, ast.Name):
				func_name = node.func.id
				if func_name in self._names and callable(self._names[func_name]):
					args = [self._eval(a) for a in node.args]
					return self._names[func_name](*args)
			raise ValueError("Only simple function calls are allowed")
		if isinstance(node, ast.Name):
			if node.id in self._names:
				val = self._names[node.id]
				if isinstance(val, (int, float)):
					return val
			raise ValueError(f"Unknown name: {node.id}")
		if isinstance(node, ast.Expr):
			return self._eval(node.value)
		raise ValueError(f"Unsupported expression: {type(node)}")


class CalculatorApp(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Advanced Calculator")
		self.geometry("420x600")
		self.resizable(False, False)

		self.style = ttk.Style(self)
		# default theme
		self._theme = "light"
		self._apply_theme()

		self.evaluator = SafeEvaluator()
		self.memory = 0.0
		self.history: list[str] = []

		self._create_widgets()
		self._bind_keys()

	def _apply_theme(self):
		if self._theme == "dark":
			bg = "#2e2e2e"
			fg = "#ffffff"
			btn_bg = "#3c3f41"
			entry_bg = "#1e1e1e"
		else:
			bg = "#f3f4f6"
			fg = "#111827"
			btn_bg = "#ffffff"
			entry_bg = "#ffffff"
		self.configure(bg=bg)
		self.style.configure("TFrame", background=bg)
		self.style.configure("TLabel", background=bg, foreground=fg)
		self.style.configure("TButton", background=btn_bg, foreground=fg)

	def _create_widgets(self):
		main = ttk.Frame(self)
		main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

		# display
		self.display_var = tk.StringVar()
		entry = ttk.Entry(main, textvariable=self.display_var, font=("Segoe UI", 20), justify=tk.RIGHT)
		entry.pack(fill=tk.X, pady=(0, 10))
		entry.focus()

		# buttons frame
		btn_frame = ttk.Frame(main)
		btn_frame.pack()

		buttons = [
			["MC", "MR", "M+", "M-"],
			["7", "8", "9", "/"],
			["4", "5", "6", "*"],
			["1", "2", "3", "-"],
			["0", ".", "%", "+"],
			["(", ")", "^", "sqrt"],
			["sin", "cos", "tan", "log"],
			["C", "⌫", "Ans", "="],
		]

		for r, row in enumerate(buttons):
			for c, label in enumerate(row):
				b = ttk.Button(btn_frame, text=label, command=lambda l=label: self._on_button(l))
				b.grid(row=r, column=c, ipadx=10, ipady=12, padx=4, pady=4, sticky="nsew")
		for i in range(4):
			btn_frame.grid_columnconfigure(i, weight=1)

		# history
		hist_label = ttk.Label(main, text="History")
		hist_label.pack(anchor=tk.W, pady=(10, 0))
		self.history_list = tk.Listbox(main, height=6)
		self.history_list.pack(fill=tk.X)
		self.history_list.bind("<<ListboxSelect>>", self._on_history_select)

		# bottom controls
		bottom = ttk.Frame(main)
		bottom.pack(fill=tk.X, pady=(10, 0))

		theme_btn = ttk.Button(bottom, text="Toggle Theme", command=self._toggle_theme)
		theme_btn.pack(side=tk.LEFT)

		copy_btn = ttk.Button(bottom, text="Copy", command=self._copy)
		copy_btn.pack(side=tk.RIGHT)

	def _on_button(self, label: str):
		if label == "C":
			self.display_var.set("")
			return
		if label == "⌫":
			self.display_var.set(self.display_var.get()[:-1])
			return
		if label == "=":
			self._calculate()
			return
		if label == "Ans":
			if self.history:
				last = self.history[-1].split(" = ")[-1]
				self.display_var.set(self.display_var.get() + last)
			return
		if label in ("M+", "M-", "MR", "MC"):
			self._memory_op(label)
			return
		# map ^ -> ** and sqrt -> sqrt(...)
		if label == "^":
			self.display_var.set(self.display_var.get() + "**")
			return
		if label == "sqrt":
			self.display_var.set(self.display_var.get() + "sqrt(")
			return
		if label in ("sin", "cos", "tan", "log"):
			self.display_var.set(self.display_var.get() + f"{label}(")
			return
		# default: append label
		self.display_var.set(self.display_var.get() + label)

	def _calculate(self):
		expr = self.display_var.get().strip()
		if not expr:
			return
		try:
			result = self.evaluator.eval(expr)
			# format nicely
			if isinstance(result, float) and result.is_integer():
				result = int(result)
			self.history.append(f"{expr} = {result}")
			self._refresh_history()
			self.display_var.set(str(result))
		except Exception as e:
			messagebox.showerror("Error", str(e))

	def _refresh_history(self):
		self.history_list.delete(0, tk.END)
		for item in reversed(self.history[-100:]):
			self.history_list.insert(tk.END, item)

	def _on_history_select(self, _ev):
		sel = self.history_list.curselection()
		if not sel:
			return
		item = self.history_list.get(sel[0])
		expr = item.split(" = ")[0]
		self.display_var.set(expr)

	def _memory_op(self, op: str):
		try:
			if op == "MC":
				self.memory = 0.0
			elif op == "MR":
				self.display_var.set(self.display_var.get() + str(self.memory))
			elif op == "M+":
				val = float(self.display_var.get() or 0)
				self.memory += val
			elif op == "M-":
				val = float(self.display_var.get() or 0)
				self.memory -= val
		except Exception:
			messagebox.showerror("Error", "Memory operation failed")

	def _toggle_theme(self):
		self._theme = "dark" if self._theme == "light" else "light"
		self._apply_theme()

	def _copy(self):
		self.clipboard_clear()
		self.clipboard_append(self.display_var.get())

	def _bind_keys(self):
		self.bind("<Return>", lambda e: self._calculate())
		self.bind("<BackSpace>", lambda e: self.display_var.set(self.display_var.get()[:-1]))
		self.bind("<Escape>", lambda e: self.display_var.set(""))
		for ch in "0123456789.+-*/()%":
			self.bind(ch, lambda e, c=ch: self.display_var.set(self.display_var.get() + c))
		# caret ^ mapping
		self.bind("^", lambda e: self.display_var.set(self.display_var.get() + "**"))


def main():
	app = CalculatorApp()
	app.mainloop()


if __name__ == "__main__":
	main()

