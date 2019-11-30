import numpy as np


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

    def __init__(full_image_data, series_of_grains, afm_image_name, dna_masks = {}, skeletons = {}, fitted_traces = {},
    splined_traces = {}):
        self.full_image_data = full_image_data
        self.series_of_grains = series_of_grains
        self.afm_image_name = afm_image_name
        self.dna_masks = dna_masks
        self.skeletons = skeletons
        self.fitted_traces = fitted_traces
        self.splined_traces = splined_traces

        self.getParams()
        self.getNumpyArraysfromGrains()
        self.getSkeletons()
        self.getOrderedTrace()
        self.getFittedTraces()
        self.getSplinedTraces()

    def getParams(self):
        #do something with some of the gwyddion objects to get important parameters
        pass

    def getNumpyArraysfromGrains(self):

        ''' Function to get each grain as a numpy array which is stored in a
        dictionary

        I find using the gwyddion objects clunky and not helpful once the
        grains have been found '''

        #for num, i in enumerate(series_of_grains):
            #self.dna_masks[num] = np.array(series_of_grains[num])
        pass

    def getSkeletons(self):

        '''Does skeletonisation for all of the dna_masks (grains) made in Alice's
        part of the code'''

        for dna_mol_no in sorted(self.dna_masks.keys()):
            skele = morphology.skeletonize(mask3)
            self.skeleton[dna_mol_no] = skele

        print('Skeletonising finished for all molecules from AFM image %s' % self.afm_image_name)

    def getOrderedTraces(self):

        '''The skeletonised traces are not in a sequence that follows the path
        of the DNA molecule - this function fixes this issue

        This could be replaced with a simpler and more elegant solution in the future

        This function is both slow and buggy - room for improvement'''

        for dna_mol in sorted(self.skeletons(keys)):
            #def FindOrderedTrace(trace_area, trace_coords2d, xmid, ymid, square_size, pixel_size):
            trace_coords = self.skeleton[dna_mol]

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
                ordered_points, vector_angle_array, vector2, average_angle2, end, last_point = FindNextPoint(tree, next_point, query, ordered_points, vector_angle_array, trace_coords, vector2, average_angle2, last_point)
                ordered_points = np.vstack((ordered_point, next_point))
                if end == True:
            		break

            self.ordered_trace[dna_num] = ordered_points

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

    		angle = atan2(vector2[1], vector2[0]) - atan2(vector1[1], vector1[0])
    		if angle < 0:
    			angle += 2*pi
    		angle = degrees(angle)
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
    					elif query[0][j+k] > query[0][j]*sqrt(2):
    						continue

    					test_vector = np.subtract(test_point, last_point)
    					test_angle = atan2(vector2[1], vector2[0]) - atan2(test_vector[1], test_vector[0])
    					if test_angle < 0:
    						test_angle += 2*pi
    					test_angle = degrees(test_angle)
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

    						old_angle = atan2(vector2[1], vector2[0])
    						new_angle = atan2(vector1[1], vector1[0])
    						test_angle = atan2(test_vector[1], test_vector[0])

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

    def getFittedTraces(self, DNA_map, coordinates, pixel_size, xscan, yscan):

        ''' Moves the coordinates from the skeletionised traces to lie on the
        highest point on the DNA molecule '''

    	tree = spatial.cKDTree(coordinates)
    	pixel_distance = int(40/sqrt(pixel_size))

    	sigma = (20/sqrt(pixel_size))/1.5

    	DNA_map = filters.gaussian_filter(DNA_map, sigma)
    	#plt.figure()
    	for i in coordinates:
    		if i[0] < 0:
    			i[0] = pixel_distance
    		elif i[0] >= len(xscan)-pixel_distance:
    			i[0] = i[0] = len(xscan)-pixel_distance
    		elif i[1] < 0:
    			i[1] = (pixel_distance+1)
    		elif i[1] >= len(yscan)-pixel_distance:
    			i[1] = len(yscan) - pixel_distance

    		height_values = None
    		neighbour_array = tree.query(i, k = 6)
    		nearest_point = coordinates[neighbour_array[1][3]]
    		vector = np.subtract(nearest_point, i)
    		vector_angle = degrees(atan2(vector[1],vector[0]))	#Angle with respect to x-axis

    		if vector_angle < 0:
    			vector_angle += 180

    		if 67.5 > vector_angle >= 22.5:	#aka if  angle is closest to 45 degrees
    			perp_direction = 'negative diaganol'
    			#positive diagonal (change in x and y)
    			#Take height values at the inverse of the positive diaganol (i.e. the negative diaganol)
    			y_coords = np.arange(i[1] - pixel_distance, i[1] + pixel_distance)[::-1]
    			x_coords = np.arange(i[0] - pixel_distance, i[0] + pixel_distance)

    		elif 157.5 >= vector_angle >= 112.5:#aka if angle is closest to 135 degrees
    			perp_direction = 'positive diaganol'
    			y_coords = np.arange(i[1] - pixel_distance, i[1] + pixel_distance)
    			x_coords = np.arange(i[0] - pixel_distance, i[0] + pixel_distance)

    		if 112.5 > vector_angle >= 67.5: #if angle is closest to 90 degrees
    			perp_direction = 'horizontal'
    			x_coords = np.arange(i[0] - pixel_distance, i[0]+pixel_distance)
    			y_coords = np.full(len(x_coords), i[1])

    		elif 22.5 > vector_angle: #if angle is closest to 0 degrees
    			perp_direction = 'vertical'
    			y_coords = np.arange(i[1] - pixel_distance, i[1] + pixel_distance)
    			x_coords = np.full(len(y_coords), i[0])

    		elif vector_angle >= 157.5: #if angle is closest to 180 degrees
    			perp_direction = 'vertical'
    			y_coords = np.arange(i[1] - pixel_distance, i[1] + pixel_distance)
    			x_coords = np.full(len(y_coords), i[0])

    		perp_array = np.column_stack((x_coords, y_coords))

    		#plt.plot(perp_array[:,1], perp_array[:,0])
    		#plt.draw()
    		for j in perp_array:
    			height = DNA_map[j[0], j[1]]
    			if height_values == None:
    				height_values = height
    			else:
    				height_values = np.vstack((height_values, height))

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
    			int_func = interp.interp1d(perp_array[:,0], np.ndarray.flatten(height_values), kind = 'cubic')
    			interp_heights = int_func(np.arange(perp_array[0,0], perp_array[-1,0], 0.1))
    		else:
    			quit('A fatal error occured in the CorrectHeightPositions function, this was likely caused by miscalculating vector angles')

    		if perp_direction == 'negative diaganol':
    			fine_x_coords = np.arange(perp_array[0,0], perp_array[-1,0], 0.1)
    			fine_y_coords = np.arange(perp_array[-1,1], perp_array[0,1], 0.1)[::-1]
    		elif perp_direction == 'positive diaganol':
    			fine_x_coords = np.arange(perp_array[0,0], perp_array[-1,0], 0.1)
    			fine_y_coords = np.arange(perp_array[0,1], perp_array[-1,1], 0.1)
    		elif perp_direction == 'vertical':
    			fine_y_coords = np.arange(perp_array[0,1], perp_array[-1,1], 0.1)
    			fine_x_coords = np.full(len(fine_y_coords), i[0], dtype = 'float')
    		elif perp_direction == 'horizontal':
    			fine_x_coords = np.arange(perp_array[0,0], perp_array[-1,0], 0.1)
    			fine_y_coords = np.full(len(fine_x_coords), i[1], dtype = 'float')


    		fine_coords = np.column_stack((fine_x_coords, fine_y_coords))

    		sorted_array = fine_coords[np.argsort(interp_heights)]
    		highest_point = sorted_array[-1]
    		try:
    			fitted_coordinate_array = np.vstack((fitted_coordinate_array, highest_point))
    		except UnboundLocalError:
    			fitted_coordinate_array = highest_point

            #plt.pcolor(xlimit, ylimit, DNA_map, cmap = 'binary')
        	#plt.plot(coordinates[:,1], coordinates[:,0], '.')
        	#plt.plot(fitted_coordinate_array[:,1], fitted_coordinate_array[:,0], '.')
        	#plt.show()

        	return fitted_coordinate_array


    def getSplinedTraces(self):

        '''Gets a splined version of the fitted trace - useful for finding the
        radius of gyration etc

        This function actually calculates the average of several splines which
        is important for getting a good fit on the lower res data'''

        step_size = 10 #arbitary number for time being

        for dna_num in self.fitted_traces.keys():

            #This function makes 5 a bunch of splined plots and averages them
        	for i in range(step_size):
            		try:
            			nbr = len(ordered_points[:,0])
            			x = [ordered_points[:,0][j] for j in range(i,nbr,step_size)]
            			y = [ordered_points[:,1][j] for j in range(i,nbr,step_size)]
            			tck,u = interp.splprep([x,y], s=0, per=1)
            			out = interp.splev(np.linspace(0,1,nbr), tck)
            			splined_coords = np.column_stack((out[0], out[1]))
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
            		spline_coords = None

                self.splined_coords[dna_num] = spline_coords

    def findWrithe(self):
        pass

    def findRadiusOfCurvature(self):
        pass