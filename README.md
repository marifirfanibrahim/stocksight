# StockSight

It is a desktop application for inventory **demand forecasting**.  
It aims to helps you go from raw transactional data to forecasts and exports **fast**, even for **10,000+ SKUs**.

---

## 1. What StockSight Does

StockSight guides you through a **4-step workflow**:

1. **Data Health** – Load your data, map columns, and fix obvious data issues.
2. **Pattern Discovery** – See how items behave (steady, seasonal, erratic) and view anomalies.
3. **Feature Engineering** – Create “smart features” that help models understand your data.
4. **Forecast Factory** – Run forecasting strategies and export results.

The objectives of this application is to be/use:

- **Offline** – Runs on your machine (PyQt desktop app, no web server required).
- **Scale-aware** – Designed for 10K+ SKUs without trying to load everything into memory at once.
- **Plain English** – Uses business language (“patterns”, “influence factors”) instead of ML jargon.

---

## 2. Main Features

### Data Health Tab

- Drag & drop file upload (CSV, Excel, Parquet).
- Automatic column detection (date, item/SKU, quantity, category, price, promotion).
- Data quality report (missing values, duplicates, negatives, coverage).
- One-click fixes for:
  - Missing values (fill, zero, average, or remove rows).
  - Duplicate item+date rows (sum, average, or take first).
  - Negative quantities (zero or absolute value).
  - Outliers (remove or cap).
- Basic **ABC classification** (A/B/C items by volume).

### Pattern Discovery Tab

- Item navigator with views by:
  - Category
  - Volume tier (A/B/C)
  - Pattern type (seasonal / erratic / steady / variable)
  - Cluster (“High Volume – Seasonal” etc.)
- Rule-based clustering:
  - Volume tiers (A/B/C)
  - Pattern types using variability (CV) and Q4 concentration.
- Heatmap of clusters and patterns.
- Sparklines for quick visual comparison.
- Time series chart with optional anomalies overlay.
- Anomaly detection:
  - IQR, z-score, and rolling window methods.
  - Review dialog to **keep**, **flag**, **auto-correct**, or **remove** anomaly points.

> Note: After you remove or correct large anomalies, the data distribution changes.  
> A second detection pass may find a smaller “second layer” of unusual points.  
> This is expected and explained in the **Learn** help dialog.

### Feature Engineering Tab
 
- Curated library of 20 “smart features” (lags, rolling stats, date features, promo/price, trend, seasonality).
- Tier-based presets:
  - A-items: richer feature set.
  - B-items: medium.
  - C-items: basic.
- Optional advanced extraction (more features, more processing time).
- Simple feature importance view to explain which features matter.

### Forecast Factory Tab

- Three strategies, described in business terms:
  - **Simple & Fast** – quick baseline for all items.
  - **Smart & Balanced** – recommended default for most use cases.
  - **Advanced AI** – runs on A-items only.
- Supports daily, weekly, or monthly forecasting horizons.
- Tier-aware processing (A, B, C items).
- Model comparison (optional) to see which models work best on a sample.
- Results table with summary and item-level metrics (MAPE, MAE, RMSE).
- Forecast preview chart (history + forecast + confidence range).
- Export options:
  - CSV for systems/Excel
  - Excel workbook (forecasts, summary, model performance)
  - PowerPoint executive summary
  - PDF executive summary (maybe?)

---

## 3. Typical Workflow

1. **Open the app**  
   - You will see a Welcome dialog with the 4 main steps.

2. **Data Health tab**
   - Drag and drop your file or use “File → Open Data…”.
   - Confirm or adjust column mapping.
   - Review the quality score and issues.
   - Use the Abnormal Data dialog if needed to fix missing/duplicate/negative/outlier rows.
   - Check the A/B/C item split.

3. **Pattern Discovery tab**
   - Click “Run Clustering” to group items by volume and pattern.
   - Use the navigator, heatmap, and sparklines to explore.
   - Click “Detect Anomalies” to find unusual points.
   - Open “Review Anomalies” to:
     - Keep values (ignore),
     - Flag items for correction (sent back to Tab 1),
     - Auto-correct some anomalies,
     - Remove invalid points.
   - Optionally re-run detection once to see the cleaned picture.

4. **Feature Engineering tab**
   - Choose a feature set (Tier-based is recommended).
   - Optionally enable advanced extraction if you accept longer processing time.
   - Click “Create Features” and review feature importance.

5. **Forecast Factory tab**
   - Click “Configure” to pick a strategy, frequency, and horizon.
   - Click “Generate Forecasts”.
   - Review:
     - Total forecast,
     - Average MAPE,
     - Item statuses (Good / Fair / Review).
   - Export:
     - CSV for integrations,
     - Excel for deeper analysis,
     - PowerPoint for management.

---

## 4. Installation

### 4.1. From Source (Python Environment)

1. **Clone or copy the repository** so you have the `stocksight` folder.

2. **Install dependencies:**
```Bash
pip install -r requirements.txt
```

3. **Run the application:**
```Bash
python main.py
```

---

## 5. Data Requirements
Your input data should be transactional or aggregated time series, with at least:

* A date column (daily, weekly, or monthly).
* An item/SKU identifier.
* A quantity or demand/sales measure.

Optional columns that improve results:
* Category / Group
* Price
* Promotion / Campaign flag

Supported file formats:
* CSV
* Excel (.xlsx, .xls, multiple sheets supported)
* Parquet

Max default file size: **500 MB** (configurable in config.py).

---

## 6. Configuration
Most behavior is controlled through config.py, including:
* Column detection keywords and thresholds.
* Clustering thresholds for A/B/C and pattern types.
* Feature sets and group rules (A/B/C usage).
* Forecast strategy definitions and timing estimates.
* Performance settings (chunk size, max SKUs in memory).
* Export formats and template colors.

You can adjust these values without touching UI code.

---

## 7. Notes and Tips
For large datasets (10K+ SKUs × 2+ years daily), let the app complete each step rather than opening many windows at once.

Use the Learn help item in the Help menu to understand how:
* Data Health fixes in Tab 1,
* Abnormal Data review in Tab 1,
* Anomaly detection in Tab 2 work together.
  
It is usually enough to:
* Clean obvious issues once,
* Run anomaly detection once or twice,
* Then move on to forecasting.
  
If you are unsure about a setting, the defaults are chosen to be safe and reasonable for most business use cases.

