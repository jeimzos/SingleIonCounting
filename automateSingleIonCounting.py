########################################################################################################
# automateSingleIonCounting.py
# 
# Python code for the automation of single ion counting in a specified folder along with some stats 
#
# Input
#   folderName:                 folder containing ASC files to be iterated
#   maxCutoff:                  set max pixel value cut off to remove high-intensity noise
#   nst:                        set noise threshold pixel value to remove background noise 
#   px:                         set ASC pixel resolution (default=256; ie 256 by 256) 
#   DCSize:                     set 'blob' size to reject (this accounts for dark current) 
#   t:                          set pixel threshold in pixels; input an integer
#
# Output
#   getAllIonCounts()           the following are saved in a folder named 'autoSingleIonCounting'
#       ionOverTime:            .png file of ion count variation over time                
#       ionFreqDist:            .png file of ion frequency distribution       
#       xportToExcel:           .csv file containing surmised data
#       getAvgIonCount:         average ion count over all files inside folder (in terminal) 
#
# References
#   -
#
# Notes
#   Automation of the single ion counting process is performed for every ASC file in a specified folder;
#   the average ion count is returned, along with some stats aformentioned;
#   positions of all counted ions are returned and can be exported;
#   optional surmised data export is also possible.  
#
########################################################################################################

import time
import numpy as np
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from collections import namedtuple

print('begin run...\n')

### set ASC folder & parameterrs
folderName = Path('data') # add ASC files into 'data' folder to be iterated
maxCutoff = 300     # set max pixel value cut off to remove high-intensity noise
nst = 80            # set noise threshold pixel value to remove background noise
px = 256            # set ASC pixel resolution (default=256; ie 256 by 256)
DCSize = 2          # set 'blob' size to reject (this accounts for dark current)
t = 2               # set pixel threshold in pixels; input an intege

colormapDPI = 100   # default=100, publishing quality=1200 
Point = namedtuple('Point', 'x y')
# t1 = time.time()



### some data preprocessing 
def preProcess(data):
    originalData = np.loadtxt(data, usecols=range(1, px+1)).astype(int) 
    setMaxCutoff = np.where(originalData >= maxCutoff, 0, originalData) 
    binariseData = np.where(setMaxCutoff <= nst, '0', '1').tolist() # if true yield 0, else yield 1
    stringData   = list(map(''.join, binariseData)) 
    return stringData

### tell algo what an ion 'looks' like 
def points_adjoin(p1, p2): 
    return -t <= p1.x-p2.x <= t and -t <= p1.y-p2.y <= t # returns True if ANY points are adjacent, otherwise False 

def adjoins(pts, pt): 
    return any(points_adjoin(p, pt) for p in pts) # return True if adjacent points 1s, return False if adjacent points 0s

### locate all ions from ASC data // ion counting algorithm
def findIons(data): 
    data = map(list, preProcess(data))
    datapts = [Point(x,y) for y,row in enumerate(data) for x,value in enumerate(row) if value == '1'] # co-ords of all 1s
    ions = []     
    for dp in datapts: 
        adjpts = set() 
        for b in ions:
            if adjoins(b,dp): # if adjoins() True (i.e. each element in ions and datapts is 1 and adjacent)
                adjpts = b    # else, adjpts is empty 
        if adjpts: # implicit booleanness: if adjpts not empty
            adjpts.add(dp) 
        else:      # if adjpts empty
            ions.append(set([dp])) # if not adjoining any, create new 'blob' i.e add a new set
    #ionsDenoised                     = [sets for sets in ions if len(sets)>1] 
    ionsDenoisedAndDarkCountsRemoved = [sets for sets in ions if len(sets)>DCSize] 
    return ionsDenoisedAndDarkCountsRemoved 

### get single ion positions
def ionLocations(fileName):
    ionLocations = []
    blobs = findIons(fileName)
    for blob in blobs:
        Xpts = [pt.x for pt in blob]
        Ypts = [pt.y for pt in blob]
        avgX = int("{:.0f}".format(sum(Xpts) / len(Xpts))) # avg and round to nearest integer
        avgY = int("{:.0f}".format(sum(Ypts) / len(Ypts)))
        pos = Point(avgX,avgY)
        ionLocations.append(pos)
    return ionLocations

### count all ions after denoised & dark counts removed
def countIons(ionsFound):
    return len(findIons(ionsFound))

