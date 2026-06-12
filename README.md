# SPC Quality Control Application

A desktop Python application for Statistical Process Control (SPC) and quality analysis.

This project was created to support quality-control work by analyzing historical production data, comparing current measurements with past performance, and visualizing process behavior through SPC charts and statistical summaries.

## Features

* I-MR Control Charts
* Moving Range Monitoring
* EWMA Monitoring
* Process Capability Analysis (Cp, Cpk)
* Customer-Based Statistics
* Historical Trend Analysis
* Outlier Exclusion
* Material-Type Analysis
* Boxplot Visualization
* Excel Import Support

## Technologies

* Python
* Pandas
* NumPy
* SciPy
* Matplotlib
* Tkinter

## How to Run

Install the required libraries:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python spc_quality_control.py
```

## Excel Input

The application works with Excel files containing production or quality-control measurements.

It can analyze data based on fields such as:

* Code
* Order ID
* Order Type
* Measurement
* Customer
* Material Type
* Process Date

The exact column names can be adjusted inside the application logic if needed.

## Sample Data

The repository includes a dummy Excel dataset for demonstration purposes:

`Dummy_Data.xlsx`

No real customer or production data are included.

## How It Works

The user imports an Excel file containing historical quality-control measurements.

After selecting the search field, product code, measurement column, and current value, the application filters the relevant historical data and calculates SPC statistics.

The tool then generates I-MR charts, EWMA monitoring charts, distribution plots, process capability metrics, and customer-based summaries.

The current measurement is compared against historical performance, control limits, and specification limits to support quality-control evaluation.


## Specification Limits

By default, the application automatically creates provisional specification limits:

* LSL = Mean × 0.85
* USL = Mean × 1.15

These default limits are only used as configurable demonstration values.

They do not represent any official standard, ISO requirement, customer specification, or regulatory limit.

Users can manually adjust LSL and USL according to the actual product specifications and quality requirements.


## Screenshots

### I Chart

![I Chart](images/Git_SPC1.png)

### MR & EWMA Monitoring

![MR & EWMA](images/Git_SPC2.png)

### Material Analysis

![Material Analysis](images/Git_SPC3.png)

### Process Capability Analysis

![Process Capability](images/Git_SPC4.png)

## Development Note

This project was developed with the assistance of AI coding tools for code generation, debugging, and refactoring.

The SPC methodology, quality-control requirements, calculations, business logic, and application structure were defined, reviewed, and tested by the author.

## Custom Evaluation Metrics

In addition to standard SPC and capability metrics, the application includes custom support indicators such as safety ratio, p-safe score, min ratio, and p-min score.

These indicators are experimental engineering-support metrics designed to compare the current mean value against the lower specification limit and the lowest historical value.

They are not official SPC or ISO-standard metrics and should be used only as additional decision-support information together with Cp, Cpk, control limits, customer specifications, and engineering judgment.

## Future Improvements

* Nelson Rules
* Western Electric Rules
* Xbar-R Charts
* p / np / c / u Charts
* PDF Report Export
* Database Integration
* Power BI Connectivity

## Disclaimer

This application is intended as an educational and engineering-support tool.

Quality decisions should always be verified against official product specifications, customer requirements, internal quality procedures, and engineering judgment.


