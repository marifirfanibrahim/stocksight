"""
dialog windows for stocksight
column mapper with extra columns, sheet selection, diagnostics
"""


# ================ IMPORTS ================

import tkinter as tk
from tkinter import ttk
import os
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import STATE


# ================ COLUMN MAPPER ================

class ColumnMapperDialog:
    # dialog for mapping columns to required fields
    # includes additional columns selection
    
    KEYWORDS = {
        'date': ['date', 'time', 'timestamp', 'day', 'period'],
        'sku': ['sku', 'product', 'item', 'code', 'article', 'name', 'id'],
        'quantity': ['quantity', 'qty', 'amount', 'count', 'units', 'sales', 'demand', 'sold']
    }
    
    def __init__(self, parent, df):
        self.df = df
        self.result_df = None
        self.columns = df.columns.tolist()
        self.additional_columns = []
        self.checkbox_vars = {}
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Column Mapping")
        self.dialog.geometry("600x650") 
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # center dialog
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 600) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 650) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_ui()
        self.suggest_mapping()
        self.update_additional_columns()
    
    def create_ui(self):
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="COLUMN MAPPING", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(5, 15))
        
        # ---------- REQUIRED COLUMNS ----------
        ttk.Label(frame, text="REQUIRED COLUMNS", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text="Select which column represents each field:",
                  foreground="gray").pack(anchor=tk.W, pady=(0, 10))
        
        map_frame = ttk.Frame(frame)
        map_frame.pack(fill=tk.X, pady=5)
        
        # date
        ttk.Label(map_frame, text="Date:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.date_var = tk.StringVar()
        self.date_combo = ttk.Combobox(map_frame, textvariable=self.date_var,
                                        values=self.columns, state="readonly", width=30)
        self.date_combo.grid(row=0, column=1, padx=10, pady=5)
        self.date_combo.bind("<<ComboboxSelected>>", lambda e: self.update_additional_columns())
        
        # sku
        ttk.Label(map_frame, text="SKU/Product:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.sku_var = tk.StringVar()
        self.sku_combo = ttk.Combobox(map_frame, textvariable=self.sku_var,
                                       values=self.columns, state="readonly", width=30)
        self.sku_combo.grid(row=1, column=1, padx=10, pady=5)
        self.sku_combo.bind("<<ComboboxSelected>>", lambda e: self.update_additional_columns())
        
        # quantity
        ttk.Label(map_frame, text="Quantity:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.qty_var = tk.StringVar()
        self.qty_combo = ttk.Combobox(map_frame, textvariable=self.qty_var,
                                       values=self.columns, state="readonly", width=30)
        self.qty_combo.grid(row=2, column=1, padx=10, pady=5)
        self.qty_combo.bind("<<ComboboxSelected>>", lambda e: self.update_additional_columns())
        
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
        
        # ---------- ADDITIONAL COLUMNS ----------
        ttk.Label(frame, text="ADDITIONAL COLUMNS (Optional)", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text="Select extra columns to include in analysis:",
                  foreground="gray").pack(anchor=tk.W, pady=(0, 5))
        
        # button row
        btn_row = ttk.Frame(frame)
        btn_row.pack(fill=tk.X, pady=5)
        ttk.Button(btn_row, text="Select All", command=self.select_all_additional, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_row, text="Deselect All", command=self.deselect_all_additional, width=10).pack(side=tk.LEFT)
        
        # scrollable checkbox frame
        checkbox_container = ttk.Frame(frame)
        checkbox_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        canvas = tk.Canvas(checkbox_container, height=120, highlightthickness=0)
        scrollbar = ttk.Scrollbar(checkbox_container, orient="vertical", command=canvas.yview)
        self.checkbox_frame = ttk.Frame(canvas)
        
        self.checkbox_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.checkbox_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # ---------- VALIDATION MESSAGE ----------
        self.message_var = tk.StringVar(value="")
        self.message_label = ttk.Label(frame, textvariable=self.message_var, foreground="red")
        self.message_label.pack(anchor=tk.W, pady=5)
        
        # ---------- BUTTONS ----------
        btn_frame_bottom = ttk.Frame(frame)
        btn_frame_bottom.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame_bottom, text="Confirm", command=self.confirm,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame_bottom, text="Cancel", command=self.cancel).pack(side=tk.LEFT)
    
    def update_additional_columns(self):
        # update additional columns checkboxes based on required column selections
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()
        self.checkbox_vars.clear()
        
        required = {self.date_var.get(), self.sku_var.get(), self.qty_var.get()}
        additional = [col for col in self.columns if col and col not in required]
        
        if not additional:
            ttk.Label(self.checkbox_frame, text="No additional columns available", 
                     foreground="gray").pack(anchor=tk.W)
            return
        
        for col in additional:
            var = tk.BooleanVar(value=False)
            self.checkbox_vars[col] = var
            cb = ttk.Checkbutton(self.checkbox_frame, text=col, variable=var)
            cb.pack(anchor=tk.W, pady=1)
    
    def select_all_additional(self):
        for var in self.checkbox_vars.values():
            var.set(True)
    
    def deselect_all_additional(self):
        for var in self.checkbox_vars.values():
            var.set(False)
    
    def suggest_mapping(self):
        for col in self.columns:
            col_lower = col.lower().strip()
            for field, keywords in self.KEYWORDS.items():
                for keyword in keywords:
                    if keyword in col_lower:
                        if field == 'date' and not self.date_var.get(): self.date_var.set(col)
                        elif field == 'sku' and not self.sku_var.get(): self.sku_var.set(col)
                        elif field == 'quantity' and not self.qty_var.get(): self.qty_var.set(col)
                        break
    
    def confirm(self):
        date_col = self.date_var.get()
        sku_col = self.sku_var.get()
        qty_col = self.qty_var.get()
        
        if not date_col or not sku_col or not qty_col:
            self.message_var.set("Please select all required columns")
            return
        
        if len(set([date_col, sku_col, qty_col])) < 3:
            self.message_var.set("Each column must be different")
            return
        
        self.additional_columns = [col for col, var in self.checkbox_vars.items() if var.get()]
        
        rename_map = {date_col: 'Date', sku_col: 'SKU', qty_col: 'Quantity'}
        
        columns_to_keep = list(rename_map.keys()) + self.additional_columns
        self.result_df = self.df[columns_to_keep].rename(columns=rename_map)
        
        STATE.column_mapping = {'Date': date_col, 'SKU': sku_col, 'Quantity': qty_col}
        STATE.additional_columns = self.additional_columns
        
        self.dialog.destroy()
    
    def cancel(self):
        self.result_df = None
        self.dialog.destroy()


# ================ SHEET SELECTION ================

class SheetSelectionDialog:
    # dialog for selecting excel sheet
    
    def __init__(self, parent, sheet_names):
        self.selected_sheet = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Select Sheet")
        self.dialog.geometry("450x250")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 250) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="EXCEL SHEET SELECTION", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(5, 15))
        
        ttk.Label(frame, text="This file has multiple sheets.\nSelect which sheet to load:").pack(anchor=tk.W)
        
        self.sheet_var = tk.StringVar(value=sheet_names[0])
        ttk.Combobox(frame, textvariable=self.sheet_var,
                     values=sheet_names, state="readonly", width=30).pack(fill=tk.X, pady=10)
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Load Sheet", command=self.confirm,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT)
    
    def confirm(self):
        self.selected_sheet = self.sheet_var.get()
        self.dialog.destroy()
    
    def cancel(self):
        self.selected_sheet = None
        self.dialog.destroy()


