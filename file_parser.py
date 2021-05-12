from PIL import Image, ImageTk, ImageEnhance
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image
import sys, getopt, os
import time
import tkinter as tk
import xml.etree.ElementTree as ET
from xml.dom import minidom
import cv2
import math
print('starting file parser')

# Code adopted from run_labeller.py
# There will be a lot of adopted/inspired code from run_labller.py
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

# Finds all xml files and splits them into files that have
# been labelled and haven't been labelled
def find_labelled(file):
    labelled = []
    unlabelled = []
    #i is the iteration we are on
    # xml_file_name is the name of the xml file we are messing
    # around with
    for i, xml_file_name in enumerate(file):
        try:
            xml_tree = ET.parse(xml_file_name)
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
                labelled.append(xml_file_name)
            else:
                unlabelled.append(xml_file_name)

        except:
            print("Failed to parse label file for %s." % xml_file_name)

    return labelled, unlabelled

def getXMLFile(filepath):
    xmltree = ET.parse(filepath)
    root = xmltree.getroot()
    return root

def get_dir(filename):
    file_dir = ''
    filename_start = filename[:4]
    if filename_start == 'P101':
        file_dir = '2019_12/lambs/101_PANA/'
    elif filename_start == 'P102':
        file_dir = '2019_12/lambs/102_PANA/'
    elif filename_start == 'P103':
        if int(filename[4:8]) <= 977:
            file_dir = '2019_12/lambs/103_PANA/'
        else:
            file_dir = '2019_12/Ewes/103_PANA/'
    elif filename_start == 'P104':
        file_dir = '2019_12/Ewes/104_PANA/'
    elif filename_start == 'P105':
        file_dir = '2019_12/Ewes/105_PANA/'
    else:
        file_dir = '2020_06/ims/'
    return file_dir

def get_dims(xmlFile):
    tree = ET.parse(xmlFile)
    root = tree.getroot()

    x1 = 0
    y1 = 0
    x2 = 0
    y2 = 0

    # iterate through xml tree
    for node in root:
        # Find node named object
        if node.tag == 'object':
            for obj_child in node:
                # Find the bndbox node inside the object node
                if obj_child.tag == 'bndbox':
                    # Extract the dimensions of the bndbx for the purposes of cropping the
                    # image around the face of the sheep
                    for bb in obj_child:
                        if bb.tag == 'xmin':
                            x1 = int(bb.text)
                        elif bb.tag == 'ymin':
                            y1 = int(bb.text)
                        elif bb.tag == 'xmax':
                            x2 = int(bb.text)
                        elif bb.tag == 'ymax':
                            y2 = int(bb.text)
    return x1, y1, x2, y2

# This file takes a list of XML filenames/paths and uses these
# to get the boundbox tags of each XML file, and crop the corresponding
# sheep image according to the values inside the boundbox tags.
def compress_imgs(files):
    print('compressing images')
    for file in files:
        filename = os.path.basename(os.path.normpath(file))[:-4]
        img_filename = filename + '.jpg'
        file_dir = ''
        # if image doesn't exist in compressed folder, we continue
        if not os.path.isfile('compressed/' + img_filename):
            file_dir = get_dir(filename)
            dims = get_dims(file)
            print('found uncompressed labelled image at ' + file_dir + img_filename)

            x1 = dims[0]
            y1 = dims[1]
            x2 = dims[2]
            y2 = dims[3]

            og_image = Image.open(file_dir + img_filename)
            cropped_img = og_image.crop((x1, y1, x2, y2))
            cropped_img = cropped_img.resize((128, 128), Image.ANTIALIAS)
            cropped_img.save('compressed/'+img_filename,optimize=True)

