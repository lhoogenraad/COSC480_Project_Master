from PIL import Image, ImageTk, ImageEnhance
import numpy as np
#import matplotlib.pyplot as plt
import sys, getopt, os
import time
import tkinter as tk
import xml.etree.ElementTree as ET
from xml.dom import minidom
import cv2



def read_labels(folder):

   x = []

   for _, _, files in os.walk(folder):
      for file in files:
         extension = os.path.splitext(file)[1]
         if extension.lower() == '.xml':
            image_path = os.path.join(folder, file)
            x.append(image_path)
      break

   return x

# Automatic brightness and contrast optimization with optional histogram clipping
def automatic_brightness_and_contrast(image, clip_hist_percent=25):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Calculate grayscale histogram
    hist = cv2.calcHist([gray],[0],None,[256],[0,256])
    hist_size = len(hist)

    # Calculate cumulative distribution from the histogram
    accumulator = []
    accumulator.append(float(hist[0]))
    for index in range(1, hist_size):
        accumulator.append(accumulator[index -1] + float(hist[index]))

    # Locate points to clip
    maximum = accumulator[-1]
    clip_hist_percent *= (maximum/100.0)
    clip_hist_percent /= 2.0

    # Locate left cut
    minimum_gray = 0
    while accumulator[minimum_gray] < clip_hist_percent:
        minimum_gray += 1

    # Locate right cut
    maximum_gray = hist_size -1
    while accumulator[maximum_gray] >= (maximum - clip_hist_percent):
        maximum_gray -= 1

    # Calculate alpha and beta values
    alpha = 255 / (maximum_gray - minimum_gray)
    beta = -minimum_gray * alpha

    '''
    # Calculate new histogram with desired range and show histogram 
    new_hist = cv2.calcHist([gray],[0],None,[256],[minimum_gray,maximum_gray])
    plt.plot(hist)
    plt.plot(new_hist)
    plt.xlim([0,256])
    plt.show()
    '''

    auto_result = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
    return (auto_result, alpha, beta)


