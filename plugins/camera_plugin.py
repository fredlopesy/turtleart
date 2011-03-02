#!/usr/bin/env python
#Copyright (c) 2011 Walter Bender

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:

#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.

import gst
import gtk
from fcntl import ioctl

from gettext import gettext as _

from camera.tacamera import Camera
from camera.v4l2 import v4l2_control, V4L2_CID_AUTOGAIN, VIDIOC_G_CTRL, \
 VIDIOC_S_CTRL

from plugin import Plugin

from TurtleArt.taprimitive import Primitive, Palette, make_prim
from TurtleArt.talogo import MEDIA_BLOCKS_DICTIONARY, PLUGIN_DICTIONARY
from TurtleArt.tautils import get_path

import logging
_logger = logging.getLogger('turtleart-activity camera plugin')


class Camera_plugin(Plugin):

    def __init__(self, parent):
        self._parent = parent
        self._status = False

        v4l2src = gst.element_factory_make('v4l2src')
        if v4l2src.props.device_name is not None:

            if self._parent.running_sugar:
                self._imagepath = get_path(self._parent.activity,
                                          'data/turtlepic.png')
            else:
                self._imagepath = '/tmp/turtlepic.png'
            self._camera = Camera(self._imagepath)

            self._status = True

    def setup(self):
        sensors = Palette('sensor')
        sensors.set_help(_('Palette of sensor blocks'))
        sensors.add_palette()

        # set up camera-specific blocks
        if self._status:
            PLUGIN_DICTIONARY['luminance'] = self.prim_read_camera
            make_prim('luminance',
                      palette='sensor',
                      style='box-style',
                      label=_('brightness'),
                      help_string=_('light level detected by camera'),
                      value_block=True,
                      prim_name='luminance')
            self._parent.lc._def_prim('luminance', 0,
                lambda self: PLUGIN_DICTIONARY['luminance'](True))

            # Depreciated block
            PLUGIN_DICTIONARY['read_camera'] = self.prim_read_camera
            make_prim('read_camera',
                      palette='sensor',
                      style='box-style',
                      label=_('brightness'),
                      help_string=_('Average RGB color from camera is pushed \
to the stack'),
                      value_block=True,
                      prim_name='luminance')
            self._parent.lc._def_prim('read_camera', 0,
                lambda self: PLUGIN_DICTIONARY['read_camera'](True))

            MEDIA_BLOCKS_DICTIONARY['camera'] = self.prim_take_picture
            make_prim('camera',
                      palette='sensor',
                      style='box-style-media',
                      label=' ',
                      default='CAMERA',
                      help_string=_('camera output'),
                      content_block=True)

    def start(self):
        # This gets called by the start button
        pass

    def stop(self):
        # This gets called by the stop button
        if self._status:
            self._camera.stop_camera_input()

    def goto_background(self):
        # This gets called when your process is sent to the background
        pass

    def return_to_foreground(self):
        # This gets called when your process returns from the background
        pass

    def quit(self):
        # This gets called by the quit button
        pass

    def _status_report(self):
        print 'Reporting camera status: %s' % (str(self._status))
        return self._status

    # Block primitives used in talogo

    def prim_take_picture(self):
        if self._status:
            ''' method called by media block '''
            self._camera.save_camera_input_to_file()
            self._camera.stop_camera_input()
            self._parent.lc.filepath = self._imagepath

    def prim_read_camera(self, luminance_only=False):
        """ Read average pixel from camera and push b, g, r to the stack """
        pixbuf = None
        array = None
        w, h = self._parent.lc._w(), self._parent.lc._h()
        if w > 0 and h > 0 and self._status:
            try:
                self._video_capture_device = open('/dev/video0', 'rw')
            except:
                self._video_capture_device = None
                _logger.debug('video capture device not available')

            if self._video_capture_device is not None:
                self._ag_control = v4l2_control(V4L2_CID_AUTOGAIN)
                try:
                    ioctl(self._video_capture_device, VIDIOC_G_CTRL,
                          self._ag_control)
                    self._ag_control.value = 0  # disable AUTOGAIN
                    ioctl(self._video_capture_device, VIDIOC_S_CTRL,
                          self._ag_control)
                except:
                    _logger.debug('AUTOGAIN control not available')
                    pass

            if self._video_capture_device is not None:
                self._video_capture_device.close()

            self._camera.save_camera_input_to_file()
            self._camera.stop_camera_input()
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(self._imagepath, w, h)
            try:
                array = pixbuf.get_pixels()
            except:
                array = None

        if array is not None:
            length = len(array) / 3
            r, g, b, i = 0, 0, 0, 0
            for j in range(length):
                r += ord(array[i])
                i += 1
                g += ord(array[i])
                i += 1
                b += ord(array[i])
                i += 1
            if luminance_only:
                lum = int((r * 0.3 + g * 0.6 + b * 0.1) / length)
                self._parent.lc.update_label_value('luminance', lum)
                return lum
            else:
                self._parent.lc.heap.append(int((b / length)))
                self._parent.lc.heap.append(int((g / length)))
                self._parent.lc.heap.append(int((r / length)))
        else:
            if luminance_only:
                return -1
            else:
                self._parent.lc.heap.append(-1)
                self._parent.lc.heap.append(-1)
                self._parent.lc.heap.append(-1)


