# Decision Calendar

A Python-based tool for creating Decision Calendar Plots for Hydrological Forecasting.

## Overview

This repository contains tools to generate decision calendar visualizations for hydrological forecasting. Decision calendars help river forecast centers, water resource managers and stakeholders understand the timing of key decisions and their relationship to hydrological forecasts.

## Repository Structure

- `notebooks/` - Jupyter Notebook for creating decision calendars
-`config/` - Configuration files in YAML format
  - `chena.yaml` - Configuration for Chena River analysis
  - `ross.yaml` - Configuration for Ross River analysis
- `scripts/` - Python scripts for generating decision calendars
  - `decision_calendars.py` - Main script for creating decision calendar plots
- `data/` - Data files for streamflow and snow data
- `output/` - Output files for decision calendars
- `images/` - Images used in the decision calendars

## Example Output

![Example Decision Calendar](./output/chena_decision_calendars.png)

## Getting Started

### Prerequisites

- Python 3.x
- Required Python packages (recommend creating a virtual environment):
  ```bash
  pip install jupyter numpy pandas matplotlib pyyaml pycirclize
  ```

### Usage

1. Clone the repository:
   ```bash
   git clone https://github.com/DaveCasson/decision_calendar.git
   cd decision_calendar
   ```

2. Launch Jupyter Notebook:
   ```bash
   jupyter notebook
   ```

3. Run the notebook `notebooks/decision_calendars.ipynb` to create decision calendars.

4. Configure your analysis (and colour schemes) by modifying the YAML files in the `config/` directory to match your specific river system and decision points.

## Configuration

The YAML configuration files in the `config/` directory define the parameters for each river system's decision calendar. You can use the existing templates (`chena.yaml` and `ross.yaml`) as examples for creating configurations for other river systems.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

##  MIT License



