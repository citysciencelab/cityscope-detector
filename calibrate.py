import time
import numpy as np
import cv2
from imutils import video
import scanner.modules as mod

def calib(img, patternsize=(9, 6)):
    retval, corners = cv2.findChessboardCorners(img, patternsize)
    if retval:
        cv2.drawChessboardCorners(img, patternsize, corners, retval)
        cv2.imshow("corners",img)
        return corners

def run(video_capture, cam_num):
    done = False
    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(8,5,0)
    objp = np.zeros((6*9,3), np.float32)
    objp[:,:2] = np.mgrid[0:9,0:6].T.reshape(-1,2)
    # Arrays to store object points and image points from all the images.
    objpoints = [] # 3d point in real world space
    imgpoints = [] # 2d points in image plane.

    while True:
        # read video frames
        if type(video_capture) is cv2.VideoCapture:
            valid, THIS_FRAME = video_capture.read()
            if not valid: continue
        elif type(video_capture) is video.WebcamVideoStream:
            THIS_FRAME = video_capture.read()

        width  = THIS_FRAME.shape[1]
        height = THIS_FRAME.shape[0]

        cv2.imshow("original feed", THIS_FRAME)
        gray = cv2.cvtColor(THIS_FRAME, cv2.COLOR_BGR2GRAY)

        KEY_STROKE = cv2.waitKey(1)
        if chr(KEY_STROKE & 255) == 'q':
            break
        if chr(KEY_STROKE & 255) == 'c':
            ret = calib(gray)
            if ret is None:
                continue
            objpoints.append(objp)
            imgpoints.append(ret)
        if chr(KEY_STROKE & 255) == 'm':
            if len(objpoints) < 5: # number 5 is arbitrary
                print("not enough images to calibrate!")
                continue
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape, None, None)
            img = THIS_FRAME
            h,  w = img.shape[:2]
            newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w, h), 1, (w, h))
            # undistort
            dst = cv2.undistort(img, mtx, dist, None, newcameramtx)
            # write distortion params to disk
            np.savetxt("data/mtx"+str(cam_num)+".txt", mtx)
            np.savetxt("data/dist"+str(cam_num)+".txt", dist)
            np.savetxt("data/ncmtx"+str(cam_num)+".txt", newcameramtx)

            # crop the image
            # x,y,w,h = roi
            # dst = dst[y:y+h, x:x+w]
            cv2.imshow('calibresult', dst)
            cv2.imwrite('calibresult.png', dst)
            done = True

        if done:
            print("calibrated camera #" + str(cam_num))
            time.sleep(5)
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    from helpers import utility
    config_filepath = "data/config.json"
    num_cams = utility.parse_file(config_filepath, 'num_cams')
    for cam_num in range(1, num_cams+1): #iterate over all cams
        video_capture = mod.getCamera(config_filepath, cam_num)
        run(video_capture, cam_num)
