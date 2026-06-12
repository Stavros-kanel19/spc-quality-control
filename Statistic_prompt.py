import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy import stats as scipy_stats


D2_MOVING_RANGE_2 = 1.128
D4_MOVING_RANGE_2 = 3.267


def fmt(value, decimals=2):
    if value is None or pd.isna(value):
        return "-"
    if isinstance(value, str):
        return value
    return f"{float(value):.{decimals}f}"


class QualityControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Quality Control Application")
        self.root.geometry("1420x920")
        self.root.minsize(1180, 780)

        self.df = None
        self.customer_col = "Customer"
        self.default_search_columns = ["Code", "Order_ID", "Order_Type"]
        self.sort_states = {}

        self.i_canvas = None
        self.mr_ewma_canvas = None
        self.dist_canvas = None
        self.recent_canvas = None
        self.normal_canvas = None

        self.last_model = None
        self.last_measure_col = None
        self.last_search_col = None
        self.last_code = None
        self.last_new_value = None
        self.last_stats = None
        self.last_removed_count = 0
        self.last_filter_text = "Inactive"
        self.last_ewma_lambda = 0.20
        self.auto_lsl = None
        self.auto_usl = None

        self.use_recent_distribution = tk.BooleanVar(value=False)
        self.use_recent_normal = tk.BooleanVar(value=False)
        self.use_recent_data = tk.BooleanVar(value=False)
        self.use_recent_customer = tk.BooleanVar(value=False)

        self.create_widgets()

    def create_widgets(self):
        file_frame = tk.Frame(self.root, pady=10)
        file_frame.pack(fill=tk.X, padx=16)

        self.btn_load = tk.Button(
            file_frame,
            text="Import Excel",
            command=self.load_excel,
            font=("Arial", 11, "bold"),
            bg="#642e7d",
            fg="white",
            padx=14,
            pady=4,
        )
        self.btn_load.pack(side=tk.LEFT)

        self.lbl_file = tk.Label(file_frame, text="No File Selected", fg="gray", font=("Arial", 10))
        self.lbl_file.pack(side=tk.LEFT, padx=10)

        controls = tk.LabelFrame(self.root, text="Control Parameters", padx=10, pady=10, font=("Arial", 11, "bold"))
        controls.pack(fill=tk.X, padx=16, pady=(0, 6))

        tk.Label(controls, text="Search by:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.cmb_search_col = ttk.Combobox(controls, values=self.default_search_columns, state="readonly", width=16)
        self.cmb_search_col.set("Code")
        self.cmb_search_col.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(controls, text="Code:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.entry_code = tk.Entry(controls, width=12)
        self.entry_code.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(controls, text="Selected Column:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.cmb_measure_col = ttk.Combobox(controls, values=["Measurement"], state="readonly", width=16)
        self.cmb_measure_col.set("Measurement")
        self.cmb_measure_col.grid(row=0, column=5, padx=5, pady=5)

        tk.Label(controls, text="Current Value:").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
        self.entry_new_value = tk.Entry(controls, width=12)
        self.entry_new_value.grid(row=0, column=7, padx=5, pady=5)

        tk.Label(controls, text="EWMA lambda:").grid(row=0, column=8, padx=5, pady=5, sticky=tk.W)
        self.entry_ewma_lambda = tk.Entry(controls, width=7)
        self.entry_ewma_lambda.insert(0, "0.20")
        self.entry_ewma_lambda.grid(row=0, column=9, padx=5, pady=5)

        tk.Label(controls, text="Last N:").grid(row=0, column=10, padx=5, pady=5, sticky=tk.W)
        self.entry_recent_n = tk.Entry(controls, width=7)
        self.entry_recent_n.insert(0, "5")
        self.entry_recent_n.grid(row=0, column=11, padx=5, pady=5)

        self.btn_analyze = tk.Button(
            controls,
            text="Analyse",
            command=self.analyze_data,
            font=("Arial", 10, "bold"),
            bg="#1565c0",
            fg="white",
            padx=16,
        )
        self.btn_analyze.grid(row=0, column=12, padx=10, pady=5)

        filters = tk.LabelFrame(self.root, text="Outliers exclusion", padx=10, pady=8, font=("Arial", 10, "bold"))
        filters.pack(fill=tk.X, padx=16, pady=(0, 8))

        tk.Label(filters, text="Remove").grid(row=0, column=0, padx=5, sticky=tk.W)
        self.entry_remove_high = tk.Entry(filters, width=7)
        self.entry_remove_high.insert(0, "0")
        self.entry_remove_high.grid(row=0, column=1, padx=5)
        tk.Label(filters, text="higher values and remove").grid(row=0, column=2, padx=5, sticky=tk.W)
        self.entry_remove_low = tk.Entry(filters, width=7)
        self.entry_remove_low.insert(0, "0")
        self.entry_remove_low.grid(row=0, column=3, padx=5)
        tk.Label(
            filters,
            text="lower values. Enter 0 for not exlusion",
            fg="#555",
        ).grid(row=0, column=4, padx=8, sticky=tk.W)

        self.lbl_status = tk.Label(self.root, text="", font=("Arial", 14, "bold"), pady=7)
        self.lbl_status.pack(fill=tk.X, padx=16)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=8)

        self.tab_i_chart = ttk.Frame(self.notebook)
        self.tab_mr_ewma = ttk.Frame(self.notebook)
        self.tab_distributions = ttk.Frame(self.notebook)
        self.tab_normal = ttk.Frame(self.notebook)
        self.tab_recent = ttk.Frame(self.notebook)
        self.tab_data = ttk.Frame(self.notebook)
        self.tab_customer = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_i_chart, text="I graph")
        self.notebook.add(self.tab_mr_ewma, text="MR & EWMA")
        self.notebook.add(self.tab_distributions, text="Material_Type & Boxplot")
        self.notebook.add(self.tab_normal, text="Normal Distribution")
        self.notebook.add(self.tab_recent, text="Last N")
        self.notebook.add(self.tab_data, text="Statistics")
        self.notebook.add(self.tab_customer, text="Statistics per Customer")

        self.build_distribution_tab()
        self.build_normal_tab()
        self.build_data_tab()
        self.build_customer_tab()

    def build_distribution_tab(self):
        top = tk.Frame(self.tab_distributions)
        top.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(top, text="Boxplot by:").pack(side=tk.LEFT)
        self.cmb_boxplot_group = ttk.Combobox(top, values=["Material_Type", "Type", "Order_Type"], state="readonly", width=18)
        self.cmb_boxplot_group.set("Material_Type")
        self.cmb_boxplot_group.pack(side=tk.LEFT, padx=8)
        self.cmb_boxplot_group.bind("<<ComboboxSelected>>", lambda _event: self.redraw_distribution_charts())

        tk.Checkbutton(
            top,
            text="Use last N",
            variable=self.use_recent_distribution,
            command=self.redraw_distribution_charts,
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(top, text="Refresh", command=self.redraw_distribution_charts).pack(side=tk.LEFT, padx=5)

        self.distribution_plot_frame = tk.Frame(self.tab_distributions)
        self.distribution_plot_frame.pack(fill=tk.BOTH, expand=True)

    def build_normal_tab(self):
        top = tk.Frame(self.tab_normal)
        top.pack(fill=tk.X, padx=10, pady=8)

        tk.Label(top, text="LSL (-15%):").pack(side=tk.LEFT)
        self.entry_lsl = tk.Entry(top, width=12)
        self.entry_lsl.pack(side=tk.LEFT, padx=5)

        tk.Label(top, text="USL (+15%):").pack(side=tk.LEFT, padx=(10, 0))
        self.entry_usl = tk.Entry(top, width=12)
        self.entry_usl.pack(side=tk.LEFT, padx=5)

        tk.Checkbutton(
            top,
            text="Use last N",
            variable=self.use_recent_normal,
            command=self.redraw_normal_chart,
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(top, text="Refresh", command=self.redraw_normal_chart).pack(side=tk.LEFT, padx=8)

        body = tk.Frame(self.tab_normal)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self.normal_plot_frame = tk.Frame(body)
        self.normal_plot_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        normal_side = tk.Frame(body)
        normal_side.grid(row=0, column=1, sticky="nsew")
        normal_side.rowconfigure(0, weight=1)
        normal_side.rowconfigure(1, weight=1)
        normal_side.rowconfigure(2, weight=1)
        normal_side.columnconfigure(0, weight=1)

        self.lbl_normal_stats = tk.Label(
            normal_side,
            text="After analysis Cp/Cpk will show up.",
            justify=tk.LEFT,
            anchor=tk.NW,
            font=("Consolas", 10),
            bg="#f4f6f8",
            relief="sunken",
            padx=10,
            pady=10,
        )
        self.lbl_normal_stats.grid(row=0, column=0, sticky="nsew", pady=(0, 6))

        self.lbl_safety_ratio = tk.Label(
            normal_side,
            text="Safety ratio",
            justify=tk.LEFT,
            anchor=tk.NW,
            font=("Consolas", 10, "bold"),
            bg="white",
            relief="sunken",
            padx=10,
            pady=10,
        )
        self.lbl_safety_ratio.grid(row=1, column=0, sticky="nsew", pady=(0, 6))

        self.lbl_min_ratio = tk.Label(
            normal_side,
            text="Min ratio",
            justify=tk.LEFT,
            anchor=tk.NW,
            font=("Consolas", 10, "bold"),
            bg="white",
            relief="sunken",
            padx=10,
            pady=10,
        )
        self.lbl_min_ratio.grid(row=2, column=0, sticky="nsew")

    def build_data_tab(self):
        self.tab_data.columnconfigure(0, weight=3)
        self.tab_data.columnconfigure(1, weight=2)
        self.tab_data.rowconfigure(0, weight=1)

        left = tk.Frame(self.tab_data)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        data_header = tk.Frame(left)
        data_header.pack(fill=tk.X)
        tk.Label(data_header, text="Historical Data", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Checkbutton(
            data_header,
            text="Use last N",
            variable=self.use_recent_data,
            command=self.redraw_data_tab,
        ).pack(side=tk.RIGHT)

        history_cols = ("Date", "Code", "Customer", "Measurement", "SPC", "Percentile")
        self.tree_history = ttk.Treeview(left, columns=history_cols, show="headings")
        headings = {
            "Date": "Date",
            "Code": "Code",
            "Customer": "Customer",
            "Measurement": "Measurement",
            "SPC": "SPC",
            "Percentile": "% rank",
        }
        widths = {
            "Date": 105,
            "Code": 90,
            "Customer": 180,
            "Measurement": 95,
            "SPC": 90,
            "Percentile": 90,
        }
        for col in history_cols:
            self.tree_history.heading(col, text=headings[col])
            self.tree_history.column(col, width=widths[col], anchor=tk.CENTER)

        self.enable_tree_sorting(self.tree_history, history_cols)

        history_scroll_y = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.tree_history.yview)
        history_scroll_x = ttk.Scrollbar(left, orient=tk.HORIZONTAL, command=self.tree_history.xview)
        self.tree_history.configure(yscrollcommand=history_scroll_y.set, xscrollcommand=history_scroll_x.set)
        history_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        history_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_history.pack(fill=tk.BOTH, expand=True)

        right = tk.Frame(self.tab_data)
        right.grid(row=0, column=1, sticky="nsew", pady=10)
        tk.Label(right, text="Summary Statistics", font=("Arial", 11, "bold")).pack(anchor=tk.W)

        self.lbl_stats = tk.Label(
            right,
            text="Load an Excel file, enter the code and current mean value, then click Analyze.",
            justify=tk.LEFT,
            anchor=tk.NW,
            font=("Consolas", 10),
            bg="#f4f6f8",
            relief="sunken",
            padx=10,
            pady=10,
        )
        self.lbl_stats.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

    def build_customer_tab(self):
        frame = tk.Frame(self.tab_customer)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        customer_header = tk.Frame(frame)
        customer_header.pack(fill=tk.X)
        tk.Label(customer_header, text="Statistics per customer for filtered data", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        tk.Checkbutton(
            customer_header,
            text="Use last N",
            variable=self.use_recent_customer,
            command=self.redraw_customer_stats,
        ).pack(side=tk.RIGHT)

        customer_cols = (
            "Customer",
            "Count",
            "Mean",
            "Min",
            "Max",
            "Std",
            "MRbar",
            "Lower15",
            "Upper15",
            "LCL",
            "UCL",
            "NewPercent",
            "Status",
        )
        self.tree_customer = ttk.Treeview(frame, columns=customer_cols, show="headings")
        headings = {
            "Customer": "Customer",
            "Count": "Count",
            "Mean": "Mean",
            "Min": "Min",
            "Max": "Max",
            "Std": "St. Deviation",
            "MRbar": "MRbar",
            "Lower15": "15% lower",
            "Upper15": "15% upper",
            "LCL": "LCL I-MR",
            "UCL": "UCL I-MR",
            "NewPercent": "Current up from %",
            "Status": "Status",
        }
        widths = {
            "Customer": 220,
            "Count": 75,
            "Mean": 95,
            "Min": 95,
            "Max": 95,
            "Std": 95,
            "MRbar": 95,
            "Lower15": 95,
            "Upper15": 95,
            "LCL": 100,
            "UCL": 100,
            "NewPercent": 120,
            "Status": 115,
        }
        for col in customer_cols:
            self.tree_customer.heading(col, text=headings[col])
            self.tree_customer.column(col, width=widths[col], anchor=tk.CENTER)

        self.enable_tree_sorting(self.tree_customer, customer_cols)

        scroll_y = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tree_customer.yview)
        scroll_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.tree_customer.xview)
        self.tree_customer.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_customer.pack(fill=tk.BOTH, expand=True)

    def enable_tree_sorting(self, tree, columns):
        for col in columns:
            tree.heading(col, command=lambda c=col, t=tree: self.sort_treeview(t, c))

    def sort_treeview(self, tree, col):
        key = (id(tree), col)
        reverse = not self.sort_states.get(key, False)
        self.sort_states[key] = reverse
        rows = [(self.sort_value(tree.set(item, col)), item) for item in tree.get_children("")]
        rows.sort(key=lambda row: row[0], reverse=reverse)
        for index, (_, item) in enumerate(rows):
            tree.move(item, "", index)

    def sort_value(self, value):
        text = str(value).strip()
        if text in {"", "-"}:
            return (3, "")
        date_value = pd.to_datetime(text, dayfirst=True, errors="coerce")
        if pd.notna(date_value) and "/" in text:
            return (0, date_value.timestamp())
        numeric_text = text.replace("%", "").replace(",", ".")
        try:
            return (1, float(numeric_text))
        except ValueError:
            return (2, text.upper())

    def canonical_column_name(self, column):
        aliases = {
            "JobNo": "Order_ID",
            "jobSpec": "Order_Type",
            "MaterialType": "Material_Type",
            "description": "Description",
            "ECT": "Force",
        }
        cleaned = str(column).strip()
        return aliases.get(cleaned, cleaned)

    def normalize_columns_to_english(self, df):
        renamed = {}
        used = set()
        for column in df.columns:
            canonical = self.canonical_column_name(column)
            if canonical in used:
                canonical = str(column).strip()
            renamed[column] = canonical
            used.add(canonical)
        return df.rename(columns=renamed)

    def detect_header_row(self, file_path):
        preview = pd.read_excel(file_path, header=None, nrows=30)
        expected = {"ProcessDate", "Order_ID", "Order_Type", "Customer", "Material_Type", "Measurement", "Code"}
        for index, row in preview.iterrows():
            values = {self.canonical_column_name(value) for value in row.dropna().tolist()}
            if len(expected.intersection(values)) >= 2:
                return index
        return 0

    def load_excel(self):
        file_path = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if not file_path:
            return

        try:
            header_row = self.detect_header_row(file_path)
            df = pd.read_excel(file_path, header=header_row)
            df.columns = [str(col).strip() for col in df.columns]
            df = self.normalize_columns_to_english(df)
            df = df.dropna(how="all")

            if "ProcessDate" in df.columns:
                df["ProcessDate"] = pd.to_datetime(df["ProcessDate"], errors="coerce")

            for col in df.columns:
                if col != "ProcessDate":
                    numeric_source = df[col].astype(str).str.replace(",", ".", regex=False)
                    numeric = pd.to_numeric(numeric_source, errors="coerce")
                    if numeric.notna().sum() >= max(1, int(df[col].notna().sum() * 0.8)):
                        df[col] = numeric

            if "Customer" in df.columns:
                self.customer_col = "Customer"
            else:
                self.customer_col = "Customer"
                df[self.customer_col] = "No name"

            search_cols = [col for col in self.default_search_columns if col in df.columns]
            if not search_cols:
                search_cols = [col for col in df.columns if col != "ProcessDate"]
            self.cmb_search_col.config(values=search_cols)
            self.cmb_search_col.set(search_cols[0])

            numeric_cols = [
                col for col in df.columns
                if col != "ProcessDate" and pd.api.types.is_numeric_dtype(df[col])
            ]
            if not numeric_cols:
                raise ValueError("No numeric column for analysis.")
            if "Measurement" in numeric_cols:
                numeric_cols = ["Measurement"] + [col for col in numeric_cols if col != "Measurement"]
            self.cmb_measure_col.config(values=numeric_cols)
            self.cmb_measure_col.set(numeric_cols[0])

            boxplot_options = [col for col in ["Material_Type", "Type", "Order_Type"] if col in df.columns]
            if boxplot_options:
                self.cmb_boxplot_group.config(values=boxplot_options)
                self.cmb_boxplot_group.set("Material_Type" if "Material_Type" in boxplot_options else boxplot_options[0])

            self.df = df
            self.lbl_file.config(text=file_path.split("/")[-1].split("\\")[-1], fg="black")
            messagebox.showinfo(
                "Success",
                f"File loaded successfully.\nRows: {len(df)}\nColumns: {len(df.columns)}\nHeader row: {header_row + 1}",
            )
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load file.\nDetails: {exc}")

    def parse_float(self, text, field_name):
        try:
            return float(str(text).strip().replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"The field '{field_name}' must be a number.") from exc

    def parse_optional_float(self, text, field_name):
        cleaned = str(text).strip()
        if cleaned == "":
            return None
        try:
            return float(cleaned.replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"The field '{field_name}' must be a number.") from exc

    def parse_nonnegative_int(self, text, field_name, default_value=0):
        cleaned = str(text).strip()
        if cleaned == "":
            return default_value
        try:
            value = int(cleaned)
        except ValueError as exc:
            raise ValueError(f"The field '{field_name}' must be an integer") from exc
        if value < 0:
            raise ValueError(f"The field '{field_name}' cant be negative number")
        return value

    def parse_positive_int(self, text, field_name, default_value=None):
        cleaned = str(text).strip()
        if not cleaned and default_value is not None:
            return default_value
        try:
            value = int(cleaned)
        except ValueError as exc:
            raise ValueError(f"The field '{field_name}' must be an integer") from exc
        if value < 1:
            raise ValueError(f"The field '{field_name}' must be 1 or larger")
        return value

    def parse_ewma_lambda(self):
        value = self.parse_float(self.entry_ewma_lambda.get(), "EWMA lambda")
        if not 0 < value <= 1:
            raise ValueError("EWMA lambda must be between 0 and 1.")
        return value

    def recent_n_value(self):
        return self.parse_positive_int(self.entry_recent_n.get(), "Last N", 5)

    def model_for_scope(self, model, use_recent):
        if not use_recent:
            return model
        recent_n = self.recent_n_value()
        return model.tail(recent_n).copy()

    def filtered_data(self, search_col, code):
        column = self.df[search_col]
        numeric_column = pd.to_numeric(column, errors="coerce")
        if numeric_column.notna().any():
            return self.df[numeric_column == code].copy()
        return self.df[column.astype(str).str.strip() == str(code).strip()].copy()

    def apply_outlier_filter(self, model, measure_col):
        remove_high = self.parse_nonnegative_int(self.entry_remove_high.get(), "Larger values", 0)
        remove_low = self.parse_nonnegative_int(self.entry_remove_low.get(), "Lower values", 0)

        total = len(model)
        if remove_high + remove_low >= total:
            raise ValueError("The outlier filter would remove all values. Reduce the numbers.")

        ranked = model.sort_values(measure_col, ascending=False).copy()
        kept = ranked.iloc[remove_high: total - remove_low if remove_low else total].copy()
        removed = total - len(kept)

        if removed == 0:
            return kept, "Inactive", 0

        text = f"Removed {remove_high} highest and {remove_low} lowest values from {total} values"
        return kept, text, removed

    def calculate_stats(self, series, new_value, ewma_lambda=0.2):
        values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
        count = int(values.count())
        if count == 0:
            raise ValueError("There are no numeric values to calculate.")

        mean = float(values.mean())
        std = float(values.std(ddof=1)) if count > 1 else 0.0
        moving_ranges = values.diff().abs()
        mr_values = moving_ranges.dropna()
        mrbar = float(mr_values.mean()) if not mr_values.empty else 0.0
        sigma_imr = mrbar / D2_MOVING_RANGE_2 if mrbar else 0.0
        imr_delta = 3 * sigma_imr
        lcl = mean - imr_delta
        ucl = mean + imr_delta
        mr_lcl = 0.0
        mr_ucl = D4_MOVING_RANGE_2 * mrbar if mrbar else 0.0

        below_new = int((values < new_value).sum())
        equal_new = int((values == new_value).sum())
        above_new = int((values > new_value).sum())
        ewma = values.ewm(alpha=ewma_lambda, adjust=False).mean()
        ewma_lcl, ewma_ucl = self.ewma_limits(count, mean, sigma_imr, ewma_lambda)

        return {
            "count": count,
            "mean": mean,
            "std": std,
            "min": float(values.min()),
            "max": float(values.max()),
            "median": float(values.median()),
            "q1": float(values.quantile(0.25)),
            "q3": float(values.quantile(0.75)),
            "iqr": float(values.quantile(0.75) - values.quantile(0.25)),
            "lower15": mean * 0.85,
            "upper15": mean * 1.15,
            "mrbar": mrbar,
            "sigma_imr": sigma_imr,
            "lcl": lcl,
            "ucl": ucl,
            "mr_lcl": mr_lcl,
            "mr_ucl": mr_ucl,
            "z_new": (new_value - mean) / sigma_imr if sigma_imr else 0.0,
            "new_mr": abs(new_value - float(values.iloc[-1])) if count else None,
            "new_above_percent": below_new / count * 100 if count else 0.0,
            "new_equal_percent": equal_new / count * 100 if count else 0.0,
            "new_below_percent": above_new / count * 100 if count else 0.0,
            "cv": std / mean * 100 if mean else 0.0,
            "out_of_spc": int(((values < lcl) | (values > ucl)).sum()) if sigma_imr else 0,
            "out_of_mr": int((mr_values > mr_ucl).sum()) if mrbar else 0,
            "last_ma5": values.rolling(5).mean().dropna().iloc[-1] if count >= 5 else None,
            "last_ewma": float(ewma.iloc[-1]) if count else None,
            "ewma_lcl": ewma_lcl,
            "ewma_ucl": ewma_ucl,
            "ewma_lambda": ewma_lambda,
        }

    def ewma_limits(self, count, mean, sigma, ewma_lambda):
        lcls = []
        ucls = []
        for i in range(1, count + 1):
            factor = (ewma_lambda / (2 - ewma_lambda)) * (1 - (1 - ewma_lambda) ** (2 * i))
            width = 3 * sigma * (factor ** 0.5) if sigma else 0.0
            lcls.append(mean - width)
            ucls.append(mean + width)
        return lcls, ucls

    def get_spec_values(self, stats):
        lsl_text = self.entry_lsl.get().strip()
        usl_text = self.entry_usl.get().strip()
        lsl_input = self.parse_optional_float(lsl_text, "LSL")
        usl_input = self.parse_optional_float(usl_text, "USL")
        lsl_is_auto = lsl_input is None or (self.auto_lsl is not None and abs(lsl_input - self.auto_lsl) < 0.01)
        usl_is_auto = usl_input is None or (self.auto_usl is not None and abs(usl_input - self.auto_usl) < 0.01)

        if lsl_is_auto:
            lsl = stats["lower15"]
            self.entry_lsl.delete(0, tk.END)
            self.entry_lsl.insert(0, fmt(lsl))
            self.auto_lsl = lsl
        else:
            lsl = lsl_input

        if usl_is_auto:
            usl = stats["upper15"]
            self.entry_usl.delete(0, tk.END)
            self.entry_usl.insert(0, fmt(usl))
            self.auto_usl = usl
        else:
            usl = usl_input

        if usl is None:
            usl = stats["upper15"]
        if lsl >= usl:
            raise ValueError("LSL must be lower than USL.")
        return lsl, usl

    def capability_and_hypothesis(self, series, stats, lsl, usl, current_mean):
        values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
        n = int(values.count())
        historical_mean = float(values.mean())
        sample_std = float(values.std(ddof=1)) if n > 1 else 0.0
        sigma_cap = stats["sigma_imr"] if stats["sigma_imr"] else sample_std

        if sigma_cap:
            cu = (usl - current_mean) / (3 * sigma_cap)
            cl = (current_mean - lsl) / (3 * sigma_cap)
            cp = (usl - lsl) / (6 * sigma_cap)
            cpk = min(cu, cl)
        else:
            cu = cl = cp = cpk = None

        if n > 1 and sample_std:
            df = n - 1
            chi_low = scipy_stats.chi2.ppf(0.975, df)
            chi_high = scipy_stats.chi2.ppf(0.025, df)
            sigma_ci_low = ((df * sample_std ** 2) / chi_low) ** 0.5
            sigma_ci_high = ((df * sample_std ** 2) / chi_high) ** 0.5
        else:
            df = None
            sigma_ci_low = sigma_ci_high = None

        return {
            "lsl": lsl,
            "usl": usl,
            "n": n,
            "historical_mean": historical_mean,
            "current_mean": current_mean,
            "sample_std": sample_std,
            "sigma_cap": sigma_cap,
            "cp": cp,
            "cpk": cpk,
            "cu": cu,
            "cl": cl,
            "sigma_ci_low": sigma_ci_low,
            "sigma_ci_high": sigma_ci_high,
        }

    def lower_limit_safety_score(self, current_value, lower_limit, sigma_ref, historical_mean, z_required=2.85, lower_label="LSL"):
        denominator = historical_mean - lower_limit
        safety_ratio = float((current_value - lower_limit) / denominator) if denominator > 0 else None

        if sigma_ref is None or sigma_ref <= 0:
            return {
                "z_margin": None,
                "z_required": z_required,
                "p_safe": None,
                "safety_ratio": safety_ratio,
                "zone": "Insufficient sigma",
                "interpretation": "Safety cannot be calculated",
            }

        z_margin = float((current_value - lower_limit) / sigma_ref)
        if current_value <= lower_limit:
            return {
                "z_margin": z_margin,
                "z_required": z_required,
                "p_safe": 0.0,
                "safety_ratio": safety_ratio,
                "zone": f"FAIL / Below {lower_label}",
                "interpretation": "Not acceptable",
            }

        p_safe = float(scipy_stats.norm.cdf(z_margin - z_required))
        if safety_ratio is None:
            zone = "Insufficient ratio"
            interpretation = "There is no valid LSL-to-mean range"
        elif safety_ratio < 0.10:
            zone = "Red zone"
            interpretation = "Barely passing, very risky"
        elif safety_ratio < 0.30:
            zone = "Gray/orange zone"
            interpretation = "Above LSL but close"
        elif safety_ratio < 0.60:
            zone = "Yellow zone"
            interpretation = "Acceptable but needs monitoring"
        elif safety_ratio < 1.00:
            zone = "Green zone"
            interpretation = "Good/safe range"
        else:
            zone = "Above mean"
            interpretation = "Very good relative to the lower limit"

        return {
            "z_margin": z_margin,
            "z_required": z_required,
            "p_safe": p_safe,
            "safety_ratio": safety_ratio,
            "zone": zone,
            "interpretation": interpretation,
        }

    def analyze_data(self):
        if self.df is None:
            messagebox.showwarning("Warning", "Please load an Excel file first.")
            return

        search_col = self.cmb_search_col.get()
        measure_col = self.cmb_measure_col.get()
        if search_col not in self.df.columns or measure_col not in self.df.columns:
            messagebox.showerror("Error", "The selected columns were not found in the Excel file.")
            return

        try:
            code = self.parse_float(self.entry_code.get(), "Code")
            new_value = self.parse_float(self.entry_new_value.get(), "Current mean value")
            ewma_lambda = self.parse_ewma_lambda()
            recent_n = self.parse_positive_int(self.entry_recent_n.get(), "Last N", 5)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return

        model = self.filtered_data(search_col, code)
        model[measure_col] = pd.to_numeric(model[measure_col], errors="coerce")
        model = model.dropna(subset=[measure_col])

        if model.empty:
            messagebox.showinfo("Information", f"No historical data found for {search_col}: {code:g}")
            return

        try:
            model, filter_text, removed_count = self.apply_outlier_filter(model, measure_col)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return

        if "ProcessDate" in model.columns:
            model = model.sort_values("ProcessDate")
        else:
            model = model.reset_index(drop=True)

        stats = self.calculate_stats(model[measure_col], new_value, ewma_lambda)
        try:
            lsl, usl = self.get_spec_values(stats)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return

        self.last_model = model
        self.last_measure_col = measure_col
        self.last_search_col = search_col
        self.last_code = code
        self.last_new_value = new_value
        self.last_stats = stats
        self.last_removed_count = removed_count
        self.last_filter_text = filter_text
        self.last_ewma_lambda = ewma_lambda

        self.update_status(new_value, stats, lsl, usl)
        self.draw_i_chart(model, search_col, measure_col, code, new_value, stats)
        self.draw_mr_ewma_chart(model, measure_col, stats)
        distribution_model = self.model_for_scope(model, self.use_recent_distribution.get())
        normal_model = self.model_for_scope(model, self.use_recent_normal.get())
        normal_stats = self.calculate_stats(normal_model[measure_col], new_value, ewma_lambda)
        lsl, usl = self.get_spec_values(normal_stats)
        data_model = self.model_for_scope(model, self.use_recent_data.get())
        data_stats = self.calculate_stats(data_model[measure_col], new_value, ewma_lambda)
        customer_model = self.model_for_scope(model, self.use_recent_customer.get())

        self.draw_distribution_charts(distribution_model, measure_col)
        self.draw_normal_chart(normal_model, measure_col, normal_stats, lsl, usl)
        self.draw_recent_chart(model, search_col, measure_col, code, new_value, stats, recent_n)
        self.update_history(data_model, search_col, measure_col, code, data_stats)
        self.update_stats_text(search_col, measure_col, code, new_value, data_stats, filter_text, removed_count, recent_n, data_model)
        self.update_customer_stats(customer_model, measure_col, new_value, ewma_lambda)

    def update_status(self, new_value, stats, lsl, usl):
        diff_from_production = new_value - stats["mean"]
        if stats["sigma_imr"] == 0:
            self.lbl_status.config(text="Not enough variability for SPC I-MR limits", fg="#555")
        elif new_value < lsl:
            self.lbl_status.config(
                text=f"BELOW LSL: current {new_value:g}, LSL {lsl:.2f}, production mean {stats['mean']:.2f}",
                fg="#c62828",
            )
        elif new_value > usl:
            self.lbl_status.config(
                text=f"ABOVE USL: current {new_value:g}, USL {usl:.2f}, production mean {stats['mean']:.2f}",
                fg="#c62828",
            )
        elif new_value < stats["lcl"] or new_value > stats["ucl"]:
            self.lbl_status.config(
                text=f"Inside LSL/USL but outside I-MR SPC. Difference from production mean: {diff_from_production:.2f}",
                fg="#ef6c00",
            )
        else:
            self.lbl_status.config(
                text=f"WITHIN LIMITS: current {new_value:g}, production mean {stats['mean']:.2f}, difference {diff_from_production:.2f}",
                fg="#2e7d32",
            )

    def redraw_data_tab(self):
        if self.last_model is None or self.last_measure_col is None:
            return
        try:
            model = self.model_for_scope(self.last_model, self.use_recent_data.get())
            stats = self.calculate_stats(model[self.last_measure_col], self.last_new_value, self.last_ewma_lambda)
            recent_n = self.recent_n_value()
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.update_history(model, self.last_search_col, self.last_measure_col, self.last_code, stats)
        self.update_stats_text(
            self.last_search_col,
            self.last_measure_col,
            self.last_code,
            self.last_new_value,
            stats,
            self.last_filter_text,
            self.last_removed_count,
            recent_n,
            model,
        )

    def redraw_customer_stats(self):
        if self.last_model is None or self.last_measure_col is None:
            return
        try:
            model = self.model_for_scope(self.last_model, self.use_recent_customer.get())
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.update_customer_stats(model, self.last_measure_col, self.last_new_value, self.last_ewma_lambda)

    def chart_x_values(self, model):
        if "ProcessDate" in model.columns and model["ProcessDate"].notna().any():
            return model["ProcessDate"], True
        return list(range(1, len(model) + 1)), False

    def clear_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def draw_i_chart(self, model, search_col, measure_col, code, new_value, stats):
        self.clear_frame(self.tab_i_chart)
        self.i_canvas = None

        fig, ax = plt.subplots(figsize=(12, 6.2), dpi=100)
        x_values, has_dates = self.chart_x_values(model)
        y_values = model[measure_col].astype(float)
        ma5 = y_values.rolling(5).mean()

        ax.plot(x_values, y_values, marker="o", markersize=4, linewidth=1.4, color="#1565c0", label="Historical values")
        ax.plot(x_values, ma5, linewidth=1.8, linestyle="--", color="#ef6c00", label="MA 5")
        ax.axhline(stats["mean"], color="#111111", linewidth=1.6, label=f"Mean {stats['mean']:.2f}")
        ax.axhline(new_value, color="#6a1b9a", linestyle="--", linewidth=1.8, label=f"Current mean {new_value:g}")
        ax.axhline(stats["lcl"], color="#c62828", linestyle=":", linewidth=2, label=f"LCL I-MR {stats['lcl']:.2f}")
        ax.axhline(stats["ucl"], color="#c62828", linestyle=":", linewidth=2, label=f"UCL I-MR {stats['ucl']:.2f}")
        ax.axhline(stats["lower15"], color="#2e7d32", linestyle="-.", linewidth=1.3, label=f"15% lower {stats['lower15']:.2f}")
        ax.axhline(stats["upper15"], color="#2e7d32", linestyle="-.", linewidth=1.3, label=f"15% upper {stats['upper15']:.2f}")
        ax.fill_between(x_values, stats["lcl"], stats["ucl"], color="#ef9a9a", alpha=0.10)
        ax.fill_between(x_values, stats["lower15"], stats["upper15"], color="#66bb6a", alpha=0.25)

        if has_dates:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
            fig.autofmt_xdate(rotation=30)
        else:
            ax.set_xlabel("Measurement sequence")

        ax.set_title(f"I chart for {search_col}: {code:g}", fontsize=13)
        ax.set_ylabel(measure_col)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
        fig.tight_layout()

        self.i_canvas = FigureCanvasTkAgg(fig, master=self.tab_i_chart)
        self.i_canvas.draw()
        self.i_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def draw_mr_ewma_chart(self, model, measure_col, stats):
        self.clear_frame(self.tab_mr_ewma)
        self.mr_ewma_canvas = None

        fig, axes = plt.subplots(2, 1, figsize=(12, 7.5), dpi=100, sharex=True)
        x_values, has_dates = self.chart_x_values(model)
        y_values = model[measure_col].astype(float)
        mr_values = y_values.diff().abs()
        ewma = y_values.ewm(alpha=stats["ewma_lambda"], adjust=False).mean()

        ax_mr, ax_ewma = axes
        ax_mr.plot(x_values, mr_values, marker="o", markersize=4, linewidth=1.4, color="#455a64", label="Moving Range")
        ax_mr.axhline(stats["mrbar"], color="#111111", linewidth=1.5, label=f"MRbar {stats['mrbar']:.2f}")
        ax_mr.axhline(stats["mr_lcl"], color="#c62828", linestyle=":", linewidth=1.8, label="LCL MR 0.00")
        ax_mr.axhline(stats["mr_ucl"], color="#c62828", linestyle=":", linewidth=1.8, label=f"UCL MR {stats['mr_ucl']:.2f}")
        ax_mr.set_title("MR chart", fontsize=12)
        ax_mr.set_ylabel("MR")
        ax_mr.grid(True, alpha=0.3)
        ax_mr.legend(loc="upper left", bbox_to_anchor=(1.01, 1))

        ax_ewma.plot(x_values, y_values, marker=".", linewidth=0.8, color="#90a4ae", alpha=0.65, label="Values")
        ax_ewma.plot(x_values, ewma, marker="o", markersize=3, linewidth=1.8, color="#00897b", label=f"EWMA lambda={stats['ewma_lambda']:.2f}")
        ax_ewma.axhline(stats["mean"], color="#111111", linewidth=1.4, label=f"Mean {stats['mean']:.2f}")
        ax_ewma.plot(x_values, stats["ewma_lcl"], color="#c62828", linestyle=":", linewidth=1.8, label="EWMA LCL")
        ax_ewma.plot(x_values, stats["ewma_ucl"], color="#c62828", linestyle=":", linewidth=1.8, label="EWMA UCL")
        ax_ewma.set_title("EWMA chart", fontsize=12)
        ax_ewma.set_ylabel("EWMA")
        ax_ewma.grid(True, alpha=0.3)
        ax_ewma.legend(loc="upper left", bbox_to_anchor=(1.01, 1))

        if has_dates:
            ax_ewma.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
            fig.autofmt_xdate(rotation=30)
        else:
            ax_ewma.set_xlabel("Measurement sequence")

        fig.tight_layout()
        self.mr_ewma_canvas = FigureCanvasTkAgg(fig, master=self.tab_mr_ewma)
        self.mr_ewma_canvas.draw()
        self.mr_ewma_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def redraw_distribution_charts(self):
        if self.last_model is None or self.last_measure_col is None:
            return
        try:
            model = self.model_for_scope(self.last_model, self.use_recent_distribution.get())
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.draw_distribution_charts(model, self.last_measure_col)

    def draw_distribution_charts(self, model, measure_col):
        self.clear_frame(self.distribution_plot_frame)
        self.dist_canvas = None

        fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.8), dpi=100)
        ax_bar, ax_box = axes

        if "Material_Type" in model.columns:
            material_means = (
                model.groupby("Material_Type")[measure_col]
                .mean()
                .sort_values(ascending=False)
                .dropna()
            )
            if not material_means.empty:
                bars = ax_bar.bar(
                    material_means.index.astype(str),
                    material_means.values,
                    color="#0b2d5b",
                    edgecolor="#061426",
                    linewidth=1.4,
                    alpha=0.92,
                )
                ax_bar.set_title("Mean value by Material_Type")
                ax_bar.set_ylabel(f"Mean {measure_col}")
                ax_bar.tick_params(axis="x", rotation=35)
                y_offset = max(material_means.values) * 0.005 if len(material_means.values) else 0
                for bar, value in zip(bars, material_means.values):
                    ax_bar.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + y_offset,
                        f"{value:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=9,
                        color="#061426",
                        fontweight="bold",
                    )
                for tick in ax_bar.get_xticklabels():
                    tick.set_ha("right")
            else:
                ax_bar.text(0.5, 0.5, "No Material_Type values available.", ha="center", va="center")
        else:
            ax_bar.text(0.5, 0.5, "Material_Type column was not found.", ha="center", va="center")
        ax_bar.grid(True, axis="y", alpha=0.25)

        group_col = self.cmb_boxplot_group.get()
        if group_col in model.columns:
            grouped = []
            labels = []
            medians = []
            for label, series in model.groupby(group_col)[measure_col]:
                values = pd.to_numeric(series, errors="coerce").dropna()
                if not values.empty:
                    grouped.append(values)
                    labels.append(str(label))
                    medians.append(float(values.median()))

            if grouped:
                order = sorted(range(len(grouped)), key=lambda i: medians[i], reverse=True)
                grouped = [grouped[i] for i in order]
                labels = [labels[i] for i in order]
                ax_box.boxplot(grouped, labels=labels, showmeans=True)
                ax_box.set_title(f"Boxplot by {group_col}")
                ax_box.set_ylabel(measure_col)
                ax_box.tick_params(axis="x", rotation=35)
                for tick in ax_box.get_xticklabels():
                    tick.set_ha("right")
            else:
                ax_box.text(0.5, 0.5, f"No data available for {group_col}.", ha="center", va="center")
        else:
            ax_box.text(0.5, 0.5, f"{group_col} column was not found.", ha="center", va="center")
        ax_box.grid(True, axis="y", alpha=0.25)

        fig.tight_layout()
        self.dist_canvas = FigureCanvasTkAgg(fig, master=self.distribution_plot_frame)
        self.dist_canvas.draw()
        self.dist_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def redraw_normal_chart(self):
        if self.last_model is None or self.last_measure_col is None or self.last_stats is None:
            return
        try:
            model = self.model_for_scope(self.last_model, self.use_recent_normal.get())
            stats = self.calculate_stats(model[self.last_measure_col], self.last_new_value, self.last_ewma_lambda)
            lsl, usl = self.get_spec_values(stats)
        except ValueError as exc:
            messagebox.showerror("Error", str(exc))
            return
        self.draw_normal_chart(model, self.last_measure_col, stats, lsl, usl)

    def draw_normal_chart(self, model, measure_col, stats, lsl, usl):
        self.clear_frame(self.normal_plot_frame)
        self.normal_canvas = None

        values = model[measure_col].astype(float)
        capability = self.capability_and_hypothesis(values, stats, lsl, usl, self.last_new_value)
        mean = capability["historical_mean"]
        sigma = capability["sigma_cap"] or capability["sample_std"]

        fig, ax = plt.subplots(figsize=(9, 5.8), dpi=100)
        if sigma:
            x_min = min(values.min(), lsl, stats["lower15"], self.last_new_value, mean - 4 * sigma)
            x_max = max(values.max(), usl, stats["upper15"], self.last_new_value, mean + 4 * sigma)
            x_values = np.linspace(x_min, x_max, 500)
            y_values = scipy_stats.norm.pdf(x_values, loc=mean, scale=sigma)
            ax.plot(x_values, y_values, color="#1565c0", linewidth=2, label="Normal distribution")
            denominator = mean - lsl
            if denominator > 0:
                zones = (
                    (x_min, lsl, "#c62828", 0.10, "FAIL"),
                    (lsl, lsl + 0.10 * denominator, "#e53935", 0.22, "Red"),
                    (lsl + 0.10 * denominator, lsl + 0.30 * denominator, "#fb8c00", 0.20, "Gray/orange"),
                    (lsl + 0.30 * denominator, lsl + 0.60 * denominator, "#fdd835", 0.22, "Yellow"),
                    (lsl + 0.60 * denominator, mean, "#43a047", 0.20, "Green"),
                    (mean, x_max, "#1b5e20", 0.10, "Above mean"),
                )
                for start, end, color, alpha, label in zones:
                    if end > start:
                        ax.fill_between(
                            x_values,
                            0,
                            y_values,
                            where=(x_values >= start) & (x_values <= end),
                            color=color,
                            alpha=alpha,
                            label=label,
                        )
        else:
            ax.text(0.5, 0.5, "There is no variability for a normal curve.", ha="center", va="center")

        for value, color, label, linestyle in (
            (mean, "#111111", f"Mean {mean:.2f}", "-"),
            (lsl, "#c62828", f"LSL {lsl:.2f}", ":"),
            (usl, "#c62828", f"USL {usl:.2f}", ":"),
            (self.last_new_value, "#6a1b9a", f"Current mean {self.last_new_value:g}", "--"),
            (stats["lower15"], "#2e7d32", f"-15% {stats['lower15']:.2f}", "-."),
            (stats["upper15"], "#2e7d32", f"+15% {stats['upper15']:.2f}", "-."),
        ):
            ax.axvline(value, color=color, linestyle=linestyle, linewidth=1.7, label=label)

        min_value = float(values.min())
        ax.scatter(
            [min_value],
            [0],
            s=42,
            color="#263238",
            edgecolor="white",
            linewidth=0.8,
            zorder=5,
            label=f"Min {min_value:.2f}",
        )
        ax.annotate(
            "min",
            xy=(min_value, 0),
            xytext=(0, 8),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color="#263238",
            fontweight="bold",
        )
        ax.set_ylim(bottom=0)

        ax.set_title(f"Normal distribution for {measure_col}")
        ax.set_xlabel(measure_col)
        ax.set_ylabel("Density")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
        fig.tight_layout()

        self.normal_canvas = FigureCanvasTkAgg(fig, master=self.normal_plot_frame)
        self.normal_canvas.draw()
        self.normal_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        safety = self.lower_limit_safety_score(
            current_value=capability["current_mean"],
            lower_limit=lsl,
            sigma_ref=capability["sigma_cap"],
            historical_mean=capability["historical_mean"],
        )
        min_safety = self.lower_limit_safety_score(
            current_value=capability["current_mean"],
            lower_limit=float(values.min()),
            sigma_ref=capability["sigma_cap"],
            historical_mean=capability["historical_mean"],
            z_required=2.50,
            lower_label="min",
        )
        chi_text = (
            f"{capability['sigma_ci_low']:.2f} to {capability['sigma_ci_high']:.2f}"
            if capability["sigma_ci_low"] is not None
            else "-"
        )
        normal_text = (
            f"Current process comparison\n"
            f"Production mean             : {capability['historical_mean']:.2f}\n"
            f"Current mean value          : {capability['current_mean']:.2f}\n"
            f"Current-production diff.    : {capability['current_mean'] - capability['historical_mean']:.2f}\n\n"
            f"Specification limits\n"
            f"LSL                         : {lsl:.2f}\n"
            f"USL                         : {usl:.2f}\n\n"
            f"Current process indices\n"
            f"Cp                          : {fmt(capability['cp'])}\n"
            f"Cpk                         : {fmt(capability['cpk'])}\n"
            f"Cu                          : {fmt(capability['cu'])}\n"
            f"Cl                          : {fmt(capability['cl'])}\n\n"
            f"Standard deviations\n"
            f"Sample s                    : {capability['sample_std']:.2f}\n"
            f"I-MR sigma                  : {capability['sigma_cap']:.2f}\n"
            f"95% sigma CI with chi-square: {chi_text}"
        )
        self.lbl_normal_stats.config(text=normal_text)

        safety_text = (
            f"Safety ratio against LSL\n"
            f"LSL                         : {lsl:.2f}\n"
            f"Current mean                : {capability['current_mean']:.2f}\n"
            f"Difference from LSL         : {capability['current_mean'] - lsl:.2f}\n"
            f"z-margin                    : {fmt(safety['z_margin'], 4)}\n"
            f"safety p-score              : {fmt(safety['p_safe'], 5)}\n"
            f"safety ratio                : {fmt(safety['safety_ratio'], 4)}\n"
            f"Zone                        : {safety['zone']}\n"
            f"Interpretation              : {safety['interpretation']}"
        )
        self.lbl_safety_ratio.config(text=safety_text)

        min_text = (
            f"Min ratio against lowest value\n"
            f"Historical min              : {values.min():.2f}\n"
            f"Current mean                : {capability['current_mean']:.2f}\n"
            f"Difference from min         : {capability['current_mean'] - values.min():.2f}\n"
            f"z-margin min                : {fmt(min_safety['z_margin'], 4)}\n"
            f"p-min score                 : {fmt(min_safety['p_safe'], 5)}\n"
            f"min ratio                   : {fmt(min_safety['safety_ratio'], 4)}\n"
            f"Zone                        : {min_safety['zone']}\n"
            f"Interpretation              : {min_safety['interpretation']}"
        )
        self.lbl_min_ratio.config(text=min_text)

    def draw_recent_chart(self, model, search_col, measure_col, code, new_value, stats, recent_n):
        self.clear_frame(self.tab_recent)
        self.recent_canvas = None

        recent = model.tail(recent_n).copy()
        recent_values = recent[measure_col].astype(float)
        recent_mean = float(recent_values.mean()) if not recent_values.empty else 0.0
        x_values, has_dates = self.chart_x_values(recent)

        fig, ax = plt.subplots(figsize=(12, 6.2), dpi=100)
        ax.plot(
            x_values,
            recent_values,
            marker="o",
            markersize=5,
            linewidth=1.8,
            color="#1565c0",
            label=f"Last {len(recent)} values",
        )
        ax.axhline(recent_mean, color="#f57c00", linestyle="--", linewidth=2, label=f"Last {len(recent)} mean: {recent_mean:.2f}")
        ax.axhline(stats["mean"], color="#111111", linewidth=1.6, label=f"Production mean {stats['mean']:.2f}")
        ax.axhline(new_value, color="#6a1b9a", linestyle="--", linewidth=1.8, label=f"Current mean {new_value:g}")
        ax.axhline(stats["lcl"], color="#c62828", linestyle=":", linewidth=2, label=f"LCL I-MR {stats['lcl']:.2f}")
        ax.axhline(stats["ucl"], color="#c62828", linestyle=":", linewidth=2, label=f"UCL I-MR {stats['ucl']:.2f}")
        ax.axhline(stats["lower15"], color="#2e7d32", linestyle="-.", linewidth=1.4, label=f"15% lower {stats['lower15']:.2f}")
        ax.axhline(stats["upper15"], color="#2e7d32", linestyle="-.", linewidth=1.4, label=f"15% upper {stats['upper15']:.2f}")
        ax.fill_between(x_values, stats["lower15"], stats["upper15"], color="#66bb6a", alpha=0.25)

        if has_dates:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
            fig.autofmt_xdate(rotation=30)
        else:
            ax.set_xlabel("Measurement sequence")

        ax.set_title(f"I chart for last {len(recent)} measurements for {search_col}: {code:g}", fontsize=13)
        ax.set_ylabel(measure_col)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
        fig.tight_layout()

        self.recent_canvas = FigureCanvasTkAgg(fig, master=self.tab_recent)
        self.recent_canvas.draw()
        self.recent_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def update_history(self, model, search_col, measure_col, code, stats):
        for item in self.tree_history.get_children():
            self.tree_history.delete(item)

        values = model[measure_col].astype(float)
        sorted_values = values.sort_values()
        total = len(sorted_values)

        for idx, row in model.iterrows():
            date_value = row.get("ProcessDate", None)
            date_text = date_value.strftime("%d/%m/%Y") if pd.notna(date_value) and hasattr(date_value, "strftime") else "-"
            measurement = float(row[measure_col])
            spc_text = "Out" if stats["sigma_imr"] and (measurement < stats["lcl"] or measurement > stats["ucl"]) else "OK"
            percentile = (sorted_values < measurement).sum() / total * 100 if total else 0.0
            customer = row.get(self.customer_col, "-")
            code_value = row.get(search_col, code)

            self.tree_history.insert(
                "",
                tk.END,
                values=(
                    date_text,
                    fmt(code_value, 0),
                    str(customer),
                    fmt(measurement),
                    spc_text,
                    f"{percentile:.2f}%",
                ),
            )

    def update_stats_text(self, search_col, measure_col, code, new_value, stats, filter_text, removed_count, recent_n, model):
        last_ma5 = fmt(stats["last_ma5"]) if stats["last_ma5"] is not None else "-"
        last_ewma = fmt(stats["last_ewma"]) if stats["last_ewma"] is not None else "-"
        recent = model.tail(recent_n)
        recent_mean = recent[measure_col].mean() if not recent.empty else None
        text = (
            f"Values after filter          : {stats['count']}\n"
            f"Removed values               : {removed_count}\n"
            f"Min                           : {stats['min']:.2f}\n"
            f"Max                           : {stats['max']:.2f}\n"
            f"Mean                          : {stats['mean']:.2f}\n"
            f"Last {len(recent):<3} mean                : {fmt(recent_mean)}\n"
            f"Median                        : {stats['median']:.2f}\n"
            f"Q1 / Q3                       : {stats['q1']:.2f} / {stats['q3']:.2f}\n"
            f"IQR                           : {stats['iqr']:.2f}\n"
            f"Sample standard deviation     : {stats['std']:.2f}\n"
            f"CV                            : {stats['cv']:.2f}%\n"
            f"Last MA 5                     : {last_ma5}\n\n"
            f"MRbar                         : {stats['mrbar']:.2f}\n"
            f"Sigma I-MR = MRbar/1.128      : {stats['sigma_imr']:.2f}\n"
            f"LCL / UCL I-MR                : {stats['lcl']:.2f} / {stats['ucl']:.2f}\n"
            f"MR LCL / UCL                  : {stats['mr_lcl']:.2f} / {stats['mr_ucl']:.2f}\n"
            f"Historical values outside I-MR: {stats['out_of_spc']}\n"
            f"MR points outside limit       : {stats['out_of_mr']}\n"
            f"Current mean I-MR Z           : {stats['z_new']:.2f}\n\n"
            f"15% lower / 15% upper         : {stats['lower15']:.2f} / {stats['upper15']:.2f}\n"
            f"Last EWMA                     : {last_ewma}\n\n"
            f"Current mean is above         : {stats['new_above_percent']:.2f}% of historical values\n"
            f"Equal to                      : {stats['new_equal_percent']:.2f}% of historical values\n"
            f"Below                         : {stats['new_below_percent']:.2f}% of historical values"
        )
        self.lbl_stats.config(text=text)

    def update_customer_stats(self, model, measure_col, new_value, ewma_lambda):
        for item in self.tree_customer.get_children():
            self.tree_customer.delete(item)

        grouped = model.groupby(self.customer_col, dropna=False)[measure_col]
        for customer, series in grouped:
            values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
            if values.empty:
                continue

            stats = self.calculate_stats(values, new_value, ewma_lambda)
            if stats["sigma_imr"] and (new_value < stats["lcl"] or new_value > stats["ucl"]):
                status = "Out of I-MR"
            elif stats["lower15"] <= new_value <= stats["upper15"]:
                status = "OK 15%"
            else:
                status = "OK I-MR"

            self.tree_customer.insert(
                "",
                tk.END,
                values=(
                    str(customer),
                    stats["count"],
                    fmt(stats["mean"]),
                    fmt(stats["min"]),
                    fmt(stats["max"]),
                    fmt(stats["std"]),
                    fmt(stats["mrbar"]),
                    fmt(stats["lower15"]),
                    fmt(stats["upper15"]),
                    fmt(stats["lcl"]),
                    fmt(stats["ucl"]),
                    f"{stats['new_above_percent']:.2f}%",
                    status,
                ),
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = QualityControlApp(root)
    root.mainloop()
