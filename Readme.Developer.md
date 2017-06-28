# Overview
Once you have installed, setup, or configured your IGV server, then adding an XML manifest to a project is simple:
* Add an XML to the registry, for a certain group

    dx-igv-registry.py -p $project_id -g LKCGP

* Add an XML to the registry, for mm10 reference genome

    dx-igv-registry.py -p $project_id -g NEIWAT -r mm10

* Add all XMLs from a group to the registry

    for project_id in $(dx find projects --tag LKCGP --brief); do 
        dx-igv-registry.py -p $project_id -g LKCGP
    done

## additional options

    $ dx-igv-registry.py -h
    usage: dx-igv-registry.py [-h] [-p PROJECT_ID] [-d DURATION] [-r REF_GENOME]
                              [-g GROUP] [--xmlOnly XMLONLY] [--igvdata IGVDATA]
                              [--url URL] [-t] [-f]
    
    Generate an IGV registry, based on data that you can access in DNAnexus.
    
    optional arguments:
      -h, --help            show this help message and exit
      -p PROJECT_ID, --project_id PROJECT_ID
                            Update specific project_id(s), or project_name(s). Can
                            be specified any number of times
      -d DURATION, --duration DURATION
                            Duration to generate URLs for, in seconds
      -r REF_GENOME, --ref_genome REF_GENOME
                            reference ref_genome build (eg 1kg_v37, mm10, hg19)
      -g GROUP, --group GROUP
                            Remote IGV server Group to associate data with
      --xmlOnly             [Advanced] Only create an XML file
      --igvdata IGVDATA     [Advanced] Override the path to local igvdata
      --url URL             [Advanced] Override the web accessible URL to igvdata
      -t, --test            Test mode, over a few projects only
      -f, --force           Force recreation of XML files within a registry
    
    You will need to use a recent version of IGV (> 2.3.90).

# IGV setup
IGV setup is simple, and you only have to do this once:
  # open IGV, version 2.3.90 or newer
  # View > Preferences > Advanced
  # set Data Registry URL = https://seave.bio/igvdata/LKCGP/$$_dataServerRegistry.txt
  # Hit OK
  # Ensure that your reference genome is "Human (1kg, b37+decoy)", or mm10 if appropriate. ie not hg19, or b37
  
# IGV Usage:
  # open IGV, version 2.3.90 or newer
  # File > Load from Server...
  # Enter your username + password
  # Select the appropriate data to load.


There are a number of common usage scenarios:
1. You are an end user, and just want to connect to a server that's been setup.
2. You want to setup a local IGV data server & add XML files that you've been given
3. You want to setup a local IGV data server & create your own XML files 
4. You want to setup an IGV dataserver on an Apache server, and generate your own XML files

# Scenario 1
## Setup IGV server
1. You are an end user, and just want to connect to a server that's been setup.
* See Readme.md

# Scenario 2
2. You want to setup a local IGV data server & add XML files that you've been given
## one time setup
    [[ -d ~/igvdata ]] || mkdir ~/igvdata
## Start a simple webserver
* You need to start the webserver every time you reboot your computer, or at least every time you want to use IGV
* This works on OSX, and should work on Linux
* open Terminal app & type

    cd $HOME && python -m SimpleHTTPServer 8000

* You can terminate this process at any time via Ctrl-C

## Install the XML files
* Simply place these files inside the ~/igvdata directory
* Create a txt file called ~/igvdata/1kg_v37_dataServerRegistry.txt
* Add URLs to each of the XML files within that directory.
* Heres some examples

    http://localhost:8000/igvdata/170505_NS500817_0171_AHKWKLBGX2.xml
    http://localhost:8000/igvdata/20161024_MoST.xml
    http://localhost:8000/igvdata/R_160805_EMIMOU_LIONSDNA_M002.xml
    http://localhost:8000/igvdata/Test%20IGV%20Server.xml
* Note the last file had spaces in the filename, which were URL encoded

# Scenario 3
3. You want to setup a local IGV data server & create your own XML files 
## setup and start webserver
* as per Scenario 2.

## install kccg-dx-igvserver
    [[ -d ~/apps ]] || mkdir ~/apps
    cd ~/apps
    git clone ssh://git@kccg.garvan.org.au:7999/nex/kccg-dx-igvserver.git
    git checkout PIPELINE-1215-seave.bio

## create XML manifest for a project(s)
* See Usage section below


# Scenario 4
4. You want to setup an IGV dataserver on an Apache server, and generate your own XML files

## setup web-accessible location
* on seave.bio, this is /var/www/html/igvdata 

    if [[ ! -d /var/www/html/igvdata ]]; then
      mkdir /var/www/html/igvdata
      sudo chgrp -R www-data /var/www/html/igvdata
      chmod -R 750 /var/www/html/igvdata
    fi

## install dx-toolkit
    sudo apt-get install -y python-dev
    wget https://wiki.dnanexus.com/images/files/dx-toolkit-v0.222.0-ubuntu-14.04-amd64.tar.gz
    tar -xzvf dx-toolkit-v0.222.0-ubuntu-14.04-amd64.tar.gz 
    sudo mv dx-toolkit /usr/local

## install source code
* on localhost (since git clone isn't working for me at the moment)
    cd ~/src/DNANexus_Applets/kccg-dx-igvserver/
    ./push2seave.sh

## setup virtual env

    ssh seave.bio
    cd /home/ubuntu/apps/kccg-dx-igvserver/
    test -d venv || python virtualenv-1.11.6/virtualenv.py -p python2.7 venv
    source venv/bin/activate
    pip install -r requirements.txt
    dx login --no-projects
    dx select kccg
