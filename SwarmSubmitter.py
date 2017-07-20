# -*- coding: utf-8 -*-
"""
Created on Fri Jun 16 18:20:31 2017

@author: Sanket Gupte

"""

import threading
import os, sys
import errno


#semaphore = threading.Semaphore(20) # The number twenty here is the number of threads that can acquire the semaphore at one time. This limits the number of subprocesses that can be run at once.



#def run_command(cmd):
#    with semaphore:
#        return os.system(cmd)

class SwarmThread (threading.Thread):
    def __init__(self,semaphore,XConn,name, fs_path,fs_fname,xnat_path):#threadID, name, cmd_str):
        self.semaphore=semaphore
        self.XConn=XConn
        threading.Thread.__init__(self)
        #self.threadID = threadID
        self.name = name
        self.fs_path=fs_path
        self.fs_fname=fs_fname
        self.xnat_path=xnat_path
        
        
    def download_files(self,cmd):
        with self.semaphore:
            print(cmd)
            if self.create_local_dirs():
                self.download_from_xnat()
            return 0
#            return os.system(cmd)
    def create_local_dirs(self):
        """
        Make the directory structure according to the fs_path
        """
        print("Making::" +self.fs_path)
        
        dir_success=True   #Assuming creating directory was a success, unless otherwise changed
        if not os.path.exists(self.fs_path):
            try:
                #detail_logger.info("Creating Directories if needed")
                os.makedirs(self.fs_path)
            except os.error as e:
                if e.errno ==errno.EEXIST:
                    #raise     #Only raises errors that are not of the type File exist (Redundant check)
                    #print "Path already Exists. No need to create it."
                    pass

                elif e.errno ==13:
                    dir_success=False
                    #detail_logger.error("You do not have permission to create this directory")
                    #print "You do not have permission to create this directory"
                else:
                    #print "Something went wrong with creating this directory"
                    dir_success=False
                    #detail_logger.error("Something went wrong with Creating this directory this directory")
                    #detail_logger.error(str(e.errno))
                    #detail_logger.error(str(e.message))
        return dir_success
        
    def download_from_xnat(self):
        """
        Download all the files at location xnat_path as fs_fname
        """
        print("Downloading now !!")
        self.XConn.getZip(self.xnat_path+"/resources/DICOM",self.fs_path,self.fs_fname)
        
    def splitRestPath(self,xnat_path):
        """
        /data/archive/projects/483/subjects/126176/experiments/126176-1/scans/1
        """
        return xnat_path[14:].split('/')[1::2]  #Getting just the values 
    def make_sym_links_from_xnat(self):
        pass
        
    def run(self):
        print ("Starting " + self.name)
        status=self.download_files("self.cmd_str")
        
        if status!=0:   #0 = Success , 1=Warning , rest=other errors
            print ("Some Error")
        
        print ("Exiting " + self.name)
        
class SwarmJob:
    """
    Class for submitting jobs in parallel
    """
    def __init__(self,XConn,MaxThreads):
        """
        XConn is an object of "XnatRest" type
        """
        self.XConn=XConn
        self.semaphore=threading.Semaphore(MaxThreads)
        self.swarmThreads=[]
        
    def addJob(self,d_format,fs_path,fs_fname,xnat_path,cmd,downld_no):
        """
        xnat_path is a full REST path of the resource to download
        """
        print(fs_path)
        print(fs_fname)
        print(xnat_path)
#        print(cmd)
#        print(downld_no)
        sThread=SwarmThread(self.semaphore,self.XConn,downld_no,fs_path,fs_fname,xnat_path)
        self.swarmThreads.append(sThread)
        #print(self.XConn.getProjects())
        
        
    def RunSwarm(self):
        
        """Start Script
        """
        #Start the threads
        for t in self.swarmThreads:
            t.start()
            
        # Wait for all threads to complete
        for t in self.swarmThreads:
            t.join()
        print ("Exiting Main Thread")
    
if __name__=="__main__":
    print ('This cannot be run by itself. import the classes')

#    parser = argparse.ArgumentParser(description='Program to run Swarm Jobs')    
#    parser.add_argument('file-loc', help='/loc/of/file.batch') #This is the name of the shell script , My-process.sh or whatever
#    args = parser.parse_args()
#    #swarm=SwarmJob(args)
#    #status=swarm.RunSwarm()
    sys.exit(0)
