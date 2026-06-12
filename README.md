# SPC Quality Control Application

A Python application for Statistical Process Control (SPC) and quality analysis.

The tool helps evaluate production performance using historical data, control charts, process capability metrics, and statistical visualizations.

## Features

- I-MR Control Charts
- EWMA Monitoring
- Process Capability Analysis (Cp, Cpk)
- Customer-Based Statistics
- Historical Trend Analysis
- Outlier Exclusion
- Boxplot Visualization
- Excel Import Support

## Technologies

- Python
- Pandas
- NumPy
- SciPy
- Matplotlib
- Tkinter

## Specification Limits

By default, specification limits are automatically generated as:

- LSL = Mean × 0.85
- USL = Mean × 1.15

These values are used as configurable demonstration limits and do not follow any specific standard or customer specification.

Both limits can be manually adjusted by the user.

## Development Note

This project was developed with the assistance of AI coding tools for code generation and debugging. The SPC methodology, calculations, business logic, and quality-control requirements were defined and reviewed by the author.

## Future Improvements

- Nelson Rules
- Xbar-R Charts
- p / np / c / u Charts
- PDF Reports
- Database Integration
- Power BI Connectivity
