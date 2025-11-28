"""
scenarios tab interface
scenario simulation controls
"""


# ================ IMPORTS ================

import dearpygui.dearpygui as dpg

from config import GUIConfig, ScenarioConfig


# ================ SCENARIOS TAB ================

def create_scenarios_tab():
    """
    create scenarios tab content
    """
    with dpg.tab(label="Scenarios"):
        dpg.add_spacer(height=5)
        
        dpg.add_text("SCENARIO SIMULATION", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        dpg.add_text("Simulate demand changes or supply delays.", 
                    wrap=350, color=(180, 180, 180))
        dpg.add_text("Apply modifications before running forecast.", 
                    wrap=350, color=(180, 180, 180))
        
        dpg.add_spacer(height=15)
        
        # ---------- SCENARIO TYPE ----------
        dpg.add_text("TYPE", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        dpg.add_text("Scenario Type:", color=(200, 200, 200))
        dpg.add_combo(["Demand Spike", "Supply Delay"], 
                     default_value="Demand Spike", tag="scenario_type", width=-1)
        dpg.add_text("Choose scenario type to apply", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=10)
        
        # ---------- SKU SELECTION ----------
        dpg.add_text("Target SKU:", color=(200, 200, 200))
        dpg.add_combo([], tag="scenario_sku", width=-1)
        dpg.add_text("Select which SKU to modify", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=15)
        
        # ---------- DATE RANGE ----------
        dpg.add_text("DATE RANGE", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        dpg.add_text("Start Date:", color=(200, 200, 200))
        dpg.add_input_text(default_value="2024-01-15", 
                           tag="scenario_start", width=-1)
        dpg.add_text("When scenario begins (YYYY-MM-DD)", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=5)
        
        dpg.add_text("End Date:", color=(200, 200, 200))
        dpg.add_input_text(default_value="2024-01-25",
                           tag="scenario_end", width=-1)
        dpg.add_text("When scenario ends (for demand spike only)", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=15)
        
        # ---------- DEMAND SPIKE ----------
        dpg.add_text("DEMAND SPIKE SETTINGS", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        dpg.add_text("Multiplier:", color=(200, 200, 200))
        dpg.add_input_float(default_value=ScenarioConfig.DEFAULT_SPIKE_MULTIPLIER,
                            min_value=ScenarioConfig.MIN_SPIKE_MULTIPLIER, 
                            max_value=ScenarioConfig.MAX_SPIKE_MULTIPLIER, 
                            tag="spike_multiplier", width=-1)
        dpg.add_text("Multiply quantity by this factor (1.5 = 50% increase)", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=5)
        dpg.add_button(label="Reset Multiplier", 
                      callback=lambda: dpg.set_value("spike_multiplier", ScenarioConfig.DEFAULT_SPIKE_MULTIPLIER),
                      width=-1)
        
        dpg.add_spacer(height=15)
        
        # ---------- SUPPLY DELAY ----------
        dpg.add_text("SUPPLY DELAY SETTINGS", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        dpg.add_text("Delay Days:", color=(200, 200, 200))
        dpg.add_input_int(default_value=ScenarioConfig.DEFAULT_DELAY_DAYS,
                          min_value=ScenarioConfig.MIN_DELAY_DAYS, 
                          max_value=ScenarioConfig.MAX_DELAY_DAYS, 
                          tag="delay_days", width=-1)
        dpg.add_text("Number of days to shift dates forward", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=5)
        dpg.add_button(label="Reset Delay", 
                      callback=lambda: dpg.set_value("delay_days", ScenarioConfig.DEFAULT_DELAY_DAYS),
                      width=-1)
        
        dpg.add_spacer(height=15)
        
        # ---------- ACTION BUTTONS ----------
        dpg.add_text("ACTIONS", color=GUIConfig.HEADER_COLOR)
        dpg.add_separator()
        
        from ui.callbacks import apply_scenario_callback, reset_all_scenarios_callback, reset_data_callback
        
        apply_btn = dpg.add_button(label="Apply Scenario", callback=apply_scenario_callback, width=-1, height=35)
        dpg.bind_item_theme(apply_btn, "apply_scenario_theme")
        dpg.add_text("Apply selected scenario to data", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=5)
        
        reset_all_btn = dpg.add_button(label="Reset All Scenarios", callback=reset_all_scenarios_callback, width=-1)
        dpg.bind_item_theme(reset_all_btn, "reset_scenario_theme")
        dpg.add_text("Reset all scenario settings to defaults", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=5)
        
        dpg.add_button(label="Reset Data to Original", callback=reset_data_callback, width=-1)
        dpg.add_text("Undo all applied scenarios", 
                    wrap=350, color=(150, 150, 150))
        
        dpg.add_spacer(height=15)
        
        # ---------- SCENARIO HISTORY ----------
        with dpg.collapsing_header(label="Applied Scenarios", default_open=False):
            dpg.add_text("No scenarios applied yet", tag="scenario_history_text", 
                        wrap=340, color=(150, 150, 150))