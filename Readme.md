This application allows you to run an IGV Data Server, for serving up data that lives in DNAnexus. The server can be
run on your localhost, or on Apache server (eg seave.bio).

An IGV Data Server is simply an HTTP server, hosting a web-accessible TXT file, which contains hyperlinks to XML files. 
Each XML file contains hyperlinks to genomic data on DNAnexus. As such, these URLs will expire (default 1 year).

# Adding XML manifests to the server (local machine, or seave.bio)
* Add an XML to the registry

    dx-igv-registry.py -p $project_id

* Add an XML to the registry, for a certain group, where URLs expire after 1 month (31*24*3600 seconds)

    dx-igv-registry.py -p $project_id -g LKCGP -d 2678400

* Add all XMLs from a group to the registry

    for project_id in $(dx find projects --tag LKCGP --brief); do 
        dx-igv-registry.py -p $project_id -g LKCGP
    done

# IGV Setup
To use your IGV Data Server, you need to configure IGV to use the server, instead of the default server at Broad.
Setup is simple, and you only have to do this once:
* open IGV, version 2.3.90 or newer
* View > Preferences > Advanced
* if using the seav.bio server:
  * set Data Registry URL = https://seave.bio/igvdata/LKCGP/$$_dataServerRegistry.txt
    * Change LKCGP to your group if necessary, eg MoST, TxGen, ...
* if using localhost:
  * set Data Registry URL = http://localhost:8000/igvdata/$$_dataServerRegistry.txt
* Hit OK
* Ensure that your reference genome is “Human (1kg, b37+decoy)”

# Usage:
* open IGV, version 2.3.90 or newer
* File > Load from Server...
* If using seave.bio, then enter your username + password
* Select the appropriate data to load.

## Hints:
* the BAM files with (tdf) at the end of their name are BAM files that are linked to genome-wide coverage files (tdf format). These will let you still see read coverage if you zoom out beyond 10Kb.
* The data lives in the US, so loading the reads can be slow. So I disable IGV from loading them by default, via: View > Preferences > Alignments: On initial load show: only Coverage Track.
* You can load the reads when you need them by right clicking the coverage track, and then ‘load alignments’

## Getting Access
If you’d like access, please choose a username + password, then visit http://www.htaccesstools.com/htpasswd-generator/,
enter this information, and let Mark C, or Vel know.

# Installation
* See Readme.Developer.md for instructions on how to install this application, and how to setup an IGV server.

# Administration
* To add a project to the server:

    ./dx-igv-registry.py -p $project_id -g LKCGP

* To add many projects to the server:

    for project_id in $(dx find projects --tag LKCGP --brief); do ./dx-igv-registry.py -p $project_id -g LKCGP; done

* See Readme.Developer.md for more info.