### enumerate all located ions 
def indexIons(ionsFound,p):
    return next(i for i,reg in enumerate(ionsFound,start=1) if p in reg) # if p found in any 'sets', return 'set' p belongs to

### visualise all located ions
def visualiseIons(ionsFound): 
    allregionpts = set().union(*ionsFound)
    nline = []
    for y in range(0,px+1): # for each row
        line = []
        for x in range(0,px+1): 
            p = Point(x,y)
            if p in allregionpts: 
                line.append(indexIons(ionsFound,p)) # replace 1s with the correct ion index 
            else:
                line.append(0) # 0s remain as 0s
        nline.append(line)
    return np.array(nline) # recreate array

### plot ion count over time
def ionOverTime(files, to_dir):
    plt.plot(pd.DataFrame(files).ion_count)
    plt.title('ion count variation over time')
    plt.xlabel('image # (i.e. time)')
    plt.ylabel('# of ions')
    plt.savefig(f'{to_dir}/ion count variation over time', dpi=colormapDPI)
    plt.show()
    return 

### plot ion frequency distribution
def ionFreqDist(files, to_dir):
    max_ions = max(f.ion_count for f in files)
    min_ions = min(f.ion_count for f in files)
    bins = [i for i in range(min_ions-1, max_ions+2, 1)]
    freq = [f.ion_count for f in files]
    mean, median = np.mean(freq), np.median(freq)
    stats = f'ion stats (ions): \n mean = {mean} , median = {median} over {len(files)} files' 

    plt.title('ion count frequency')
    plt.xlabel(stats) # plt.xlabel(stats, c='r', size='x-large')
    plt.ylabel('frequency')
    plt.hist(freq, bins=bins, edgecolor='black')
    plt.savefig(f'{to_dir}/ion frequency distribution histogram', dpi=colormapDPI)
    plt.show()
    return

### export ion count data to excel
def xportToExcel(files, to_dir):
    df = pd.DataFrame(files)
    df.to_csv(f'{to_dir}/ioncountsNpositions.csv', index=False)
    return

### get average ion count over all files in folder
def getAvgIonCount(files):
    allIonCounts = [i.ion_count for i in files]
    averageIonCount = sum(allIonCounts) / len(allIonCounts)
    return print(f'The average ion count is {averageIonCount}')

### return ion counts for all ASC files in specified folder // automation
def getAllIonCounts(folderName):
    # create new file
    newdir = Path('', 'autoSingleIonCounting')
    newdir.mkdir(parents=True, exist_ok=True)

    files = []
    File = namedtuple('File', 'file_name ion_count ion_positions')
    for file in folderName.rglob('*.asc'):
        if file.suffix in ['.asc']:
            file_name = file.name 
            originalData = np.loadtxt(file, usecols=range(1,px+1))
            ionsDenoisedAndDarkCountsRemoved = findIons(file)
            ionsDnDFound = f'ions found = {countIons(file)}' # 'ions found = %d' % countIons(file)
            files.append(File(file_name, countIons(file), ionLocations(file))) 

            fig, (ax1, ax2) = plt.subplots(nrows=1, ncols=2)
            fig.tight_layout()            

            ax1.set_aspect('equal')
            ax1.set_title('original')
            ax1.imshow(originalData, cmap='viridis')

            ax2.set_aspect('equal')
            ax2.set_title('processed')
            ax2.set_xlabel(ionsDnDFound, c='r', size='x-large')
            ax2.imshow(visualiseIons(ionsDenoisedAndDarkCountsRemoved))

            file_name = file_name.split('.')[0]
            fig.savefig(f'autoSingleIonCounting/{file_name}', dpi=colormapDPI)
            print(f'file {file_name} saved')
            plt.close(fig) 

    ionOverTime(files,newdir)   # plot ion count variation over time & save as png
    ionFreqDist(files,newdir)   # plot ion frequency distribution as histogram & save as png
    xportToExcel(files,newdir)  # export surmised data to an excel
    getAvgIonCount(files)       # get average ion count in terminal
    
    return print('iteration complete :-)')     



getAllIonCounts(folderName) 



# t2 = time.time()
# print('time elapsed:', t2-t1, 's') 
# # time elapsed: 4.694884777069092 s for 100 files (no colormaps)
# # time elapsed: 39.17892241477966 s for 100 files (with colormaps)
print('\n...finished!')
