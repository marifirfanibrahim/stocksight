"""
column mapping dialog
user selects which column is which
smart suggestions provided
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg
from config import GUIConfig


# ================ STATE ================

class TempDataClass:
    def __init__(self):
        self.pending_df = None
        self.pending_path = None
        self.additional_columns = []
        self.original_data = None 

TEMP_DATA = TempDataClass()


# ================ SUGGESTION KEYWORDS ================

COLUMN_KEYWORDS = {
    'date': ['date', 'time', 'timestamp', 'day', 'period', 'datetime'],
    'sku': ['sku', 'product', 'item', 'code', 'article', 'name', 'id'],
    'quantity': ['quantity', 'qty', 'amount', 'count', 'units', 'sales', 'demand', 'sold', 'volume']
}


# ================ CALLBACKS ================

def confirm_mapping_callback(sender, app_data):
    """
    validate and apply column mapping
    """
    from ui.callbacks import process_loaded_data
    
    msg, color = validate_mapping_selection()
    dpg.set_value("mapping_validation_text", msg)
    dpg.configure_item("mapping_validation_text", color=color)
    
    if color != GUIConfig.SUCCESS_COLOR:
        return
    
    date_col = dpg.get_value("mapping_date_combo")
    sku_col = dpg.get_value("mapping_sku_combo")
    qty_col = dpg.get_value("mapping_quantity_combo")
    
    # get additional columns
    additional_cols = get_selected_additional_columns()
    TEMP_DATA.additional_columns = additional_cols
    
    # store original column names mapping (new -> old)
    from core.state import STATE
    STATE.column_mapping = {
        'Date': date_col,
        'SKU': sku_col,
        'Quantity': qty_col
    }
    
    # rename required columns
    rename_map = {
        date_col: 'Date',
        sku_col: 'SKU',
        qty_col: 'Quantity'
    }
    
    df_renamed = TEMP_DATA.pending_df.rename(columns=rename_map)
    
    hide_column_mapping_dialog()
    
    # build mapping info
    if additional_cols:
        mapping_info = f"Mapped + {len(additional_cols)} extra"
    else:
        mapping_info = "Mapped columns"
    
    process_loaded_data(df_renamed, TEMP_DATA.pending_path, mapping_info)


def cancel_mapping_callback(sender, app_data):
    """
    cancel mapping process
    """
    from ui.callbacks import update_status
    
    hide_column_mapping_dialog()
    update_status("Loading cancelled", warning=True)


def select_all_additional_callback(sender, app_data):
    """
    select all additional columns
    """
    if not dpg.does_item_exist("additional_columns_group"):
        return
    
    children = dpg.get_item_children("additional_columns_group", 1)
    for child in children:
        try:
            item_type = dpg.get_item_type(child)
            if "Checkbox" in item_type:
                dpg.set_value(child, True)
        except:
            pass


def deselect_all_additional_callback(sender, app_data):
    """
    deselect all additional columns
    """
    if not dpg.does_item_exist("additional_columns_group"):
        return
    
    children = dpg.get_item_children("additional_columns_group", 1)
    for child in children:
        try:
            item_type = dpg.get_item_type(child)
            if "Checkbox" in item_type:
                dpg.set_value(child, False)
        except:
            pass


def get_selected_additional_columns():
    """
    get list of selected additional columns
    """
    selected = []
    
    if not dpg.does_item_exist("additional_columns_group"):
        return selected
    
    children = dpg.get_item_children("additional_columns_group", 1)
    for child in children:
        try:
            item_type = dpg.get_item_type(child)
            if "Checkbox" in item_type:
                if dpg.get_value(child):
                    label = dpg.get_item_label(child)
                    selected.append(label)
        except:
            pass
    
    return selected


# ================ SUGGESTION FUNCTION ================

def suggest_column_mapping(columns):
    """
    suggest which column might be which
    returns dict with suggestions or none
    """
    suggestions = {
        'date': None,
        'sku': None,
        'quantity': None
    }
    
    for col in columns:
        col_lower = col.lower().strip()
        
        if col_lower == 'date':
            suggestions['date'] = col
        elif col_lower in ['sku', 'product']:
            suggestions['sku'] = col
        elif col_lower in ['quantity', 'qty']:
            suggestions['quantity'] = col
        else:
            for field, keywords in COLUMN_KEYWORDS.items():
                if suggestions[field] is None:
                    for keyword in keywords:
                        if keyword in col_lower:
                            suggestions[field] = col
                            break
    
    return suggestions


# ================ DIALOG CREATION ================

def create_column_mapping_dialog():
    """
    create column selection dialog
    """
    with dpg.window(label="Column Mapping", 
                   tag="mapping_dialog",
                   modal=True,
                   show=False,
                   width=580,
                   height=420,
                   pos=[410, 190],
                   no_resize=False):
        
        dpg.add_text("COLUMN MAPPING", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        dpg.add_spacer(height=5)
        
        dpg.add_text("Select which column represents each required field:", 
                    wrap=560, color=(200, 200, 200))
        
        dpg.add_spacer(height=15)
        
        # ---------- REQUIRED COLUMNS ----------
        dpg.add_text("REQUIRED COLUMNS", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        dpg.add_spacer(height=5)
        
        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_text("Date:")
                dpg.add_combo([], tag="mapping_date_combo", width=165)
            
            with dpg.group():
                dpg.add_text("SKU/Product:")
                dpg.add_combo([], tag="mapping_sku_combo", width=165)
            
            with dpg.group():
                dpg.add_text("Quantity:")
                dpg.add_combo([], tag="mapping_quantity_combo", width=165)
        
        dpg.add_spacer(height=15)
        
        # ---------- ADDITIONAL COLUMNS (COLLAPSIBLE) ----------
        with dpg.collapsing_header(label="ADDITIONAL COLUMNS (click to expand)", 
                                   tag="additional_columns_header",
                                   default_open=False):
            
            dpg.add_text("Select extra columns to include:", color=(150, 150, 150))
            
            with dpg.group(horizontal=True):
                dpg.add_button(label="Select All", callback=select_all_additional_callback, width=80)
                dpg.add_button(label="Deselect All", callback=deselect_all_additional_callback, width=80)
            
            dpg.add_spacer(height=5)
            
            # scrollable container for columns
            with dpg.child_window(height=120, border=True, tag="additional_columns_window"):
                with dpg.group(tag="additional_columns_group"):
                    dpg.add_text("Load data to see columns", color=(120, 120, 120))
        
        dpg.add_spacer(height=15)
        
        # ---------- VALIDATION MESSAGE ----------
        dpg.add_text("", tag="mapping_validation_text", wrap=560)
        
        dpg.add_spacer(height=10)
        
        # ---------- BUTTONS ----------
        with dpg.group(horizontal=True):
            confirm_btn = dpg.add_button(label="Confirm Mapping", 
                                        callback=confirm_mapping_callback, 
                                        width=130, height=35)
            dpg.bind_item_theme(confirm_btn, "forecast_button_theme")
            
            dpg.add_spacer(width=15)
            
            cancel_btn = dpg.add_button(label="Cancel", 
                                       callback=cancel_mapping_callback, 
                                       width=100, height=35)
            dpg.bind_item_theme(cancel_btn, "danger_button_theme")


def show_column_mapping_dialog(df, suggestions):
    """
    populate and display mapping dialog
    """
    columns = df.columns.tolist()
    
    # callback to refresh additional columns when combos change
    def refresh_additional_callback(sender, app_data):
        populate_additional_columns(df, suggestions)
    
    dpg.configure_item("mapping_date_combo", items=columns, callback=refresh_additional_callback)
    dpg.configure_item("mapping_sku_combo", items=columns, callback=refresh_additional_callback)
    dpg.configure_item("mapping_quantity_combo", items=columns, callback=refresh_additional_callback)
    
    if suggestions['date']:
        dpg.set_value("mapping_date_combo", suggestions['date'])
    elif columns:
        dpg.set_value("mapping_date_combo", columns[0])
    
    if suggestions['sku']:
        dpg.set_value("mapping_sku_combo", suggestions['sku'])
    elif len(columns) > 1:
        dpg.set_value("mapping_sku_combo", columns[1])
    
    if suggestions['quantity']:
        dpg.set_value("mapping_quantity_combo", suggestions['quantity'])
    elif len(columns) > 2:
        dpg.set_value("mapping_quantity_combo", columns[2])
    
    # populate additional columns based on initial selections
    populate_additional_columns(df, suggestions)
    
    dpg.set_value("mapping_validation_text", "")
    dpg.configure_item("mapping_dialog", show=True)
    

def populate_additional_columns(df, suggestions):
    """
    populate additional columns checkboxes
    only show columns not selected as required fields
    """
    # clear existing
    for child in dpg.get_item_children("additional_columns_group", 1):
        dpg.delete_item(child)
    
    # get CURRENTLY selected required columns from combos
    date_col = dpg.get_value("mapping_date_combo")
    sku_col = dpg.get_value("mapping_sku_combo")
    qty_col = dpg.get_value("mapping_quantity_combo")
    
    required = [date_col, sku_col, qty_col]
    
    # add checkboxes for non-required columns only
    additional = [col for col in df.columns if col not in required]
    
    if not additional:
        dpg.add_text("No additional columns available", parent="additional_columns_group", 
                    color=(120, 120, 120))
        return
    
    # update header label with count
    dpg.set_item_label("additional_columns_header", f"ADDITIONAL COLUMNS ({len(additional)} available)")
    
    for col in additional:
        dpg.add_checkbox(label=col, parent="additional_columns_group", default_value=False)


def hide_column_mapping_dialog():
    """
    hide mapping dialog
    """
    dpg.configure_item("mapping_dialog", show=False)


def validate_mapping_selection():
    """
    check if selections are valid
    return tuple of status message and color
    """
    date_col = dpg.get_value("mapping_date_combo")
    sku_col = dpg.get_value("mapping_sku_combo")
    qty_col = dpg.get_value("mapping_quantity_combo")
    
    if not date_col or not sku_col or not qty_col:
        return "Select all required columns", GUIConfig.ERROR_COLOR
    
    selections = [date_col, sku_col, qty_col]
    if len(set(selections)) < 3:
        return "Each column must be different", GUIConfig.ERROR_COLOR
    
    additional = get_selected_additional_columns()
    if additional:
        return f"Ready ({len(additional)} extra columns)", GUIConfig.SUCCESS_COLOR
    
    return "Ready to confirm", GUIConfig.SUCCESS_COLOR