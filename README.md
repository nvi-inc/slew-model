# VLBI Antenna Slew Model

This project compute antenna slew model (rate and offset) using FS log files.

## Installation
First created a directory and cd to it. The config command create bin/slew file and download the antenna.cat file

```
python3 -m venv .venv

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip  install git+https://github.com/nvi-inc/slew-model.git

config

deactivate
```

### Directory structure
The application ’slew’ needs a specific structure.<\br>
The directory needs the file antenna.cat that has been downloaded by 'config'
 
You need to create a directory for each session you want to process logs.<\br>
For each session, you need the skd or vex file.
 
The directory should look like this
 
slew-model
        |
        - antenna.cat
        |
        - vo4318
           |
           - vo4318.skd
           - vo4318k2.log
           - vo4318mg.log
        |
        - vo4325
           |
           - vo4325.vex
           - vo4325k2.log
           - vo4325mg_full.log.bz2

The application will use first the skd over the vex.
It will also prefer the log over the full_log.
No need to uncompress the full log.

To compute a model for a specific station.

cd to your working directory.

bin/slew station_code

if you want to specify which sessions to use.

bin/slew station_code -s session_code_1 session_code_2 ...




