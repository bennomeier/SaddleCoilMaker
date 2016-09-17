from numpy import pi

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
    """A Coordinate is just a set of values, x and y."""
    def __init__(self, x, y):
        """x: x value of coordinate
        y: y value of coordinate"""
        
        self.x = x
        self.y = y

    def __add__(self, other):
        return Coordinate(self.x + other.x, self.y + other.y)

    def shiftX(self, x):
        return Coordinate(self.x + x, self.y)

    def shiftY(self, y):
        return Coordinate(self.x, self.y + y)

class Straight(object):
    """A class representing a straight cut."""

    def __init__(self, x, y, p0 = Coordinate(0, 0)):
        """Specify a straight line"""
        self.destination = Coordinate(x, y) + p0

    def gCode(self):
        return "G1 X{0:.3f} Y{1:.3f}".format(destination.x, destination.y)

class ClockwiseArc(object):
    """A class representing a clockwise arc."""
    def __init__(self, x, y, xC, yC, p0 = Coordinate(0, 0)):
        """Specify a Clockwise Arc
        x: x component of destination
        y: y component of destination
        xC: x offset of arc center
        yC: y offset of arc center"""
        self.destination = Coordinate(x, y) + p0
        self.arcCenter = Coordinate(xC, yC)

    def gCode(self):
        return "G2 X{0:.3f} Y{1:.3f} I{2:.3f} {J:.3f}".format(self.destination.x, self.destination.y, self.arcCenter.x, self.arcCenter.y)

class CounterClockwiseArc(ClockwiseArc):
    """Inherits from clockwise arc. Overwrites gCode generation and TikZ Code generation."""
    def gCode(self):
        return "G3 X{0:.3f} Y{1:.3f} I{2:.3f} {J:.3f}".format(self.destination.x, self.destination.y, self.arcCenter.x, self.arcCenter.y)

    
class Path(object):
    """A base class to represent a path. For our purposes, a path is a list of either straight lines or clockwise or counterclockwise arcs. 
    """

    def __init__(self, x0, y0):
        """Init Method of path. This will set the starting point for the path."""
        p0 = Coordinate(x0, y0)
        
        self.points = [p0]
        self.path = []

    def gCode(self):
        retVal = "G0 Z5\n"
        retVal += "G0 X{0:.3f} Y{0:.3f}".format(self.p0.x, self.p0.y)
        retVal += "G0 Z0.5\n"

        for p in self.path:
            retVal += p.gCode + "\n"

class SaddleCoil(object):
    """A class to represent a simple saddle coil, as machined from a 2D sheet.

        Its purpose is to generate G-Code to cut a saddle coil using a CNC mill.
        Optionally generate tikz code to visualize the result using LaTeX."""

    def __init__(self, h, r, alpha, width, cutterDiameter, gap = 1, legLength = 10, cornerRadius = 0):
        """This routine creates the coordinates for the cuts.
        
        - h: height of the saddle coil as distance between center of traces
        - r: radius (!) of the coil, not diameter
        - alpha: opening angle of the saddle coil
        - width: width of the copper traces
        - cutterDiameter: cutting diameter of the tool.
        - gap: Additional gap to increase the minimal distance between different segments of the coil.
        - legLength: Length of the coils legs.
        - cornerRadius: A radius > 0 will introduce rounded corners.

        All units are in mm."""

        #Setup a few useful coordinates along the path:

        self.circumference = 2*pi*r

        self.cD = cutterDiameter
        self.width = width

        cD2 = self.cD/2.
        w2 = self.width/2.

        #todo: get rid of x and y, merge into Point objects!
        yInnerBottom = w2 + cD2
        yInnerTop = h - w2 - cD2

        yOuterBottom = 0 - w2 - cD2
        yOuterTop = h + w2 + cD2

        #xInnerLeft: first or left loop of the coil, inside left cutter coordinates
        xInnerLeft_Left = self.angleToX(0) + w2 + cD2 
        xInnerLeft_Right = self.angleToX(alpha) - w2 - cD2

        xOuterLeft_Right = self.angleToX(alpha) + w2 + cD2
        xOuterLeft_Left = self.angleToX(0) - w2 - cD2

        #xInnerRight: second or right loop of the coil
        xInnerRight_Left = self.angleToX(180) + w2 + cD2 
        xInnerRight_Right = self.angleToX(180 + alpha) - w2 - cD2

        xOuterRight_Left = self.angleToX(180) - w2 - cD2 
        xOuterRight_Right = self.angleToX(180 + alpha) + w2 + cD2

    


   
