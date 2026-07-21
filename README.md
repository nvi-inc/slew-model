# VLBI Antenna Slew Model

This project compute antenna slew model (rate and offset) using FS log files.

## Installation
First created a directory and cd to it.  
The config command at end of script creates the executable file bin/slew and download antenna.cat

```
python3 -m venv .venv

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip  install git+https://github.com/nvi-inc/slew-model.git

config

deactivate
```

## Directory structure
The application ’slew’ needs a specific structure.  
 
You need to create a directory for each session you want to process logs.  
Directory name must be in lower case.  
Save the schedule files (skd or vex) in the session directory.  
Save logs or full logs in the session directory.  

The application will use the .skd first over the .vex.
It will also prefer the log over the full_log.
No need to uncompress the full log.

## Usage

To compute a model for a specific station.

cd to your working directory.

bin/slew station_code

if you want to specify which sessions to use.

bin/slew station_code -s session_code_1 session_code_2 ...

Other options
-h : Help
-v : Verbose. Print all records used in computation.
-c : Catalog. If you have a different file than antenna.cat


