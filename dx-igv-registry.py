#!/usr/bin/env python

# Script to create an IGV session for a WGS sequencing project on dx
# usage
# python dx-igv-registry.py
# python -m SimpleHTTPServer 8000
#
import dxpy
from urllib import quote
import os
from xml.etree.ElementTree import ElementTree, Element, SubElement
from xml.dom import minidom


class DxProjectRegistry(object):
    """Represent an DX Project as an IGV registry (XML)"""

    def __init__(self, project, genome="1kg_v37", URL_DURATION=86400):
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
        # @TODO - how to do this with dxpy?
        subfolders = os.popen(
            "dx ls --folders {} | sed 's|/$||'".format(self.project.get_id() + ":" + folder)).read().splitlines()
        for subfolder in subfolders:
            subnode = SubElement(self.Global, "Category", name=subfolder)
            subnodepath = str(folder + "/" + subfolder).replace("//", "/")
            self.addLevel(subnode, subnodepath)

        files = list(dxpy.find_data_objects(
            recurse=False, folder=folder, return_handler=True, project=self.project.get_id())
        )
        for file in files:
            if isinstance(file, dxpy.DXFile):
                n, ext = os.path.splitext(file.name)
                # if ext[1:] in ("bam", "vcf", "gz", "bed"):
                if ext[1:] == "bam":
                    print "Adding {}:{}/{}".format(self.project.name, folder, file.name)
                    # print "file_id: {}:{}".format(project.id, file.id)

                    BAM_dx = file
                    # BAM_url = BAM_dx.get_download_url(duration=self.URL_DURATION, preauthenticated=True, 
                    # project=project.id)
                    BAM_url = BAM_dx.get_download_url(
                        duration=self.URL_DURATION, filename=BAM_dx.name, preauthenticated=True
                    )

                    bai_name = file.name + ".bai"
                    BAI_dx = dxpy.find_one_data_object(
                        zero_ok=False, name=bai_name, folder=folder, name_mode="exact", return_handler=True,
                        project=self.project.get_id()
                    )
                    # BAI_url = BAI_dx.get_download_url(duration=self.URL_DURATION, preauthenticated=True, 
                    # filename=bai_name, project=project.id)
                    BAI_url = BAI_dx.get_download_url(
                        duration=self.URL_DURATION, preauthenticated=True, filename=BAI_dx.name
                    )

                    BAM_Resource = SubElement(node, "Resource")
                    BAM_Resource.set("name", file.name)
                    BAM_Resource.set("path", BAM_url[0])
                    BAM_Resource.set("index", BAI_url[0])

                    # for debugging, just save the first BAM.
                    if debug:
                        break

    def getXmlName(self):
        filename = self.genome + "." + self.project.name + ".xml"
        return filename

    def writeXML(self):
        filename = self.getXmlName
        ElementTree(self.Global).write(filename, encoding="utf-8", xml_declaration=True)
        print "'%s' successfully created!" % filename

    def writeRegistryTXT(self, filename="registry.txt"):
        with open(filename, "a") as myfile:
            url = quote("http://localhost:8000/" + self.getXmlName(), safe="%/:=&?~#+!$,;'@()*[]")
            myfile.writelines(url)


def test():
    ##### TEST
    os.unlink("registry.txt")
    project_ids = (u'project-Bz6GbkQ0VGPv0fpqZZ6ZZGfx', u'project-Bb9KVk8029vp1qzXz4yx4xB3')
    for project_id in project_ids:
        project = dxpy.DXProject(project_id)
        reg = DxProjectRegistry(project=project, genome="1kg_v37", URL_DURATION=86400)
        reg.addData(debug=True)
        reg.writeXML()
        reg.writeRegistryTXT("registry.txt")
    import sys
    sys.exit(0)


test()

URL_DURATION = 86400

# if os.exists("registry.txt"):
#    os.unlink("registry.txt")
starting_project = dxpy.WORKSPACE_ID
projects = list(dxpy.find_projects(return_handler=True))
print "Found {} projects, for {}".format(len(projects), dxpy.whoami())
# project_ids = [project["id"] for project in projects]
# for project_id in project_ids:
#    project = dxpy.DXProject(project_id)
for project in projects:
    reg = DxProjectRegistry(project=project, genome="1kg_v37", URL_DURATION=86400)
    reg.addData(debug=True)
    reg.writeXML()
    reg.writeRegistryTXT("registry.txt")