# yeah this is yikers
def get_obj_values(file, objname):
    # Values array, by order: xmin, ymin, xmax, ymax
    values = [-1, -1, -1, -1]
    tree = ET.parse(file)
    root = tree.getroot()

    for node in root:
        if node.tag == 'object':
            for objnode in node:
                # Ignore sheepface2 tags
                if objnode.tag == 'name' and objnode.text == 'sheepface2':
                    break
                if objnode.tag == 'subobj':
                    # At this point, we are iterating through all the nodes
                    # in the <subnode></subnode> tag
                    for subobjsubnode in objnode:
                        # If we have found the right subobj node
                        if subobjsubnode.text == objname:
                            for findcoords in objnode:
                                if findcoords.tag == 'coords':
                                    for coordsobj in findcoords:
                                        if coordsobj.tag == 'x1':
                                            values[0] = int(coordsobj.text)
                                        elif coordsobj.tag == 'y1':
                                            values[1] = int(coordsobj.text)
                                        elif coordsobj.tag == 'x2':
                                            values[2] = int(coordsobj.text)
                                        elif coordsobj.tag == 'y2':
                                            values[3] = int(coordsobj.text)
    return values


# Given a list of xml files, get all the inputs required
# for identifying the sheep facial features i.e. coords of
# the facial features such as right eye etc.
#
# Returns a 3d array, the first dimension being an array of complete sheep labels.
# The second dimension being an array of the individual sheep label 'objects'
# e.g. right eye, left mouth etc.
# The third dimension being the individual values of the facial feature
# label e.g. left eye begins at 13 pixels down.
# e.g. array[4][0][2] represents the 3rd value (xmax if i remember correctly)
# of the left eye of the 5th sheep in the labelled dataset.
#
# This will be a long, yucky looking method, I sincerely apologise!
def get_inputs():
    print('not yet implemented')
    # Our current working directory.
    currentdir = os.getcwd()
    # The path to the file containing all the labels
    labelsfile = read_labels(os.path.join(currentdir, "labels"))
    # All the label xml files that have been labelled.
    labelled = find_labelled(labelsfile)[0]
    inputsReturn = []
    # for each XML files in the list of filenames in labelled
    for i in range(len(labelled)):
        inputs = [-1, -1, -1, -1, -1, -1]
        # These vars represent the width and height of the original image
        # we are working with. This is important since we need these dimensions
        # to determine our new label positions on the cropped, resized image
        imgheight = -1
        imgwidth = -1
        tree = ET.parse(labelled[i])
        root = tree.getroot()
        # finding the dimensions of the original, uncompressed img
        for node in root:
            if node.tag == 'size':
                for sizenode in node:
                    if sizenode.tag == 'width':
                        imgwidth = int(sizenode.text)
                    elif sizenode.tag == 'height':
                        imgheight = int(sizenode.text)

        # Here we are finding the
        x_diff = imgwidth/128
        y_diff = imgheight/128
        inputs[0] = get_obj_values(labelled[i], 'leye')
        inputs[1] = get_obj_values(labelled[i], 'reye')
        inputs[2] = get_obj_values(labelled[i], 'rmouth')
        inputs[3] = get_obj_values(labelled[i], 'lmouth')
        inputs[4] = get_obj_values(labelled[i], 'lnostril')
        inputs[5] = get_obj_values(labelled[i], 'rnostril')
        print(labelled[i])
        print(inputs)
        for input in inputs:
            if input != -1:
                # Convert float result to int and round down so we maintain
                # our -1 encoding for non-present labels
                input[0] = int(math.floor(input[0]/x_diff))
                input[1] = int(math.floor(input[1]/x_diff))
                input[2] = int(math.floor(input[2]/x_diff))
                input[3] = int(math.floor(input[3]/x_diff))

        print(inputs, '\n')
        inputsReturn.append(inputs)
    return inputsReturn, labelled


#####################################################################
# ------------------------------ Main ------------------------------#
#####################################################################
# Our current working directory.
currentdir = os.getcwd()
# The path to the file containing all the labels
labelsfile = read_labels(os.path.join(currentdir, "labels"))
# All the label xml files that have been labelled.
labelled = find_labelled(labelsfile)[0]

# Run this everytime the script executes to check for labelled XMl files
# that don't have corresponding compressed imgs in the compressed directory
compress_imgs(labelled)

inputs = get_inputs()

print(inputs[0])
print(inputs[1])