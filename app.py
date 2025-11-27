import dearpygui.dearpygui as dpg
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime, timedelta
import sys

# Add utils to path
sys.path.append('utils')
from preprocessing import validate_data, clean_data, prepare_forecast_data, export_forecast, normalize_column_names

try:
    from autots import AutoTS
    AUTOTS_AVAILABLE = True
except ImportError:
    print("AutoTS not available - forecasting disabled")
    AUTOTS_AVAILABLE = False

class InventoryForecastingApp:
    def __init__(self):
        self.df = None
        self.forecast_results = None
        self.current_sku = None
        self.sku_list = []
        
        # Initialize DPG
        dpg.create_context()
        self.setup_theme()
        self.create_windows()
        
    def setup_theme(self):
        """Setup application theme"""
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (42, 130, 218))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (52, 140, 228))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (32, 120, 208))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (40, 40, 40))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))
                
        dpg.bind_theme(global_theme)
    
    def create_windows(self):
        """Create main application windows"""
        
        # Main window
        with dpg.window(tag="Primary Window", label="SyamsulAI - Inventory Forecasting"):
            
            # Header
            with dpg.group(horizontal=True):
                dpg.add_text("SyamsulAI Inventory Forecasting", color=(42, 130, 218))
                dpg.add_spacer()
                dpg.add_text("v1.0", color=(150, 150, 150))
            
            dpg.add_separator()
            
            # File upload section
            with dpg.group(horizontal=True):
                dpg.add_button(label="📁 Upload CSV", callback=self.upload_csv, width=120)
                dpg.add_text("No file loaded", tag="file_status")
            
            dpg.add_separator()
            
            # Data preview
            with dpg.collapsing_header(label="📊 Data Preview", default_open=True):
                dpg.add_text("Upload a CSV file to preview data", tag="preview_text")
                with dpg.child_window(height=150, tag="data_table"):
                    pass
            
            dpg.add_separator()
            
            # Forecasting controls
            with dpg.group(horizontal=True):
                dpg.add_text("Forecast Settings:")
                dpg.add_combo(label="Select SKU", tag="sku_selector", callback=self.on_sku_select, width=150)
                dpg.add_input_int(label="Forecast Days", default_value=30, tag="forecast_days", width=100)
                dpg.add_button(label="🚀 Generate Forecast", callback=self.generate_forecast, width=150)
            
            # Scenario simulation
            with dpg.collapsing_header(label="🔮 Scenario Simulation"):
                dpg.add_text("Simulate business scenarios to understand potential impacts:")
                
                with dpg.group(horizontal=True):
                    dpg.add_input_float(label="Demand Spike %", default_value=20.0, tag="spike_percent", width=100)
                    dpg.add_input_int(label="Spike Duration (days)", default_value=7, tag="spike_duration", width=120)
                    dpg.add_button(label="Simulate Demand Spike", callback=self.simulate_demand_spike, width=150)
                
                with dpg.group(horizontal=True):
                    dpg.add_input_int(label="Supply Delay (days)", default_value=14, tag="delay_days", width=100)
                    dpg.add_button(label="Simulate Supply Delay", callback=self.simulate_supply_delay, width=150)
                
                with dpg.group(horizontal=True):
                    dpg.add_input_float(label="Stockout Risk %", default_value=10.0, tag="stockout_risk", width=100)
                    dpg.add_button(label="Analyze Stockout Risk", callback=self.analyze_stockout_risk, width=150)
            
            # Results section
            with dpg.collapsing_header(label="📈 Forecast Results", tag="results_section", show=False):
                dpg.add_text("Forecast results will appear here", tag="results_text")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="💾 Export Forecast CSV", callback=self.export_forecast, tag="export_btn", show=False)
                    dpg.add_button(label="🖼️ Save Chart", callback=self.save_chart, tag="save_chart_btn", show=False)
                    dpg.add_button(label="📋 Copy Summary", callback=self.copy_summary, tag="copy_btn", show=False)
            
            # Plot area
            dpg.add_separator()
            with dpg.child_window(tag="plot_window", height=400, show=False):
                dpg.add_text("Chart will appear here after forecast generation", tag="chart_placeholder")
        
        # Viewport setup
        dpg.create_viewport(title='SyamsulAI - Inventory Forecasting', width=1400, height=900)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("Primary Window", True)
    
    def upload_csv(self, sender, app_data):
        """Handle CSV file upload"""
        try:
            with dpg.file_dialog(directory_selector=False, show=False, callback=self.file_dialog_callback, 
                                tag="file_dialog_id", width=700, height=400):
                dpg.add_file_extension("CSV Files (*.csv){.csv}")
        except:
            pass
        
        dpg.show_item("file_dialog_id")
    
    def file_dialog_callback(self, sender, app_data):
        """Process selected CSV file"""
        if app_data["selections"]:
            filepath = list(app_data["selections"].values())[0]
            try:
                # Read CSV file
                self.df = pd.read_csv(filepath)
                
                # Store original column names for display
                original_columns = self.df.columns.tolist()
                
                # Normalize column names for processing
                self.df = normalize_column_names(self.df)
                normalized_columns = self.df.columns.tolist()
                
                # Validate data
                is_valid, errors = validate_data(self.df)
                if not is_valid:
                    dpg.set_value("file_status", f"❌ Validation failed: {errors[0]}")
                    return
                
                # Clean data
                self.df = clean_data(self.df)
                
                # Update UI with column mapping info
                column_mapping = dict(zip(original_columns, normalized_columns))
                column_info = " | ".join([f"{k} → {v}" for k, v in column_mapping.items()])
                
                dpg.set_value("file_status", f"✅ Loaded: {os.path.basename(filepath)}")
                dpg.set_value("preview_text", 
                             f"📁 Data loaded successfully!\n"
                             f"• Rows: {len(self.df):,}\n"
                             f"• SKUs: {self.df['sku'].nunique()}\n"
                             f"• Date range: {self.df['date'].min().strftime('%Y-%m-%d')} to {self.df['date'].max().strftime('%Y-%m-%d')}\n"
                             f"• Column mapping: {column_info}")
                
                # Display sample data
                self.display_data_preview(self.df.head(10))
                
                # Populate SKU selector
                self.sku_list = self.df['sku'].unique().tolist()
                dpg.configure_item("sku_selector", items=self.sku_list)
                if self.sku_list:
                    dpg.set_value("sku_selector", self.sku_list[0])
                    self.current_sku = self.sku_list[0]
                
                # Hide previous results
                dpg.configure_item("results_section", show=False)
                dpg.configure_item("plot_window", show=False)
                
            except Exception as e:
                dpg.set_value("file_status", f"❌ Error loading file: {str(e)}")
    
    def display_data_preview(self, data_sample):
        """Display a preview of the loaded data"""
        # Clear previous table
        dpg.delete_item("data_table", children_only=True)
        
        # Create a simple text-based table preview
        with dpg.table(parent="data_table", header_row=True, resizable=True, 
                      policy=dpg.mvTable_SizingStretchProp, row_background=True,
                      borders_innerH=True, borders_outerH=True, borders_innerV=True,
                      borders_outerV=True):
            
            # Add columns
            for column in data_sample.columns:
                dpg.add_table_column(label=column.capitalize())
            
            # Add rows
            for _, row in data_sample.iterrows():
                with dpg.table_row():
                    for value in row:
                        if pd.isna(value):
                            dpg.add_text("")
                        elif isinstance(value, pd.Timestamp):
                            dpg.add_text(value.strftime('%Y-%m-%d'))
                        else:
                            dpg.add_text(str(value))
    
    def on_sku_select(self, sender, app_data):
        """Handle SKU selection change"""
        self.current_sku = app_data
        if self.current_sku and self.df is not None:
            # Update preview with SKU-specific info
            sku_data = self.df[self.df['sku'] == self.current_sku]
            if len(sku_data) > 0:
                dpg.set_value("preview_text", 
                             f"📊 Selected: {self.current_sku}\n"
                             f"• Data points: {len(sku_data)}\n"
                             f"• Date range: {sku_data['date'].min().strftime('%Y-%m-%d')} to {sku_data['date'].max().strftime('%Y-%m-%d')}\n"
                             f"• Total quantity: {sku_data['quantity'].sum():,}\n"
                             f"• Average daily: {sku_data['quantity'].mean():.1f}")
    
    def generate_forecast(self, sender, app_data):
        """Generate forecast using AutoTS"""
        if self.df is None or self.current_sku is None:
            dpg.set_value("results_text", "❌ Please load data and select an SKU first")
            return
        
        if not AUTOTS_AVAILABLE:
            dpg.set_value("results_text", "❌ AutoTS not available. Please install: pip install autots")
            return
        
        try:
            # Show loading state
            dpg.set_value("results_text", "🔄 Generating forecast... This may take a moment.")
            dpg.configure_item("results_section", show=True)
            
            # Prepare data for forecasting
            forecast_days = dpg.get_value("forecast_days")
            sku_data = self.df[self.df['sku'] == self.current_sku]
            
            # Create time series
            ts_data = sku_data.groupby('date')['quantity'].sum().sort_index()
            
            # Ensure we have a proper time series
            if len(ts_data) < 10:
                dpg.set_value("results_text", f"❌ Not enough data for {self.current_sku}. Need at least 10 data points, got {len(ts_data)}.")
                return
            
            # Generate forecast using AutoTS
            model = AutoTS(
                forecast_length=forecast_days,
                frequency='D',
                ensemble='simple',
                max_generations=5,
                num_validations=2,
                verbose=0
            )
            
            # Prepare data for AutoTS
            ts_df = ts_data.reset_index()
            ts_df.columns = ['date', 'quantity']
            
            model = model.fit(ts_df, date_col='date', value_col='quantity')
            forecast = model.predict()
            
            # Get best forecast
            self.forecast_results = forecast.forecast
            
            # Display results
            self.display_forecast_results(ts_data, self.forecast_results)
            
        except Exception as e:
            dpg.set_value("results_text", f"❌ Forecast error: {str(e)}")
    
    def display_forecast_results(self, historical, forecast):
        """Display forecast results and create visualization"""
        try:
            # Create matplotlib figure
            plt.figure(figsize=(12, 8))
            
            # Plot historical data
            plt.subplot(2, 1, 1)
            plt.plot(historical.index, historical.values, label='Historical', marker='o', color='blue', linewidth=2)
            
            # Plot forecast
            forecast_dates = pd.date_range(
                start=historical.index[-1] + timedelta(days=1), 
                periods=len(forecast),
                freq='D'
            )
            plt.plot(forecast_dates, forecast.values, label='Forecast', marker='s', 
                    linestyle='--', color='red', linewidth=2)
            
            plt.title(f'📈 Inventory Forecast - {self.current_sku}', fontsize=14, fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Quantity')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            
            # Plot combined view
            plt.subplot(2, 1, 2)
            all_dates = list(historical.index) + list(forecast_dates)
            all_values = list(historical.values) + list(forecast.values)
            
            plt.plot(all_dates, all_values, label='Historical + Forecast', color='green', linewidth=2)
            plt.axvline(x=historical.index[-1], color='red', linestyle=':', alpha=0.7, label='Forecast Start')
            
            plt.title('Combined View', fontweight='bold')
            plt.xlabel('Date')
            plt.ylabel('Quantity')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Save plot
            os.makedirs('output', exist_ok=True)
            plot_path = 'output/forecast_plot.png'
            plt.savefig(plot_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            # Calculate statistics
            historical_avg = historical.mean()
            forecast_avg = forecast.mean()
            forecast_total = forecast.sum()
            confidence_interval = forecast.std()
            
            # Update UI with results
            dpg.set_value("results_text", 
                         f"✅ Forecast completed for: {self.current_sku}\n\n"
                         f"📊 Statistics:\n"
                         f"• Historical data points: {len(historical):,}\n"
                         f"• Forecast period: {len(forecast)} days\n"
                         f"• Historical average: {historical_avg:.2f} units/day\n"
                         f"• Forecast average: {forecast_avg:.2f} units/day\n"
                         f"• Total forecasted demand: {forecast_total:,.0f} units\n"
                         f"• Forecast variability: ±{confidence_interval:.2f} units\n\n"
                         f"💡 Recommendation: Maintain stock above {forecast_avg + confidence_interval:.0f} units")
            
            dpg.configure_item("results_section", show=True)
            dpg.configure_item("export_btn", show=True)
            dpg.configure_item("save_chart_btn", show=True)
            dpg.configure_item("copy_btn", show=True)
            dpg.configure_item("plot_window", show=True)
            
            # Update chart placeholder
            dpg.set_value("chart_placeholder", f"📊 Chart generated and saved to:\n{plot_path}\n\nOpen the file to view the forecast visualization.")
            
        except Exception as e:
            dpg.set_value("results_text", f"❌ Error displaying results: {str(e)}")
    
    def simulate_demand_spike(self, sender, app_data):
        """Simulate demand spike scenario"""
        if self.forecast_results is None:
            dpg.set_value("results_text", "❌ Generate a forecast first before simulating scenarios")
            return
        
        spike_percent = dpg.get_value("spike_percent") / 100
        spike_duration = dpg.get_value("spike_duration")
        
        # Apply spike to forecast
        adjusted_forecast = self.forecast_results.copy()
        adjustment_factor = 1 + spike_percent
        
        # Apply spike to first N days
        days_to_adjust = min(spike_duration, len(adjusted_forecast))
        adjusted_forecast.iloc[:days_to_adjust] = adjusted_forecast.iloc[:days_to_adjust] * adjustment_factor
        
        # Display scenario results
        original_avg = self.forecast_results.mean()
        adjusted_avg = adjusted_forecast.mean()
        additional_demand = adjusted_forecast.sum() - self.forecast_results.sum()
        
        dpg.set_value("results_text", 
                     f"🔮 Demand Spike Simulation Results:\n\n"
                     f"⚡ Scenario: {spike_percent*100:.1f}% demand spike for {spike_duration} days\n\n"
                     f"📈 Impact Analysis:\n"
                     f"• Original daily average: {original_avg:.2f} units\n"
                     f"• Adjusted daily average: {adjusted_avg:.2f} units\n"
                     f"• Additional total demand: {additional_demand:,.0f} units\n"
                     f"• Peak demand increase: {spike_percent*100:.1f}%\n\n"
                     f"🚨 Action Required: Increase safety stock by {additional_demand:.0f} units")
    
    def simulate_supply_delay(self, sender, app_data):
        """Simulate supply chain delay scenario"""
        if self.forecast_results is None:
            dpg.set_value("results_text", "❌ Generate a forecast first before simulating scenarios")
            return
        
        delay_days = dpg.get_value("delay_days")
        
        # Create delayed forecast (shift right and pad with zeros)
        delayed_forecast = self.forecast_results.copy()
        if delay_days >= len(delayed_forecast):
            delayed_forecast = pd.Series([0] * len(delayed_forecast))
        else:
            delayed_forecast = pd.concat([
                pd.Series([0] * delay_days),
                delayed_forecast.iloc[:-delay_days]
            ]).reset_index(drop=True)
        
        # Display scenario results
        original_total = self.forecast_results.sum()
        delayed_total = delayed_forecast.sum()
        lost_sales = original_total - delayed_total
        
        dpg.set_value("results_text", 
                     f"🔮 Supply Delay Simulation Results:\n\n"
                     f"⏰ Scenario: {delay_days}-day supply chain delay\n\n"
                     f"📉 Impact Analysis:\n"
                     f"• Original forecasted sales: {original_total:,.0f} units\n"
                     f"• Delayed sales potential: {delayed_total:,.0f} units\n"
                     f"• Potential lost sales: {lost_sales:,.0f} units\n"
                     f"• Revenue impact: {lost_sales/original_total*100:.1f}% reduction\n\n"
                     f"🚨 Action Required: Secure {lost_sales:.0f} units from alternative suppliers")
    
    def analyze_stockout_risk(self, sender, app_data):
        """Analyze stockout risk based on forecast"""
        if self.forecast_results is None:
            dpg.set_value("results_text", "❌ Generate a forecast first before analyzing risks")
            return
        
        risk_percent = dpg.get_value("stockout_risk") / 100
        
        # Calculate risk metrics
        max_demand = self.forecast_results.max()
        avg_demand = self.forecast_results.mean()
        std_demand = self.forecast_results.std()
        
        # Calculate safety stock requirement
        z_score = 1.28  # ~90th percentile
        safety_stock = z_score * std_demand
        
        # Calculate reorder point
        reorder_point = avg_demand + safety_stock
        
        dpg.set_value("results_text", 
                     f"🔮 Stockout Risk Analysis:\n\n"
                     f"⚠️  Risk Level: {risk_percent*100:.1f}% tolerance\n\n"
                     f"📊 Demand Profile:\n"
                     f"• Average daily demand: {avg_demand:.2f} units\n"
                     f"• Peak daily demand: {max_demand:.2f} units\n"
                     f"• Demand variability: ±{std_demand:.2f} units\n\n"
                     f"🛡️  Protection Strategy:\n"
                     f"• Safety stock required: {safety_stock:.0f} units\n"
                     f"• Recommended reorder point: {reorder_point:.0f} units\n"
                     f"• Buffer for peak demand: {max_demand - avg_demand:.0f} units")
    
    def export_forecast(self, sender, app_data):
        """Export forecast to CSV"""
        if self.forecast_results is not None:
            try:
                # Create forecast dataframe
                forecast_dates = pd.date_range(
                    start=datetime.now() + timedelta(days=1),
                    periods=len(self.forecast_results),
                    freq='D'
                )
                
                forecast_df = pd.DataFrame({
                    'date': forecast_dates,
                    'sku': self.current_sku,
                    'forecast_quantity': self.forecast_results.values,
                    'confidence_interval': self.forecast_results.std()
                })
                
                filepath = export_forecast(forecast_df)
                dpg.set_value("results_text", f"✅ Forecast exported to:\n{filepath}\n\n"
                                            f"File contains {len(forecast_df)} days of forecast data.")
                
            except Exception as e:
                dpg.set_value("results_text", f"❌ Export error: {str(e)}")
    
    def save_chart(self, sender, app_data):
        """Save the current chart"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chart_path = f"output/forecast_chart_{self.current_sku}_{timestamp}.png"
            
            # Regenerate and save chart
            if self.df is not None and self.current_sku is not None and self.forecast_results is not None:
                sku_data = self.df[self.df['sku'] == self.current_sku]
                ts_data = sku_data.groupby('date')['quantity'].sum().sort_index()
                
                # Regenerate chart
                plt.figure(figsize=(10, 6))
                plt.plot(ts_data.index, ts_data.values, label='Historical', marker='o')
                
                forecast_dates = pd.date_range(
                    start=ts_data.index[-1] + timedelta(days=1), 
                    periods=len(self.forecast_results),
                    freq='D'
                )
                plt.plot(forecast_dates, self.forecast_results.values, label='Forecast', marker='s', linestyle='--')
                
                plt.title(f'Inventory Forecast - {self.current_sku}')
                plt.xlabel('Date')
                plt.ylabel('Quantity')
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                plt.savefig(chart_path, dpi=150, bbox_inches='tight')
                plt.close()
                
                dpg.set_value("results_text", f"✅ Chart saved to:\n{chart_path}")
            
        except Exception as e:
            dpg.set_value("results_text", f"❌ Error saving chart: {str(e)}")
    
    def copy_summary(self, sender, app_data):
        """Copy forecast summary to clipboard"""
        try:
            if self.forecast_results is not None:
                summary = (
                    f"SyamsulAI Forecast Summary - {self.current_sku}\n"
                    f"Forecast Period: {len(self.forecast_results)} days\n"
                    f"Average Daily Forecast: {self.forecast_results.mean():.2f} units\n"
                    f"Total Forecasted Demand: {self.forecast_results.sum():.0f} units\n"
                    f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
                # Note: Dear PyGui doesn't have direct clipboard access
                # In a real implementation, you'd use pyperclip or similar
                dpg.set_value("results_text", f"📋 Summary ready for copying:\n\n{summary}")
                
        except Exception as e:
            dpg.set_value("results_text", f"❌ Error preparing summary: {str(e)}")
    
    def run(self):
        """Run the application"""
        dpg.start_dearpygui()
        dpg.destroy_context()

if __name__ == "__main__":
    app = InventoryForecastingApp()
    app.run()