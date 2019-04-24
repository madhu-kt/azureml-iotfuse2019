# azureml-iotfuse2019
This repo contains all the required code for the Azure ML Workshop at IoTFuse 2019. 

# Getting started

## Join the Slack channel!

https://join.slack.com/t/iotfuse2019/shared_invite/enQtNjE5NTQwMDM4Mzc0LTg0M2I5MzgyNzk1YmZjNTFmOTNmNTc1ZDhjOTliYzliMDBmNTBkZGVlZjgwZTcxOTIyNzc2ZDFhYzVmZTdiNzg

## Install Anaconda

- Download: https://docs.anaconda.com/anaconda/install/
- Create environment: `conda create --name [your environment name here] python=3.5`
- Activate environment: `conda activate [your environment name here]`
- `pip install ipykernel`
## Install Jupyter Notebook

- Download: https://jupyter.readthedocs.io/en/latest/install.html
- Set kernel: python -m ipykernel install --user --name [your environment name here] --display-name "Python 3.5 (Azure ML Studio)"
- Select kernel on Jupyter: Kernel --> Change Kernel --> "Python 3.5 (Azure ML Studio)"

## Install Plotly Dash

- `pip install dash==0.39.0` - The core dash backend
- `pip install dash-daq==0.1.0` - DAQ components (newly open-sourced!)
- `pip install azure-storage` - Data storage

# Other Resources

- NASA C-MAPSS dataset paper: https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/20150007677.pdf
- Azure ML Studio: https://studio.azureml.net/
