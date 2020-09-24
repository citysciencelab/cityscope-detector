# {{ CityScope Python Detector }}

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.



##################################################

# CityScope Python Detector
# Keystone, decode a 2d array
# of uniquely tagged LEGO array
# find changes and publish them via WAMP

##################################################


from multiprocessing import Process, Manager
import argparse

from scanner import modules
from scanner import keystone
from scanner import gridmerger
from helpers import utility

##################################################
################RUN MULTITHREADED#################
##################################################

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MIT/CSL CityScope camera and detection handler.')
    parser.add_argument("-K", action='store_true',
                        help="run the keytone selection utility for calibration")
    parser.add_argument("-D", action='store_true',
                        help="show the camera feed with calibration refinement")
    args = parser.parse_args()

    # read config
    config_filepath = utility.get_folder_path()+'data/config.json'
    num_cams = utility.parse_file(config_filepath, 'num_cams') # number of used cams

    if args.K:
        for cam_num in range(1, num_cams+1): #iterate over all cams
            print("keystone " + str(cam_num))
            keystone.run(cam_num)
        exit()

    # define global list manager
    MANAGER = Manager()
    # create shared global list to work with both processes
    multiprocess_shared_dict = MANAGER.dict()
    # init this dict's props
    multiprocess_shared_dict['display_on'] = args.D
    multiprocess_shared_dict['grid'] = "" # initial population of shared list


    # make scanner processes
    scanProcs = []
    for i in range(num_cams-1): # last one goes to main thread instead
        # start all multicam porcesses
        multiprocess_shared_dict['grid' + str(num_cams-i)] = [-1] # 4 cams: grid4, grid3, grid2
        process_scanner = Process(target=modules.scanner_function,
                                  args=([multiprocess_shared_dict, num_cams-i]))
        process_scanner.start()
        scanProcs.append(process_scanner)

    process_merger = Process(target=gridmerger.runProcess,
                                args=([multiprocess_shared_dict]))

    process_merger.start()

    # start detection for last camera in main thread
    try:
        # start camera on main thread
        modules.scanner_function(multiprocess_shared_dict, 1)
    except KeyboardInterrupt:   # ctrl+c ends program
        pass


    # end all threads
    for i in range(num_cams-1):
        scanProcs[i].join()

    process_merger.join()
