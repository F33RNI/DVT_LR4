"""
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org>
"""

import os
import sys
import threading

import matplotlib.pyplot as plt
import numpy as np
import pyqtgraph.opengl as gl
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidgetItem


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        # Load GUI file
        uic.loadUi('LR4.ui', self)

        # Settings
        self.bars_width = 0.08
        self.bar_z_color = np.array(np.array([1., 0.4, 0.7, 1.]))
        self.bar_x_color = np.array(np.array([1., 1., 0., 1.]))
        self.bar_y_color = np.array(np.array([0., 1., 1., 1.]))

        # System variables
        self.dump_file = None
        self.reader_running = False
        self.packets = []
        self.points = []
        self.points_surface = gl.GLScatterPlotItem(pos=np.array([[0, 0, 0]]))
        self.points_line = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, 0]]))
        self.points_surface_plane_xy = gl.GLScatterPlotItem(pos=np.array([[0, 0, 0]]))
        self.points_line_plane_xy = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, 0]]))
        self.points_surface_plane_xz = gl.GLScatterPlotItem(pos=np.array([[0, 0, 0]]))
        self.points_line_plane_xz = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, 0]]))
        self.points_surface_plane_yz = gl.GLScatterPlotItem(pos=np.array([[0, 0, 0]]))
        self.points_line_plane_yz = gl.GLLinePlotItem(pos=np.array([[0, 0, 0], [0, 0, 0]]))

        self.bar_graph_x = gl.GLBarGraphItem(pos=np.array([[0, 0, 0]]), size=np.array([0, 0, 0]))
        self.bar_graph_y = gl.GLBarGraphItem(pos=np.array([[0, 0, 0]]), size=np.array([0, 0, 0]))
        self.bar_graph_z = gl.GLBarGraphItem(pos=np.array([[0, 0, 0]]), size=np.array([0, 0, 0]))

        # Connect GUI controls
        self.btn_load_data.clicked.connect(self.load_data)
        self.btn_stop_reading.clicked.connect(self.stop_reading)

        self.btn_show_3d.clicked.connect(self.show_3d)
        self.btn_show_average.clicked.connect(self.show_average)

        # Initialize table
        self.init_table()

        # Initialize OpenGL widget
        self.init_opengl()

        # Show GUI
        self.show()

    def dump_reader(self):
        # Clear table and data arrays
        self.points_table.setRowCount(0)
        self.packets = []

        # Create temp buffers
        bytes_buffer = [b'\x00'] * 19
        bytes_buffer_position = 0
        previous_byte = b'\x00'
        packets_readed = 0

        # Continue reading
        while self.reader_running:
            incoming_byte = self.dump_file.read(1)
            if incoming_byte is None or len(incoming_byte) == 0:
                self.reader_running = False
            else:
                bytes_buffer[bytes_buffer_position] = incoming_byte
                if bytes_buffer[bytes_buffer_position] == b'\xff' and previous_byte == b'\xff':
                    bytes_buffer_position = 0

                    time = int.from_bytes(b''.join([bytes_buffer[1], bytes_buffer[0]]), byteorder='big', signed=False)
                    source = bytes_buffer[6]
                    destination = bytes_buffer[7]
                    data = bytes_buffer[9]

                    self.packets.append([time, source, destination, data])

                    self.points_table.insertRow(packets_readed)
                    self.points_table.setItem(packets_readed, 0, QTableWidgetItem(str(packets_readed)))
                    self.points_table.setItem(packets_readed, 1, QTableWidgetItem(str(time)))
                    self.points_table.setItem(packets_readed, 2, QTableWidgetItem(str(source.hex())))
                    self.points_table.setItem(packets_readed, 3, QTableWidgetItem(str(destination.hex())))
                    self.points_table.setItem(packets_readed, 4, QTableWidgetItem(str(data.hex())))

                    packets_readed += 1
                else:
                    previous_byte = bytes_buffer[bytes_buffer_position]
                    bytes_buffer_position += 1
                    if bytes_buffer_position >= 19:
                        bytes_buffer_position = 0

        self.dump_file.close()
        print('File reading stopped. Readed', packets_readed, 'packets')

    def init_table(self):
        """
        Initializes table of points
        :return:
        """
        self.points_table.setColumnCount(5)
        self.points_table.verticalHeader().setVisible(False)
        self.points_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.points_table.setHorizontalHeaderItem(0, QtWidgets.QTableWidgetItem('Packet'))
        self.points_table.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem('Time'))
        self.points_table.setHorizontalHeaderItem(2, QtWidgets.QTableWidgetItem('Src'))
        self.points_table.setHorizontalHeaderItem(3, QtWidgets.QTableWidgetItem('Dst'))
        self.points_table.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem('Data'))
        header = self.points_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)

    def init_opengl(self):
        """
        Initializes OpenGL Widget
        :return:
        """

        # Cube bottom square
        cube_bottom_square = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(cube_bottom_square)

        # Cube top square
        cube_top_square = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1], [0, 0, 1]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(cube_top_square)

        # Cube sides
        cube_line_bl = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, 0, 1]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(cube_line_bl)
        cube_line_br = gl.GLLinePlotItem(
            pos=np.array([[0, 1, 0], [0, 1, 1]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(cube_line_br)
        cube_line_tr = gl.GLLinePlotItem(
            pos=np.array([[1, 1, 0], [1, 1, 1]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(cube_line_tr)
        cube_line_tl = gl.GLLinePlotItem(
            pos=np.array([[1, 0, 0], [1, 0, 1]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(cube_line_tl)

        # Planes
        plane_xzp = gl.GLLinePlotItem(
            pos=np.array([[0, -0.5, 0], [1, -0.5, 0], [1, -0.5, 1], [0, -0.5, 1], [0, -0.5, 0]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(plane_xzp)
        plane_xzm = gl.GLLinePlotItem(
            pos=np.array([[0, 1.5, 0], [1, 1.5, 0], [1, 1.5, 1], [0, 1.5, 1], [0, 1.5, 0]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(plane_xzm)
        plane_xyp = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 1.5], [1, 0, 1.5], [1, 1, 1.5], [0, 1, 1.5], [0, 0, 1.5]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(plane_xyp)
        plane_xym = gl.GLLinePlotItem(
            pos=np.array([[0, 0, -0.5], [1, 0, -0.5], [1, 1, -0.5], [0, 1, -0.5], [0, 0, -0.5]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(plane_xym)
        plane_yzp = gl.GLLinePlotItem(
            pos=np.array([[1.5, 0, 0], [1.5, 1, 0], [1.5, 1, 1], [1.5, 0, 1], [1.5, 0, 0]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(plane_yzp)
        plane_yzm = gl.GLLinePlotItem(
            pos=np.array([[-0.5, 0, 0], [-0.5, 1, 0], [-0.5, 1, 1], [-0.5, 0, 1], [-0.5, 0, 0]]),
            color=[1, 1, 1, 1])
        self.openGLWidget.addItem(plane_yzm)

        # Add data elements
        self.openGLWidget.addItem(gl.GLAxisItem())
        self.openGLWidget.addItem(self.points_surface)
        self.openGLWidget.addItem(self.points_line)
        self.openGLWidget.addItem(self.points_surface_plane_xy)
        self.openGLWidget.addItem(self.points_line_plane_xy)
        self.openGLWidget.addItem(self.points_surface_plane_xz)
        self.openGLWidget.addItem(self.points_line_plane_xz)
        self.openGLWidget.addItem(self.points_surface_plane_yz)
        self.openGLWidget.addItem(self.points_line_plane_yz)
        self.openGLWidget.addItem(self.bar_graph_x)
        self.openGLWidget.addItem(self.bar_graph_y)
        self.openGLWidget.addItem(self.bar_graph_z)

    def show_3d(self, average=False):
        if average:
            blocks = self.average_blocks.value()
        else:
            blocks = 0
        if len(self.packets) > 1:
            blocks_counter = 0
            x = 0
            y = 0
            z = 0
            x_count = 0
            y_count = 0
            z_count = 0

            self.points = []
            # Sort packets by time
            self.packets = sorted(self.packets, key=lambda x: (x[0]))
            time = -1
            for i in range(len(self.packets)):
                if self.packets[i][0] != time:
                    # New block
                    time = self.packets[i][0]
                    k = i
                    while k < len(self.packets) and self.packets[k][0] == time:
                        source = self.packets[k][1]
                        destination = self.packets[k][2]
                        data = self.packets[k][3]
                        # X
                        if source == bytes.fromhex(self.line_x_from.text()) and \
                                destination == bytes.fromhex(self.line_x_to.text()):
                            x += float(int(data.hex(), 16))
                            x_count += 1

                        # Y
                        if source == bytes.fromhex(self.line_y_from.text()) and \
                                destination == bytes.fromhex(self.line_y_to.text()):
                            y += float(int(data.hex(), 16))
                            y_count += 1

                        # Z
                        if source == bytes.fromhex(self.line_z_from.text()) and \
                                destination == bytes.fromhex(self.line_z_to.text()):
                            z += float(int(data.hex(), 16))
                            z_count += 1

                        k += 1

                    blocks_counter += 1
                    if blocks_counter > blocks:
                        if x_count > 0:
                            x /= x_count
                        if y_count > 0:
                            y /= y_count
                        if z_count > 0:
                            z /= z_count
                        self.points.append([x, y, z])
                        blocks_counter = 0
                        x = 0
                        y = 0
                        z = 0
                        x_count = 0
                        y_count = 0
                        z_count = 0

            self.points = np.array(self.points)
            self.points /= np.max(self.points)
            self.draw_points()

    def show_average(self):
        self.show_3d(True)

    def show_on_table(self):
        """
        Shows points in table
        :return:
        """
        self.points_table.setRowCount(0)
        for point in self.points:
            row_position = self.points_table.rowCount()
            self.points_table.insertRow(row_position)
            self.points_table.setItem(row_position, 0, QTableWidgetItem(str(point[0])))
            self.points_table.setItem(row_position, 1, QTableWidgetItem(str(point[1])))
            self.points_table.setItem(row_position, 2, QTableWidgetItem(str(point[2])))

    def update_bars(self):
        """
        Updates and draws 3D - bar charts
        """
        bar_pos, bar_size = self.count_blocks([item[1] for item in self.points], 0)
        self.openGLWidget.removeItem(self.bar_graph_x)
        self.bar_graph_x = gl.GLBarGraphItem(pos=np.array(bar_pos), size=np.array(bar_size))
        self.bar_graph_x.setColor(self.bar_x_color)
        self.openGLWidget.addItem(self.bar_graph_x)

        bar_pos, bar_size = self.count_blocks([item[0] for item in self.points], 1)
        self.openGLWidget.removeItem(self.bar_graph_y)
        self.bar_graph_y = gl.GLBarGraphItem(pos=np.array(bar_pos), size=np.array(bar_size))
        self.bar_graph_y.setColor(self.bar_y_color)
        self.openGLWidget.addItem(self.bar_graph_y)

        bar_pos, bar_size = self.count_blocks([item[2] for item in self.points], 2)
        self.openGLWidget.removeItem(self.bar_graph_z)
        self.bar_graph_z = gl.GLBarGraphItem(pos=np.array(bar_pos[::-1]), size=np.array(bar_size))
        self.bar_graph_z.setColor(self.bar_z_color)
        self.openGLWidget.addItem(self.bar_graph_z)

    def count_blocks(self, data, orientation):
        """
        Counts how many points in each block and returns bars data
        """
        max_block_value = 0
        bar_pos = []
        bar_size = []
        for x in range(0, 10):
            points_in_block = 0
            for i in range(len(data)):
                if x / 10 <= data[i] < (x / 10 + 0.1):
                    points_in_block += 1
            if points_in_block > max_block_value:
                max_block_value = points_in_block

            if points_in_block > 0:
                if orientation == 0:
                    pos = [0, x / 10, 1.5]
                    size = [points_in_block, self.bars_width, 0]
                elif orientation == 1:
                    pos = [x / 10, 1.5, 0]
                    size = [self.bars_width, 0, points_in_block]
                else:
                    pos = [1.5, x / 10, 0]
                    size = [0, self.bars_width, points_in_block]
                bar_pos.append(pos)
                bar_size.append(size)

        bar_size_normalized = []
        for bar in bar_size:
            if orientation == 0:
                bar[0] /= max_block_value
            elif orientation == 1:
                bar[2] /= max_block_value
            elif orientation == 2:
                bar[2] /= max_block_value
            bar_size_normalized.append(bar)
        return bar_pos, bar_size_normalized

    def draw_points(self):
        """
        Draws 3D points with OpenGL
        :return:
        """
        if self.points is not None and len(self.points) > 0:
            points_plane_xy = np.array([[item[0], item[1], -0.5] for item in self.points])
            points_plane_xz = np.array([[item[0], -0.5, item[2]] for item in self.points])
            points_plane_yz = np.array([[-0.5, item[1], item[2]] for item in self.points])
            # Create color map
            z = np.array(np.array([item[2] for item in self.points]))
            cmap = plt.get_cmap('hsv')
            min_z = np.min(z)
            max_z = np.max(z)
            if max_z != min_z:
                rgba_img = cmap(1.0 - (z - min_z) / (max_z - min_z))
            else:
                rgba_img = cmap(1.0 - (z - min_z))

            # Draw points
            self.points_surface.setData(pos=self.points, color=rgba_img)
            self.points_line.setData(pos=self.points, color=rgba_img)
            self.points_surface_plane_xy.setData(pos=points_plane_xy, color=rgba_img)
            self.points_line_plane_xy.setData(pos=points_plane_xy, color=rgba_img)
            self.points_surface_plane_xz.setData(pos=points_plane_xz, color=rgba_img)
            self.points_line_plane_xz.setData(pos=points_plane_xz, color=rgba_img)
            self.points_surface_plane_yz.setData(pos=points_plane_yz, color=rgba_img)
            self.points_line_plane_yz.setData(pos=points_plane_yz, color=rgba_img)

            self.update_bars()

    def load_data(self):
        """
        Loads dump file
        :return:
        """
        if not self.reader_running:
            if os.path.exists(self.data_file.text()):
                print('Loading data...')
                self.dump_file = open(self.data_file.text(), 'rb')
                self.reader_running = True
                thread = threading.Thread(target=self.dump_reader)
                thread.start()
            else:
                print('File', self.data_file.text(), 'doesn\'t exist!')

    def stop_reading(self):
        """
        Stops reading data from dump file
        :return:
        """
        self.reader_running = False


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    win = Window()
    sys.exit(app.exec_())
