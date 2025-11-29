"""
centralized theme definitions
button and widget styling
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg
import platform
import os


# ================ FONT HELPER ================

def get_system_font():
    """
    get system font path based on os
    """
    system = platform.system()
    
    if system == "Windows":
        candidates = [
            "C:\\Windows\\Fonts\\Arial.ttf",
            "C:\\Windows\\Fonts\\segoeui.ttf",
            "C:\\Windows\\Fonts\\tahoma.ttf",
        ]
    elif system == "Darwin":
        candidates = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNS.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
    else:
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/TTF/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    
    for path in candidates:
        if os.path.exists(path):
            return path
    
    return None


# ================ THEME CREATION ================

def create_all_themes():
    """
    create all button themes
    call once during gui setup
    """
    # ---------- FONT REGISTRY ----------
    with dpg.font_registry():
        font_path = get_system_font()
        if font_path and os.path.exists(font_path):
            try:
                dpg.add_font(font_path, 20, tag="stat_font")
            except Exception as e:
                print(f"font load warning: {e}")
                # Continue without custom font
        else:
            print("no system font found, using default")
    
    # ---------- RUN FORECAST BUTTON THEME ----------
    with dpg.theme(tag="forecast_button_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 150, 100), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 200, 130), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 255, 150), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
    
    # ---------- EXPORT BUTTON THEME ----------
    with dpg.theme(tag="export_button_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (100, 100, 180), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (130, 130, 220), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (150, 150, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
    
    # ---------- DANGER BUTTON THEME ----------
    with dpg.theme(tag="danger_button_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 60, 60), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (220, 80, 80), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 100, 100), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
    
    # ---------- UPLOAD BUTTON THEME ----------
    with dpg.theme(tag="upload_button_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (80, 120, 180), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (100, 150, 220), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (120, 180, 255), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
    
    # ---------- APPLY SCENARIO BUTTON THEME ----------
    with dpg.theme(tag="apply_scenario_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (180, 130, 50), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (220, 160, 70), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (255, 180, 80), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
    
    # ---------- RESET BUTTON THEME ----------
    with dpg.theme(tag="reset_scenario_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (100, 100, 100), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (130, 130, 130), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (160, 160, 160), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
    
    # ---------- REFRESH CHART THEME ----------
    with dpg.theme(tag="refresh_chart_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (60, 120, 160), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (80, 150, 200), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (100, 180, 240), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)
    
    # ---------- SUMMARY CHART THEME ----------
    with dpg.theme(tag="summary_chart_theme"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (120, 100, 160), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (150, 130, 200), category=dpg.mvThemeCat_Core)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (180, 160, 240), category=dpg.mvThemeCat_Core)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5, category=dpg.mvThemeCat_Core)