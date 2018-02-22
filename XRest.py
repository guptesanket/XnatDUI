# -*- coding: utf-8 -*-
"""
Created on Wed Jun  7 15:13:15 2017

@author: Sanket Gupte

A Simple Wrapper class for talking to Xnat using REST via requests package
"""
import requests
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import ConnectionError

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

CHUNKSIZE=2048 #After trying 512,1024,2048,4096, 8192 - There is no considerable impact in speed after 2048

class XnatRest:
    def __init__(self,host,user,passwd,verify=True):
        # Set up session
        if host[-1]=='/':
            self.host=host[:-1]
        else:
            self.host=host
        self.user=user
        self.passwd=passwd
        self.verify=verify
        #self.xnat_session=None
        self.intf = requests.Session()
        self.intf.verify = False
        self.intf.auth = (self.user,self.passwd)
        
    def refresh(self):
        """
        Refreshes http connection to url
        """
        self.intf=None
        self.__init__(self.host,self.user,self.passwd,self.verify)

    def getProjects(self):
        projects=self.get()
        proj_ids=[]
        if projects==0:
            return False
        for proj in projects:
            proj_ids.append(proj['ID'])
        return proj_ids
        
    def getSubjects(self,proj):
        """
       {'ID': 'Xnat_S02566',
        'URI': '/data/subjects/Xnat_S02566',
        'insert_date': '2016-07-27 13:27:23.636',
        'insert_user': 'moynihan',
        'label': '184612',
        'project': '000'},
        """
        return self.get(proj)
#        subjects =self.get(proj)
#        ret_subs=[]
#        for sub in subjects:
#            ret_subs.append({'ID':sub['ID'],'label':sub['label']})
#        return ret_subs
    def getExperiments(self,proj,subj):
        """
        {'ID': 'Xnat_E03214',
            'URI': '/data/experiments/Xnat_E03214',
            'date': '2017-02-23',
            'insert_date': '2017-03-02 09:57:35.695',
            'label': '185574-1',
            'project': '457',
            'xnat:subjectassessordata/id': 'Xnat_E03214',
            'xsiType': 'xnat:mrSessionData'}
        """
        return self.get(proj,subj)
    def getScans(self,proj,subj,exp):
        """
        {'ID': '1',
          'URI': '/data/experiments/Xnat_E03214/scans/1',
          'note': '',
          'quality': 'unknown',
          'series_description': 'localizer',
          'type': 'localizer',
          'xnat_imagescandata_id': '45077',
          'xsiType': 'xnat:mrScanData'},
        """
        return self.get(proj,subj,exp)
    def getQualityLabels(self):
        """
        The url "/REST/config/scan-quality/labels" stores all sitewide scan quality labels. 
        {'ResultSet': {'Result': [{'contents': 'unknown,usable,questionable,unusable\n',
            'create_date': '2014-03-10 14:00:36.086',
            'path': 'labels',
            'project': '',
            'reason': '',
            'status': 'enabled',
            'tool': 'scan-quality',
            'unversioned': 'true',
            'user': 'admin',
            'version': '1'}]}}
        """
        url="/REST/config/scan-quality/labels"
        result=self._get(self.host+url)
        try:
            result.json()['ResultSet']['Result']
        except:
            return 0
        
        labels=result.json()['ResultSet']['Result'][0]['contents']
        if labels[-1]=='\n':
            return labels[:-1].split(",")
        else:
            return labels.split(",")
    def get(self,proj=None,subj=None,exp=None,scan=None):
        """
        Does a GET request according to the query
        """
        tail="?format=json"
        if proj==None:
            url="/data/archive/projects"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif subj==None:
            url="/data/archive/projects/"+proj+"/subjects"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif exp==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif scan==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/scans"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
            
    def getResourcesList(self,proj=None,subj=None,exp=None,scan=None):
        """
        Gets a list of resources for the level specified last
        """
        """
        When pulling session resources
        [{'content': 'QC Data', 'tags': '', 
        'cat_id': 'Xnat_E03541', 
        'element_name': 'xnat:resourceCatalog', 
        'category': 'resources', 'file_size': '756', 
        'xnat_abstractresource_id': '64655', 
        'file_count': '1', 'label': 'QC', 
        'format': 'csv', 'cat_desc': ' '}]
            
        For scan resources
        [{'content': 'RAW', 'tags': '', 'cat_id': '11', 
        'element_name': 'xnat:resourceCatalog', 'category': 'scans', 
        'file_size': '137058630', 'xnat_abstractresource_id': '17972', 
        'file_count': '275', 'label': 'DICOM', 'format': 'DICOM', 
        'cat_desc': 'EP_Prediction_v1.0'}]
        """
        tail="?format=json"
        if proj==None:
            url="/data/archive/projects"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif subj==None:
            url="/data/archive/projects/"+proj+"/resources"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif exp==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/resources"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif scan==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/resources"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif scan is not None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/scans/"+scan+"/resources"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
            
    def getScanResources(self,proj,subj,exp,scan):
        """
        Separate method just for scan, to speed it up
        """
        result=self._get(self.host+"/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/scans/"+scan+"/resources?format=json")
        if result==0:
            return 0
        else:
            return result.json()['ResultSet']['Result']
            
    def getResourceFiles(self,proj=None,subj=None,exp=None,scan=None,resid=None,download=False):
        """
        Does a GET request according to the query
        r=XCon._get("https://Xnat.nih.gov/data/archive/projects/186/subjects/185861/experiments/185861-1PRE/resources/MRSI/files")
        r=XCon._get("https://Xnat.nih.gov/data/archive/projects/186/subjects/185861/experiments/185861-1PRE/scans/3/resources/DICOM/files")
        
        """
        """
        When Getting a session resource 
        [{'Name': 'QC-v1_0-20170621.csv', 
        'file_content': 'QC Data', 'cat_ID': '65429', 
        'collection': 'QC', 'file_format': 'csv', 
        'file_tags': '',
        'URI': '/data/projects/483/subjects/Xnat_S00573/experiments/Xnat_E03472/resources/65429/files/QC-v1_0-20170621.csv', 
        'Size': '756'}]
        """
        #resid cannot be None
        if not resid:
            return []
        
        if download: #If true, will download as a zip. This doesn't work yet.
            tail="?format=zip"  ##Made a separate Download Function. Wont need this
        else:        #Else will give a list of files
            tail="?format=json"
        if proj==None:
            url="/data/archive/projects"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif subj==None:
            url="/data/archive/projects/"+proj+"/resources/"+resid+"/files"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif exp==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/resources/"+resid+"/files"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif scan==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/resources/"+resid+"/files"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif scan is not None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/scans/"+scan+"/resources/"+resid+"/files"
            result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']

    def _get(self,url):
        """
        Does a GET on the url
        """
        try:
            r = self.intf.get(url)
            r.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.RequestException) as e:
            print ("Request Failed")
            print ("    " + str( e ))
            print ("    Please Check Username/Password")
            print ("    Make sure you are connected to the Internet/VPN")
            return 0
            #sys.exit(1)
        return r
    
    def getZip(self,url,fs_path,fs_fname):
        """
        Works for scan level
        """
        tail="/files?format=zip"
        try:
            #print("URL:  "+self.host+url+tail)
            response = self.intf.get(self.host+url+tail,stream=True)
            #print (response.status_code)
            if response.status_code !=200:
                #Return something meaningful so the program knows.
                print("Oops Error Code: %s"%response.status_code)
                #print(url)
                return False
            else:
                # Get the content length if available
                #content_length = response.headers.get('Content-Length', -1)
                #if isinstance(content_length,str):
                #    content_length=int(content_length)
                fd= open(os.path.join(fs_path,fs_fname),"wb")
                #Use bytes_read for progress bar
                #bytes_read=0
                for chunk in response.iter_content(chunk_size=CHUNKSIZE):
                    if chunk: #Filter out keep-alive new chunks
                        if chunk[0] == '<' and chunk.startswith(('<!DOCTYPE', '<html>')):#bytes_read==0 and chunk[0] == '<' and chunk.startswith(('<!DOCTYPE', '<html>')):
                            print("Invalid response from XNAT")
                        #bytes_read += len(chunk)
                        fd.write(chunk)
                fd.close()
                return True
            
        except Exception as inst:
            print(inst)
            return False
