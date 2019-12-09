#! /usr/bin/env python
# coding=utf-8
#================================================================
#   Copyright (C) 2019 * Ltd. All rights reserved.
#
#   Editor      : VIM
#   File name   : backbone.py
#   Author      : YunYang1994
#   Created date: 2019-02-17 11:03:35
#   Description :
#
#================================================================

import core.common as common
import tensorflow as tf


def darknet53(input_data, trainable):

    with tf.variable_scope('darknet'):

        input_data = common.convolutional(input_data, filters_shape=(3, 3,  3,  32), trainable=trainable, name='conv0')
        input_data = common.convolutional(input_data, filters_shape=(3, 3, 32,  64),
                                          trainable=trainable, name='conv1', downsample=True)

        for i in range(1):
            input_data = common.residual_block(input_data,  64,  32, 64, trainable=trainable, name='residual%d' %(i+0))

        input_data = common.convolutional(input_data, filters_shape=(3, 3,  64, 128),
                                          trainable=trainable, name='conv4', downsample=True)

        for i in range(2):
            input_data = common.residual_block(input_data, 128,  64, 128, trainable=trainable, name='residual%d' %(i+1))

        input_data = common.convolutional(input_data, filters_shape=(3, 3, 128, 256),
                                          trainable=trainable, name='conv9', downsample=True)

        for i in range(8):
            input_data = common.residual_block(input_data, 256, 128, 256, trainable=trainable, name='residual%d' %(i+3))

        route_1 = input_data
        input_data = common.convolutional(input_data, filters_shape=(3, 3, 256, 512),
                                          trainable=trainable, name='conv26', downsample=True)

        for i in range(8):
            input_data = common.residual_block(input_data, 512, 256, 512, trainable=trainable, name='residual%d' %(i+11))

        route_2 = input_data
        input_data = common.convolutional(input_data, filters_shape=(3, 3, 512, 1024),
                                          trainable=trainable, name='conv43', downsample=True)

        for i in range(4):
            input_data = common.residual_block(input_data, 1024, 512, 1024, trainable=trainable, name='residual%d' %(i+19))

        return route_1, route_2, input_data


def MobilenetV2(input_data, trainable):
    with tf.variable_scope('MobilenetV2'):
        conv = common.convolutional(name='Conv', input_data=input_data, filters_shape=(3, 3, 3, 32),
                             trainable=trainable, downsample=True, activate=True, bn=True)
        conv = common.inverted_residual(name='expanded_conv', input_data=conv, input_c=32, output_c=16,
                                 trainable=trainable, t=1)

        conv = common.inverted_residual(name='expanded_conv_1', input_data=conv, input_c=16, output_c=24, downsample=True,
                                 trainable=trainable)
        conv = common.inverted_residual(name='expanded_conv_2', input_data=conv, input_c=24, output_c=24, trainable=trainable)

        conv = common.inverted_residual(name='expanded_conv_3', input_data=conv, input_c=24, output_c=32, downsample=True,
                                 trainable=trainable)
        conv = common.inverted_residual(name='expanded_conv_4', input_data=conv, input_c=32, output_c=32, trainable=trainable)
        feature_map_s = common.inverted_residual(name='expanded_conv_5', input_data=conv, input_c=32, output_c=32,
                                          trainable=trainable)

        conv = common.inverted_residual(name='expanded_conv_6', input_data=feature_map_s, input_c=32, output_c=64,
                                 downsample=True, trainable=trainable)
        conv = common.inverted_residual(name='expanded_conv_7', input_data=conv, input_c=64, output_c=64, trainable=trainable)
        conv = common.inverted_residual(name='expanded_conv_8', input_data=conv, input_c=64, output_c=64, trainable=trainable)
        conv = common.inverted_residual(name='expanded_conv_9', input_data=conv, input_c=64, output_c=64, trainable=trainable)

        conv = common.inverted_residual(name='expanded_conv_10', input_data=conv, input_c=64, output_c=96, trainable=trainable)
        conv = common.inverted_residual(name='expanded_conv_11', input_data=conv, input_c=96, output_c=96, trainable=trainable)
        feature_map_m = common.inverted_residual(name='expanded_conv_12', input_data=conv, input_c=96, output_c=96,
                                          trainable=trainable)

        conv = common.inverted_residual(name='expanded_conv_13', input_data=feature_map_m, input_c=96, output_c=160,
                                 downsample=True, trainable=trainable)
        conv = common.inverted_residual(name='expanded_conv_14', input_data=conv, input_c=160, output_c=160, trainable=trainable)
        conv = common.inverted_residual(name='expanded_conv_15', input_data=conv, input_c=160, output_c=160, trainable=trainable)

        conv = common.inverted_residual(name='expanded_conv_16', input_data=conv, input_c=160, output_c=320, trainable=trainable)

        feature_map_l = common.convolutional(name='Conv_1', input_data=conv, filters_shape=(1, 1, 320, 1280),
                                      trainable=trainable, downsample=False, activate=True, bn=True)
    return feature_map_s, feature_map_m, feature_map_l

