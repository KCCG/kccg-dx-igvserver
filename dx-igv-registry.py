#!/usr/bin/env python

# Script to create an IGV session for a WGS sequencing project on dx

import dxpy
from urllib import quote
import os
from xml.etree.ElementTree import ElementTree, Element, SubElement
from xml.dom import minidom


class DxProjectRegistry(object):
    """Represent an DX Project as an IGV registry (XML)"""
    
    def __init__(self, project_name, genome="1kg_v37", URL_DURATION=86400):
        Global = Element('Global')
        Global.set("name", project_name)
        Global.set("genome", "1kg_v37")
        Global.set("version", "3")
        self.Global = Global
        self.URL_DURATION = URL_DURATION
        self.project_name = project_name
    
    def addData(self, project):
        #node = SubElement(self.Global, "Category", name=project.name)
        self.addLevel(self.Global, "/", project)
    
    def addLevel(self, node, folder="/", project=None):
        print "Adding {}:{}".format(project.name, folder)
        # @TODO - how to do this with dxpy?
        subfolders = os.popen("dx ls --folders {} | sed 's|/$||'".format(folder)).read().splitlines()
        os.popen("dx ls {} | sed 's|/$||'".format(folder)).read().splitlines()
        for subfolder in subfolders:
            subnode = SubElement(self.Global, "Category", name=subfolder)
            subnodepath = str(folder + "/" + subfolder).replace("//", "/")
            self.addLevel(subnode, subnodepath, project)
        
        files = list(dxpy.find_data_objects(recurse=False, folder=folder, return_handler=True))
        for file in files:
            if isinstance(file, dxpy.DXFile):
                n, ext = os.path.splitext(file.name)
                #if ext[1:] in ("bam", "vcf", "gz", "bed"):
                if ext[1:] == "bam":
                    #print "file_id: {}:{}".format(project.id, file.id)
                    
                    BAM_dx = file
                    #BAM_url = BAM_dx.get_download_url(duration=self.URL_DURATION, preauthenticated=True, project=project.id)
                    BAM_url = BAM_dx.get_download_url(duration=self.URL_DURATION, filename=BAM_dx.name, preauthenticated=True)
                    
                    bai_name = file.name + ".bai"
                    BAI_dx = dxpy.find_one_data_object(zero_ok=False, name=bai_name, folder=folder, name_mode="exact", return_handler=True)
                    #BAI_url = BAI_dx.get_download_url(duration=self.URL_DURATION, preauthenticated=True, filename=bai_name, project=project.id)
                    BAI_url = BAI_dx.get_download_url(duration=self.URL_DURATION, preauthenticated=True, filename=BAI_dx.name)
                    
                    BAM_Resource = SubElement(node, "Resource")
                    BAM_Resource.set("name", file.name)
                    BAM_Resource.set("path", BAM_url[0])
                    BAM_Resource.set("index", BAI_url[0])
    
    def getXmlName(self):
        filename = self.project_name + ".xml"
        return filename
    
    def writeXML(self):
        filename = self.getXmlName()
        ElementTree(self.Global).write(filename, encoding="utf-8", xml_declaration=True)
        print "'%s' successfully created!" % filename

    def writeRegistryTXT(self, filename="registry.txt"):
        with open(filename, "a") as myfile:
            url = quote("http://localhost:8000/" + self.getXmlName(), safe="%/:=&?~#+!$,;'@()*[]")
            myfile.write(url)

def test():
    ##### TEST
    project_id = u'project-Byz88f80Qpz95F9JfbXKb27z'
    project = dxpy.DXProject(project_id)
    reg = DxProjectRegistry(project_name=project.name, genome="1kg_v37", URL_DURATION=86400)
    reg.addData(project)
    reg.writeXML()
    os.unlink("registry.txt")
    reg.writeRegistryTXT("registry.txt")
    
#test()
#import sys
#sys.exit(0)

URL_DURATION = 86400

os.unlink("registry.txt")
reg = DxProjectRegistry(genome="1kg_v37", URL_DURATION=URL_DURATION)
projects = list(dxpy.find_projects())
project_ids = [project["id"] for project in projects]
for project_id in project_ids:
    project = dxpy.DXProject(project_id)
    reg = DxProjectRegistry(project_name=project.name, genome="1kg_v37", URL_DURATION=86400)
    reg.addData(project)
    reg.writeXML()
    reg.writeRegistryTXT("registry.txt")
