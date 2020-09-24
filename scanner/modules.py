# {{ CityScope Python Detector }}

##################################################

# CityScope Python Scanner - Modules
# decode a 2d array
# of uniquely tagged LEGO array

##################################################

# imports packages
import itertools
import socket
import os
import sys
import json
import time
from datetime import datetime
from datetime import timedelta
from datetime import date
import math
import numpy as np
import cv2
from imutils import video

from helpers import udp
from helpers import utility

##################################################
##################################################
# GLOBAL DEFINITIONS
##################################################
##################################################

class Grid:
    def __init__(self, configfile):
        '''
        set grid parameters globally from values out of json file
        '''

        self.dimensions_x = utility.parse_file(configfile, 'gridsize_x')
        self.dimensions_y = utility.parse_file(configfile, 'gridsize_y')
        self.colour_array_resolution_x = utility.parse_file(configfile, 'coding_resolution_x')
        self.colour_array_resolution_y = utility.parse_file(configfile, 'coding_resolution_y')

        self.video_resolution_x = 0
        self.video_resolution_y = 0

    def scanner_width(self):
        return int( self.video_resolution_x/
                    self.dimensions_x/
                    self.colour_array_resolution_x) 
            
    def scanner_height(self):
        return int( self.video_resolution_y/
                    self.dimensions_y/
                    self.colour_array_resolution_y)

class Camera:
    def __init__(self,mtx,dist,newcammtx):
        self.mtx = mtx
        self.dist=dist
        self.newcammtx=newcammtx

    @staticmethod
    def fromFile(filepath,cam_num):
        try:
            mtx = np.loadtxt(filepath + "mtx" + str(cam_num) + ".txt", dtype=np.float32)
            dist = np.loadtxt(filepath + "dist" + str(cam_num) + ".txt", dtype=np.float32)
            newcammtx = np.loadtxt(filepath + "ncmtx" + str(cam_num) + ".txt", dtype=np.float32)
            #if one is missing -> exception -> return None, no undistort later
            cam = Camera(mtx, dist, newcammtx)
            return cam
        except:
            return None

COLOUR_CODES = {
    #"bbbb" : 240,
    # "bbby" : 280,
    # "bbyy" : 320,
    # "byyy" : 400,
    #"rrrr" : 40,
    # "brrr" : 80,
    #"bbrr" : 120,
    # "bbbr" : 200,
    "yyyy" : -1,
    # "rryy" : 1500
}

##################################################
##################################################
# MAIN FUNCTIONS / PROCESSES
##################################################
##################################################

