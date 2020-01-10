import numpy as np
import matplotlib.pyplot as plt
from scipy import ndimage, spatial, interpolate as interp
from skimage import morphology, filters
import math

class dnaTrace(object):

    '''
    This class gets all the useful functions from the old tracing code and staples
    them together to create an object that contains the traces for each DNA molecule
    in an image and functions to calculate stats from those traces.

    The traces are stored in dictionaries labelled by their gwyddion defined grain
    number and are represented as numpy arrays.

    The object also keeps track of the skeletonised plots and other intermediates
    in case these are useful for other things in the future.
    '''

    def __init__(self, full_image_data, gwyddion_grains, afm_image_name, pixel_size,
    number_of_columns, number_of_rows):
        self.full_image_data = full_image_data
        self.gwyddion_grains = gwyddion_grains
        self.afm_image_name = afm_image_name
        self.pixel_size = pixel_size
        self.number_of_columns = number_of_columns
        self.number_of_rows = number_of_rows

        self.gauss_image = []
        self.grains = {}
        self.dna_masks = {}
        self.skeletons = {}
        self.ordered_traces = {}
        self.fitted_traces = {}
        self.splined_traces = {}

        self.number_of_traces = 0

        #self.getParams()
        self.getNumpyArraysfromGwyddion()
        self.getSkeletons()
        self.getFittedTraces()
        self.determineLinearOrCircular()
        self.getOrderedTraces()
        self.getSplinedTraces()

    def getParams(self):

        ''' '''

        pass

    def getNumpyArraysfromGwyddion(self):

        ''' Function to get each grain as a numpy array which is stored in a
        dictionary

        Currently the grains are unnecessarily large (the full image) as I don't
        know how to handle the cropped versions

        I find using the gwyddion objects clunky and not helpful once the
        grains have been found '''

        for grain_num in set(self.gwyddion_grains):
            #Skip the background
            if grain_num == 0:
                continue

            #Saves each grain as a multidim numpy array
            single_grain_1d = np.array([1 if i == grain_num else 0 for i in self.gwyddion_grains])
            self.grains[grain_num] = np.reshape(single_grain_1d, (self.number_of_columns, self.number_of_rows))

        #Get a 20 A gauss filtered version of the original image - not sure this is actually used anymore
        sigma = (5/math.sqrt(self.pixel_size*1e8))/1.5
        self.gauss_image = filters.gaussian(self.full_image_data, sigma)

    def getSkeletons(self):

        ''' Function to make a skeleton for each of the grains in an image

        There is a bit of work to do here as the grains often have very rough
        edges '''

        for grain_num in sorted(self.grains.keys()):

            smoothed_grain = ndimage.binary_dilation(self.grains[grain_num], iterations = 1)

            sigma = (5/math.sqrt(self.pixel_size*1e8))/1.5
            very_smoothed_grain = ndimage.gaussian_filter(smoothed_grain, sigma)

            skeletonised_image = morphology.skeletonize(very_smoothed_grain)

            #The skeleton is saved as a 2D array of the skeleton coordinates relative to the original image
            self.skeletons[grain_num] = np.argwhere(skeletonised_image == 1)
            self.number_of_traces +=1


    def getOrderedTraces(self):

        '''The skeletonised traces are not in a sequence that follows the path
        of the DNA molecule - this function fixes this issue

        This could be replaced with a simpler and more elegant solution in the future

        This function is both overly complicated and buggy - room for improvement'''

        for dna_mol in sorted(self.fitted_traces.keys()):

            trace_coords = self.fitted_traces[dna_mol]

            first_point = np.array((trace_coords[0]))
            tree = spatial.cKDTree(trace_coords)
            ordered_points = np.empty((0,1))
            vector_angle_array = np.empty((0))

            query = tree.query(first_point, k=2)
            next_point = trace_coords[query[1][1]]
            last_point = next_point

            vector2 = np.subtract(next_point, last_point)
            third_point = first_point
            ordered_points = np.vstack((first_point, next_point))
            average_angle2 = 0

            contour_length = 0
            for i in range(len(trace_coords)-2):
            	query = tree.query(last_point, k = 30)
                ordered_points, vector_angle_array, vector2, average_angle2, end, last_point = self._getNextPoint(tree, next_point, query, ordered_points, vector_angle_array, trace_coords, vector2, average_angle2, last_point)
                ordered_points = np.vstack((ordered_points, last_point))
                if end == True:
            		break

            self.ordered_traces[dna_mol] = ordered_points

    def _getNextPoint(self, tree, next_point, query, ordered_points, vector_angle_array,
    trace_coords, vector2, average_angle2, last_point):

        '''Fairly nightmarish function to find the "next point" in the trace coordinates
        used in getFittedTraces function

        As with getOrderedTraces this function needs to be simplified - but works'''

    	points_tree = spatial.cKDTree(ordered_points)
    	end = False
    	scale_factor = 40
    	for j in range(len(query[1])):
    		next_point = trace_coords[query[1][j]]
    		vector1 = np.subtract(next_point, last_point)

    		angle = math.atan2(vector2[1], vector2[0]) - math.atan2(vector1[1], vector1[0])
    		if angle < 0:
    			angle += 2*math.pi
    		angle = math.degrees(angle)
    		if angle > 180:
    			angle -= 180
    		points_query = points_tree.query(next_point, k = 1)

    		last_vectors = np.append(vector_angle_array[-19:], angle)
    		average_angle1 = np.mean(last_vectors)

    		if points_query[0] == 0:
    			continue
    		elif len(ordered_points) < 10:
    			break
    		elif average_angle2 - average_angle1 == 0:
    			break
    		elif average_angle2 - average_angle1 > scale_factor:
    			continue
    		elif np.all(ordered_points[0] == next_point):
    			print 'end'
    			end = True
    			break
    		else:
    			for k in range(1,5,1):
    				try:
    					test_point = trace_coords[query[1][j+k]]

    					points_query = points_tree.query(test_point, k = 1)

    					if points_query[0] == 0:
    						continue
    					elif query[0][j+k] > query[0][j]*math.sqrt(2):
    						continue

    					test_vector = np.subtract(test_point, last_point)
    					test_angle = math.atan2(vector2[1], vector2[0]) - math.atan2(test_vector[1], test_vector[0])
    					if test_angle < 0:
    						test_angle += 2*math.pi
    					test_angle = math.degrees(test_angle)
    					if test_angle > 180:
    						test_angle -= 180

    					local_angles = np.mean(vector_angle_array[-20:])
    					local_average_angle = np.mean(np.append(vector_angle_array[-19:], angle))
    					test_average_angle = np.mean(np.append(vector_angle_array[-19:], test_angle))

    					if local_angles - local_average_angle > local_angles - test_average_angle:
    						next_point = test_point
    						angle = test_angle
    						break
    					if local_angles - local_average_angle == local_angles - test_average_angle:
    						test_vector = test_point - last_point

    						old_angle = math.atan2(vector2[1], vector2[0])
    						new_angle = math.atan2(vector1[1], vector1[0])
    						test_angle = math.atan2(test_vector[1], test_vector[0])

    						if old_angle - test_angle > old_angle - new_angle:
    							next_point = test_point
    						break
    				except IndexError:
    					break
    			break
    	average_angle2 = average_angle1
    	last_point = next_point
    	vector_angle_array = np.append(vector_angle_array, angle)

        return ordered_points, vector_angle_array, vector2, average_angle2, end, last_point

    def getFittedTraces(self):

        ''' Moves the coordinates from the skeletionised traces to lie on the
        highest point on the DNA molecule

        There is some kind of discrepency between the ordering of arrays from
        gwyddion and how they're usually handled in np arrays meaning you need
        to be careful when indexing from gwyddion derived numpy arrays'''

        for dna_num in sorted(self.grains.keys()):

            individual_skeleton = self.skeletons[dna_num]
            tree = spatial.cKDTree(individual_skeleton)

            #This sets a 5 nm search in a direction perpendicular to the DNA chain
            height_search_distance = int(15/(self.pixel_size*1e7))

            for coord_num, trace_coordinate in enumerate(individual_skeleton):

                height_values = None

                #I don't have a clue what this block of code is doing
                if trace_coordinate[0] < 0:
                    trace_coordinate[0] = height_search_distance
                elif trace_coordinate[0] >= self.number_of_rows - height_search_distance:
                    trace_coordinate[0] = trace_coordinate[0] = self.number_of_rows - height_search_distance
                elif trace_coordinate[1] < 0:
                    trace_coordinate[1] = (height_search_distance+1)
                elif trace_coordinate[1] >= self.number_of_columns - height_search_distance:
                    trace_coordinate[1] = self.number_of_columns - height_search_distance

                height_values = None
                neighbour_array = tree.query(trace_coordinate, k = 6)
                nearest_point = individual_skeleton[neighbour_array[1][3]]
                vector = np.subtract(nearest_point, trace_coordinate)
                vector_angle = math.degrees(math.atan2(vector[1],vector[0]))	#Angle with respect to x-axis

                if vector_angle < 0:
                    vector_angle += 180

                if 67.5 > vector_angle >= 22.5:	#aka if  angle is closest to 45 degrees
                    perp_direction = 'negative diaganol'
        			#positive diagonal (change in x and y)
        			#Take height values at the inverse of the positive diaganol (i.e. the negative diaganol)
                    y_coords = np.arange(trace_coordinate[1] - height_search_distance, trace_coordinate[1] + height_search_distance)[::-1]
                    x_coords = np.arange(trace_coordinate[0] - height_search_distance, trace_coordinate[0] + height_search_distance)

                elif 157.5 >= vector_angle >= 112.5:#aka if angle is closest to 135 degrees
                    perp_direction = 'positive diaganol'
                    y_coords = np.arange(trace_coordinate[1] - height_search_distance, trace_coordinate[1] + height_search_distance)
                    x_coords = np.arange(trace_coordinate[0] - height_search_distance, trace_coordinate[0] + height_search_distance)

                if 112.5 > vector_angle >= 67.5: #if angle is closest to 90 degrees
                    perp_direction = 'horizontal'
                    #print(trace_coordinate[0] - height_search_distance)
                    #print(trace_coordinate[0] + height_search_distance)
                    x_coords = np.arange(trace_coordinate[0] - height_search_distance, trace_coordinate[0]+height_search_distance)
                    y_coords = np.full(len(x_coords), trace_coordinate[1])

                elif 22.5 > vector_angle: #if angle is closest to 0 degrees
                    perp_direction = 'vertical'
                    y_coords = np.arange(trace_coordinate[1] - height_search_distance, trace_coordinate[1] + height_search_distance)
                    x_coords = np.full(len(y_coords), trace_coordinate[0])

                elif vector_angle >= 157.5: #if angle is closest to 180 degrees
                    perp_direction = 'vertical'
                    y_coords = np.arange(trace_coordinate[1] - height_search_distance, trace_coordinate[1] + height_search_distance)
                    x_coords = np.full(len(y_coords), trace_coordinate[0])

                #Use the perp array to index the guassian filtered image
                perp_array = np.column_stack((x_coords, y_coords))
                height_values = self.gauss_image[perp_array[:,1],perp_array[:,0]]

                #Use interpolation to get "sub pixel" accuracy for heighest position
                if perp_direction == 'negative diaganol':
                    int_func = interp.interp1d(perp_array[:,0], np.ndarray.flatten(height_values), kind = 'cubic')
                    interp_heights = int_func(np.arange(perp_array[0,0], perp_array[-1,0], 0.1))

                elif perp_direction == 'positive diaganol':
                    int_func = interp.interp1d(perp_array[:,0], np.ndarray.flatten(height_values), kind = 'cubic')
                    interp_heights = int_func(np.arange(perp_array[0,0], perp_array[-1,0], 0.1))

                elif perp_direction == 'vertical':
                    int_func = interp.interp1d(perp_array[:,1], np.ndarray.flatten(height_values), kind = 'cubic')
                    interp_heights = int_func(np.arange(perp_array[0,1], perp_array[-1,1], 0.1))

                elif perp_direction == 'horizontal':
                    #print(perp_array[:,0])
                    #print(np.ndarray.flatten(height_values))
                    int_func = interp.interp1d(perp_array[:,0], np.ndarray.flatten(height_values), kind = 'cubic')
                    interp_heights = int_func(np.arange(perp_array[0,0], perp_array[-1,0], 0.1))
                else:
                    quit('A fatal error occured in the CorrectHeightPositions function, this was likely caused by miscalculating vector angles')

                #Make "fine" coordinates which have the same number of coordinates as the interpolated height values
                if perp_direction == 'negative diaganol':
                    fine_x_coords = np.arange(perp_array[0,0], perp_array[-1,0], 0.1)
                    fine_y_coords = np.arange(perp_array[-1,1], perp_array[0,1], 0.1)[::-1]
                elif perp_direction == 'positive diaganol':
                    fine_x_coords = np.arange(perp_array[0,0], perp_array[-1,0], 0.1)
                    fine_y_coords = np.arange(perp_array[0,1], perp_array[-1,1], 0.1)
                elif perp_direction == 'vertical':
                    fine_y_coords = np.arange(perp_array[0,1], perp_array[-1,1], 0.1)
                    fine_x_coords = np.full(len(fine_y_coords), trace_coordinate[0], dtype = 'float')
                elif perp_direction == 'horizontal':
                    fine_x_coords = np.arange(perp_array[0,0], perp_array[-1,0], 0.1)
                    fine_y_coords = np.full(len(fine_x_coords), trace_coordinate[1], dtype = 'float')

                #Get the coordinates relating to the highest point in the interpolated height values
                fine_coords = np.column_stack((fine_x_coords, fine_y_coords))
                sorted_array = fine_coords[np.argsort(interp_heights)]
                highest_point = sorted_array[-1]

                try:
                    fitted_coordinate_array = np.vstack((fitted_coordinate_array, highest_point))
                except UnboundLocalError:
                    fitted_coordinate_array = highest_point

            self.fitted_traces[dna_num] = fitted_coordinate_array
            del fitted_coordinate_array

    def determineLinearOrCircular(self):

        ''' Its important for the "ordering" function that it is known if a
        given DNA molecule is linear or circular as this will change how the
        "ordering" of the coordinates is done '''

        pass

    def getSplinedTraces(self):

        '''Gets a splined version of the fitted trace - useful for finding the
        radius of gyration etc

        This function actually calculates the average of several splines which
        is important for getting a good fit on the lower res data'''

        step_size = 10 #arbitary number for time being

        for dna_num in sorted(self.ordered_traces.keys()):

            single_fitted_trace = np.unique(self.ordered_traces[dna_num], axis = 0)

            nbr = len(single_fitted_trace[:,0])
            count = 0

            #This function makes 5 splined plots and averages them
            for i in range(step_size):
                    try:
                        #nbr = len(single_fitted_trace[:,0])
                        x = [single_fitted_trace[:,0][j] for j in range(i,nbr,step_size)]
                        y = [single_fitted_trace[:,1][j] for j in range(i,nbr,step_size)]
                        tck,u = interp.splprep([x,y], s=0, per=1)
                        out = interp.splev(np.linspace(0,1,nbr), tck)
                        splined_coords = np.column_stack((out[0], out[1]))
                        print(np.shape(out), np.shape(splined_coords))
                        try:
                            rolling_total = np.add(rolling_total, splined_coords)
                        except UnboundLocalError:
                            rolling_total = splined_coords
                        spline_success = True
                        count +=1

                    #Not a great sign that system errors are being caught hah
                    except SystemError:
                        print 'Could not spline coordinates'
                        spline_success = False
                        splined_coords = None
                        continue
                    except TypeError:
                        print 'The trace is too short or something'
                        spline_success = False
                        splined_coords = None
            if spline_success:
                rolling_average = np.divide(rolling_total, [count, count])

                nbr = len(rolling_average[:,0])
                x = rolling_average[:,0]
                y = rolling_average[:,1]
                tck,u = interp.splprep([x,y], s=0, per=1)
                out = interp.splev(np.linspace(0,1,nbr), tck)

                splined_coords = np.column_stack((out[0], out[1]))
            else:
                splined_coords = None

            self.splined_traces[dna_num] = splined_coords

            del rolling_total

    def showTraces(self):

        plt.pcolor(self.full_image_data)
        plt.colorbar()
        for dna_num in sorted(self.ordered_traces.keys()):
            print('adding new line')
            plt.plot(self.ordered_traces[dna_num][:,0], self.ordered_traces[dna_num][:,1])
        plt.show()

    def findWrithe(self):
        pass

    def findRadiusOfCurvature(self):
        pass
