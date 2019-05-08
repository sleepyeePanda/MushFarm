from pyqtgraph.Qt import QtGui,  QtCore
import pyqtgraph as pg

pg.mkQApp()

# Axis
a2 = pg.AxisItem("left")

# ViewBoxes
v2 = pg.ViewBox()

# main view
pw = pg.GraphicsView()
pw.setWindowTitle('pyqtgraph example: multiple y-axis')
pw.show()

# layout
l = pg.GraphicsLayout()
pw.setCentralWidget(l)

# add axis to layout
## watch the col parameter here for the position
l.addItem(a2, row = 2, col = 1,  rowspan=1, colspan=1)

# plotitem and viewbox
## at least one plotitem is used whioch holds its own viewbox and left axis
pI = pg.PlotItem()
v1 = pI.vb # reference to viewbox of the plotitem
l.addItem(pI, row = 2, col = 2,  rowspan=1, colspan=1) # add plotitem to layout

# add viewboxes to layout
l.scene().addItem(v2)


# link axis with viewboxes
a2.linkToView(v2)


# link viewboxes
v2.setXLink(v1)


# axes labels
pI.getAxis("left").setLabel('axis 1 in ViewBox of PlotItem', color='#FFFFFF')
a2.setLabel('axis 2 in Viewbox 2', color='#2E2EFE')

v3 = pg.ViewBox()
a3 = pg.AxisItem('right')
pI.layout.addItem(a3, 2, 3)
pI.scene().addItem(v3)
a3.linkToView(v3)
v3.setXLink(pI)
a3.setZValue(-10000)
a3.setLabel('axis 3', color='#ff0000')





# slot: update view when resized
def updateViews():

    v2.setGeometry(v1.sceneBoundingRect())
    v3.setGeometry(v1.sceneBoundingRect())

# data
x = [1,2,3,4,5,6]
y1 = [0,4,6,8,10,4]
y2 = [0,5,7,9,11,3]
y3 = [0,1,2,3,4,12]
y4 = [0,8,0.3,0.4,2,5]
y5 = [0,1,6,4,2,1]
y6 = [0,0.2,0.3,0.4,0.5,0.6]

# plot
v1.addItem(pg.PlotCurveItem(x, y1, pen='#FFFFFF'))
v2.addItem(pg.PlotCurveItem(x, y2, pen='#2E2EFE'))
v3.addItem(pg.PlotCurveItem(x, y3, pen='#FF0000'))


# updates when resized
v1.sigResized.connect(updateViews)

# autorange once to fit views at start
v2.enableAutoRange(axis= pg.ViewBox.XYAxes, enable=True)
v3.enableAutoRange(axis= pg.ViewBox.XYAxes, enable=True)

updateViews()

if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()