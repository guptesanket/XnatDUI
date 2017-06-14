# -*- coding: utf-8 -*-
"""
Created on Wed Jun  7 15:13:15 2017

@author: guptess
"""
import requests

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
        for proj in projects:
            proj_ids.append(proj['ID'])
        return proj_ids
        
    def getSubjects(self,proj):
        """
       {'ID': 'Cerebra_S02566',
        'URI': '/data/subjects/Cerebra_S02566',
        'insert_date': '2016-07-27 13:27:23.636',
        'insert_user': 'moynihanbt',
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
        {'ID': 'Cerebra_E03214',
            'URI': '/data/experiments/Cerebra_E03214',
            'date': '2017-02-23',
            'insert_date': '2017-03-02 09:57:35.695',
            'label': '185574-1',
            'project': '457',
            'xnat:subjectassessordata/id': 'Cerebra_E03214',
            'xsiType': 'xnat:mrSessionData'}
        """
        return self.get(proj,subj)
    def getScans(self,proj,subj,exp):
        """
        {'ID': '1',
          'URI': '/data/experiments/Cerebra_E03214/scans/1',
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
            
    def getResourceFiles(self,proj=None,subj=None,exp=None,scan=None,resid=None,download=False):
        """
        Does a GET request according to the query
        r=XCon._get("https://cerebra.nida.nih.gov/data/archive/projects/186/subjects/185861/experiments/185861-1PRE/resources/MRSI/files")
        r=XCon._get("https://cerebra.nida.nih.gov/data/archive/projects/186/subjects/185861/experiments/185861-1PRE/scans/3/resources/DICOM/files")
        
        """
        #resid cannot be None
        if not resid:
            return []
        
        if download: #If true, will download as a zip. This doesn't work yet.
            tail="?format=zip"
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
            return 0
            #sys.exit(1)
        return r

    def _put(url,**kwargs):
        """
        Does a PUT on the url
        """
        try:
            r = self.intf.get( url, **kwargs )
            r.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.RequestException) as e:
            print ("Request Failed")
            print ("    " + str( e ))
            sys.exit(1)
        return r

    def putFile():
        queryArgs = {"format":"csv","content":"QC Data","reference":os.path.abspath(os.path.join(dicomdir, f_name))}
        r = self.intf.put(host + "/data/experiments/%s/resources/QC/files" % (session), params=queryArgs)
        r.raise_for_status()