#!/usr/bin/env python

# Script to create an IGV server registry to access data stored on DNAnexus
#
# It creates one XML file for each DX project, and records these in a
# registry $$_dataServerRegistry.txt
# $$ is substituted by IGV based on the selected reference ref_genome.
#
# See Readme.md, and Readme.Developer.md for more information
#
# Mark Cowley, 31/1/2017
##############################

import argparse
import glob
import os
import shutil
import grp
from urllib import quote
from xml.etree.ElementTree import ElementTree, Element, SubElement, tostring
import xml.dom.minidom
import dxpy
import sys
import socket

ONE_HOUR = 3600
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7
ONE_MONTH = ONE_DAY * 31
ONE_YEAR = ONE_DAY * 365

class DxDataset(object):
    """
    Represent an DX Project as an IGV dataset, in XML format
    """

    def __init__(self, project, ref_genome="1kg_v37", url_duration=ONE_YEAR):
        """
        :param project: 
        :param ref_genome: 
        :param url_duration: number of seconds for which the generated URL will be valid 
        """
        if isinstance(project, dxpy.DXProject):
            pass
        elif project.startswith("project-"):
            project = dxpy.DXProject(project)
        else:
            project = dxpy.DXProject(dxpy.find_one_project(name=project)["id"])

        assert isinstance(project, dxpy.DXProject)
        self.project = project

        Global = Element('Global')
        Global.set("name", project.name)
        Global.set("version", "1")
        self.Global = Global
        self.url_duration = url_duration
        self.genome = ref_genome

    def addData(self):
        """
        Recursively add all data within a DX project to this DxDataset instance, starting at top level
        """
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

        print("Adding {}:{}".format(self.project.name, folder))
        subfolders = dxpy.api.project_list_folder(self.project.id, input_params={"folder": folder, "describe": {
            "fields": {"id": True, "name": True, "class": True}}, "only": "folders", "includeHidden": False},
                                                  always_retry=True)["folders"]
        subfolders = [os.path.basename(subfolder) for subfolder in subfolders]
        subfolders = list(set(subfolders) - set(("metrics", "inputFastq", "reports")))

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
                elif str(dxfile.name).endswith("seg"):
                    self.__addNonIndexedFile(dxfile, folder, node)
                elif str(dxfile.name).endswith("cn"):
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
        print("Adding {}:{}/{}".format(self.project.name, folder, dxfile.name))
        assert isinstance(dxfile, dxpy.DXFile)

        name = str(dxfile.name).replace("gvcf.gz", "g.vcf.gz").replace("merged.dedup.realigned.", "")
        file_url = dxfile.get_download_url(
            duration=self.url_duration, filename=name, preauthenticated=True
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
            print("Skipping {}, failed to find an index file".format(dxfile.name))
            return None

        name = str(index.name).replace("gvcf.gz", "g.vcf.gz").replace("merged.dedup.realigned.", "")
        indel_url = index.get_download_url(
            duration=self.url_duration, preauthenticated=True, filename=name
        )

        resource = SubElement(node, "Resource")
        resource.set("name", dxfile.name)
        resource.set("path", file_url[0])
        resource.set("index", indel_url[0])
        if "bai" in index_exts:
            tdf_names = [str(dxfile.name).replace(".bam", ".tdf"), dxfile.name + ".tdf"]
            tdf = None
            for tdf_name in tdf_names:
                print("Looking for tdf coverage file: {}".format(tdf_name))
                tdf = dxpy.find_one_data_object(
                    name=tdf_name, folder=folder, name_mode="exact", recurse=False,
                    project=self.project.get_id(), zero_ok=True, return_handler=True
                )
                if tdf:
                    break
            if tdf is not None:
                name = str(tdf.name).replace("gvcf.gz", "g.vcf.gz").replace("merged.dedup.realigned.", "")
                tdf_url = tdf.get_download_url(
                    duration=self.url_duration, preauthenticated=True, filename=name
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
        print("Adding {}:{}/{}".format(self.project.name, folder, dxfile.name))
        assert isinstance(dxfile, dxpy.DXFile)

        name = str(dxfile.name).replace("gvcf.gz", "g.vcf.gz").replace("merged.dedup.realigned.", "")
        file_url = dxfile.get_download_url(
            duration=self.url_duration, filename=name, preauthenticated=True
        )

        resource = SubElement(node, "Resource")
        resource.set("name", dxfile.name)
        resource.set("path", file_url[0])

    def getXmlPath(self, folder):
        filename = self.project.name + ".xml"
        return os.path.join(folder, filename)

    def writeXML(self, folder):
        """
        Pretty print the XML tree.
        :return: str representing the path to the XML file
        """
        file_path = self.getXmlPath(folder)
        rough_string = tostring(self.Global, 'utf-8', method="xml")
        reparsed = xml.dom.minidom.parseString(rough_string)

        with open(file_path, "w") as text_file:
            text_file.write(reparsed.toprettyxml(indent="\t", encoding='utf-8'))

        # ElementTree(self.Global).write(filename, encoding="utf-8", xml_declaration=True)
        print("'%s' successfully created!" % file_path)
        return file_path


def touch(path):
    """
    Update the timestamp on a file. If necessary it will be created.
    """
    with open(path, 'a'):
        os.utime(path, None)

class IgvRegistry(object):
    def __init__(self, ref_genome="1kg_v37",
                 folder=os.path.join(os.path.expanduser('~'), "igvdata"),
                 url_root='http://localhost:8000/igvdata',
                 url_duration=ONE_YEAR,
                 group=None):
        """
        An IgvRegistry is a TXT file, pointing to XML files representing Datasets to be loaded into IGV.
        The TXT file lives on a web server (within `folder`), and is accessible via a url (`url_root` + TXT).
        
        IGV should be configured to point to <url_root>/$$_dataServerRegistry.txt (View > Preferences... > Advanced)
        
        :param ref_genome: reference genome name, as per IGV naming scheme. We use b37d5/hs37d5, which IGV calls "1kg_v37"
        :param folder: root folder where the IgvRegistry files live. There can be >1 registry TXT file if there are >1
         ref_genome's used
        :param url_root: the web url prefix, representing the web-accessible URL to `folder` 
        :param url_duration: default duration to create web URLs for.
        :param group: Group represents a way to share data with a specific research group. Eg LKCGP. if group is specified,
        then the XML and TXT registry files will be found within url_root + group. The first time that a group is made,
        an .htaccess file is made
        """
        self.group = group
        self.ref_genome = ref_genome
        self.txt = self.ref_genome + "_dataServerRegistry.txt"
        self.url_duration = url_duration
        
        if self.group:
            assert self.group == quote(self.group)
            self.folder = os.path.join(folder, group)
            self.url_root = os.path.join(url_root, group)
        else:
            self.folder = folder
            self.url_root = url_root
        
        self.path = os.path.join(self.folder, self.txt)
        self.initialise_folder()
        
        self.projects = []
        self.updateCache()

    def initialise_folder(self):
        """
        initialise an IgvRegistry folder. it will create an .htaccess file
        """
        if not os.path.exists(self.folder):
            print("Initialising " + self.folder)
            os.mkdir(self.folder)
            self.write_htaccess_file()
        touch(self.path)
        if self.ref_genome == "1kg_v37":
            for alias in ("hg19", "b37"):
                if not os.path.exists(self.path.replace(self.ref_genome, alias)):
                    os.symlink(self.path, self.path.replace(self.ref_genome, alias))

    def write_htaccess_file(self):
        assert self.group is not None
        htpasswd_path = '/home/ubuntu/.htpasswd_{}\n'.format(self.group)
        htaccess_path = os.path.join(self.folder, ".htaccess")
        with open(htaccess_path, 'w') as htaccess:
            print("Initialising Apache folder-level security for " + htaccess_path)
            htaccess.write('AuthUserFile ' + htpasswd_path)
            htaccess.write('AuthName "{}"\n'.format(self.group))
            htaccess.write('AuthType Basic\n')
            htaccess.write('Require valid-user\n')
        print("Configured .htaccess security, within " + htaccess_path)

        touch(htpasswd_path)
        print("Configured empty .htpasswd file: " + htpasswd_path)
        
        # setup htpasswd file's security
        # Alas, the ubuntu user is not a member of www-data...
        # os.chown(htpasswd_path, -1, grp.getgrnam('www-data').gr_gid )
        # os.chmod(htpasswd_path, 640)
        print("Also, you'll need to set the group and permissions on the .htpasswd file:")
        print("sudo chgrp www-data {}".format(htpasswd_path))
        print("chmod 640 {}".format(htpasswd_path))

        print("You need to add username:password entries to " + htpasswd_path)
        print("Visit http://www.htaccesstools.com/htpasswd-generator/ to generate passwords")
        

    def updateCache(self):
        manifests = []
        os.chdir(self.folder)
        for file in glob.glob("*.xml"):
            manifests.append(str(file).replace(".xml", ""))
        self.projects = manifests

    def getProjects(self):
        return self.projects

    def addProjects(self, project_ids):
        """
        The main workhorse function. For a given list of project_ids, create an XML manifest for each, and add them to
        the registry.
        :param project_ids: list of project-id's, either by their name, or their project-id
        """
        for project_id in project_ids:
            dx_project = DxDataset(project=project_id, ref_genome=self.ref_genome, url_duration=self.url_duration)
            dx_project.addData()
            xml_path = dx_project.writeXML(self.folder)
            self.addDxDataset(dx_project.project, xml_path)

    def addDxDataset(self, project, xml_path):
        xml_relative_path = xml_path.replace(self.folder, '')
        #print("registry root path: {}\nxml_path: {}\nxml_relative_path: {}\nurl_root: {}".format(self.folder, xml_path, xml_relative_path, self.url_root))
        url = self.url_root + xml_relative_path
        url = quote(url, safe="%/:=&?~#+!$,;'@()*[]")
        print("Adding {} to registry at {}".format(url, self.path))

        if os.path.exists(self.path):
            with open(self.path, "r") as myregistry:
                urls = set(myregistry.read().splitlines()) - set([''])
        else:
            urls = set()

        urls.add(url)
        urls = list(urls)
        urls.sort()

        with open(self.path, "w") as myregistry:
            for url in urls:
                myregistry.write(url + '\n')
        self.addProjectToCache(project)

    def addProjectToCache(self, project):
        """The cache represents an in-memory set of projects within the Registry."""
        self.projects.append(project)

    def findNewProjects(self):
        """
        Find projects available on DNAnexus, not present in the local cache
        :return: string array of project names.
        """
        dx_projects = list(dxpy.find_projects(return_handler=True))
        dx_project_names = [project.name for project in dx_projects]
        new_dx_projects = list(set(dx_project_names) - set(self.getProjects()))
        new_dx_projects = [x for x in new_dx_projects if not x.startswith('PIPELINE') and not x.endswith('resources')]
        print("Found {} new projects on DNAnexus, for {}".format(len(new_dx_projects), dxpy.whoami()))
        return new_dx_projects

    def forceUpdate(self, existing_only=False):
        projects = self.projects
        os.chdir(self.folder)
        for file in glob.glob("*.xml"):
            os.unlink(file)
        self.eraseRegistryTXT()
        if not existing_only:
            projects = self.findNewProjects()
        self.addProjects(projects)

    def eraseRegistryTXT(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def testUpdate(self):
        """Run a subset of projects"""
        # project_ids = (u'project-BzPb25j0627bFJv6q9g81ZX5', u'project-Bz6GbkQ0VGPv0fpqZZ6ZZGfx', u'project-Bb9KVk8029vp1qzXz4yx4xB3')
        # project_ids = (u'project-BzPb25j0627bFJv6q9g81ZX5', u'project-Bb9KVk8029vp1qzXz4yx4xB3')
        project_ids = (u'project-BzQ9qx80Y6qG6FF56Jq27145', u'project-BzPb25j0627bFJv6q9g81ZX5')  # NA12878 public
        self.addProjects(project_ids)

# TESTING
#
# from dx_igv_registry import *
# reg = IgvRegistry()
# reg.getProjects()
# # reg.findNewProjects()  # >180 projects, so this takes some time.
# reg.testUpdate()

# from dx_igv_registry import *
# reg = IgvRegistry("1kg_v37", '/Users/marcow/var/www/html/igvdata/', 'https://seave.bio/igvdata/', ONE_DAY)
# reg.getProjects()
# reg.testUpdate()
# with open('/Users/marcow/var/www/html/igvdata/1kg_v37_dataServerRegistry.txt', "r") as myregistry:
#    myregistry.readlines()

def main(args):
    assert(args.ref_genome in ["1kg_v37", "mm10", "hg19"])

    if args.xml_only:
        """Only create the XML file in current working dir. Don't add it to a registry"""
        for project_id in args.project_ids:
            dx_project = DxDataset(project=project_id, ref_genome=args.ref_genome, url_duration=args.duration)
            dx_project.addData()
            xml_path = dx_project.writeXML(".")
            print("Wrote {} ({}) to {}".format(dx_project.project.name, dx_project.project.id, xml_path))
    else:
        """Create an XML manifest, and add it to an Igv Data Server registry"""
        hostname = socket.gethostname()
        if not args.igvdata_path or not args.igvdata_url:
            if hostname == 'ip-172-31-59-137':
                args.igvdata_url = 'https://seave.bio/igvdata'
                args.igvdata_path = '/var/www/html/igvdata/'
            elif hostname == 'ip-172-31-50-139':
                args.igvdata_url = 'https://dev.seave.bio/igvdata'
                args.igvdata_path = '/var/www/html/igvdata/'
            else:
                # args.igvdata_path = '~/var/www/html/igvdata'  # local testing of Seave mode
                args.igvdata_path = os.path.join(os.path.expanduser('~'), "igvdata")
                args.igvdata_url = 'https://localhost:8000/igvdata/'
        os.path.exists(args.igvdata_path) or os.mkdir(args.igvdata_path)
        print("See Readme.Developer.md to set the permissions of this folder properly.")

        reg = IgvRegistry(ref_genome=args.ref_genome, folder=args.igvdata_path, url_root=args.igvdata_url,
                          url_duration=args.duration, group=args.group)

        if args.project_ids:
            reg.addProjects(args.project_ids)
        elif args.test:
            reg.testUpdate()
            sys.exit(0)
        elif args.force:
            reg.forceUpdate()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate an IGV registry, based on data that you can access in DNAnexus.',
        epilog="You will need to use a recent version of IGV (> 2.3.90)."
    )

    parser.add_argument('-p', '--project_id', dest='project_ids', action='append', type=str, required=False,
                        help='Update specific project_id(s), or project_name(s). Can be specified any number of times')
    parser.add_argument('-g', '--group', help='Remote IGV server Group to associate data with', type=str,
                        required=False)
    parser.add_argument('-d', '--duration', help='Duration to generate URLs for, in seconds', type=int, required=False,
                        default=ONE_YEAR)
    parser.add_argument('-r', '--ref_genome', help="reference ref_genome build (eg 1kg_v37, mm10, hg19)", type=str,
                        default="1kg_v37")
    parser.add_argument('-x', '--xml_only', help='[Advanced] Create an XML file, but dont add it to a registry', 
                        action='store_true')
    parser.add_argument('--igvdata_path', help='[Advanced] Override the path to local igvdata', type=str, required=False)
    parser.add_argument('--url', help='[Advanced] Override the web accessible URL to igvdata', type=str, required=False)
    parser.add_argument('-t', '--test', help='Test mode, over a few projects only', action='store_true')
    parser.add_argument('-f', '--force', help='Force recreation of XML files within a registry', action='store_true')

    args = parser.parse_args()
    main(args)
