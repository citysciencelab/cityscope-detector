import pickle
import json

from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from autobahn.twisted.wamp import ApplicationSession, ApplicationRunner
import numpy as np

from helpers import udp
from helpers import utility
from processing import detect_changes

class Component(ApplicationSession):

    gridsize_x = 26*2-1  # DEFAULT
    gridsize_y = 28*2-1  # DEFAULT
    max_grids = 1

    # bbox = [0, 0, 0, 0]

    previousGrid = None

    changeDet = None


    def initialise_grids(self, max_grids):
        # the array of grids has shape (max_grids, gridsizex, gridsizey)
        self.grids = np.zeros(shape=(max_grids, self.gridsize_x, self.gridsize_y), dtype=int)
        self.last_grid = np.zeros(shape=(1, self.gridsize_x, self.gridsize_y), dtype=int)

    def print_changes(self, changes: list) -> None:
        for (row, column, new_value) in changes:
            print("INFO: At Row: {r}, Column: {c} we found new value {v}".format(r=row, c=column, v=new_value))

    def strtoarr(self, string):
        return string.split()

    @inlineCallbacks
    def onJoin(self, details):
        print("session attached")

        self.initialise_grids(self.max_grids)

        cfg_path = utility.get_folder_path() + "data/config.json"
        num_cams = utility.parse_file(cfg_path, 'num_cams')
        overlap_x = utility.parse_file(cfg_path, 'overlap_x') # overlapping rows/clos need to be subtracted from grid dimensions
        overlap_y = utility.parse_file(cfg_path, 'overlap_y')
        margins = (utility.parse_file(cfg_path, 'margin_left'),
                   utility.parse_file(cfg_path, 'margin_right'),
                   utility.parse_file(cfg_path, 'margin_top'),
                   utility.parse_file(cfg_path, 'margin_bottom'))
        self.gridsize_x = utility.parse_file(cfg_path, 'gridsize_x') * (2 if num_cams >= 2 else 1) - overlap_x + margins[0] + margins[1]  # 2 or 4 cams implies double horizontal dimension
        self.gridsize_y = utility.parse_file(cfg_path, 'gridsize_y') * (2 if num_cams == 4 else 1) - overlap_y + margins[2] + margins[3]  # 4 cams implies double vertical dimension 
        port = utility.parse_file(cfg_path, 'udp_destination_port')
        topic = utility.parse_file(cfg_path, 'ws_topic')

        with udp.UDPreceiver(port) as listener:
            while 1:
                # get grid from udp
                grid = self.strtoarr(listener.getMsg()) # formatting
                if not grid:
                    print("empty grid!")
                    continue
                grid = np.reshape(grid, (self.gridsize_x, self.gridsize_y)) # casting to np array
                
                if self.previousGrid is None:   # skip first signal
                    self.previousGrid = grid
                    continue

                if self.changeDet is None:
                    self.changeDet = detect_changes.Change(self.previousGrid)
                # compare to last grid
                changes = self.changeDet.find_changes(grid, self.gridsize_x, self.gridsize_y)

                # publish message
                if changes:
                    print('publishing '+topic, changes)
                    self.publish(topic, pickle.dumps(changes, protocol=0))

                    self.previousGrid = grid
                    yield sleep(0.001)

    # def on_event_bbox(self, x0, y0, x1, y1):
    #     print("INFO: Got new BBOX: {}".format((x0, y0, x1, y1)))
    #     self.bbox = [x0, y0, x1, y1]


if __name__ == '__main__':
    realm = u"realm"
    router = u"AUTOBAHN_ROUTER"

    cfg_path = utility.get_folder_path() + "data/config.json"
    ws_server = utility.parse_file(cfg_path, 'ws_server')

    runner = ApplicationRunner(
        ws_server,
        realm
    )
    runner.run(Component)
