"""
a simple tooltip class for tkinter widgets
theme-aware for dark and light modes
"""

# ================ IMPORTS ================

import tkinter as tk
from tkinter import ttk

# ================ TOOLTIP CLASS ================

class Tooltip:
    """
    create a tooltip for a given widget
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        """
        display the tooltip window
        """
        if self.tooltip_window or not self.text:
            return
            
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        # get style-aware colors
        style = ttk.Style()
        bg = style.lookup("TLabel", "background")
        fg = style.lookup("TLabel", "foreground")

        label = tk.Label(tw, text=self.text, justify='left',
                         background=bg, foreground=fg, relief='solid', borderwidth=1,
                         font=("", "8", "normal"), wraplength=250)
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        """
        destroy the tooltip window
        """
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None