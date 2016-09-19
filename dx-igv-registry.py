#!/usr/bin/env python

# Script to create an IGV session for a WGS sequencing project on dx
# usage
# python dx-igv-registry.py
# python -m SimpleHTTPServer 8000
#
import argparse
import glob
import os
from urllib import quote
from xml.etree.ElementTree import ElementTree, Element, SubElement, tostring
import xml.dom.minidom

import dxpy


class DxProjectRegistry(object):
    """Represent an DX Project as an IGV registry (XML)"""
    
    def __init__(self, project, genome="1kg_v37", URL_DURATION=86400):
        """
        
        :param project: 
        :param genome: 
        :param URL_DURATION: number of seconds for which the generated URL will be valid 
        """
        assert isinstance(project, dxpy.DXProject)
        
        Global = Element('Global')
        Global.set("name", project.name)
        Global.set("genome", genome)
        Global.set("version", "3")
        self.Global = Global
        self.URL_DURATION = URL_DURATION
        self.genome = genome
        self.project = project
    
    def addData(self, debug=False):
        """Add all data within a DX project to this DxProjectRegistry instance, starting at top level"""
        self.addLevel(self.Global, "/", debug=debug)
    
    def addLevel(self, node, folder, debug=False):
        """
        Recurse into folders, and find all IGV-compatible files to be added to registry
        :param node: an Element, or SubElement to add items to
        :param folder: a folder to find files within
        :param debug: boolean. If True, then stop finding files after the first one.
        :return: nothing.
        """
        assert node is not None
        assert folder is not None
        
        print "Adding {}:{}".format(self.project.name, folder)
        subfolders = dxpy.api.project_list_folder(self.project.id, input_params={"folder": folder, "describe": {
            "fields": {"id": True, "name": True, "class": True}}, "only": "folders", "includeHidden": False},
                                                  always_retry=True)["folders"]
        subfolders = [os.path.basename(subfolder) for subfolder in subfolders]
        
        for subfolder in subfolders:
            subnode = SubElement(self.Global, "Category", name=subfolder)
            subnodepath = str(folder + "/" + subfolder).replace("//", "/")
            self.addLevel(subnode, subnodepath)
        
        dxfiles = list(dxpy.find_data_objects(
            recurse=False, folder=folder, return_handler=True, project=self.project.get_id())
        )
        for dxfile in dxfiles:
            if isinstance(dxfile, dxpy.DXFile):
                n, ext = os.path.splitext(dxfile.name)
                if ext[1:] == "bam":
                    self.__addIndexedFile(dxfile, folder, node, ["bai"])
                elif str(dxfile.name).endswith("vcf.gz"):
                    self.__addIndexedFile(dxfile, folder, node, ["idx", "tbi"])
                elif str(dxfile.name).endswith("bw"):
                    self.__addNonIndexedFile(dxfile, folder, node)
                elif str(dxfile.name).endswith("bed.gz"):
                    self.__addNonIndexedFile(dxfile, folder, node)
                elif str(dxfile.name).endswith("tdf"):
                    self.__addNonIndexedFile(dxfile, folder, node)
    
    def __addIndexedFile(self, dxfile, folder, node, index_exts=["bai"]):
        """
        Add a file to XML tree, which should also have an index file
        :param dxfile: DXFile object, point to a BAM, or VCF file
        :param folder: folder in which to find the index file
        :param node: Element or SubElement object
        :param index_exts: an array of allowable file extensions of the index file. eg ['bai'], or ['idx', 'tbi']
        :return: nothing
        """
        print "Adding {}:{}/{}".format(self.project.name, folder, dxfile.name)
        assert isinstance(dxfile, dxpy.DXFile)
        
        file_url = dxfile.get_download_url(
            duration=self.URL_DURATION, filename=dxfile.name, preauthenticated=True
        )
        
        index = None
        for index_ext in index_exts:
            index_name = dxfile.name + "." + index_ext
            print "Looking for index file: {}".format(index_name)
            index = dxpy.find_one_data_object(
                name=index_name, folder=folder, name_mode="exact",
                project=self.project.get_id(), zero_ok=True, return_handler=True
            )
            if not index is None:
                break
        if index is None:
            #raise dxpy.exceptions.DXSearchError("Could not find an index file for {}".format(dxfile.name))
            #raise RuntimeWarning("Skipping {}, failed to find an index file".format(dxfile.name))
            print "Skipping {}, failed to find an index file".format(dxfile.name)
            return None
        
        indel_url = index.get_download_url(
            duration=self.URL_DURATION, preauthenticated=True, filename=index.name
        )
        
        resource = SubElement(node, "Resource")
        resource.set("name", dxfile.name)
        resource.set("path", file_url[0])
        resource.set("index", indel_url[0])
    
    def __addNonIndexedFile(self, dxfile, folder, node):
        """
        Add a file to XML tree, by generating a DX URL
        :param dxfile: DXFile object, point to a BAM, or VCF file
        :param folder: folder in which to find the index file
        :param node: Element or SubElement object
        :return: nothing
        """
        print "Adding {}:{}/{}".format(self.project.name, folder, dxfile.name)
        assert isinstance(dxfile, dxpy.DXFile)

        file_url = dxfile.get_download_url(
            duration=self.URL_DURATION, filename=dxfile.name, preauthenticated=True
        )

        resource = SubElement(node, "Resource")
        resource.set("name", dxfile.name)
        resource.set("path", file_url[0])
    
    def getXmlName(self):
        filename = self.project.name + ".xml"
        return filename
    
    def getRegistryName(self):
        filename = self.genome + "_dataServerRegistry.txt"
        return filename
    
    def writeXML(self):
        """
        pretty print the XML tree.
        :return: nothing
        """
        filename = self.getXmlName()
        rough_string = tostring(self.Global, 'utf-8', method="xml")
        reparsed = xml.dom.minidom.parseString(rough_string)
        
        with open(filename, "w") as text_file:
            text_file.write(reparsed.toprettyxml(indent="\t", encoding='utf-8'))
        
        # ElementTree(self.Global).write(filename, encoding="utf-8", xml_declaration=True)
        print "'%s' successfully created!" % filename
    
    def writeRegistryTXT(self):
        filename = self.getRegistryName()
        with open(filename, "a") as myfile:
            url = quote("http://localhost:8000/igvdata/" + self.getXmlName(), safe="%/:=&?~#+!$,;'@()*[]")
            myfile.write(url + "\n")
    
    def eraseRegistryTXT(self):
        filename = self.getRegistryName()
        if os.path.exists(filename):
            os.unlink(filename)