class SimpleSaddleCoil(object):
    """A base class to represent a simple saddle coil, as machined from a 2D sheet.

        Its purpose is to generate G-Code to cut a saddle coil using a CNC mill.
        Optionally generate tikz code to visualize the result using LaTeX.

    """

    

    def __init__(self, h, r, alpha, width, cutterDiameter, gap = 1, legLength = 10, startAngle = 10):
        """This routine creates the coordinates for the cuts.
        
        - h: height of the saddle coil as distance between center of traces
        - r: radius (!) of the coil, not diameter
        - alpha: opening angle of the saddle coil
        - width: width of the copper traces
        - cutterDiameter: cutting diameter of the tool.
        - gap: Additional gap to increase the minimal distance between different segments of the coil.

        All units are in mm."""

        self.circumference = 2*pi*r
        self.startAngle = startAngle

        self.cD = cutterDiameter
        self.width = width

        cD2 = self.cD/2.
        w2 = self.width/2.

        yInnerBottom = w2 + cD2
        yInnerTop = h - w2 - cD2

        yOuterBottom = 0 - w2 - cD2
        yOuterTop = h + w2 + cD2

        #xInnerLeft: first or left loop of the coil, inside left cutter coordinates
        xInnerLeft_Left = self.angleToX(0) + w2 + cD2 
        xInnerLeft_Right = self.angleToX(alpha) - w2 - cD2

        xOuterLeft_Right = self.angleToX(alpha) + w2 + cD2
        xOuterLeft_Left = self.angleToX(0) - w2 - cD2

        #xInnerRight: second or right loop of the coil
        xInnerRight_Left = self.angleToX(180) + w2 + cD2 
        xInnerRight_Right = self.angleToX(180 + alpha) - w2 - cD2

        xOuterRight_Left = self.angleToX(180) - w2 - cD2 
        xOuterRight_Right = self.angleToX(180 + alpha) + w2 + cD2

        
        self.lines = [
            # 3 inner cuts on first loop, starting at bottom right, clockwise
            [[xInnerLeft_Right, yInnerBottom], [xInnerLeft_Left, yInnerBottom]],
            [[xInnerLeft_Left, yInnerBottom], [xInnerLeft_Left, yInnerTop]],
            [[xInnerLeft_Left, yInnerTop], [xInnerLeft_Right, yInnerTop]],

            [[xInnerRight_Left, yInnerBottom], [xInnerRight_Left, yInnerTop]],
            [[xInnerRight_Left, yInnerTop], [xInnerRight_Right, yInnerTop]],
            [[xInnerRight_Right, yInnerTop], [xInnerRight_Right, yInnerBottom]],
            [[xInnerRight_Right, yInnerBottom], [xOuterLeft_Right, yInnerBottom]],
            [[xOuterLeft_Right, yInnerBottom], [xOuterLeft_Right, yOuterTop]],
            [[xOuterLeft_Right, yOuterTop], [xOuterLeft_Left, yOuterTop]],
            [[xOuterLeft_Left, yOuterTop], [xOuterLeft_Left, yOuterBottom]],
            [[xOuterLeft_Left, yOuterBottom], [self.angleToX(alpha) - 3*w2 - 3*cD2 - gap, yOuterBottom]],
            #now follows the leg at the left, outer side
            [[self.angleToX(alpha) - 3*w2 - 3*cD2 - gap, yOuterBottom],[self.angleToX(alpha) - 3*w2 - 3*cD2 - gap, yOuterBottom - 3*w2 - 3*cD2 - gap]],
            [[self.angleToX(alpha) - 3*w2 - 3*cD2 - gap, yOuterBottom - 3*w2 - 3*cD2 - gap],[self.angleToX(180) - 3*w2 - 3*cD2 - gap, yOuterBottom - 3*w2 - 3*cD2 - gap]],
            [[self.angleToX(180) - 3*w2 - 3*cD2 - gap, yOuterBottom - 3*w2 - 3*cD2 - gap],[self.angleToX(180) - 3*w2 - 3*cD2 - gap, yOuterBottom - legLength]],

            #cut along the left leg - innser side
            [[xInnerLeft_Right - gap, yInnerBottom],[xInnerLeft_Right - gap, yInnerBottom - 2*w2 - 2*cD2 -gap]],
            [[xInnerLeft_Right - gap, yInnerBottom - 2*w2 - 2*cD2 -gap],[self.angleToX(180) -  w2 - cD2 - gap, yInnerBottom - 2*w2 - 2*cD2 -gap]],
            [[self.angleToX(180) -  w2 - cD2 - gap, yInnerBottom - 2*w2 - 2*cD2 -gap],[self.angleToX(180) -  w2 - cD2 - gap, yOuterBottom - legLength]],

            #cut along right inner side of left loop to outer right bottom of right loop and counter-clockwise around the outside of the right loop
            [[xInnerLeft_Right, yInnerTop],[xInnerLeft_Right, yOuterBottom]],
            [[xInnerLeft_Right, yOuterBottom], [xOuterRight_Right, yOuterBottom]],
            [[xOuterRight_Right, yOuterBottom], [xOuterRight_Right, yOuterTop]],
            [[xOuterRight_Right, yOuterTop], [xOuterRight_Left, yOuterTop]],
            [[xOuterRight_Left, yOuterTop], [xOuterRight_Left, yInnerBottom]],

            #cut the additional clearance at the left side of the right loop, where the structures would cross.
            [[xOuterRight_Left, yInnerBottom + gap],[xInnerRight_Left, yInnerBottom + gap]],

            #add the cuts for the other leg
            [[self.angleToX(180) -w2 - cD2, yOuterBottom], [self.angleToX(180) - w2 - cD2, yOuterBottom - legLength]],
            [[self.angleToX(180) +w2 + cD2, yOuterBottom], [self.angleToX(180) + w2 + cD2, yOuterBottom - legLength]],

            #and the final cut to below the legs
            [[self.angleToX(alpha) -  w2 - cD2 - gap, yOuterBottom - legLength],[self.angleToX(180) +w2 + cD2, yOuterBottom - legLength]]
            ]

        minX = min([l[0][0] for l in self.lines] + [l[1][0] for l in self.lines])
        minY = min([l[0][1] for l in self.lines] + [l[1][1] for l in self.lines])

        #subtract these values from all coodinates to get a coil with bounding box starting at (0,0)
        self.linesShifted = [  [[l[0][0] - minX, l[0][1] - minY],[l[1][0] - minX, l[1][1] - minY]] for l in self.lines]
        self.lines = self.linesShifted

        self.maxX = max([l[0][0] for l in self.lines] + [l[1][0] for l in self.lines])
        self.maxY = max([l[0][1] for l in self.lines] + [l[1][1] for l in self.lines])

        print "maxX: {0:.3f} mm".format(self.maxX)
        print "maxY: {0:.3f} mm".format(self.maxY)
        
                        
    def angleToX(self, angle):
        """ Calculate X-position from angle. This function also introduces the startAngle.

        angleToX should be called once for every calculation of an X value."""
        return self.circumference*(self.startAngle + angle)/360.

    def generateGCode(self, feed = 7.5, filename = ""):
        """Generate GCode for the specified coil.

        - feed: optional argument, defaults to 7.5
        - filename: if specified, the g code is saved, if not it is printed to STDOUT."""
        
        code = """;G-Code generated by coilGenerator.py
;maxX : {0:.3f}
;maxY : {1:.3f}
G90
M10 O6.1
G00 Z5.00\n""".format(self.maxX, self.maxY)

        for l in self.lines:
            p1 = l[0]
            p2 = l[1]

            code += "G00 X{0:.3f} Y{1:.3f}\n".format(p1[0], p1[1])
            code += "G00 Z0.500\n"
            code += "G01 Z-0.3 F{:.3f}\n".format(feed)
            code += "G01 X{0:.3f} Y{1:.3f}\n".format(p2[0], p2[1])
            code += "G00 Z0.500\n"

        code += "M10 O6.0\n"

        if len(filename) > 0:
            f = open(filename, "w")
            f.write(code)
            f.close()
        else:
            print code

    def generateTikzCode(self, filename = "temp.tex", compileFile = False):
        """Export Coil to a TeX file. 

        The file needs to be compiled manually using e.g. pdflatex."""

        header = """\documentclass{article}
\usepackage{tikz}
\\begin{document}
\\begin{tikzpicture}[scale = 0.5]
"""

        footer = """\end{tikzpicture}
\end{document}
        """

        file = open(filename, "w")

        file.write(header)

        for l in self.lines:
            p1 = l[0]
            p2 = l[1]

            command = "   \draw[thick] ( {0:.3f}, {1:.3f} ) -- ( {2:.3f}, {3:.3f} );".format(p1[0], p1[1], p2[0], p2[1])
            file.write(command + "\n")

            print command

        command = " \draw[fill = red] (0,0) circle(0.15);"
        file.write(command + "\n")
        
        file.write(footer)
        file.close()

        if compileFile == True:
            print "Compiling TeX-File using pdflatex"
            call(["pdflatex", filename])

            call(["open", filename[:-4] + ".pdf"])


    
if __name__ == "__main__":
    stAndrewsCoil = simpleSaddleCoil(8, 2.05, 120, 1, 1)
    #print stAndrewsCoil.lines

    #stAndrewsCoil.generateTikzCode(filename = "stAndrews1.tex", compileFile = True)
    stAndrewsCoil.generateGCode(filename = "stAndrews1.txt")
