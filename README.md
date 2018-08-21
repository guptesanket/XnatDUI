# XnatDUI - Xnat Download-Upload UI

This is an interface to talk to [XNAT](https://www.xnat.org/), a web based -open-source neuroimaging repository. This was built out of need for some specific functionality required for [NIDA NRB](https://irp.drugabuse.gov/nrb/index.php) and after months of evolving, testing, requirements gathering, suggestions, critiques and comments, it is turned into a full fledged, fast and dependable Download-Upload-Export User Interface for Xnat.

This was still under construction before I left the world of neuroscience, and I did not leave it at a stage I had envisioned it to be. 

For any problems, comments and suggestions, please send me an email or start an Issue here on github and I will try to get to it when possible.

It is built completely in python 3.5 and has not been tested for any version below 3.5 .
There is an update in 3.6 that breaks parallel processing code. 
I did not attempt at debugging it. But if you want to try to fix it, just look for "event_loop.run_until_complete" and try to make that portable to 3.6. Everything else should work with 3.6

I have tried to keep it as bug-free as possible. But I know there are a lot of small bugs that can be fixed. But those are the bugs that you will come across if you really want to break it.
My priority was to add as many planned features as possible, since I did not have enough time to finish everything.

It has been tested for Linux and Windows machines for Downloading. Some of the upload and export functions certainly work. While some others would need a bit of understanding of the code, to be able to extend and incorporate.

Unfortunately after May 2018, I will not be able to further modify this repo much, unless it is a really minor bugfix. Feel free to branch it out, and if needed push any changes that seem important. I will approve everything that doesn't seem destructive in the first glance.
