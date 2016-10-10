import numpy as np

from subprocess import call

#coil G - code generator for saddle coils.

#TODO:
#add circular arcs to smooth corners.
#Use G2 for clockwise arcs and G3 for counterclockwise arcs.
#Use G17 to set the z axis as the axis of rotation (should be standard on all 3 axes machines)

#proceed as follows:
#position the machine at the start of the arc to be cut.
#like
#G0 X-3.2 Y0
#then use G2 giving the final coordinates of the arc, say X0 Y3.2 and the center of the arc as an offset to the starting point.
#G2 X0 Y3.2 3.2 0 will draw such a cut.

class Coordinate(object):
    """A Coordinate is just a set of values, x and y.
    This class could be replaced with a numpy array, but the shiftX and shiftY methods make the code mor
    """
    def __init__(self, x, y):
        """x: x value of coordinate
        y: y value of coordinate"""
        
        self.x = x
        self.y = y

    def __add__(self, other):
        return Coordinate(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        print "other.x: ", other.x
        return Coordinate(self.x - other.x, self.y - other.y)

    def magnitude(self):
        return np.sqrt(self.x**2 + self.y**2)
    
    def normalize(self):
        mag = self.magnitude()
        self.x = self.x/mag
        self.y = self.y/mag
    
    def shiftX(self, x):
        return Coordinate(self.x + x, self.y)

    def shiftY(self, y):
        return Coordinate(self.x, self.y + y)


class Straight(object):
    """A class representing a straight cut."""

    def __init__(self, point, p0 = Coordinate(0, 0)):
        """Specify a straight line"""
        self.destination = point + p0

    def gCode(self):
        return "G1 X{0:.3f} Y{1:.3f}".format(self.destination.x, self.destination.y)

    def tikzCode(self):
        return " -- ({0:.3f}, {1:.3f})".format(self.destination.x, self.destination.y)

class ClockwiseArc(object):
    """A class representing a clockwise arc."""
    def __init__(self, point, xC, yC, p0 = Coordinate(0, 0)):
        """Specify a Clockwise Arc
        x: x component of destination
        y: y component of destination
        xC: x offset of arc center
        yC: y offset of arc center"""
        self.destination = point + p0
        self.arcCenter = Coordinate(xC, yC)

    def gCode(self):
        return "G2 X{0:.3f} Y{1:.3f} I{2:.3f} J{3:.3f}".format(self.destination.x, self.destination.y, self.arcCenter.x, self.arcCenter.y)

    def tikzCode(self):
        r = self.arcCenter.magnitude()

        #we have the arc center and we know it is clockwise. Tikz needs startAngle, stop Angle and radius
        #the start angle is opposite the center point. If arcCenter.x > 0, the start angle is 180 degrees. The stop angle is 90 deg less.
        start = (np.angle(self.arcCenter.x + 1j*self.arcCenter.y)/np.pi*180 + 180) % 360
        stop = start - 90
        
        return " arc ({0}:{1}:{2})".format(start, stop, r)

class CounterClockwiseArc(ClockwiseArc):
    """Inherits from clockwise arc. Overwrites gCode generation and TikZ Code generation."""
    def gCode(self):
        return "G3 X{0:.3f} Y{1:.3f} I{2:.3f} J{3:.3f}".format(self.destination.x, self.destination.y, self.arcCenter.x, self.arcCenter.y)

    def tikzCode(self):
        r = self.arcCenter.magnitude()

        #we have the arc center and we know it is clockwise. Tikz needs startAngle, stop Angle and radius
        #the start angle is opposite the center point. If arcCenter.x > 0, the start angle is 180 degrees. The stop angle is 90 deg less.
        start = (np.angle(self.arcCenter.x + 1j*self.arcCenter.y)/np.pi*180 + 180) % 360
        stop = start + 90
        return " arc ({0}:{1}:{2})".format(start, stop, r)
    
    
class Path(object):
    """A base class to represent a path. For our purposes, a path is a list of either straight lines or clockwise or counterclockwise arcs. 
    """

    def __init__(self, p0):
        """Init Method of path. This will set the starting point for the path."""
        self.p0 = p0
        
        self.path = []

    def gCode(self, feed = 7.5):
        """Return the gCode of the path.

        - feed: optional, specify feed for cutting operations (defaults to 7.5)
        """
        retVal = "G0 Z5\n"
        retVal += "G0 X{0:.3f} Y{1:.3f}\n".format(self.p0.x, self.p0.y)
        retVal += "G0 Z0.5\n"
        retVal += "G01 Z-0.3 F{:.3f}\n".format(feed)

        for p in self.path:
            retVal += p.gCode() + "\n"

        retVal += "G0 Z5\n"
        return retVal

    def tikzCode(self):
        retVal = "\draw ({0:.3f},{1:.3f}) ".format(self.p0.x, self.p0.y);
        for p in self.path:
            retVal += p.tikzCode()

        retVal += ";\n"
        return retVal

class SaddleCoil(object):
    """A class to represent a simple saddle coil, as machined from a 2D sheet.

        Its purpose is to generate G-Code to cut a saddle coil using a CNC mill.
        Optionally generate tikz code to visualize the result using LaTeX."""
    
    def __init__(self, h, r, alpha, width, cutterDiameter, gap = 1, legLength = 10, cornerRadius = 0.5, compact = False):
        """This routine creates the coordinates for the cuts.
        
        - h: height of the saddle coil as distance between center of traces
        - r: radius (!) of the coil, not diameter
        - alpha: opening angle of the saddle coil
        - width: width of the copper traces
        - cutterDiameter: cutting diameter of the tool.
        - gap: Additional gap to increase the minimal distance between different segments of the coil.
        - legLength: Length of the coils legs.
        - cornerRadius: A radius > cutter Diameter will introduce rounded corners.
        - compact: compact = true is required when the coil radius approaches the cutter diameter. Drops points 3,4 and 19, 20, shifts pts 2 and 21 below 5 and 18

        All units are in mm.
        #first Cut start at the left leg on the left bottom side.
        # 05=====================06          13=====================14
        # ||                     ||          ||                     ||
        # ||  18=============17  ||          ||  10=============09  ||
        # ||  ||             ||  ||          ||  ||             ||  ||
        # ||  ||             ||  ||          ||  ||             ||  ||
        # ||  ||             ||  ||          ||  ||             ||  ||
        # ||  ||             ||  ||          ||  ||             ||  ||
        # ||  19===========20||  07==========12==11=============08  ||
        # ||               ||||                                     ||
        # 04===========03  ||16=====================================15    
        #              ||  21========22      l0=======================l1
        #              ||            ||      ||                       ||
        #              02=======01   ||      ||                       ||
        #                       ||   ||      l3=======================l2
        #                       ||   ||   g  
        #                       00===23      
        ###########################################################"""

        assert cornerRadius >= cutterDiameter, "Corner Radius required to be greater / equal cutter Diameter."

        self.cornerRadius = cornerRadius
        
        self.circumference = 2*np.pi*r

        self.cD = cutterDiameter
        self.width = width

        cD2 = self.cD/2.
        w2 = self.width/2.

        #compensate arcs for cutter diameter
        self.radii = {"s" : cornerRadius -cD2, "l" : cornerRadius + cD2}

        #Setup a few useful coordinates along the path:        
        yInnerBottom = w2 + cD2
        yInnerTop = h - w2 - cD2

        yOuterBottom = 0 - w2 - cD2
        yOuterTop = h + w2 + cD2

        #xInnerLeft: first or left loop of the coil, inside left cutter coordinates
        xInnerLeft_Left = self.angleToX(0) + w2 + cD2 
        xInnerLeft_Right = self.angleToX(alpha) - w2 - cD2

        xOuterLeft_Left = self.angleToX(0) - w2 - cD2
        xOuterLeft_Right = self.angleToX(alpha) + w2 + cD2

        #xInnerRight: second or right loop of the coil
        xInnerRight_Left = self.angleToX(180) + w2 + cD2 
        xInnerRight_Right = self.angleToX(180 + alpha) - w2 - cD2

        xOuterRight_Left = self.angleToX(180) - w2 - cD2 
        xOuterRight_Right = self.angleToX(180 + alpha) + w2 + cD2

 
        #arc radii are either small or large, depending on whether the coil material is left on the outside of the arc"
        #start with the bend at postion 0"
        #pos 11 and 12 are deliberately small bends so as not to remove too much material.
        bends = "sslslllssssssllllssslsls"
        #set up the points
        #the point definition has all the correct points if the corners are not smoothed.
        points = [Coordinate(self.angleToX(180) - 3*w2 - 3*cD2 - gap, yOuterBottom - legLength)]
        points.append(points[-1].shiftY(legLength - gap - 2*w2 - 2*cD2))
        points.append(Coordinate(self.angleToX(alpha) - 3*w2 - 3*cD2 - gap, points[-1].y))
        points.append(Coordinate(points[-1].x, yOuterBottom))
        points.append(Coordinate(xOuterLeft_Left, yOuterBottom))#now we have reached point 4, the outer lower left corner of the left turn.
        points.append(Coordinate(xOuterLeft_Left, yOuterTop))
        points.append(Coordinate(xOuterLeft_Right, yOuterTop))
        points.append(Coordinate(xOuterLeft_Right, yInnerBottom))
        points.append(Coordinate(xInnerRight_Right, yInnerBottom))
        points.append(Coordinate(xInnerRight_Right, yInnerTop))
        points.append(Coordinate(xInnerRight_Left, yInnerTop))
        points.append(Coordinate(xInnerRight_Left, yInnerBottom+gap))
        points.append(Coordinate(xOuterRight_Left, yInnerBottom+gap))
        points.append(Coordinate(xOuterRight_Left, yOuterTop))
        points.append(Coordinate(xOuterRight_Right, yOuterTop))
        points.append(Coordinate(xOuterRight_Right, yOuterBottom))
        points.append(Coordinate(xInnerLeft_Right, yOuterBottom))
        points.append(Coordinate(xInnerLeft_Right, yInnerTop))
        points.append(Coordinate(xInnerLeft_Left, yInnerTop))
        points.append(Coordinate(xInnerLeft_Left, yInnerBottom))
        points.append(Coordinate(xInnerLeft_Right - gap, yInnerBottom))
        points.append(Coordinate(xInnerLeft_Right - gap, yOuterBottom - gap)) #21
        points.append(Coordinate(points[0].x + 2*w2 + 2*cD2, yOuterBottom - gap)) # 22
        points.append(points[0].shiftX(2*w2 + 2*cD2))

        if compact == True:
            points[2].x = points[5].x
            points[21].x = points[18].x
            
            del points[19:21]
            del points[3:5]

            bends = bends[:3] + bends[5:19] + bends[21:]
        
        # add a leg keep it nearly straight, use small bends
        bends_leg = "ssss"
        points2 = [Coordinate(xOuterRight_Left, yOuterBottom - 2*cD2 - gap)]
        points2.append(points2[0].shiftX(legLength + 2*w2 + gap + cD2))
        points2.append(points2[1].shiftY(-2*w2 - 2*cD2))
        points2.append(points2[0].shiftY(-2*w2 - 2*cD2))
        
        minX = min(p.x for p in points +  points2)
        minY = min(p.y for p in points + points2)

        #shift points so that all cuts have x,y>0.
        points = [point - Coordinate(minX - cD2, minY - cD2) for point in points]
        points2 = [point - Coordinate(minX - cD2, minY - cD2) for point in points2]
        
        firstCut = self.generatePathFromPoints(points, bends)
        secondCut = self.generatePathFromPoints(points2, bends_leg)
                
        self.cuts = [firstCut, secondCut]

        self.maxX = max([p.x for p in points + points2])
        self.maxY = max([p.y for p in points + points2])

        #store the points with the module object so that the point numbers can be drawn.
        self.points = points
        self.points2 = points2
        
    def generatePathFromPoints(self, points, bends):
        cut = Path(points[0])
        for i in range(len(points)):
            previousPoint = i
            thisPoint = (i +1 ) % len(points)
            nextPoint = (i + 2) % len(points)
            
            direction = points[thisPoint] - points[previousPoint]
            direction.normalize()

            direction2 = points[nextPoint] - points[thisPoint]
            direction2.normalize()
            
            radius = self.radii[bends[thisPoint]]

            arcStart = points[thisPoint] - Coordinate(direction.x*radius, direction.y*radius)
            arcStop = points[thisPoint] + Coordinate(direction2.x*radius, direction2.y*radius)

            arcOffset = Coordinate(direction2.x*radius, direction2.y*radius)
            
            cut.path.append(Straight(arcStart))

            #choose counter clockwise or clockwise arc depending on vector product pos. or negative
            if direction.x*direction2.y - direction.y*direction2.x > 0: 
                cut.path.append(CounterClockwiseArc(arcStop, arcOffset.x, arcOffset.y))
            else:
                cut.path.append(ClockwiseArc(arcStop, arcOffset.x, arcOffset.y))

        return cut
        
    def angleToX(self, angle):
         """ Calculate X-position from angle. This function also introduces the startAngle.
         angleToX should be called once for every calculation of an X value."""
         return self.circumference*angle/360.
   
    def generateGCode(self, feed = 7.5, filename = ""):
        """Generate GCode for the specified coil.

        - feed: optional argument, defaults to 7.5
        - cutteDiameter: specify cutter Diameter for cutter compensation. 
        - filename: if specified, the g code is saved, if not it is printed to STDOUT."""
        code = """;G-Code generated by coilCalculator.py
;maxX : {0:.3f}
;maxY : {1:.3f}
G90
G00 Z5.00
M10 O6.1\n""".format(self.maxX, self.maxY)

        for path in self.cuts:
           code += path.gCode()

        
        code += "M10 O6.0\n"

        if len(filename) > 0:
            f = open(filename, "w")
            f.write(code)
            f.close()
        else:
            print code
        return code

    def generateTikzCode(self, filename = "temp.tex", compileFile = False, includePoints = False, scale = 1, includePointsText = False, includeGCode = False):
        """Export Coil to a TeX file. 

        The file needs to be compiled manually using e.g. pdflatex."""

        header = """\documentclass{article}
\usepackage{tikz}
\\begin{document}
\\begin{figure}
\centering
\\begin{tikzpicture}[scale = """

        header += "{0}]".format(scale/2.)

        footer = """\end{tikzpicture}
  \end{figure}
        """

        file = open(filename, "w")
        file.write(header)

        code = ""
        for path in self.cuts:
            #file.write(path.tikzCode())
            code += path.tikzCode()
            
        if includePoints:
            if scale > 0.9:
                circleString = "\draw ({0}, {1}) circle (0.5);\n"
            else:
                circleString = ""
                
            for i, p in enumerate(self.points):
                code += circleString + "\draw ({0}, {1}) node{{{2}}};\n".format(p.x, p.y, i)
            for i, p in enumerate(self.points2):
                code += circleString + "\draw ({0}, {1}) node{{{2}}};\n".format(p.x, p.y, i)

        code += "\draw [|-|, thick](-3, 0) -- (-3, {0}) node[pos=0.5, anchor = south, rotate = 90]{{{0} mm}};\n".format(self.maxY);
        code += "\draw [|-|, thick](0, -3) -- ({0}, -3 ) node[pos=0.5, anchor = north]{{{0:.2f} mm}};\n".format(self.maxX);
        print code
                
        file.write(code)
        file.write(footer)

        file.write("Corner Radius: {0} mm\n\n".format(self.cornerRadius))

        if includePointsText:
            file.write("\n\n\\textbf{Points} \\begin{verbatim}\n")
            for i, p in enumerate(self.points):
                file.write("{0:>2}: {1:.3f}, {2:.3f}\n".format(i, p.x, p.y))
            file.write("\end{verbatim}\n")

            file.write("\n\n\\textbf{Points2} \\begin{verbatim}\n")
            for i, p in enumerate(self.points2):
                file.write("{0:>2}: {1:.3f}, {2:.3f}\n".format(i, p.x, p.y))
            file.write("\end{verbatim}\n")

            
        if includeGCode:
            file.write("\\begin{verbatim}\n" + "Cutter Compensation Commands Required\n" + self.generateGCode(filename = "temp.txt") + "\n\end{verbatim}")
        
        file.write("\end{document}")
        file.close()

        if compileFile == True:
            print "Compiling TeX-File using pdflatex"
            call(["pdflatex", filename])

            call(["open", filename[:-4] + ".pdf"])
        else:
            print code;
    
if __name__ == "__main__":
    #SaddleCoil(height, radius, angle, width, cutter)
    #standardCoil = SaddleCoil(12, 6, 120, 2.5, 1, cornerRadius = 1)
    #standardCoil.generateGCode()
    #standardCoil.generateTikzCode(filename = "standardCoil.tex", compileFile = True, includePoints = True, scale = 0.75)
    #standardCoil.generateGCode(filename = "standardCoil.txt")


    #compactCoil = SaddleCoil(8, 2.05, 100, 1.5, 1, cornerRadius = 1, compact = True)
    #compactCoil.generateGCode()
    #compactCoil.generateTikzCode(filename = "compactCoil.tex", compileFile = True, includePoints = True)
    #compactCoil.generateGCode(filename = "compactCoil.txt")

    #innerCoilDNP = SaddleCoil(11, 7.5, 120, 3, 1, cornerRadius = 1, legLength = 35, compact = False)
    #innerCoilDNP.generateGCode(filename = "innerCoilDNP.txt", feed = 3.5)

    innerCoilWireCutter = SaddleCoil(11, 7.5, 120, 3, 0, cornerRadius = 1, legLength = 35, compact = False)
    innerCoilWireCutter.generateGCode(filename = "innerCoilWireCutter.txt", feed = 3.5) #wire cutter uses cutter compensation
    innerCoilWireCutter.generateTikzCode(filename = "innerCoil.tex", compileFile = True, includePoints = True, includePointsText = True, includeGCode = True, scale = 0.4)

