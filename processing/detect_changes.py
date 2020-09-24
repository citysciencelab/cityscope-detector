import numpy as np

class Change:
    temporalSmoothingWindow = 5 # todo: get from cfg

    def __init__(self, grid):
        self.grid = grid
        self.changeCounter = {}


    def find_changes(self, new_grid, gridsize_x, gridsize_y) -> list:
        """
        Returns a list of changes between two grids (only returns the new value)
        :param grid_a:
        :param grid_b:
        :return: (u, v, new value)
        """

        # TODO shape assertions

        # create a matrix of same dimensions with True/False values depending on equality
        equal = (self.grid == new_grid)
        num_changes = gridsize_x*gridsize_y - np.sum(equal)

        # get indices of changes, array of same dimensions. first dimension is always 0 for us
        changed = np.where(equal == 0)

        # turn the columns into shape (1, N) arrays to concatenate
        rows = np.array([changed[0]]).transpose()
        columns = np.array([changed[1]]).transpose()

        # concatenate u and v values into a 2xN array
        changed_cells = np.concatenate([rows, columns], axis=1)

        changes = []
        deleteList = []
        for (point, numFrames) in self.changeCounter.items():   # temporal smoothing of changes
            (row, column) = point
            self.changeCounter[row, column] += 1    # colour has been constant for another frame
            
            # temporal smoothing (avoid flickering signals)
            if numFrames == self.temporalSmoothingWindow:   # change has been persistent for x frames -> return
                new_value = new_grid[row, column]
                changes.append((row, column, new_value))    # return value
                print("change append: " + str(point) + " - " + str(new_value))
                deleteList.append(point)

        for point in deleteList:    # delete already published changes, so they don't clutter
            (row, column) = point
            del self.changeCounter[row, column]
        deleteList.clear()


        for (row, column) in changed_cells: # detect changes
            new_value = new_grid[row, column]
            old_value = self.grid[row, column]
            if new_value is not old_value:  # change detected
                self.changeCounter[(row, column)] = 1 # consider for temporal smoothing


        self.grid = new_grid  # remember last state for change detection
        return changes
