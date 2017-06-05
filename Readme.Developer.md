# INSTALLATION
## installation on Seave.bio
### dx-toolkit
    sudo apt-get install -y python-dev
    wget https://wiki.dnanexus.com/images/files/dx-toolkit-v0.222.0-ubuntu-14.04-amd64.tar.gz
    tar -xzvf dx-toolkit-v0.222.0-ubuntu-14.04-amd64.tar.gz 
    sudo mv dx-toolkit /usr/local

### get source code
* why isn't `git clone` working on seave.bio - permissions?


    cd ~/src/DNANexus_Applets/kccg-dx-igvserver/
    cat push2seave.sh
    #!/bin/bash
    server=ubuntu@dev.seave.bio
    dest=/home/ubuntu/apps/kccg-dx-igvserver/
    #rsync -av virtualenv-1.11.6 requirements.txt dx-igv-registry.py $server:$dest
    rsync requirements.txt dx-igv-registry.py $server:$dest

    ./push2seave.sh

### setup virtual env

    ssh seave.bio
    cd /home/ubuntu/apps/kccg-dx-igvserver/
    test -d venv || python virtualenv-1.11.6/virtualenv.py -p python2.7 venv
    source venv/bin/activate
    pip install -r requirements.txt
    dx login --no-projects
    dx select kccg

    ./dx-igv-registry.py -p $project_id -g LKCGP

## Installation on localhost
* assume you have dx-toolkit already installed, and have been using dx util for a while.


    [[ -d ~/igvdata ]] || mkdir ~/igvdata
    git clone ssh://git@kccg.garvan.org.au:7999/nex/kccg-dx-igvserver.git
    git checkout PIPELINE-1215-seave.bio

# Usage

## Add an XML to the registry, for a certain group
    dx-igv-registry.py -p $project_id -g LKCGP

## Add all XMLs from a group to the registry
    for project_id in $(dx find projects --tag LKCGP --brief); do ./dx-igv-registry.py -p $project_id -g LKCGP; done

# IGV setup
IGV setup is simple, and you only have to do this once:
  * open IGV, version 2.3.90 or newer
  * View > Preferences > Advanced
  * set Data Registry URL = https://seave.bio/igvdata/LKCGP/$$_dataServerRegistry.txt
  * Hit OK
  * Ensure that your reference genome is “Human (1kg, b37+decoy)”
  
# IGV Usage:
  * open IGV, version 2.3.90 or newer
  * File > Load from Server…
  * Enter your username + password
  * Select the appropriate data to load.