class SheepSelect:

   def __init__(self, root,width=720,height=480,dataFolder=os.getcwd(),cont=False,n=0,nSet=False):
      self.root = root
      self.width = width
      self.height = height

      self.dataFolder = dataFolder

      self.canvas = tk.Canvas(root, width=width, height=height)
      self.canvas.pack()

      self.image_offset = (0,10)
      self.image_on_canvas = self.canvas.create_image(self.image_offset[0], self.image_offset[1], anchor=tk.NW)
      self.canvas.grid(row=0, column=1)

      self.prev_button = tk.Button(root, text="<", command=self.prev, height = 20,
          width = 5)
      self.prev_button.grid(row=0, column=0)


      self.next_button = tk.Button(root, text=">", command=self.next,height = 20,
          width = 5)
      self.next_button.grid(row=0, column=2)

      self.bscale = tk.Scale(root, from_=-1, to=2,tickinterval=20, resolution=0.1, orient=tk.HORIZONTAL, command=self.brightness)
      self.bscale.grid(row=1,column=1)

      self.cscale = tk.Scale(root, from_=-1, to=2,tickinterval=20, resolution=0.1, orient=tk.HORIZONTAL, command=self.contrast)
      self.cscale.grid(row=2,column=1)

      self.rotation = tk.IntVar()
      self.rotbox = [tk.Radiobutton(root,text="<-.",variable=self.rotation,value=90),
                     tk.Radiobutton(root, text="0", variable=self.rotation, value=0),
                     tk.Radiobutton(root, text=".->", variable=self.rotation, value=-90)]
      k = 2
      for rotbox in self.rotbox:
         rotbox.grid(row=2,column=k)
         k += 1


      self.xml_files = read_labels(os.path.join(self.dataFolder,"labels"))
      np.random.seed(0)
      I = np.random.permutation(len(self.xml_files))
      self.xml_files = np.array(self.xml_files)[I].tolist()

      # Sort the order
      xml_files1 = []
      for xml_file in self.xml_files:
         xml_files1.append(xml_file.split("/")[-1])

      labelFolder = os.path.join(self.dataFolder, "labels")
      if os.path.exists(labelFolder):
         xml_files2_fp = read_labels(labelFolder)
         xml_files2_fp.sort()

         xml_files2 = []
         for xml_file in xml_files2_fp:
            xml_files2.append(xml_file.split("/")[-1])


         I2 = []
         for xml_file in xml_files1:
            i = xml_files2.index(xml_file.split("/")[-1])
            I2.append(i)


         self.xml_files = np.array(xml_files2_fp)[I2].tolist()
      #self.images = read_images("/Users/lechszym/Downloads/test")
      #self.xml_files.sort()
      #self.images.sort(key=len)

      if cont:
         sys.stdout.write("Reading all labels...")
         sys.stdout.flush()
         I_labelled, I_unlabelled = self.find_labelled()
         xml_files2 = []
         for i in I_labelled:
            xml_files2.append(self.xml_files[i])

         for i in I_unlabelled:
            xml_files2.append(self.xml_files[i])

         self.xml_files = xml_files2

         if not nSet:
            n = len(I_labelled)

         sys.stdout.write("done\n")
         sys.stdout.flush()




      self.n = n-1 #335

      self.canvas.bind('<ButtonPress-1>', self.draw_object)
      self.canvas.bind('<ButtonRelease-1>', self.draw_object)
      self.canvas.bind('<B1-Motion>', self.draw_object)

      self.canvas.bind('<ButtonPress-2>', self.draw_object)
      self.canvas.bind('<ButtonRelease-2>', self.draw_object)
      self.canvas.bind('<B2-Motion>', self.draw_object)

      self.button = 1

      self.root.bind('<Escape>', self.undo)
      self.root.bind('e', self.bind_for_eyes)
      self.root.bind('m', self.bind_for_mouth)
      self.root.bind('f', self.bind_for_face)
      self.root.bind('n', self.bind_for_nostril)
      self.root.bind('s', self.search_next_empty)

      self.obj_types = ['eye','mouth','nostril']
      self.obj_draws = ['circle','line','line']

      self.sides = ['r','l']

      self.obj_colours = [ ['#f5cb38','#39fd8c'],
                            ['#f5cb38','#39fd8c'],
                            ['#A86512','#39aa8c']]

      self.face_colour = '#55f1f7'

      self.bind_for_eyes(None)

      self.markers = list()
      self.capture = None

      self.reset_canvas()

      #for i,xml_file in enumerate(self.xml_files):
      #   if xml_file.split("/")[-1]=="12.18_484.xml":
      #      print("selecting n %d" % i)
      #      self.n = i-1

      #self.xml_files.sort()
      #lastn = self.n
      self.load_next_image(1)
      #while(lastn != self.n):
      #   lastn = self.n
      #   self.next()
      #   time.sleep(0.1)

   def brightness(self, scale):
      scale = 1.0+float(scale)
      self.benh = scale
      self.adjust_ac()

   def contrast(self, scale):
      scale = 1.0 + float(scale)
      self.cenh = scale
      self.adjust_ac()

   def adjust_ac(self):

      im = self.pil_im
      if self.benh is not None and self.benh != 1.0:
         benh = ImageEnhance.Brightness(im)
         im = benh.enhance(self.benh) # gives original image

      if self.cenh is not None and self.cenh != 1.0:
         cenh = ImageEnhance.Contrast(im)
         im = cenh.enhance(self.cenh)

      self.im = ImageTk.PhotoImage(im)

      self.canvas.itemconfig(self.image_on_canvas, image=self.im)
      self.canvas.update_idletasks()



   def reset_canvas(self):
      self.face = list()
      self.objs = list()

      self.benh = None
      self.cenh = None

      self.bscale.set(0)
      self.cscale.set(0)

      # Remove and clear old markers
      for object,_,_ in self.markers:
         self.canvas.delete(object)

      self.markers = list()

      self.xml_tree = None
      self.xml_root = None

      self.xml_face = list()
      self.xml_objs = list()

      self.rotation.set(0)

      self.bind_for_eyes(None)

   def bind_for_eyes(self,event):
      self.mode = 'eye'

   def bind_for_mouth(self,event):
      self.mode = 'mouth'

   def bind_for_face(self,event):
      self.mode = 'face'

   def bind_for_nostril(self,event):
      self.mode = 'nostril'

   def search_next_empty(self, event):
      found = False
      while not found:
         self.load_next_image(1)
         found = True
         for obj in self.objs:
            if obj is not None:
               found = False
               break

   def undo(self,event):

      if len(self.markers)>0:
         object, face_index, obj_type = self.markers.pop()

         if obj_type == 'face':
            self.face[face_index] = None
         else:
            side = obj_type[0]
            type = obj_type[1:]

            side_idx = self.sides.index(side)
            type_idx = self.obj_types.index(type)

            self.objs[face_index][type_idx*2+side_idx] = None

         self.canvas.delete(object)

   def draw_rectangle(self,x1,y1,x,y,outline,width):
      return self.canvas.create_rectangle(x1 + self.image_offset[0], y1 + self.image_offset[1], x +self.image_offset[0],
                                   y + self.image_offset[1], outline=outline, width=width)

   def draw_oval(self,x1,y1,x,y,outline,width):
      return self.canvas.create_oval(x1 + self.image_offset[0], y1 + self.image_offset[1],
                                             x + self.image_offset[0], y + self.image_offset[1], outline=outline,
                                             width=width)

   def draw_line(self,x1,y1,x,y,fill,width):
      return self.canvas.create_line(x1 + self.image_offset[0], y1 + self.image_offset[1],
                                             x + self.image_offset[0], y + self.image_offset[1], fill=fill, width=width)

   def draw_object(self,event):

      x, y = event.x, event.y
      x -= self.image_offset[0]
      y -= self.image_offset[1]

      if str(event.type) == 'Motion' or str(event.type)=='ButtonRelease':
         if self.capture is None:
            return

         if x <= 0:
            x = 0

         if y <= 0:
            y = 0

         if x >= self.cur_size[0]:
            x = self.cur_size[0]-1

         if y >= self.cur_size[1]:
            y = self.cur_size[1]-1

      if self.mode == 'face':
         colour = self.face_colour
      else:
         type = self.obj_types.index(self.mode)
         side= self.button-1
         if self.button == 1:
            colour = self.obj_colours[type][side]
         else:
            colour = self.obj_colours[type][side]

      if not self.mode=='face' and str(event.type) == 'ButtonPress':
         #Check if within bbox and if so, which bbox index it is in
         self.face_index = -1
         for i in range(len(self.face)):
            if self.face[i] is None:
               continue

            xmin, ymin, xmax, ymax, _ = self.face[i]
            if x >= xmin and x<=xmax and y>=ymin and y<=ymax:
               self.face_index = i
               break
      else:
         if x < 0 or x>=self.cur_size[0] or y < 0 or y >= self.cur_size[1]:
            return

      if str(event.type) == 'ButtonPress':

         if self.mode != 'face' and self.face_index == -1:
            return

         self.button = event.num
         self.capture = None

         if self.mode != 'face':
            type = self.obj_types.index(self.mode)
            side = self.button-1

            if self.objs[self.face_index][type*2+side] is not None:
               return

         self.canvas.old_coords = x, y
         x1, y1 = self.canvas.old_coords
         if self.mode == 'face':
            self.capture = self.draw_rectangle(x1,y1,x,y,outline=colour,width=2)
         else:
            if self.obj_draws[type] == 'circle':
               self.capture = self.draw_oval(x1,y1,x,y,outline=colour,width=2)
            elif self.obj_draws[type] == 'line':
               self.capture = self.draw_line(x1,y1,x,y,fill=colour,width=2)

         self.canvas.new_coords = None


      elif str(event.type) == 'ButtonRelease':
         if self.capture is None:
            return

         if self.mode != 'face' and self.face_index == -1:
            x, y = self.canvas.new_coords

         x1, y1 = self.canvas.old_coords

         self.canvas.delete(self.capture)

         if self.mode == 'face':
            self.capture = self.draw_rectangle(x1,y1,x,y,outline=colour,width=2)
            self.markers.append((self.capture, len(self.face), 'face'))

            self.face.append((min(x1,x),min(y1,y),max(x1,x),max(y1,y),self.capture))
            self.objs.append(list())
            self.xml_face.append(None)
            self.xml_objs.append(list())
            for i in range(len(self.obj_types)):
               for j in range(len(self.sides)):
                  self.objs[-1].append(None)
                  self.xml_objs[-1].append(None)
         else:
            type = self.obj_types.index(self.mode)
            side = self.button-1

            if self.obj_draws[type] == 'circle':
               self.capture = self.draw_oval(x1,y1,x,y,outline=colour,width=2)
            elif self.obj_draws[type] == 'line':
               self.capture = self.draw_line(x1,y1,x,y,fill=colour,width=2)

            self.objs[self.face_index][2*type+side] = (x1, y1, x, y, self.capture)
            self.markers.append((self.capture, self.face_index, self.sides[side] + self.obj_types[type]))


         self.capture = None

      elif str(event.type) == 'Motion':
         if self.mode != 'face' and self.face_index == -1:
            return


         if self.capture is None:
            return

         self.canvas.delete(self.capture)
         x1, y1 = self.canvas.old_coords
         self.canvas.new_coords = x, y

         if self.mode == 'face':
            self.capture = self.draw_rectangle(x1, y1, x, y, outline=colour, width=2)
         else:
            type = self.obj_types.index(self.mode)

            if self.obj_draws[type] == 'circle':
               self.capture = self.draw_oval(x1, y1, x, y, outline=colour, width=2)
            elif self.obj_draws[type] == 'line':
               self.capture = self.draw_line(x1, y1, x, y, fill=colour, width=2)

   def find_labelled(self):

      I_labelled = []
      I_unlabelled = []

      for i, imxml in enumerate(self.xml_files):
         try:
            xml_tree = ET.parse(imxml)
            xml_root = xml_tree.getroot()

            for object in xml_root.findall('object'):
               object_name = object.find('name').text

               if object_name != 'sheepface':
                  continue

               subobjFound = False
               for subobj in object.findall('subobj'):
                  subobjFound = True
                  break

               break

            if subobjFound:
               I_labelled.append(i)
            else:
               I_unlabelled.append(i)

         except:
            print("Failed to parse label file for %s." % imxml)

      return I_labelled, I_unlabelled


   def load_next_image(self, dir):

      while True:
         # Index of next image
         self.n += dir
         if self.n < 0:
            self.n=0
         elif self.n >= len(self.xml_files):
            self.n = len(self.xml_files)-1

         #print("Loading image %s (%d/%d)" % (self.xml_files[self.n].split("/")[-1],self.n, len(self.xml_files)))

         self.reset_canvas()

         # Read info from xml
         self.imxml = self.xml_files[self.n]

         imfile = None
         impath = None

         try:
            self.xml_tree = ET.parse(self.imxml)
            self.xml_root = self.xml_tree.getroot()
            self.xml_adjust = None
            self.xml_brightness = None
            self.xml_contrast = None

            self.xml_folder = self.xml_root.find('folder')
            self.imfolder = self.xml_folder.text


            imfile = self.xml_root.find('filename').text

            self.xml_path = self.xml_root.find('path')
            self.impath = self.xml_path.text

            if self.impath[0] == '/':
               if self.impath.find('/DSD2/ims') >= 0:
                  self.impath = self.impath[self.impath.find('/DSD2/ims/') + len('/DSD2/ims/'):]
                  self.impath = os.path.join(self.dataFolder, "2020_06", "ims", self.impath)
               else:
                  self.impath = self.impath[self.impath.find('/DSD/') + len('/DSD/'):]

               self.imfolder = self.impath[:-len(imfile)-1]


            impath = os.path.join(self.dataFolder, self.impath)

            impath = impath.replace("DSD2/ims", "DSD/2020_06/ims")

            #im = cv2.imread(impath)
            #im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            #self.orig_size = (im.shape[1],im.shape[0])
            #self.cur_size = (self.width, self.height)

            #im = cv2.resize(im, self.cur_size, interpolation=cv2.INTER_AREA)



            # Open file and save its original size
            self.pil_im = Image.open(impath)

            #self.pil_im = self.pil_im.rotate(-90, expand=True)

            self.orig_size = self.pil_im.size

            # Resize for this window
            self.pil_im.thumbnail((self.width, self.height))
            self.im = ImageTk.PhotoImage(self.pil_im)
            self.cur_size = self.pil_im.size

            self.xscale = self.cur_size[0] / self.orig_size[0]
            self.yscale = self.cur_size[1] / self.orig_size[1]


            self.xml_rotation = self.xml_root.find("rotation")
            if self.xml_rotation is not None:
               self.rotation.set(int(self.xml_rotation.text))

            self.xml_adjust = self.xml_root.find("adjust")
            if self.xml_adjust is not None:
               self.xml_brightness = self.xml_adjust.find("brightness")
               if self.xml_brightness is not None:
                  self.benh = float(self.xml_brightness.text)
                  self.bscale.set(self.benh-1)

               self.xml_contrast = self.xml_adjust.find("contrast")
               if self.xml_contrast is not None:
                  self.cenh = float(self.xml_contrast.text)
                  self.cscale.set(self.cenh-1)

            self.main_face = -1
            for object in self.xml_root.findall('object'):
               object_name = object.find('name').text

               if object_name != 'sheepface' and object_name != 'sheepface2':
                  continue

               if object_name == 'sheepface':
                  self.main_face = len(self.face)

               xml_tree_bbox = object.find('bndbox')
               xmin = int(np.round(int(xml_tree_bbox.find('xmin').text)*self.xscale))
               ymin = int(np.round(int(xml_tree_bbox.find('ymin').text)*self.yscale))
               xmax = int(np.round(int(xml_tree_bbox.find('xmax').text)*self.xscale))
               ymax = int(np.round(int(xml_tree_bbox.find('ymax').text)*self.yscale))

               #im[ymin:ymax,xmin:xmax,:], alpha, beta = automatic_brightness_and_contrast(im[ymin:ymax,xmin:xmax,:])

               canvas_object = self.draw_rectangle(xmin, ymin, xmax, ymax, outline=self.face_colour, width=2)
               self.face.append((xmin, ymin, xmax, ymax, canvas_object))
               self.markers.append((canvas_object, len(self.face)-1, 'face'))

               self.objs.append(list())

               self.xml_face.append(object)
               self.xml_objs.append(list())

               for i in range(len(self.obj_types)):
                  for j in range(len(self.sides)):
                     self.objs[-1].append(None)
                     self.xml_objs[-1].append(None)

               for subobj in object.findall('subobj'):

                  xml_tree_bbox = subobj.find('coords')
                  x1 = int(np.round(int(xml_tree_bbox.find('x1').text) * self.xscale))
                  y1 = int(np.round(int(xml_tree_bbox.find('y1').text) * self.yscale))
                  x2 = int(np.round(int(xml_tree_bbox.find('x2').text) * self.xscale))
                  y2 = int(np.round(int(xml_tree_bbox.find('y2').text) * self.yscale))

                  subobj_name = subobj.find('name').text

                  k = len(self.face)-1
                  side = self.sides.index(subobj_name[0])
                  type = self.obj_types.index(subobj_name[1:])

                  if self.obj_draws[type] == 'circle':
                     canvas_object = self.draw_oval(x1, y1, x2, y2,
                                                           outline=self.obj_colours[type][side], width=2)
                  elif self.obj_draws[type] == 'line':
                     canvas_object = self.draw_line(x1, y1, x2, y2,
                                                           fill=self.obj_colours[type][side], width=2)

                  self.objs[k][2*type+side] = (x1,y1,x2,y2,canvas_object)
                  self.xml_objs[k][2*type+side] = subobj
                  self.markers.append((canvas_object, k, subobj_name))
            break
         except:
            print("Failed to parse label file for %s." % self.imxml)


      if self.main_face==-1:
         print("No main face in %s" % self.imxml)

      # Change title of the window
      root.title(imfile + " (n=%d) (%.2f%%)" % (self.n, self.n/len(self.xml_files)*100))

      #self.im = ImageTk.PhotoImage(Image.fromarray(im))
      self.canvas.itemconfig(self.image_on_canvas, image=self.im)

      self.canvas.update_idletasks()



   def xml_write_bndbox(self,name,bbox,parent,element,tag):
      x1 = int(np.round(bbox[0]/self.xscale))
      y1 = int(np.round(bbox[1]/self.yscale))
      x2 = int(np.round(bbox[2]/self.xscale))
      y2 = int(np.round(bbox[3]/self.yscale))

      if x1 < x2:
         xmin = x1
         xmax = x2
      else:
         xmin = x2
         xmax = x1

      if y1 < y2:
         ymin = y1
         ymax = y2
      else:
         ymin = y2
         ymax = y1

      if element is None:
         attrib = {}
         element = parent.makeelement(tag, attrib)
         parent.append(element)

         # adding an element to the seconditem node
         subelement = element.makeelement('name', attrib)
         subelement.text = name
         element.append(subelement)

         bndbox = element.makeelement('bndbox', attrib)
         element.append(bndbox)

         subelement = bndbox.makeelement('xmin', attrib)
         subelement.text = "%d" % xmin
         bndbox.append(subelement)

         subelement = bndbox.makeelement('ymin', attrib)
         subelement.text = "%d" % ymin
         bndbox.append(subelement)

         subelement = bndbox.makeelement('xmax', attrib)
         subelement.text = "%d" % xmax
         bndbox.append(subelement)

         subelement = bndbox.makeelement('ymax', attrib)
         subelement.text = "%d" % ymax
         bndbox.append(subelement)
      else:
         belem = element.find('bndbox')

         subelement = belem.find('xmin')
         subelement.text = "%d" % xmin
         subelement = belem.find('ymin')
         subelement.text = "%d" % ymin
         subelement = belem.find('xmax')
         subelement.text = "%d" % xmax
         subelement = belem.find('ymax')
         subelement.text = "%d" % ymax

      return element

   def xml_write_props(self,name,value,element,parent):

      if element is None:
         attrib = {}
         if parent is None:
            parent = self.xml_root.makeelement("adjust", attrib)
            self.xml_root.append(parent)

         element = parent.makeelement(name, attrib)
         parent.append(element)

      element.text = "%.1f" % value

      return parent

   def xml_write_obj(self,name,bbox,parent,element,tag):
      x1 = int(np.round(bbox[0]/self.xscale))
      y1 = int(np.round(bbox[1]/self.yscale))
      x2 = int(np.round(bbox[2]/self.xscale))
      y2 = int(np.round(bbox[3]/self.yscale))

      if element is None:
         attrib = {}
         element = parent.makeelement(tag, attrib)
         parent.append(element)

         # adding an element to the seconditem node
         subelement = element.makeelement('name', attrib)
         subelement.text = name
         element.append(subelement)

         bndbox = element.makeelement('coords', attrib)
         element.append(bndbox)

         subelement = bndbox.makeelement('x1', attrib)
         subelement.text = "%d" % x1
         bndbox.append(subelement)

         subelement = bndbox.makeelement('y1', attrib)
         subelement.text = "%d" % y1
         bndbox.append(subelement)

         subelement = bndbox.makeelement('x2', attrib)
         subelement.text = "%d" % x2
         bndbox.append(subelement)

         subelement = bndbox.makeelement('y2', attrib)
         subelement.text = "%d" % y2
         bndbox.append(subelement)
      else:
         belem = element.find('coords')

         subelement = belem.find('x1')
         subelement.text = "%d" % x1
         subelement = belem.find('y1')
         subelement.text = "%d" % y1
         subelement = belem.find('x2')
         subelement.text = "%d" % x2
         subelement = belem.find('y2')
         subelement.text = "%d" % y2

      return element


   def xml_delete(self,xml_parent,xml_object):
      xml_parent.remove(xml_object)

   def save(self):



      if self.xml_tree is not None:

         if self.xml_folder is not None:
            self.xml_folder.text = self.imfolder

         if self.xml_path is not None:
            self.xml_path.text = self.impath

         if self.xml_rotation is None:
            self.xml_rotation = self.xml_root.makeelement('rotation',{})
            self.xml_root.append(self.xml_rotation)

         self.xml_rotation.text = "%d" % self.rotation.get()

         if self.benh is not None:
            self.xml_adjust = self.xml_write_props("brightness", self.benh, self.xml_brightness, self.xml_adjust)

         if self.cenh is not None:
            self.xml_adjust = self.xml_write_props("contrast", self.cenh, self.xml_contrast, self.xml_adjust)


         firstFace = True
         for k in range(len(self.xml_face)):
            if self.face[k] is not None:
               if firstFace:
                  tag = 'sheepface'
               else:
                  tag = 'sheepface2'

               self.xml_face[k] = self.xml_write_bndbox(tag,self.face[k], self.xml_root, self.xml_face[k],'object')
               firstFace = False

               for i in range(len(self.obj_types)):
                  for j in range(len(self.sides)):
                     if self.objs[k][2*i+j] is not None:
                        self.xml_write_obj(self.sides[j]+self.obj_types[i],self.objs[k][2*i+j], self.xml_face[k], self.xml_objs[k][2*i+j], 'subobj')
                     elif self.xml_objs[k][2*i+j] is not None:
                        self.xml_delete(self.xml_face[k],self.xml_objs[k][2*i+j])

            elif self.xml_face[k] is not None:
               self.xml_delete(self.xml_root,self.xml_face[k])

      #self.xml_tree.write(self.imxml)#, pretty_print=True)
      els = self.xml_tree.findall("*")
      els_assigned = np.zeros(len(els))
      tag_order = ['folder','filename','path','source','size','segmented','rotation','adjust']
      tags_known = []
      tags_other = []

      for tag in tag_order:
         for k in range(len(els)):
            if els[k].tag == tag:
               tags_known.append(els[k])
               els_assigned[k] = 1
               break

      for k in range(len(els)):
         if els_assigned[k] == 0:
            tags_other.append(els[k])

      tags = tags_known + tags_other
      self.xml_root[:] = tags

      xmlstr = minidom.parseString(ET.tostring(self.xml_root)).toprettyxml(indent="  ")
      xmlstr = os.linesep.join([s for s in xmlstr.splitlines() if s.strip()])  # remove the weird newline issue
      with open(self.imxml, "w") as f:
         f.write(xmlstr)


   def next(self):
      self.save()
      self.load_next_image(1)

   def prev(self):
      self.save()
      self.load_next_image(-1)

#def help():


if __name__ == "__main__":

   n = 0
   dataFolder = os.getcwd()
   cont = True
   nSet = False

   try:
      opts, args = getopt.getopt(sys.argv[1:], "cd:n:",
                                 ["data=", "number="])
   except getopt.GetoptError:
      help()
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         help()
         sys.exit()
      elif opt in ("-d", "--data"):
         dataFolder = arg
      elif opt in ("-c", "--continue"):
         cont = True
      elif opt in ("-n", "--number"):
         n = int(arg)
         nSet = True

   # Main tkinter window
   root = tk.Tk()
   root.title("Select Sheep")

   #df = SheepSelect(root, width=720,height=480)
   df = SheepSelect(root, width=1028,height=720,dataFolder=dataFolder,cont=cont,n=n,nSet=nSet)

   # Run the main loop
   root.mainloop()



