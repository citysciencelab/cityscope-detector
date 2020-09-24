#
#
# takes multiple detection outputs from multicam setups and merges them intp single grid
# resulting merged grid gets sent over udp in plain text format
#

import json
import numpy as np

from helpers import utility
from helpers import udp

class GridData:
    num_cams = 1
    grid_x = 1
    grid_y = 1

    overlap_horizontal = 0
    overlap_vertical = 0

    def __init__(self, num_cams, grid_x, grid_y, overlap_x = 0, overlap_y = 0):
        self.num_cams = num_cams
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.tl = [] # init new matrices
        self.tr = []
        self.bl = []
        self.br = []
        self.overlap_horizontal = overlap_x
        self.overlap_vertical = overlap_y

    def parseMsg(self, data):
        if data is None or data == "": return

        try:
            jd = json.loads(data)
        except json.decoder.JSONDecodeError:
            return
            
        if 'grid' in jd:
            self.tl = jd['grid']
        if 'grid2' in jd:
            self.tr = jd['grid2']

        if 'grid3' in jd:
            self.bl = jd['grid3']
        if 'grid4' in jd:
            self.br = jd['grid4']

        return self.update()

    def parseList(self, name, data):
        #data = data.split()
        print("length "+str(len(data)))
        print(data)
        if data is None or len(data) == 1: return
        if name == 'grid':
            self.tl = data
        if name == 'grid2':
            self.tr = data

        if name == 'grid3':
            self.bl = data
        if name == 'grid4':
            self.br = data

        return self.update()


    def update(self):
        if self.tl == []: return []
        tl_mat = np.reshape(self.tl, (self.grid_x, self.grid_y))
        # careful with differing grid dimensions!

        if self.num_cams == 1:
            merged_mat = tl_mat
            return merged_mat

        if self.tr == []: return
        tr_mat = np.reshape(self.tr, (self.grid_x, self.grid_y))

        if self.overlap_horizontal > 0: # strip overlapping columns
            tl_mat = tl_mat[:, :-self.overlap_horizontal]
        if self.overlap_horizontal < 0: # fill missing columns
            tl_mat = np.vstack((tl_mat, np.zeros((-self.overlap_horizontal, self.grid_y), dtype=np.int8)))

        top_mat = np.vstack((tl_mat, tr_mat))
        if self.margins[2] > 0: #top margin
            newcol = np.zeros((top_mat.shape[0], self.margins[2]), dtype=np.int8) # top_mat.shape[0] = grid_x*ceil(numcams/2)+overlap
            top_mat = np.hstack((newcol, top_mat))
            

        if self.num_cams == 2:
            if self.margins[3] > 0: #bottom margin
                newcol = np.zeros((top_mat.shape[0], self.margins[3]), dtype=np.int8) # top_mat.shape[0] = grid_x*ceil(numcams/2)+overlap
                top_mat = np.hstack((top_mat, newcol))
            if self.margins[0] > 0: #left margin
                newrow = np.zeros((self.margins[0], top_mat.shape[1]), dtype=np.int8) # top_mat.shape[0] = grid_x*ceil(numcams/2)+overlap
                top_mat = np.vstack((newcol, top_mat))
            if self.margins[1] > 0: #right margin
                newrow = np.zeros((self.margins[1], top_mat.shape[1]), dtype=np.int8) # top_mat.shape[0] = grid_x*ceil(numcams/2)+overlap
                top_mat = np.vstack((top_mat, newcol))

            merged_mat = top_mat
            return merged_mat

        # 4 cams
        if self.bl == [] or self.br == []: return
        bl_mat = np.reshape(self.bl, (self.grid_x, self.grid_y))
        br_mat = np.reshape(self.br, (self.grid_x, self.grid_y))

        if self.overlap_horizontal > 0: # strip overlapping columns
            bl_mat = bl_mat[:, :-self.overlap_horizontal]
        if self.overlap_horizontal < 0: # fill missing columns
            bl_mat = np.vstack((bl_mat, np.zeros((-self.overlap_horizontal, self.grid_y), dtype=np.int8)))

        bot_mat = np.vstack((bl_mat, br_mat))

        if self.overlap_vertical > 0: # strip overlapping rows
            top_mat = top_mat[:-self.overlap_vertical, :]
        if self.overlap_vertical < 0: # fill missing rows
            newcol = np.zeros((top_mat.shape[0], -self.overlap_vertical), dtype=np.int8) # top_mat.shape[0] = grid_x*ceil(numcams/2)+overlap
            top_mat = np.hstack((top_mat, newcol))
        
        if self.margins[3] > 0: #bottom margin
            newcol = np.zeros((bot_mat.shape[0], self.margins[3]), dtype=np.int8) # bot_mat.shape[0] = grid_x*ceil(numcams/2)+overlap
            bot_mat = np.hstack((bot_mat, newcol))

        merged_mat = np.hstack((top_mat, bot_mat))

        if self.margins[0] > 0: #left margin
            newrow = np.zeros((self.margins[0], merged_mat.shape[1]), dtype=np.int8) # merged_mat.shape[1] = grid_y*ceil(numcams/2)+overlap
            merged_mat = np.vstack((newrow, merged_mat))
        if self.margins[1] > 0: #right margin
            newrow = np.zeros((self.margins[1], merged_mat.shape[1]), dtype=np.int8) # merged_mat.shape[1] = grid_y*ceil(numcams/2)+overlap
            merged_mat = np.vstack((merged_mat, newrow))
        
        return merged_mat

    @staticmethod
    def fromConfig():
        # read config
        config_filepath = utility.get_folder_path()+'data/config.json'
        num_cams = utility.parse_file(config_filepath, 'num_cams') # number of used cams

        # grid dims
        grid_x = utility.parse_file(config_filepath, 'gridsize_x')
        grid_y = utility.parse_file(config_filepath, 'gridsize_y')
        overlap_x = utility.parse_file(config_filepath, 'overlap_x') # overlapping rows/cols need to be subtracted from grid dimensions
        overlap_y = utility.parse_file(config_filepath, 'overlap_y')
        ret = GridData(num_cams, grid_x, grid_y, overlap_x, overlap_y)
        
        ret.margins = (utility.parse_file(config_filepath, 'margin_left'),
                utility.parse_file(config_filepath, 'margin_right'),
                utility.parse_file(config_filepath, 'margin_top'),
                utility.parse_file(config_filepath, 'margin_bottom'))

        return ret

