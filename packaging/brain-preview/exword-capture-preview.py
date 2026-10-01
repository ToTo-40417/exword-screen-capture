"""Low-rate GTK preview using the existing projector-only USB receiver."""
import argparse
import ctypes as C
import ctypes.util
import json
import queue
import sys
import time

sys.path.insert(0, '/opt/exword-capture/lib')
from brain_usb_source import UsbSource

# Use the installed GTK C ABI, avoiding an additional introspection runtime.
gtk = C.CDLL(ctypes.util.find_library('gtk-3'))
gdk = C.CDLL(ctypes.util.find_library('gdk_pixbuf-2.0'))
glib = C.CDLL(ctypes.util.find_library('glib-2.0'))
obj = C.CDLL(ctypes.util.find_library('gobject-2.0'))
P, I = C.c_void_p, C.c_int

def bind(lib, name, result, *args):
    f = getattr(lib, name)
    f.restype, f.argtypes = result, args
    return f

init = bind(gtk, 'gtk_init_check', I, P, P)
window_new = bind(gtk, 'gtk_window_new', P, I)
title = bind(gtk, 'gtk_window_set_title', None, P, C.c_char_p)
size = bind(gtk, 'gtk_window_set_default_size', None, P, I, I)
box_new = bind(gtk, 'gtk_box_new', P, I, I)
image_new = bind(gtk, 'gtk_image_new', P)
label_new = bind(gtk, 'gtk_label_new', P, C.c_char_p)
pack = bind(gtk, 'gtk_box_pack_start', None, P, P, I, I, C.c_uint)
add = bind(gtk, 'gtk_container_add', None, P, P)
show = bind(gtk, 'gtk_widget_show_all', None, P)
label_set = bind(gtk, 'gtk_label_set_text', None, P, C.c_char_p)
set_image = bind(gtk, 'gtk_image_set_from_pixbuf', None, P, P)
get_width = bind(gtk, 'gtk_widget_get_allocated_width', I, P)
get_height = bind(gtk, 'gtk_widget_get_allocated_height', I, P)
bytes_new = bind(glib, 'g_bytes_new', P, P, C.c_size_t)
bytes_unref = bind(glib, 'g_bytes_unref', None, P)
pix_new = bind(gdk, 'gdk_pixbuf_new_from_bytes', P, P, I, I, I, I, I, I)
scale = bind(gdk, 'gdk_pixbuf_scale_simple', P, P, I, I, I)
unref = bind(obj, 'g_object_unref', None, P)
main = bind(gtk, 'gtk_main', None)
quit_main = bind(gtk, 'gtk_main_quit', None)
timeout = bind(glib, 'g_timeout_add', C.c_uint, C.c_uint, P, P)
connect = bind(obj, 'g_signal_connect_data', C.c_ulong, P, C.c_char_p, P, P, P, I)

parser = argparse.ArgumentParser()
parser.add_argument('--projector-mode', action='store_true', required=True)
parser.add_argument('--demo', action='store_true')
args = parser.parse_args()
source = None if args.demo else UsbSource()
if not init(None, None):
    raise SystemExit('Cannot open X display')
window = window_new(0)
title(window, b'EX-word Live')
size(window, 820, 420)
box = box_new(1, 0)
image = image_new()
status = label_new(b'Waiting for projector mode')
pack(box, image, 1, 1, 0)
pack(box, status, 0, 0, 0)
add(window, box)
sequence = 0
frames = 0
started = time.monotonic()

def tick(_):
    global sequence, frames
    if source:
        while True:
            try:
                key, values = source.messages.get_nowait()
                message = (f'USB frames {values["received"]} | decoded {values["decoded"]}'
                           if key == 'transport' else key + ': ' + str(values)[:100])
                label_set(status, message.encode())
                print(json.dumps({'event': key, **values}), flush=True)
            except queue.Empty:
                break
        current, frame = source.snapshot()
    else:
        from exword_capture.cli import demo_frame
        current, frame = 1, demo_frame() if sequence == 0 else None
    if frame and current != sequence:
        sequence = current
        width, height, rgb = frame
        sample = rgb[::max(1, len(rgb)//2048)]
        print(json.dumps({'event': 'frame_data', 'size': len(rgb),
                          'min': min(sample), 'max': max(sample),
                          'levels': len(set(sample)),
                          'allocated': [get_width(image), get_height(image)]}), flush=True)
        buffer = C.create_string_buffer(rgb)
        blob = bytes_new(buffer, len(rgb))
        pixbuf = pix_new(blob, 0, 0, 8, width, height, width * 3)
        bytes_unref(blob)
        factor = min(1.0, max(1, get_width(image)) / width,
                     max(1, get_height(image)) / height)
        if factor < 1:
            smaller = scale(pixbuf, max(1, int(width * factor)), max(1, int(height * factor)), 0)
            unref(pixbuf)
            pixbuf = smaller
        set_image(image, pixbuf)
        unref(pixbuf)
        frames += 1
        label_set(status, f'{width}x{height} | frames {frames} | {frames / max(1, time.monotonic()-started):.1f} fps'.encode())
        print(json.dumps({'event': 'displayed', 'frames': frames,
                          'width': width, 'height': height}), flush=True)
    return True

def close(*_):
    if source:
        source.stop()
    quit_main()

close_callback = C.CFUNCTYPE(None, P, P)(close)
tick_callback = C.CFUNCTYPE(I, P)(tick)
connect(window, b'destroy', close_callback, None, None, 0)
show(window)
if source:
    source.start()
timeout(100, tick_callback, None)
main()