def scanner_function(multiprocess_shared_dict, cam_num):
    # set grid params from file
    config_filepath = utility.get_folder_path()+'data/config.json'
    grid = Grid(config_filepath)

    # load the initial keystone data from file
    keystone_points_array = np.loadtxt(
        utility.get_folder_path()+"data/keystone" + ("" if cam_num == 1 else str(cam_num)) + ".txt", dtype=np.float32)

    # define the video stream
    video_capture = getCamera(config_filepath, cam_num)

    # get video resolution from webcam
    if type(video_capture) is cv2.VideoCapture:
        grid.video_resolution_x = int(video_capture.get(3))
        grid.video_resolution_y = int(video_capture.get(4))
    elif type(video_capture) is video.WebcamVideoStream:
        grid.video_resolution_x = int(video_capture.stream.get(3))
        grid.video_resolution_y = int(video_capture.stream.get(4))

    cam = Camera.fromFile(utility.get_folder_path()+"data/", cam_num) # find camera calibration

    if multiprocess_shared_dict['display_on']:
        # define the video window
        cv2.namedWindow('CityScopeScanner '+str(cam_num), cv2.WINDOW_NORMAL)
        cv2.resizeWindow('CityScopeScanner '+str(cam_num), 600, 400)

        # make the GUI
        create_user_interface(keystone_points_array, grid, cam_num)


    ##################################################
    ###################MAIN LOOP######################
    ##################################################

    # run the video loop until interrupt
    while True:
        # get a new matrix transformation every frame
        KEY_STONE_DATA = keystone(
            grid.video_resolution_x,
            grid.video_resolution_y,
            listen_to_UI_interaction(cam_num) if multiprocess_shared_dict['display_on']
                else keystone_points_array)

        # read video frames
        if type(video_capture) is cv2.VideoCapture:
            valid, THIS_FRAME = video_capture.read()
            if not valid: continue
        elif type(video_capture) is video.WebcamVideoStream:
            THIS_FRAME = video_capture.read()

        if cam:
            THIS_FRAME = cv2.undistort(THIS_FRAME, cam.mtx, cam.dist, None, cam.newcammtx)

        # warp the video based on keystone info
        DISTORTED_VIDEO_STREAM = cv2.warpPerspective(
            THIS_FRAME, KEY_STONE_DATA, (grid.video_resolution_y, grid.video_resolution_y))

        grid.video_resolution_x = grid.video_resolution_y   # square makes adjustements easier

        #  convert input to LAB colour space
        labmat = cv2.cvtColor(DISTORTED_VIDEO_STREAM, cv2.COLOR_BGR2LAB)

        ### Colour checking and Voting
        votes = {}
        voteForColour(grid, labmat, "b", votes)
        voteForColour(grid, labmat, "y", votes)
        voteForColour(grid, labmat, "r", votes)

        # fill into grid
        rotation = utility.parse_file(config_filepath, 'rotate_'+str(cam_num))

        if rotation == -1 or rotation == 1:
            retgridw = grid.dimensions_y
            retgridh = grid.dimensions_x
        else:
            retgridw = grid.dimensions_x
            retgridh = grid.dimensions_y
        retgrid = [[0] * retgridw for i in range(retgridh)]

        for (x, y) in votes:
            val = votes[(x, y)]
            # TODO: handle underfilled vote bins (len<4)
            if len(val) < 4:
                # print("skip "+ val)
                continue
            # TODO: handle overfull vote bin (len>4)
            if len(val) == 8:
                # print("prune "+ val)
                val = val[2:6]
            # elif len(val) > 4:
            #     print("??? " + val)

            if val in COLOUR_CODES: # unrecognised colours get skipped
                newval = COLOUR_CODES[val]  # encode colour values
                # rotate according to config
                newx, newy = rotateCell(grid, x, y, rotation)
                retgrid[newx][newy] = newval

        typestr = arr2str(retgrid)

        if cam_num == 1:
            multiprocess_shared_dict['grid'] = typestr    # csl format
        else:
            multiprocess_shared_dict['grid'+str(cam_num)] = typestr    # multicam

        if multiprocess_shared_dict['display_on']:
            rectSizeX = grid.video_resolution_x/grid.dimensions_x
            rectSizeY = grid.video_resolution_y/grid.dimensions_y

            # print grid lines
            for hor in range(0, grid.dimensions_y+1):
                cv2.line(DISTORTED_VIDEO_STREAM,
                (int(hor*rectSizeY), 0),
                (int(hor*rectSizeY), grid.video_resolution_x),
                (255,255,255),1)
            for ver in range(0, grid.dimensions_x+1):
                cv2.line(DISTORTED_VIDEO_STREAM,
                (0, int(ver*rectSizeX)),
                (grid.video_resolution_y, int(ver*rectSizeX)),
                (255,255,255),1)

            # print detections in squares
            for (x,y) in votes:
                cv2.putText(DISTORTED_VIDEO_STREAM, votes[x, y], (int(x * rectSizeX), int(y * rectSizeY)+20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)	

            # show feed preview
            if cam_num == 2:
                camera_txt = "topright"
            elif cam_num == 3:
                camera_txt = "bottomleft"
            elif cam_num == 4:
                camera_txt = "bottomright"
            else:
                camera_txt = "topleft"
            cv2.putText(DISTORTED_VIDEO_STREAM, camera_txt,
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow("contours "+str(cam_num), DISTORTED_VIDEO_STREAM)

            # INTERACTION
            KEY_STROKE = cv2.waitKey(1)
            if chr(KEY_STROKE & 255) == 'q':
                break
            # saves to file
            if chr(KEY_STROKE & 255) == 's':
                save_keystone_to_file(
                    listen_to_UI_interaction(cam_num), cam_num)


    # close opencv
    # video_capture.release()
    cv2.destroyAllWindows()


##################################################
### cam + transform

def rotateCell(grid, x, y, rotation):
    # rotate grid according to config
    if rotation is 0: return (x, y)
    if rotation == -1:
        return (y, grid.dimensions_x - x -1)
    if rotation == 1:
        return (grid.dimensions_y - y -1, x)

def getCamera(config_filepath, cam_num):
    camera_source = utility.parse_file(config_filepath, 'camera_source')
    if cam_num == 2:
        camera_source = utility.parse_file(config_filepath, 'camera_source_tr')
    elif cam_num == 3:
        camera_source = utility.parse_file(config_filepath, 'camera_source_bl')
    elif cam_num == 4:
        camera_source = utility.parse_file(config_filepath, 'camera_source_br')
    
    print(str(cam_num) + ": " + camera_source)

    # define the video stream
    try:
        if camera_source == "local": #  allow local cams as well
            # try from a device 1 in list, not default webcam
            # todo: autoselect cameras
            video_capture = cv2.VideoCapture(1)
            # if not exist, use device 0
            if not video_capture.isOpened():
                print('no cam in pos 1')
                video_capture = cv2.VideoCapture(0)
                
            if not video_capture.isOpened():
                print('no cam in pos 0')
                exit()
        
        else:
            video_capture = video.WebcamVideoStream(camera_source)
            video_capture.start()
            time.sleep(1.0)

    finally:
        print(video_capture)
    
    return video_capture

def keystone(video_resolution_x, video_resolution_y, keyStonePts):
    '''
    NOTE: Aspect ratio must be flipped
    so that aspectRat[0,1] will be aspectRat[1,0]
    '''

    # inverted screen ratio for np source array
    video_aspect_ratio = (video_resolution_y, video_resolution_x)
    # np source points array
    keystone_origin_points_array = np.float32(
        [
            [0, 0],
            [video_aspect_ratio[1], 0],
            [0, video_aspect_ratio[0]],
            [video_aspect_ratio[1], video_aspect_ratio[0]]
        ])
    # make the 4 pnts matrix perspective transformation
    transfromed_matrix = cv2.getPerspectiveTransform(
        keyStonePts[0:4], keystone_origin_points_array)

    return transfromed_matrix

##################################################
### detection

def arr2str(arr):
    typestr = "["
    for row in arr:
        for cell in row:

            typestr += "\""+str(cell)+"\"" + ", " # compacting ("0000"->0) grid here to reduce bandwith

    typestr = typestr[:-2] # strip trailing comma and space from last element
    typestr+="]"
    return typestr

def getContour(labmat, colour):
    channel_l, channel_a, channel_b = cv2.split(labmat)

    # TODO: thresholds from config
    # TODO: thresholds fine tuning for lighting

    if colour is "b":
        mask = np.where((channel_b <= 128 - 12) & (channel_l < 90), 255, 0).astype(np.uint8)
    # elif colour is "green":
    #     mask = np.where(channel_a < 128 - 32, 255, 0).astype(np.uint8)
    elif colour is "r":
        mask = np.where((channel_a >= 128 + 16) & (channel_b <= 128 + 18), 255, 0).astype(np.uint8)
    elif colour is "y":
        mask = np.where(channel_b >= 128 + 18, 255, 0).astype(np.uint8)
    # elif colour is "black":
    #     mask = np.zeros(channel_l.shape, dtype=np.uint8)

    kernel = np.ones((3, 3), np.uint8)  # 3x3-Matrix

    closed_mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    if cv2.__version__[0] is '3':
        _, contours, hierarchy = cv2.findContours(
            closed_mask.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    else:
        contours, hierarchy = cv2.findContours(
            closed_mask.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    newcontours = filter(lambda e : cv2.contourArea(e) > 20, contours) # TODO: magic number
    contours = []
    for item in newcontours:
        contours.append(item)

    # if colour is "y":
    #     contourimg = np.zeros(labmat.shape)
    #     cv2.drawContours(contourimg, contours, -1, (0,255,255), 1)
    #     cv2.imshow("contours", contourimg)

    return contours, mask

def getCorrespindingRect(grid, x, y):
    if x < 0 or y < 0 or x > grid.video_resolution_x or y > grid.video_resolution_y:
        print("ERROR in finding rect: outside of bounds")

    rectSizeX = grid.video_resolution_x/grid.dimensions_x
    rectSizeY = grid.video_resolution_y/grid.dimensions_y

    return (int(x / rectSizeX), int(y/rectSizeY))

def areaOfColourInRect(mask, rect):
    (x,y,w,h) = rect
    h = int(h)
    w = int(w)
    relevantmask = mask[y:y+h, x:x+w]
    sumarea = np.sum(relevantmask)
    percentarea = sumarea / (w*h*255)
    return percentarea

def voteForColour(grid, labmat, colourtag, votes):

    # thresholds from config
    config_filepath = utility.get_folder_path()+'data/config.json'
    xxxx = utility.parse_file(config_filepath, 'xxxx')
    xxx = utility.parse_file(config_filepath, 'xxx')
    xx = utility.parse_file(config_filepath, 'xx')
    mina = utility.parse_file(config_filepath, 'x')

    contours, mask = getContour(labmat, colourtag)

    rectSizeX = grid.video_resolution_x/grid.dimensions_x
    rectSizeY = grid.video_resolution_y/grid.dimensions_y
    for contour in contours:
        M = cv2.moments(contour)
        if(M['m00'] == 0):
            centroid_x = 0
            centroid_y = 0
        else:
            centroid_x = int(M['m10'] / M['m00'])
            centroid_y = int(M['m01'] / M['m00'])
            (x,y) = getCorrespindingRect(grid, centroid_x, centroid_y)
            percentarea= areaOfColourInRect(mask, (int(x * rectSizeX),int(y * rectSizeY),rectSizeX,rectSizeY))
            
            # print(percentarea,"%")
            if percentarea > 1.2 or percentarea < mina: continue
            if (x,y) in votes:  # first vote
                votes[(x,y)] += colourtag
            else:
                votes[(x,y)] = colourtag

            if(percentarea > xx):   # 50% vote
                votes[(x,y)] += colourtag
            if(percentarea > xxx):  # 75%
                votes[(x,y)] += colourtag
            if(percentarea > xxxx): # all 4 subcells
                votes[(x,y)] += colourtag


##################################################
#### UI

def create_user_interface(keystone_points_array, grid: Grid, cam_num=1):
    """
    Creates user interface and GUI.

    Steps:
    makes a list of sliders for interaction

    Args:

    Returns none
    """

    cv2.createTrackbar('Upper Left X', 'CityScopeScanner '+str(cam_num),
                       keystone_points_array[0][0], grid.video_resolution_x, dont_return_on_ui)
    cv2.createTrackbar('Upper Left Y', 'CityScopeScanner '+str(cam_num),
                       keystone_points_array[0][1], grid.video_resolution_y, dont_return_on_ui)
    cv2.createTrackbar('Upper Right X', 'CityScopeScanner '+str(cam_num),
                       keystone_points_array[1][0], grid.video_resolution_x, dont_return_on_ui)
    cv2.createTrackbar('Upper Right Y', 'CityScopeScanner '+str(cam_num),
                       keystone_points_array[1][1], grid.video_resolution_y, dont_return_on_ui)
    cv2.createTrackbar('Bottom Left X', 'CityScopeScanner '+str(cam_num),
                       keystone_points_array[2][0], grid.video_resolution_x, dont_return_on_ui)
    cv2.createTrackbar('Bottom Left Y', 'CityScopeScanner '+str(cam_num),
                       keystone_points_array[2][1], grid.video_resolution_y, dont_return_on_ui)
    cv2.createTrackbar('Bottom Right X', 'CityScopeScanner '+str(cam_num),
                       keystone_points_array[3][0], grid.video_resolution_x, dont_return_on_ui)
    cv2.createTrackbar('Bottom Right Y', 'CityScopeScanner '+str(cam_num),
                       keystone_points_array[3][1], grid.video_resolution_y, dont_return_on_ui)

def dont_return_on_ui(event):
    pass

def listen_to_UI_interaction(cam_num=1):
    """
    listens to user interaction.

    Steps:
    listen to a list of sliders

    Args:

    Returns 4x2 array of points location for key-stoning
    """

    ulx = cv2.getTrackbarPos('Upper Left X', 'CityScopeScanner '+str(cam_num))
    uly = cv2.getTrackbarPos('Upper Left Y', 'CityScopeScanner '+str(cam_num))
    urx = cv2.getTrackbarPos('Upper Right X', 'CityScopeScanner '+str(cam_num))
    ury = cv2.getTrackbarPos('Upper Right Y', 'CityScopeScanner '+str(cam_num))
    blx = cv2.getTrackbarPos('Bottom Left X', 'CityScopeScanner '+str(cam_num))
    bly = cv2.getTrackbarPos('Bottom Left Y', 'CityScopeScanner '+str(cam_num))
    brx = cv2.getTrackbarPos('Bottom Right X', 'CityScopeScanner '+str(cam_num))
    bry = cv2.getTrackbarPos('Bottom Right Y', 'CityScopeScanner '+str(cam_num))

    return np.asarray([(ulx, uly), (urx, ury), (blx, bly), (brx, bry)], dtype=np.float32)

##################################################
### file output

def save_keystone_to_file(keystone_data_from_user_interaction, cam_num=1):
    """
    saves keystone data from user interaction.

    Steps:
    saves an array of points to file

    """

    filePath = utility.get_folder_path() + "data/keystone" + ("" if cam_num == 1 else str(cam_num)) + ".txt"
    np.savetxt(filePath, keystone_data_from_user_interaction)
    print("[!] keystone points were saved in", filePath)