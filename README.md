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

The directory structure will look like this.  

working_directory  
&emsp;|  
&emsp;&nbsp;antenna.cat  
&emsp;&nbsp;bin/  
&emsp;&nbsp;bin/slew  
&emsp;|  
&emsp;&nbsp;vo6007/  
&emsp;&nbsp;vo6007/vo6007.azel  
&emsp;&nbsp;vo6007/vo6007gs.log  
&emsp;&nbsp;vo6007/vo6007k2.log  
&emsp;&nbsp;vo6007/vo6007mg_full.log.bz2  
&emsp;|  
&emsp;&nbsp;vo6014/  
&emsp;&nbsp;vo6014/vo6014.skd  
&emsp;&nbsp;vo6014/vo6014gs.log  
&emsp;&nbsp;vo6014/vo6014k2.log  
&emsp;&nbsp;vo6014/vo6014mg_full.log.bz2  


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


