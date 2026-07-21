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

You need session.azel or session.skd or session.vex to be able to compute azimuth and elevation of sources.  
Save these files in the session directory. 

The application will use the .azel file first if available.  
If .azel not available, 'slew' will use the .skd first over the .vex file.  
In this case, azimuth and elevation of sources are computed using python package [astropy](https://www.astropy.org).  

Save also the .log or _full.log.bz2 files in the session directory.  
The .log file will be used first.  
No need to uncompress the full log.

## Usage

To compute a model for a specific station.

cd to your working directory.

bin/slew station_code

if you want to specify which sessions to use.

bin/slew station_code -s session [session ...] 

Other options.  
-h : Help  
-v : Verbose. Print all records used in computation.  
-c : Catalog. If you have a different file than antenna.cat  