#        except :
#           print("Something went wrong")
            
    def putResourceFile(self,proj=None,subj=None,exp=None,scan=None,resid=None,file_path=None):#,download=False):
        """
        Does a PUT request according to the query
        
        """
        result=0 #Remove this line
        if not file_path: #This shouldn't happen. Unless something is really messed up
            return 0
        else:
            queryArgs = {"content":resid,"reference":os.path.abspath(file_path)}
        if proj==None:
            url="/data/archive/projects"
            #result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif subj==None:
            url="/data/archive/projects/"+proj+"/resources/"+resid+"/files"
            #result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif exp==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/resources/"+resid+"/files"
            #result=self._get(self.host+url+tail)
            print(url)
            print(queryArgs)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif scan==None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/resources/"+resid+"/files"
            #result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
        elif scan is not None:
            url="/data/archive/projects/"+proj+"/subjects/"+subj+"/experiments/"+exp+"/scans/"+scan+"/resources/"+resid+"/files"
            #result=self._get(self.host+url+tail)
            if result==0:
                return 0
            else:
                return result.json()['ResultSet']['Result']
            


    def _put(self,url,**kwargs):
        """
        Does a PUT on the url
        """
        if kwargs["proj"]==None:
            print("Nooo")
            
        for key in kwargs:
            print("{} and {}".format(key,kwargs[key]))
#        try:
#            r = self.intf.put( url, **kwargs )
#            r.raise_for_status()
#        except (requests.ConnectionError, requests.exceptions.RequestException) as e:
#            print ("Request Failed")
#            print ("    " + str( e ))
#            #sys.exit(1)
#        return r

    def putFile():
        queryArgs = {"format":"csv","content":"QC Data","reference":os.path.abspath(os.path.join(dicomdir, f_name))}
        r = self.intf.put(host + "/data/experiments/%s/resources/QC/files" % (session), params=queryArgs)
        r.raise_for_status()