# ================ DIAGNOSTICS ================

class DiagnosticsDialog:
    # sku diagnostics dialog
    # analyzes forecast quality missing data and potential issues
    
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("SKU Diagnostics")
        self.dialog.geometry("950x650")
        self.dialog.transient(parent)
        
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 950) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 650) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self.create_ui()
        self.load_data()
    
    def create_ui(self):
        frame = ttk.Frame(self.dialog, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="SKU FORECAST DIAGNOSTICS", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(5, 15))
        
        self.summary_frame = ttk.Frame(frame)
        self.summary_frame.pack(fill=tk.X, pady=10)
        
        self.total_label = ttk.Label(self.summary_frame, text="Total SKUs: 0")
        self.total_label.pack(anchor=tk.W)
        self.success_label = ttk.Label(self.summary_frame, text="Forecasted: 0", foreground="green")
        self.success_label.pack(anchor=tk.W)
        self.skipped_label = ttk.Label(self.summary_frame, text="Issues: 0", foreground="red")
        self.skipped_label.pack(anchor=tk.W)
        
        # filter frame
        filter_frame = ttk.Frame(frame)
        filter_frame.pack(fill=tk.X, pady=5)
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 5))
        self.filter_var = tk.StringVar(value="All")
        filter_cb = ttk.Combobox(filter_frame, textvariable=self.filter_var, 
                                 values=["All", "Forecasted", "Issues"], state="readonly", width=15)
        filter_cb.pack(side=tk.LEFT)
        filter_cb.bind("<<ComboboxSelected>>", lambda e: self.load_data())

        table_frame = ttk.Frame(frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        columns = ("SKU", "Status", "Records", "Avg Qty", "CV (Var)", "Date Range")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_tree(c, False))
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(frame, text="Close", command=self.dialog.destroy).pack(pady=10)
    
    def auto_fit_columns(self):
        # auto-fit column widths based on content
        for col in self.tree["columns"]:
            # get header width
            header_width = len(str(col)) * 10 + 20
            max_width = header_width
            
            # check all items
            for item in self.tree.get_children():
                cell_value = self.tree.set(item, col)
                cell_width = len(str(cell_value)) * 8 + 20
                if cell_width > max_width:
                    max_width = cell_width
            
            # set column width with min and max limits
            # give status column more room
            if col == "Status":
                max_width = min(max_width, 400)
            else:
                max_width = min(max_width, 250)
                
            max_width = max(max_width, 80)
            self.tree.column(col, width=max_width)
    
    def sort_tree(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        try:
            # try numeric sort
            l.sort(key=lambda t: float(t[0].replace(',', '').replace('%','')), reverse=reverse)
        except ValueError:
            # fallback string sort
            l.sort(reverse=reverse)
            
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)
            
        self.tree.heading(col, command=lambda: self.sort_tree(col, not reverse))

    def load_data(self):
        # clear existing
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        if STATE.clean_data is None: return
        
        total = len(STATE.sku_list)
        successful = len(STATE.successful_skus)
        
        self.total_label.configure(text=f"Total SKUs: {total}")
        self.success_label.configure(text=f"Forecasted: {successful}")
        
        filter_mode = self.filter_var.get()
        issue_count = 0
        
        for sku in STATE.sku_list:
            # status determination
            if sku in STATE.skipped_skus:
                status = f"ERR: {STATE.skipped_skus[sku]}"
            elif sku in STATE.successful_skus:
                status = "OK"
            else:
                sku_df_check = STATE.clean_data[STATE.clean_data['SKU'] == sku]
                if len(sku_df_check) < 5:
                    status = "WARN: Low Data"
                else:
                    status = "Ready"
            
            # filter logic
            if filter_mode == "Forecasted" and status != "OK": continue
            if filter_mode == "Issues" and not ("ERR" in status or "WARN" in status): continue
            
            if "ERR" in status or "WARN" in status:
                issue_count += 1
            
            # get basic stats
            sku_df = STATE.clean_data[STATE.clean_data['SKU'] == sku]
            records = len(sku_df)
            
            if records > 0:
                avg_qty = sku_df['Quantity'].mean()
                std_dev = sku_df['Quantity'].std()
                cv = (std_dev / avg_qty) if avg_qty > 0 else 0
                min_date = sku_df['Date'].min().strftime('%Y-%m-%d')
                max_date = sku_df['Date'].max().strftime('%Y-%m-%d')
            else:
                avg_qty = 0
                cv = 0
                min_date = "N/A"
                max_date = "N/A"
            
            self.tree.insert("", "end", values=(
                sku,
                status,
                records,
                f"{avg_qty:,.2f}",
                f"{cv:.2f}",
                f"{min_date} to {max_date}"
            ))
        
        self.skipped_label.configure(text=f"Issues/Skipped: {issue_count}")
        
        # auto-fit after loading
        self.auto_fit_columns()