def getConfig():
    # read config
    config_filepath = utility.get_folder_path()+'data/config.json'
    num_cams = utility.parse_file(config_filepath, 'num_cams') # number of used cams

    # grid dims
    grid_x = utility.parse_file(config_filepath, 'gridsize_x')
    grid_y = utility.parse_file(config_filepath, 'gridsize_y')
    overlap_x = utility.parse_file(config_filepath, 'overlap_x') # overlapping rows/cols need to be subtracted from grid dimensions
    overlap_y = utility.parse_file(config_filepath, 'overlap_y')
    margins = (utility.parse_file(config_filepath, 'margin_left'),
               utility.parse_file(config_filepath, 'margin_right'),
               utility.parse_file(config_filepath, 'margin_top').
               utility.parse_file(config_filepath, 'margin_bottom'))

    # order of cams?
    return (num_cams, grid_x, grid_y, overlap_x, overlap_y, margins)


# compartmentalised, to allow running on local thread instead of communicating over network
def runProcess(multiprocess_shared_dict):

    #(num_cams, grid_x, grid_y, overlap_x, overlap_y, margins) = getConfig()
    
    num_cams = utility.parse_file(utility.get_folder_path()+'data/config.json', 'num_cams') # number of used cams

    merged_mat = np.zeros(1)
    griddata = GridData.fromConfig() #GridData(num_cams, grid_x, grid_y, overlap_x, overlap_y)
    #griddata.margins = margins


    config_filepath = utility.get_folder_path()+'data/config.json'
    dest_addr = utility.parse_file(config_filepath, 'udp_destination_address')
    dest_port = utility.parse_file(config_filepath, 'udp_destination_port')
    # open UDP socket
    with udp.UDPsender(dest_addr, dest_port) as sender:

        try:
            while 1: # listen            
                for i in range(1, num_cams+1):
                    name = "grid" + ("" if i == 1 else str(i))
                    try:
                        data = multiprocess_shared_dict[name]
                    except KeyError:
                        print("cant find grid: "+name)
                        continue
                    if data is None or len(data) == 1: continue
                    pre_json = ('{"'+name+'":')
                    data = pre_json+data+"}"
                    merged_mat = griddata.parseMsg(data)

                    # np.set_printoptions(threshold=np.nan)
                    output = ""
                    if merged_mat is None: continue
                    for row in merged_mat:
                        for item in row:
                            output += item + " "
                        output += "\n"

                    # send output via UDP to 2nd machine
                    sender.sendMsg(str(output))

        except KeyboardInterrupt:   # because of waitng for udp messages, keyboard interrupt is highly unreliable
            return merged_mat   # debug

def runSocket():#num_cams, grid_x, grid_y, overlap_x, overlap_y):

    config_filepath = utility.get_folder_path()+'DATA/config.json'
    port = utility.parse_file(config_filepath, 'udp_destination_port')

    merged_mat = np.zeros(1)
    griddata = GridData.fromConfig()#GridData(num_cams, grid_x, grid_y, overlap_x, overlap_y)

    # open udp socket
    with udp.UDPreceiver(port) as listener:

        try:
            while 1: # listen
                data = listener.getMsg()

                merged_mat = griddata.parseMsg(data)
                #print(np.shape(merged_mat))
        except KeyboardInterrupt:
            return merged_mat   # send new output somewhere


if __name__ == '__main__':

    #(num_cams, grid_x, grid_y, overlap_x, overlap_y, margins) = getConfig()

    #if num_cams <= 1:
    #    print("num_cams == 1. Call me if you need me...")
    #    exit()

    merged_mat = runSocket()#num_cams, grid_x, grid_y, overlap_x, overlap_y)

    # np.set_printoptions(threshold=np.nan)
    print(merged_mat) # debug
