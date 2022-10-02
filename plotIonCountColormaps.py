#######################################################################################################
# plotIonCountColormaps.py
# 
# Python code for single ion counting, plotting of colormaps, and exporting to excel of one ASC file
#
# Input
#   fileName:                   ASC file name
#   maxCutoff:                  set max pixel value cut off to remove high-intensity noise
#   nst:                        set noise threshold pixel value to remove background noise 
#   px:                         set ASC pixel resolution (default=256; ie 256 by 256) 
#   DCSize:                     set 'blob' size to reject (this accounts for dark current) 
#   t:                          set pixel threshold in pixels; input an integer
#
# Output
#   getExcelFolder              the following are saved in a folder named 'ionCountingStepsExcel'
#       plotColormaps:          .png file of 3 colormaps; each colormap depicting a step of the algo;
#       xportToExcel:           4 .csv files containing data for each step of the ion counting process
#   countIons:                  final ion count (in terminal)
#   ionLocations:               .csv file of positions of all counted ions
#
# References
#   -
#
# Notes
#   Single ion counting is performed for one ASC file only;
#   colormaps are plotted to illustrate stepwise the algorithm's ion counting process;
#   positions of all counted ions are returned that can be exported;
#   optional data export at each stage is also supported.  
#
#######################################################################################################

import numpy as np
import pandas as pd
from pathlib import Path
from matplotlib import colors
import matplotlib.pyplot as plt
from collections import namedtuple

print('begin run...\n')

### set ASC folder & parameters
fileName = 'data/example_0319.asc' # specify ASC file (e.g 'data/0001.asc')
maxCutoff = 300     # set max pixel value cut off to remove high-intensity noise
nst = 80            # set noise threshold pixel value to remove background noise
px = 256            # set ASC pixel resolution (default=256; ie 256 by 256)
DCSize = 2          # set 'blob' size to reject (this accounts for dark current)
t = 2               # set pixel threshold in pixels; input an integer

colormapDPI = 1200  # default=100, publishing quality=1200 (uncomment fig.savefig in plotColormaps() to save colormaps in .png)
Point = namedtuple('Point', 'x y')



### some data preprocessing 
def preProcess(data):
    originalData = np.loadtxt(data, usecols=range(1, px+1)).astype(int) 
    setMaxCutoff = np.where(originalData >= maxCutoff, 0, originalData) 
    binariseData = np.where(setMaxCutoff <= nst, '0', '1').tolist() # if true yield 0, else yield 1
    stringData   = list(map(''.join, binariseData)) 
    return stringData, binariseData

### tell algo what an ion 'looks' like 
def points_adjoin(p1, p2): 
    return -t <= p1.x-p2.x <= t and -t <= p1.y-p2.y <= t # returns True if ANY points are adjacent, otherwise False 

def adjoins(pts, pt): 
    return any(points_adjoin(p, pt) for p in pts) # returns True if adjacent points are 1s, return False if adjacent points are 0s

### locate all ions from ASC data // ion counting algorithm
def findIons(data): 
    data = map(list, preProcess(data)[0])
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
    ionsDenoised                     = [sets for sets in ions if len(sets)>1] 
    ionsDenoisedAndDarkCountsRemoved = [sets for sets in ions if len(sets)>DCSize] 
    return ionsDenoised, ionsDenoisedAndDarkCountsRemoved 

### get single ion positions
def ionLocations(fileName):
    ionLocations = []
    blobs = findIons(fileName)[1]
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
    return len(findIons(ionsFound)[1])

### enumerate all located ions 
def indexIons(ionsFound,p):
    return next(i for i,reg in enumerate(ionsFound,start=1) if p in reg) # if p found in any of 'sets', it will find which 'set' p belongs to

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

### plot colormaps
def plotColormaps(data, to_dir): 
    fig, (ax1, ax2, ax3) = plt.subplots(nrows=1, ncols=3)
    fig.tight_layout()
    cmap   = colors.ListedColormap(['black', 'red'])
    bounds = [0, 1, len(findIons(data)[1])+1] # black for 0s & red for 1s, ie black background w red ions;
    norm   = colors.BoundaryNorm(bounds, cmap.N)

    originalData                     = np.loadtxt(data, usecols=range(1,px+1)) 
    ionsDenoised                     = findIons(data)[0]
    ionsDenoisedAndDarkCountsRemoved = findIons(data)[1] 
    ionsDFound   = f'ions found = {len(ionsDenoised)}' 
    ionsDnDFound = f'ions found = {len(ionsDenoisedAndDarkCountsRemoved)}'
    tempString1  = f'Ions found after denoising = {str(len(ionsDenoised))}' 
    tempString2  = f'Ions found after denoising & removing dark counts =  {str(len(ionsDenoisedAndDarkCountsRemoved))}' 

    ax1.set_aspect('equal')
    ax1.set_title('1 original')
    ax1.imshow(originalData, cmap='viridis')

    ax2.set_aspect('equal')
    ax2.set_title('2 denoised')
    ax2.set_xlabel(ionsDFound, c='r', size='x-large')
    ax2.imshow(visualiseIons(ionsDenoised), cmap, norm)

    ax3.set_aspect('equal')
    ax3.set_title('3 defects removed')
    ax3.set_xlabel(ionsDnDFound, c='r', size='x-large')
    ax3.imshow(visualiseIons(ionsDenoisedAndDarkCountsRemoved), cmap, norm)

    fig.savefig(f'{to_dir}/colormap', dpi=colormapDPI)
    plt.show()
    return print(tempString1, tempString2, sep='\n')

### export data to excels 
def xportToExcel(data, to_dir):
    originalData = np.loadtxt(data, usecols=range(1, px+1))

    df1 = pd.DataFrame(originalData) 
    df2 = pd.DataFrame(preProcess(data)[1])              # binarised 
    df3 = pd.DataFrame(visualiseIons(findIons(data)[0])) # denoised
    df4 = pd.DataFrame(visualiseIons(findIons(data)[1])) # denoised & dark counts removed
    df5 = pd.DataFrame(ionLocations(data))               # ion locations
    df5.index = np.arange(1, len(df5)+1)

    df1.to_csv(f'{to_dir}/1_original.csv', header=False, index=False)
    df2.to_csv(f'{to_dir}/2_binarised.csv', header=False, index=False)
    df3.to_csv(f'{to_dir}/3_denoised.csv', header=False, index=False)
    df4.to_csv(f'{to_dir}/4_denoisedNdarkcountsremv.csv', header=False, index=False)
    df5.to_csv(f'{to_dir}/ion_positions.csv', header=['x','y'])
    return

### compiled function for colomaps & export
def getExcelFolder():
    newdir = Path('', 'ionCountingStepsExcel')
    newdir.mkdir(parents=True, exist_ok=True)
    plotColormaps(fileName, newdir)
    xportToExcel(fileName, newdir)
    return



print('plotting colormaps & exporting excels to folder...',    getExcelFolder())
print('saved to ionCountingStepsExcel')

print('final ion count is...' ,                                countIons(fileName))
print('getting positions of all ions... ',                    *ionLocations(fileName), sep='\n')



print('\n...finished!')
