# -*- coding: utf-8 -*-
"""
Created on Fri Jun 16 18:20:31 2017

@author: Sanket Gupte

"""

import threading
import os, sys
import argparse


#semaphore = threading.Semaphore(20) # The number twenty here is the number of threads that can acquire the semaphore at one time. This limits the number of subprocesses that can be run at once.



#def run_command(cmd):
#    with semaphore:
#        return os.system(cmd)

class SwarmThread (threading.Thread):
    def __init__(self,semaphore,name, cmd_str):#threadID, name, cmd_str):
        self.semaphore=semaphore
        threading.Thread.__init__(self)
        #self.threadID = threadID
        self.name = name
        self.cmd_str = cmd_str
        
    def run_command(self,cmd):
        with self.semaphore:
            print(cmd)
            return 0
#            return os.system(cmd)
        
    def run(self):
        print ("Starting " + self.name)
        status=self.run_command(self.cmd_str)
        
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
        print(fs_path)
        print(fs_fname)
        print(xnat_path)
#        print(cmd)
#        print(downld_no)
        sThread=SwarmThread(self.semaphore,downld_no,cmd)
        self.swarmThreads.append(sThread)
        #print(self.XConn.getProjects())
        
        
    def RunSwarm(self):
        
        """Start Script
        """
        
#        threads=[]
#        Num=0
#    
#        subjects= [] #insert subject IDs here (ARC numbers probably)
#        
#        print (sys.argv[1])
#        for sub in subjects:
#            thread = myThread(Num,sys.argv[1]+' '+sub)
#            Num=Num+1
#            threads.append(thread)
    
        #Start the threads
        for t in self.swarmThreads:
            t.start()
            
        # Wait for all threads to complete
        for t in self.swarmThreads:
            t.join()
        print ("Exiting Main Thread")
    
if __name__=="__main__":
    print ('Going in Main')

    parser = argparse.ArgumentParser(description='Program to run Swarm Jobs')    
    parser.add_argument('file-loc', help='/loc/of/file.batch') #This is the name of the shell script , My-process.sh or whatever
    args = parser.parse_args()
    swarm=SwarmJob(args)
    status=swarm.RunSwarm()
    
    sys.exit(status)
