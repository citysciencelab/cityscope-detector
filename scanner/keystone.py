# ////////////////////////////////////////////////////////////////////////////////////
# {{ CityScopePy }}
# Copyright (C) {{ 2018 }}  {{ Ariel Noyman }}

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# ////////////////////////////////////////////////////////////////////////////////////

# CityScopePy KEYSTONE
# Exports a selection of keystone points using WEBCAM GUI

# "@context": "https://github.com/CityScope/", "@type": "Person", "address": {
# "@type": "75 Amherst St, Cambridge, MA 02139", "addressLocality":
# "Cambridge", "addressRegion": "MA",},
# "jobTitle": "Research Scientist", "name": "Ariel Noyman",
# "alumniOf": "MIT", "url": "http://arielnoyman.com",
# "https://www.linkedin.com/", "http://twitter.com/relno",
# https://github.com/RELNO]


import os
import json
import argparse
import numpy as np
import cv2
from helpers import utility
import scanner.modules as modules
from imutils import video

##################################################


def get_folder_path():
    """
    gets the local folder
    return is as a string with '/' at the ednd
    """
    loc = str(os.path.realpath(
        os.path.join(os.getcwd(), os.path.dirname(__file__)))) + '/'
    return loc


##################################################


# top left, top right, bottom left, bottom right
POINTS = [(0, 0), (0, 0), (0, 0), (0, 0)]
POINT_INDEX = 0
MOUSE_POSITION = (0, 0)

def selectFourPoints(WEBCAM, cam):
    # let users select 4 points on WEBCAM GUI

    print("select 4 points, by double clicking on each of them in the order: \n\
	up left, up right, bottom left, bottom right.")

    # loop until 4 clicks
    while POINT_INDEX != 4:

        key = cv2.waitKey(20) & 0xFF
        if key == 27:
            return False

        # wait for clicks
        cv2.setMouseCallback('canvas', save_this_point)

        # read the WEBCAM frames
        if type(WEBCAM) is cv2.VideoCapture:
            valid, FRAME = WEBCAM.read()
            if not valid: continue
        elif type(WEBCAM) is video.WebcamVideoStream:
            FRAME = WEBCAM.read()

        #print(FRAME.shape)

        if cam:
            FRAME = cv2.undistort(FRAME, cam.mtx, cam.dist, None, cam.newcammtx)
        # else: print("no distort")

        # draw mouse pos
        cv2.circle(FRAME, MOUSE_POSITION, 10, (0, 0, 255), 1)
        cv2.circle(FRAME, MOUSE_POSITION, 1, (0, 0, 255), 2)

        # draw clicked points
        for thisPnt in POINTS:
            cv2.circle(FRAME, thisPnt, 10, (255, 0, 0), 1)
        # show the video
        cv2.imshow('canvas', FRAME)

    return True


def save_this_point(event, x, y, flags, param):
    # saves this point to array

    # mouse callback function
    global POINT_INDEX
    global POINTS
    global MOUSE_POSITION

    if event == cv2.EVENT_MOUSEMOVE:
        MOUSE_POSITION = (x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        # draw a ref. circle
        print('point  # ', POINT_INDEX, (x, y))
        # save this point to the array pts
        POINTS[POINT_INDEX] = (x, y)
        POINT_INDEX = POINT_INDEX + 1


def parse_file(file, field):
    """
    get data from JSON settings files.

    Steps:
    - opens file
    - returns value for field

    Args:

    Returns the desired field
    """

    # open json file
    with open(file) as json_data:
        jd = json.load(json_data)

        # return item for this field
        return ""+jd[field]

def run(cam_num):
    # file path to save
    FILE_PATH = utility.get_folder_path()+"data/keystone" + ("" if cam_num == 1 else str(cam_num)) + ".txt"

    config_filepath = utility.get_folder_path()+'data/config.json'
    # define the video stream
    video_capture = modules.getCamera(config_filepath, cam_num)
    # print(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH ))
    # video winodw
    cv2.namedWindow('canvas', cv2.WINDOW_NORMAL)

    # find camera calibration
    cam = modules.Camera.fromFile(utility.get_folder_path()+"data/", cam_num)


    # checks if finished selecting the 4 corners
    if selectFourPoints(video_capture, cam):
        np.savetxt(FILE_PATH, POINTS)
        print("keystone initial points were saved")

    # video_capture.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MIT/CSL CityScope keystone utility')
    parser.add_argument("-c", default=1,
                        help="The camera number (analog to config.json) to set keystones for")
    args = parser.parse_args()
    run(args.c) # argparse camera number
