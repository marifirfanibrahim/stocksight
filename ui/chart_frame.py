"""
chart frame for displaying matplotlib charts
"""


# ================ IMPORTS ================

import tkinter as tk
from tkinter import ttk
import os


# ================ CHART FRAME ================

class ChartFrame(ttk.Frame):
    """
    frame for displaying chart images
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.image = None
        self.photo = None
        
        # Get background color safely from style
        try:
            style = ttk.Style()
            bg = style.lookup("TFrame", "background")
            # Fallback if lookup returns empty string
            if not bg:
                bg = 'white'
        except Exception:
            bg = 'white'
        
        # Create canvas with scrollbars
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, bg=bg)
        self.h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=self.h_scrollbar.set,
                               yscrollcommand=self.v_scrollbar.set)
        
        # Grid layout
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Placeholder text
        self.placeholder_id = self.canvas.create_text(
            400, 200, text="Run forecast to see chart.",
            fill="gray", font=("", 12)
        )
        
        # Bind mousewheel
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
    
    def _on_mousewheel(self, event):
        if self.v_scrollbar.winfo_ismapped():
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_shift_mousewheel(self, event):
        if self.h_scrollbar.winfo_ismapped():
            self.canvas.xview_scroll(int(-1*(event.delta/120)), "units")

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Shift-MouseWheel>", self._on_shift_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Shift-MouseWheel>")
    
    def load_image(self, image_path):
        """
        load and display image
        """
        if not os.path.exists(image_path):
            print(f"Image not found: {image_path}")
            return False
        
        try:
            from PIL import Image, ImageTk
            
            # Clear existing
            self.canvas.delete("all")
            
            # Load image
            self.image = Image.open(image_path)
            self.photo = ImageTk.PhotoImage(self.image)
            
            # Display
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
            # Update scroll region
            self.canvas.configure(scrollregion=(0, 0, self.image.width, self.image.height))
            
            return True
            
        except ImportError:
            print("PIL/Pillow not available, showing placeholder text.")
            self.canvas.create_text(
                400, 200, text=f"Chart saved to:\n{image_path}",
                fill="gray", font=("", 10), justify=tk.CENTER
            )
            return False
        except Exception as e:
            print(f"Error loading image: {e}")
            self.canvas.create_text(
                400, 200, text=f"Error loading chart: {e}",
                fill="red", font=("", 10)
            )
            return False
    
    def clear(self):
        """
        clear chart display
        """
        self.canvas.delete("all")
        self.image = None
        self.photo = None
        
        self.placeholder_id = self.canvas.create_text(
            400, 200, text="Run forecast to see chart.",
            fill="gray", font=("", 12)
        )