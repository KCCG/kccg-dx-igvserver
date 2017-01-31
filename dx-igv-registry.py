#!/usr/bin/env python

# Script to create an IGV session for a WGS sequencing project on dx
# It creates one XML file for each DX project, and records these in a 
# registry at ~/igvdata/$$_dataServerRegistry.txt
# $$ is used by IGV to choose a different dataServerRegistry file depending on the active reference genome
#
# Usage For Generating
# --------------------
#     mkdir ~/igvdata
#     python dx-igv-registry.py -u
#     python -m SimpleHTTPServer 8000
#     IGV > View > Preferences > Advanced
#      * Data Registry URL = http://localhost:8000/igvdata/$$_dataServerRegistry.txt
#
# Usage for End Users wanting to use an XML
# -----------------------------------------
# The XML file contains URLs to all of the data within a DNAnexus project. These URLs are
# pre-authenticated, ie you wont be asked for a password. So be careful
# who you share this file with.
#
# You need to do some setup to create a simple HTTP server, so IGV can connect to
# this DNAnexus data.
#
# * mkdir ~/igvdata
# * put the xml file(s) in this folder
# * create a txt file: ~/igvdata/1kg_v37_dataServerRegistry.txt, where each line
#   represents one of these xml files. it should be a valid URL to the file. like this:
#   http://localhost:8000/igvdata/NEIWAT_Lung_Cancer_Project.xml
#   If the filename has spaces in it, then they should the URL encoded, like this:
#   http://localhost:8000/igvdata/Test%20IGV%20Server.xml
#
# * start an HTTP server (default is port 8000): cd $HOME && python -m SimpleHTTPServer
# * open a new version of IGV (this works with >= 2.3.90) and configure it to use this
#   local igv server:
#   View > Preferences > Advanced > Edit Server Properties
#   * Data Registry URL = http://localhost:8000/igvdata/$$_dataServerRegistry.txt
# * load your new data tracks: File > Load From Server...
# You should only have to do this configuration once.
# You should shutdown the SimpleHTTPServer when you are done (Ctrl-C).
#
# Next time you want to connect to the data:
# * cd $HOME && python -m SimpleHTTPServer
# * open IGV, and load your new data: File > Load From Server...
#
# Mark Cowley, 19/9/2016
##############################

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
        #Global.set("genome", genome)
        Global.set("version", "1")
        self.Global = Global
        self.URL_DURATION = URL_DURATION
        self.genome = genome
        self.project = project

    def addData(self):
        """Add all data within a DX project to this DxProjectRegistry instance, starting at top level"""
        self.addLevel(self.Global, "/")

    def addLevel(self, node, folder):
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
        #subfolders = subfolders - ("metrics", "assets")

        for subfolder in subfolders:
            subnode = SubElement(self.Global, "Category", name=subfolder)
            subnodepath = str(folder + "/" + subfolder).replace("//", "/")
            self.addLevel(subnode, subnodepath)

        dxfiles = list(dxpy.find_data_objects(
            recurse=False, folder=folder, return_handler=True, project=self.project.get_id())
        )
        for dxfile in dxfiles:
            if isinstance(dxfile, dxpy.DXFile):
                # n, ext = os.path.splitext(dxfile.name)
                if str(dxfile.name).endswith("bam"):
                    self.__addIndexedFile(dxfile, folder, node, ["bai"])
                elif str(dxfile.name).endswith("vcf.gz"):
                    self.__addIndexedFile(dxfile, folder, node, ["tbi", "idx"])
                elif str(dxfile.name).endswith("bw"):
                    self.__addNonIndexedFile(dxfile, folder, node)
                elif str(dxfile.name).endswith("bed.gz"):
                    self.__addNonIndexedFile(dxfile, folder, node)
                # mate the tdf up to its matching bam file.
                #elif str(dxfile.name).endswith("tdf"):
                #    self.__addNonIndexedFile(dxfile, folder, node)

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

        name = str(dxfile.name).replace("gvcf.gz", "g.vcf.gz").replace("merged.dedup.realigned.", "")
        file_url = dxfile.get_download_url(
            duration=self.URL_DURATION, filename=name, preauthenticated=True
        )

        index = None
        for index_ext in index_exts:
            index_name = dxfile.name + "." + index_ext
            print "Looking for index file: {}".format(index_name)
            index = dxpy.find_one_data_object(
                name=index_name, folder=folder, name_mode="exact", recurse=False,
                project=self.project.get_id(), zero_ok=True, return_handler=True
            )
            if not index is None:
                break
        if index is None:
            # raise dxpy.exceptions.DXSearchError("Could not find an index file for {}".format(dxfile.name))
            # raise RuntimeWarning("Skipping {}, failed to find an index file".format(dxfile.name))
            print "Skipping {}, failed to find an index file".format(dxfile.name)
            return None

        name = str(index.name).replace("gvcf.gz", "g.vcf.gz").replace("merged.dedup.realigned.", "")
        indel_url = index.get_download_url(
            duration=self.URL_DURATION, preauthenticated=True, filename=name
        )

        resource = SubElement(node, "Resource")
        resource.set("name", dxfile.name)
        resource.set("path", file_url[0])
        resource.set("index", indel_url[0])
        if "bai" in index_exts:
            tdf_names = [str(dxfile.name).replace(".bam", ".tdf"), dxfile.name + ".tdf"]
            tdf = None
            for tdf_name in tdf_names:
                print "Looking for tdf coverage file: {}".format(tdf_name)
                tdf = dxpy.find_one_data_object(
                    name=tdf_name, folder=folder, name_mode="exact", recurse=False,
                    project=self.project.get_id(), zero_ok=True, return_handler=True
                )
                if tdf:
                    break
            if tdf is not None:
                name = str(tdf.name).replace("gvcf.gz", "g.vcf.gz").replace("merged.dedup.realigned.", "")
                tdf_url = tdf.get_download_url(
                    duration=self.URL_DURATION, preauthenticated=True, filename=name
                )
                resource.set("coverage", tdf_url[0])
            else:
                resource.set("coverage", ".")
        if "tbi" in index_exts:
            resource.set("mapping", ".")

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

        name = str(dxfile.name).replace("gvcf.gz", "g.vcf.gz").replace("merged.dedup.realigned.", "")
        file_url = dxfile.get_download_url(
            duration=self.URL_DURATION, filename=name, preauthenticated=True
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

        manifests = []
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

    def addProjectToCache(self, project):
        self.projects.append(project)

    def updateCache(self):
        new_projects = self.newProjects()
        for project in new_projects:
            dxproj = DxProjectRegistry(project=project, genome="1kg_v37", URL_DURATION=86400)
            dxproj.addData()
            dxproj.writeXML()
            dxproj.writeRegistryTXT()
            self.addProjectToCache(project)

    def forceUpdate(self):
        os.chdir(self.root)
        for file in glob.glob("*.xml"):
            os.unlink(file)
        os.unlink(self.txt)
        self.projects = []
        self.updateCache()

    def updateProjects(self, project_ids, replace=False):
        first = True
        for project_id in project_ids:
            if "project-" in project_id:
                project = dxpy.DXProject(project_id)
            else:
                project = dxpy.DXProject(dxpy.find_one_project(name=project_id)["id"])
            reg = DxProjectRegistry(project=project, genome="1kg_v37", URL_DURATION=ONE_MONTH)
            if replace and first:
                reg.eraseRegistryTXT()
                first = False
            reg.addData()
            reg.writeXML()
            reg.writeRegistryTXT()
    
    def testUpdate(self):
        """Run a subset of projects"""
        # project_ids = (u'project-BzPb25j0627bFJv6q9g81ZX5', u'project-Bz6GbkQ0VGPv0fpqZZ6ZZGfx', u'project-Bb9KVk8029vp1qzXz4yx4xB3')
        # project_ids = (u'project-BzPb25j0627bFJv6q9g81ZX5', u'project-Bb9KVk8029vp1qzXz4yx4xB3')
        project_ids = (u'project-BzQ9qx80Y6qG6FF56Jq27145', u'project-BzPb25j0627bFJv6q9g81ZX5')  # NA12878 public
        self.updateProjects(project_ids)


# reg = IgvRegistry()
# reg.getProjects()
# reg.newProjects()
# reg.testUpdate()

ONE_HOUR = 3600
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7
ONE_MONTH = ONE_DAY * 31
ONE_YEAR = ONE_DAY * 365


def main(args):
    reg = IgvRegistry("/Users/marcow/igvdata", args.duration)

    if args.test:
        reg.testUpdate()
        import sys
        sys.exit(0)
    elif args.project_id:
        reg.updateProjects(args.project_id, args.force)
    elif args.force:
        reg.forceUpdate()
    elif args.update:
        reg.updateCache()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate an IGV registry, based on data that you can access in DNAnexus.',
        epilog="You will need to use a recent version IGV (> 2.3.90)."
    )

    parser.add_argument('-t', '--test', help='Test mode, over a few projects only', action='store_true')
    parser.add_argument('-f', '--force', help='Force recreation of registry', action='store_true')
    parser.add_argument('-u', '--update', help='Update registry', action='store_true')
    parser.add_argument('-p', '--project_id', action='append', type=str, required=False,
                        help='Update specific project_id(s). Can be specified any number of times')
    parser.add_argument('-d', '--duration', help='Duration to generate URLs for', type=int, required=False,
                        default=ONE_MONTH, nargs=1)
    args = parser.parse_args()
    main(args)