class IgvRegistry(object):
    def __init__(self, root="/Users/marcow/igvdata", URL_DURATION=86400):
        self.root = root
        self.URL_DURATION = URL_DURATION
        self.txt = "1kg_v37_dataServerRegistry.txt"
        
        manifests=[]
        os.chdir(self.root)
        for file in glob.glob("*.xml"):
            manifests.append(str(file).replace(".xml", ""))
        self.projects = manifests
    
    def getProjects(self):
        return self.projects
    
    def newProjects(self):
        """
        Find projects available on DX, not present in local cache
        :return: string array of project names.
        """
        dx_projects = list(dxpy.find_projects(return_handler=True))
        dx_project_names = [project.name for project in dx_projects]
        new_dx_projects = list(set(dx_project_names) - set(self.getProjects()))
        new_dx_projects = [x for x in new_dx_projects if not x.startswith('PIPELINE') and not x.endswith('resources')]
        print "Found {} new projects on DNAnexus, for {}".format(len(new_dx_projects), dxpy.whoami())
        return new_dx_projects
    
    def updateCache(self):
        new_projects = self.newProjects()
        for project in new_projects:
            dxproj = DxProjectRegistry(project=project, genome="1kg_v37", URL_DURATION=86400)
            dxproj.addData(debug=True)
            dxproj.writeXML()
            dxproj.writeRegistryTXT()
            self.projects.append(project)
    
    def forceUpdate(self):
        os.chdir(self.root)
        for file in glob.glob("*.xml"):
            os.unlink(file)
        os.unlink(self.txt)
        self.projects = []
        self.updateCache()
    
    def testUpdate(self):
        """Run a subset of projects"""
        first = True
        #project_ids = (u'project-BzPb25j0627bFJv6q9g81ZX5', u'project-Bz6GbkQ0VGPv0fpqZZ6ZZGfx', u'project-Bb9KVk8029vp1qzXz4yx4xB3')
        project_ids = (u'project-BzPb25j0627bFJv6q9g81ZX5', u'project-Bb9KVk8029vp1qzXz4yx4xB3')
        for project_id in project_ids:
            project = dxpy.DXProject(project_id)
            reg = DxProjectRegistry(project=project, genome="1kg_v37", URL_DURATION=60*24)
            if first:
                reg.eraseRegistryTXT()
                first = False
            reg.addData(debug=True)
            reg.writeXML()
            reg.writeRegistryTXT()

# reg = IgvRegistry()
# reg.getProjects()
# reg.newProjects()
# reg.testUpdate()

ONE_HOUR = 3600
ONE_DAY = 3600*24*1
ONE_WEEK = 3600*24*7
ONE_MONTH = 3600*24*31
ONE_YEAR = 3600*24*365

def main(args):
    reg = IgvRegistry("/Users/marcow/igvdata", args.duration)

    if args.test:
        reg.testUpdate()
        import sys
        sys.exit(0)
    #elif args.force:
    #    reg.forceUpdate()
    #elif args.update:
    #    reg.updateCache()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate an IGV registry, based on data that you can access in DNAnexus.',
        epilog="And that's how you roll."
    )

    parser.add_argument('-t', '--test', help='Test mode, over a few projects only', action='store_true')
    parser.add_argument('-f', '--force', help='Force recreation of registry', action='store_true')
    parser.add_argument('-u', '--update', help='Update registry', action='store_true')
    parser.add_argument('-d', '--duration', help='Duration to generate URLs for', type=int, required=False, default=ONE_MONTH, nargs=1)
    args = parser.parse_args()
    main(args)
