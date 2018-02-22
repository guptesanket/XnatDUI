# XnatDUI - Xnat Download-Upload UI

This is an interface to talk to [XNAT](https://www.xnat.org/), a web based -open-source neuroimaging repository. This was built out of need for some specific functionality required for [NIDA NRB](https://irp.drugabuse.gov/nrb/index.php) and after months of evolving, testing, requirements gathering, suggestions, critiques and comments, it is turning into a full fledged, fast and dependable Download-Upload-Export User Interface for Xnat.

This is still under construction, and not at a stage I envision it to be. But I will try to get to that stage as and when time permits. 

For any problems, comments and suggestions, please send me an email or start an Issue here on github and I will try to get to it when possible.

It is built completely in python 3.5 and has not been tested for any version below 3.5 .
There is an update in 3.6 that breaks parallel processing code. 
Not sure how to fix it at the moment. Not sure if I will ever get to it. But if you want to try to fix it, just look for the following lines, and try to change everything that it is calling.
"event_loop.run_until_complete"
Everything else should work with 3.6

I have tried to keep it as bug-free as possible. But I know there are a lot of small bugs that can be fixed. But those are the bugs that you will come across if you really want to break it.
My priority is to add as many planned features as possible, since I don't have enough time to work on this.

It has been tested for Linux and Windows machines for Downloading. I'll push the Upload and Export functions soon to the online repo. Tweaking and testing a few things at the moment.

Unfortunately after May 2018, I will not be able to further modify this program much, unless it is a really minor bugfix. Feel free to branch it out, and if needed push any changes that seem important. I will approve everything that doesn't seem destructive in the first glance.

