## to do list

### detection
* [ ] image processing before detection? e.g. white-level adjustment
* [X] allow multiple colours
* [ ] think of something more robust than cvthresh over mean (blue doesn't get detected well)
  * [ ] try euclidean distance (LAB) to prototypical colours?
  * [ ] adaptive threshold?
  * [ ] Otsu's method?
* [X] improve performance
  * [ ] cv2.remap instead of cv2.warpperspective and cv2.undistort?
  * [X] contours first to avoid checking empty areas
* [ ] tune thresholds for lighting conditions
  * [ ] thresholds to config
* [ ] make usable for different cell subdivisions. (e.g. bento with only single colour bricks)

### multicam setup
* [X] merge into single grid
  * [X] Map inputs from 4 cams
  * [ ] make output from one camera compatible with gridmerger output without running gridmerger.py?
  * [X] rotation from config
* [X] handle overlapping rows (currently 1 in both dimensions)
  * [X] negative overlap (i.e. missing row between cams)
* [ ] allow multiple local cameras

### config
* [X] network addresses/ ports

### cleanup
* [ ] comments
* [ ] refactoring
* [X] exit multiprocessing (elegantly)
* [ ] exit networklistening
* [ ] readme.md
* [ ] wiki for usage

### compartmentalisation
* [ ] build a nice main executable .py with params for all modes, configs, etc, so you don't have to run a bakers dozen of scripts simultaneously
  * [X] scanner headless mode
  * [X] keystone cam number CL-args
    * [X] keystone multicam
  * [ ] pass merged grid locally to change detection (without udp)
  * [X] allow gridmerger to be run in local process
* [ ] packaging?
    * [X] requirements.txt
    * [ ] docker for headless mode
