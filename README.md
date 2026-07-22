# VLBI Antenna Slew Model

This project compute antenna slew model (rate and offset) using FS log files.

## Installation
First created a directory and move to it.  
The config command at end of script creates the executable file bin/slew and download antenna.cat catalog.

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

Save the .log or _full.log.bz2 files in the session directory.  
The .log file will be used first. No need to uncompress the full log.

To compute the antenna slew model, the software needs azimuth and elevation of observed source.  
You need one of these files stored in session directory: 

&emsp;session.azel or  
&emsp;session.skd or  
&emsp;session.vex  

The application will use the .azel file first if available.  
If .azel not available, 'slew' will use the .skd first over the .vex file.  
In this case, azimuth and elevation of sources are computed using python package [astropy](https://www.astropy.org).  

Example of the structure of the working directory.  

.venv/  
antenna.cat  

bin/  
bin/slew

vo6007/  
vo6007/vo6007.azel  
vo6007/vo6007gs.log  
vo6007/vo6007k2.log  
vo6007/vo6007mg_full.log.bz2  

vo6014/  
vo6014/vo6014.skd  
vo6014/vo6014gs.log  
vo6014/vo6014k2.log  
vo6014/vo6014mg_full.log.bz2  


## Usage

Go to your working directory.  

To compute a model for a specific station using all sessions.

bin/slew station

The station is the IVS 2-letters code for the station.

Ff you want to specify which sessions to use.

bin/slew station_code -s session [session ...] 

Other options.  
-h : Help  
-v : Verbose. Print all records used in computation.  
-c : Catalog. If you have a different file than antenna.cat  


## Astropy Data Sets

Astropy needs some data sets that need to be updated at specific intervale.  
This data sets are store in ~/.cache/astropy or ~/.astropy directory depending of system.

You may see messages like this.

Downloading https://datacenter.iers.org/data/9/finals2000A.all  
|===================================================================| 3.7M/3.7M (100.00%)         3s

This is normal but may be a problem if no internet access.


