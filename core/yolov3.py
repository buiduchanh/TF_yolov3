#! /usr/bin/env python
# coding=utf-8
#================================================================
#   Copyright (C) 2019 * Ltd. All rights reserved.
#
#   Editor      : VIM
#   File name   : yolov3.py
#   Author      : YunYang1994
#   Created date: 2019-02-28 10:47:03
#   Description :
#
#================================================================

import numpy as np
import tensorflow as tf
import core.utils as utils
import core.common as common
import core.backbone as backbone
from core.config import cfg
from MobilenetV2 import MobilenetV2

class YOLOV3(object):
    """Implement tensoflow yolov3 here"""
    def __init__(self, input_data, trainable):

        self.trainable        = trainable
        self.classes          = utils.read_class_names(cfg.YOLO.CLASSES)
        self.num_class        = len(self.classes)
        self.strides          = np.array(cfg.YOLO.STRIDES)
        self.anchors          = utils.get_anchors(cfg.YOLO.ANCHORS)
        self.anchor_per_scale = cfg.YOLO.ANCHOR_PER_SCALE
        self.iou_loss_thresh  = cfg.YOLO.IOU_LOSS_THRESH
        self.upsample_method  = cfg.YOLO.UPSAMPLE_METHOD
        
        self.mobile           = cfg.YOLO.BACKBONE_MOBILE
        self.gt_per_grid      = cfg.YOLO.GT_PER_GRID
        if not self.mobile:
            try:
                self.conv_lbbox, self.conv_mbbox, self.conv_sbbox = self.__build_nework(input_data)
            except:
                raise NotImplementedError("Can not build up yolov3 network!")

            with tf.variable_scope('pred_sbbox'):
                self.pred_sbbox = self.decode(self.conv_sbbox, self.anchors[0], self.strides[0])

            with tf.variable_scope('pred_mbbox'):
                self.pred_mbbox = self.decode(self.conv_mbbox, self.anchors[1], self.strides[1])

            with tf.variable_scope('pred_lbbox'):
                self.pred_lbbox = self.decode(self.conv_lbbox, self.anchors[2], self.strides[2])
        else:
            
            try:
                self.conv_lbbox, self.conv_mbbox, self.conv_sbbox = self.__build_nework(input_data)
            except:
                raise NotImplementedError("Can not build up yolov3 network!")

            with tf.variable_scope('pred_sbbox'):
                self.pred_sbbox = self.decode_mobile(conv_output=self.conv_sbbox, num_classes=self.num_class, stride=self.strides[0])
            
            with tf.variable_scope('pred_mbbox'):
                self.pred_mbbox = self.decode_mobile(conv_output=self.pred_mbbox, num_classes=self.num_class, stride=self.strides[1])
    
            with tf.variable_scope('pred_lbbox'):
                self.pred_lbbox = self.decode_mobile(conv_output=self.pred_lbbox, num_classes=self.num_class, stride=self.strides[2])

    def __build_nework_mobile(self, input_data):
        """
        :param input_data: shape为(batch_size, input_size, input_size, 3)
        :return: conv_sbbox, conv_mbbox, conv_lbbox, pred_sbbox, pred_mbbox, pred_lbbox
        conv_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid * (5 + num_classes))
        conv_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid * (5 + num_classes))
        conv_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid * (5 + num_classes))
        conv_?是YOLO的原始卷积输出(raw_dx, raw_dy, raw_dw, raw_dh, raw_conf, raw_prob)
        pred_sbbox的shape为(batch_size, input_size / 8, input_size / 8, gt_per_grid, 5 + num_classes)
        pred_mbbox的shape为(batch_size, input_size / 16, input_size / 16, gt_per_grid, 5 + num_classes)
        pred_lbbox的shape为(batch_size, input_size / 32, input_size / 32, gt_per_grid, 5 + num_classes)
        pred_?是YOLO预测bbox的信息(x, y, w, h, conf, prob)，(x, y, w, h)的大小是相对于input_size的
        """
        feature_map_s, feature_map_m, feature_map_l = MobilenetV2(input_data, self.trainable)

        conv = common.convolutional(name='conv0', input_data=feature_map_l, filters_shape=(1, 1, 1280, 512),
                                trainable=self.trainable)
        conv = common.separable_conv(name='conv1', input_data=conv, input_c=512, output_c=1024, trainable=self.trainable)
        conv = common.convolutional(name='conv2', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                trainable=self.trainable)
        conv = common.separable_conv(name='conv3', input_data=conv, input_c=512, output_c=1024, trainable=self.trainable)
        conv = common.convolutional(name='conv4', input_data=conv, filters_shape=(1, 1, 1024, 512),
                                trainable=self.trainable)

        # ----------**********---------- Detection branch of large object ----------**********----------
        conv_lbbox = common.separable_conv(name='conv5', input_data=conv, input_c=512, output_c=1024,
                                    trainable=self.trainable)
        conv_lbbox = common.convolutional(name='conv6', input_data=conv_lbbox,
                                    filters_shape=(1, 1, 1024, self.gt_per_grid * (self.num_class + 5)),
                                    trainable=self.trainable, downsample=False, activate=False, bn=False)
        # pred_lbbox = decode(name='pred_lbbox', conv_output=conv_lbbox,
        #                     num_classes=self.num_class, stride=self.__strides[2])
        # ----------**********---------- Detection branch of large object ----------**********----------

        # ----------**********---------- up sample and merge features map ----------**********----------
        conv = common.convolutional(name='conv7', input_data=conv, filters_shape=(1, 1, 512, 256),
                                trainable=self.trainable)
        conv = common.upsample(name='upsample0', input_data=conv)
        conv = common.route(name='route0', previous_output=feature_map_m, current_output=conv)
        # ----------**********---------- up sample and merge features map ----------**********----------

        conv = common.convolutional(name='conv8', input_data=conv, filters_shape=(1, 1, 96 + 256, 256), trainable=self.trainable)
        conv = common.separable_conv('conv9', input_data=conv, input_c=256, output_c=512, trainable=self.trainable)
        conv = common.convolutional(name='conv10', input_data=conv, filters_shape=(1, 1, 512, 256), trainable=self.trainable)
        conv = common.separable_conv('conv11', input_data=conv, input_c=256, output_c=512, trainable=self.trainable)
        conv = common.convolutional(name='conv12', input_data=conv, filters_shape=(1, 1, 512, 256),
                                trainable=self.trainable)

        # ----------**********---------- Detection branch of middle object ----------**********----------
        conv_mbbox = common.separable_conv(name='conv13', input_data=conv, input_c=256, output_c=512,
                                    trainable=self.trainable)
        conv_mbbox = common.convolutional(name='conv14', input_data=conv_mbbox,
                                    filters_shape=(1, 1, 512, self.gt_per_grid * (self.num_class + 5)),
                                    trainable=self.trainable, downsample=False, activate=False, bn=False)
        # pred_mbbox = decode(name='pred_mbbox', conv_output=conv_mbbox,
        #                     num_classes=self.num_class, stride=self.__strides[1])
        # ----------**********---------- Detection branch of middle object ----------**********----------

        # ----------**********---------- up sample and merge features map ----------**********----------
        conv = common.convolutional(name='conv15', input_data=conv, filters_shape=(1, 1, 256, 128),
                                trainable=self.trainable)
        conv = common.upsample(name='upsample1', input_data=conv)
        conv = common.route(name='route1', previous_output=feature_map_s, current_output=conv)
        # ----------**********---------- up sample and merge features map ----------**********----------

        conv = common.convolutional(name='conv16', input_data=conv, filters_shape=(1, 1, 32 + 128, 128),
                                trainable=self.trainable)
        conv = common.separable_conv(name='conv17', input_data=conv, input_c=128, output_c=256, trainable=self.trainable)
        conv = common.convolutional(name='conv18', input_data=conv, filters_shape=(1, 1, 256, 128),
                                trainable=self.trainable)
        conv = common.separable_conv(name='conv19', input_data=conv, input_c=128, output_c=256, trainable=self.trainable)
        conv = common.convolutional(name='conv20', input_data=conv, filters_shape=(1, 1, 256, 128),
                                trainable=self.trainable)

        # ----------**********---------- Detection branch of small object ----------**********----------
        conv_sbbox = common.separable_conv(name='conv21', input_data=conv, input_c=128, output_c=256,
                                    trainable=self.trainable)
        conv_sbbox = common.convolutional(name='conv22', input_data=conv_sbbox,
                                    filters_shape=(1, 1, 256, self.gt_per_grid * (self.num_class + 5)),
                                    trainable=self.trainable, downsample=False, activate=False, bn=False)
        # pred_sbbox = decode(name='pred_sbbox', conv_output=conv_sbbox,
        #                     num_classes=self.num_class, stride=self.__strides[0])
        # ----------**********---------- Detection branch of small object ----------**********----------

        return conv_lbbox, conv_mbbox, conv_sbbox
    def __build_nework(self, input_data):

        route_1, route_2, input_data = backbone.darknet53(input_data, self.trainable)

        input_data = common.convolutional(input_data, (1, 1, 1024,  512), self.trainable, 'conv52')
        input_data = common.convolutional(input_data, (3, 3,  512, 1024), self.trainable, 'conv53')
        input_data = common.convolutional(input_data, (1, 1, 1024,  512), self.trainable, 'conv54')
        input_data = common.convolutional(input_data, (3, 3,  512, 1024), self.trainable, 'conv55')
        input_data = common.convolutional(input_data, (1, 1, 1024,  512), self.trainable, 'conv56')

        conv_lobj_branch = common.convolutional(input_data, (3, 3, 512, 1024), self.trainable, name='conv_lobj_branch')
        conv_lbbox = common.convolutional(conv_lobj_branch, (1, 1, 1024, 3*(self.num_class + 5)),
                                          trainable=self.trainable, name='conv_lbbox', activate=False, bn=False)

        input_data = common.convolutional(input_data, (1, 1,  512,  256), self.trainable, 'conv57')
        input_data = common.upsample(input_data, name='upsample0', method=self.upsample_method)

        with tf.variable_scope('route_1'):
            input_data = tf.concat([input_data, route_2], axis=-1)

        input_data = common.convolutional(input_data, (1, 1, 768, 256), self.trainable, 'conv58')
        input_data = common.convolutional(input_data, (3, 3, 256, 512), self.trainable, 'conv59')
        input_data = common.convolutional(input_data, (1, 1, 512, 256), self.trainable, 'conv60')
        input_data = common.convolutional(input_data, (3, 3, 256, 512), self.trainable, 'conv61')
        input_data = common.convolutional(input_data, (1, 1, 512, 256), self.trainable, 'conv62')

        conv_mobj_branch = common.convolutional(input_data, (3, 3, 256, 512),  self.trainable, name='conv_mobj_branch' )
        conv_mbbox = common.convolutional(conv_mobj_branch, (1, 1, 512, 3*(self.num_class + 5)),
                                          trainable=self.trainable, name='conv_mbbox', activate=False, bn=False)

        input_data = common.convolutional(input_data, (1, 1, 256, 128), self.trainable, 'conv63')
        input_data = common.upsample(input_data, name='upsample1', method=self.upsample_method)

        with tf.variable_scope('route_2'):
            input_data = tf.concat([input_data, route_1], axis=-1)

        input_data = common.convolutional(input_data, (1, 1, 384, 128), self.trainable, 'conv64')
        input_data = common.convolutional(input_data, (3, 3, 128, 256), self.trainable, 'conv65')
        input_data = common.convolutional(input_data, (1, 1, 256, 128), self.trainable, 'conv66')
        input_data = common.convolutional(input_data, (3, 3, 128, 256), self.trainable, 'conv67')
        input_data = common.convolutional(input_data, (1, 1, 256, 128), self.trainable, 'conv68')

        conv_sobj_branch = common.convolutional(input_data, (3, 3, 128, 256), self.trainable, name='conv_sobj_branch')
        conv_sbbox = common.convolutional(conv_sobj_branch, (1, 1, 256, 3*(self.num_class + 5)),
                                          trainable=self.trainable, name='conv_sbbox', activate=False, bn=False)

        return conv_lbbox, conv_mbbox, conv_sbbox

    def decode_mobile(self, conv_output, num_classes, stride):
        
        conv_shape = tf.shape(conv_output)
        batch_size = conv_shape[0]
        output_size = conv_shape[1]
        gt_per_grid = conv_shape[3] / (5 + num_classes)

        conv_output = tf.reshape(conv_output, (batch_size, output_size, output_size, gt_per_grid, 5 + num_classes))
        conv_raw_dx1dy1 = conv_output[:, :, :, :, 0:2]
        conv_raw_dx2dy2 = conv_output[:, :, :, :, 2:4]
        conv_raw_conf = conv_output[:, :, :, :, 4:5]
        conv_raw_prob = conv_output[:, :, :, :, 5:]

        # 获取yolo的输出feature map中每个grid左上角的坐标
        # 需注意的是图像的坐标轴方向为
        #  - - - - > x
        # |
        # |
        # ↓
        # y
        # 在图像中标注坐标时通常用(y,x)，但此处为了与coor的存储格式(dx, dy, dw, dh)保持一致，将grid的坐标存储为(x, y)的形式

        y = tf.tile(tf.range(output_size, dtype=tf.int32)[:, tf.newaxis], [1, output_size])
        x = tf.tile(tf.range(output_size, dtype=tf.int32)[tf.newaxis, :], [output_size, 1])
        xy_grid = tf.concat([x[:, :, tf.newaxis], y[:, :, tf.newaxis]], axis=-1)
        xy_grid = tf.tile(xy_grid[tf.newaxis, :, :, tf.newaxis, :], [batch_size, 1, 1, gt_per_grid, 1])
        xy_grid = tf.cast(xy_grid, tf.float32)

        # (1)对xmin, ymin, xmax, ymax进行decode
        # dx_min, dy_min = exp(rawdx1dy1)
        # dx_max, dy_max = exp(rawdx2dy2)
        # xmin, ymin = ((x_grid, y_grid) + 0.5 - (dx_min, dy_min)) * stride
        # xmax, ymax = ((x_grid, y_grid) + 0.5 + (dx_max, dy_max)) * stride
        pred_xymin = (xy_grid + 0.5 - tf.exp(conv_raw_dx1dy1)) * stride
        pred_xymax = (xy_grid + 0.5 + tf.exp(conv_raw_dx2dy2)) * stride
        pred_corner = tf.concat([pred_xymin, pred_xymax], axis=-1)

        # (2)对confidence进行decode
        pred_conf = tf.sigmoid(conv_raw_conf)

        # (3)对probability进行decode
        pred_prob = tf.sigmoid(conv_raw_prob)

        pred_bbox = tf.concat([pred_corner, pred_conf, pred_prob], axis=-1)
        return pred_bbox
        
    def decode(self, conv_output, anchors, stride):
        """
        return tensor of shape [batch_size, output_size, output_size, anchor_per_scale, 5 + num_classes]
               contains (x, y, w, h, score, probability)
        """

        conv_shape       = tf.shape(conv_output)
        batch_size       = conv_shape[0]
        output_size      = conv_shape[1]
        anchor_per_scale = len(anchors)

        conv_output = tf.reshape(conv_output, (batch_size, output_size, output_size, anchor_per_scale, 5 + self.num_class))

        conv_raw_dxdy = conv_output[:, :, :, :, 0:2]
        conv_raw_dwdh = conv_output[:, :, :, :, 2:4]
        conv_raw_conf = conv_output[:, :, :, :, 4:5]
        conv_raw_prob = conv_output[:, :, :, :, 5: ]

        y = tf.tile(tf.range(output_size, dtype=tf.int32)[:, tf.newaxis], [1, output_size])
        x = tf.tile(tf.range(output_size, dtype=tf.int32)[tf.newaxis, :], [output_size, 1])

        xy_grid = tf.concat([x[:, :, tf.newaxis], y[:, :, tf.newaxis]], axis=-1)
        xy_grid = tf.tile(xy_grid[tf.newaxis, :, :, tf.newaxis, :], [batch_size, 1, 1, anchor_per_scale, 1])
        xy_grid = tf.cast(xy_grid, tf.float32)

        pred_xy = (tf.sigmoid(conv_raw_dxdy) + xy_grid) * stride
        pred_wh = (tf.exp(conv_raw_dwdh) * anchors) * stride
        pred_xywh = tf.concat([pred_xy, pred_wh], axis=-1)

        pred_conf = tf.sigmoid(conv_raw_conf)
        pred_prob = tf.sigmoid(conv_raw_prob)

        return tf.concat([pred_xywh, pred_conf, pred_prob], axis=-1)

    def focal(self, target, actual, alpha=1, gamma=2):
        focal_loss = alpha * tf.pow(tf.abs(target - actual), gamma)
        return focal_loss

    def bbox_giou(self, boxes1, boxes2):

        boxes1 = tf.concat([boxes1[..., :2] - boxes1[..., 2:] * 0.5,
                            boxes1[..., :2] + boxes1[..., 2:] * 0.5], axis=-1)
        boxes2 = tf.concat([boxes2[..., :2] - boxes2[..., 2:] * 0.5,
                            boxes2[..., :2] + boxes2[..., 2:] * 0.5], axis=-1)

        boxes1 = tf.concat([tf.minimum(boxes1[..., :2], boxes1[..., 2:]),
                            tf.maximum(boxes1[..., :2], boxes1[..., 2:])], axis=-1)
        boxes2 = tf.concat([tf.minimum(boxes2[..., :2], boxes2[..., 2:]),
                            tf.maximum(boxes2[..., :2], boxes2[..., 2:])], axis=-1)

        boxes1_area = (boxes1[..., 2] - boxes1[..., 0]) * (boxes1[..., 3] - boxes1[..., 1])
        boxes2_area = (boxes2[..., 2] - boxes2[..., 0]) * (boxes2[..., 3] - boxes2[..., 1])

        left_up = tf.maximum(boxes1[..., :2], boxes2[..., :2])
        right_down = tf.minimum(boxes1[..., 2:], boxes2[..., 2:])

        inter_section = tf.maximum(right_down - left_up, 0.0)
        inter_area = inter_section[..., 0] * inter_section[..., 1]
        union_area = boxes1_area + boxes2_area - inter_area
        iou = inter_area / union_area

        enclose_left_up = tf.minimum(boxes1[..., :2], boxes2[..., :2])
        enclose_right_down = tf.maximum(boxes1[..., 2:], boxes2[..., 2:])
        enclose = tf.maximum(enclose_right_down - enclose_left_up, 0.0)
        enclose_area = enclose[..., 0] * enclose[..., 1]
        giou = iou - 1.0 * (enclose_area - union_area) / enclose_area

        return giou

    def bbox_iou(self, boxes1, boxes2):

        boxes1_area = boxes1[..., 2] * boxes1[..., 3]
        boxes2_area = boxes2[..., 2] * boxes2[..., 3]

        boxes1 = tf.concat([boxes1[..., :2] - boxes1[..., 2:] * 0.5,
                            boxes1[..., :2] + boxes1[..., 2:] * 0.5], axis=-1)
        boxes2 = tf.concat([boxes2[..., :2] - boxes2[..., 2:] * 0.5,
                            boxes2[..., :2] + boxes2[..., 2:] * 0.5], axis=-1)

        left_up = tf.maximum(boxes1[..., :2], boxes2[..., :2])
        right_down = tf.minimum(boxes1[..., 2:], boxes2[..., 2:])

        inter_section = tf.maximum(right_down - left_up, 0.0)
        inter_area = inter_section[..., 0] * inter_section[..., 1]
        union_area = boxes1_area + boxes2_area - inter_area
        iou = 1.0 * inter_area / union_area

        return iou

    def loss_layer(self, conv, pred, label, bboxes, anchors, stride):

        conv_shape  = tf.shape(conv)
        batch_size  = conv_shape[0]
        output_size = conv_shape[1]
        input_size  = stride * output_size
        conv = tf.reshape(conv, (batch_size, output_size, output_size,
                                 self.anchor_per_scale, 5 + self.num_class))
        conv_raw_conf = conv[:, :, :, :, 4:5]
        conv_raw_prob = conv[:, :, :, :, 5:]

        pred_xywh     = pred[:, :, :, :, 0:4]
        pred_conf     = pred[:, :, :, :, 4:5]

        label_xywh    = label[:, :, :, :, 0:4]
        respond_bbox  = label[:, :, :, :, 4:5]
        label_prob    = label[:, :, :, :, 5:]

        giou = tf.expand_dims(self.bbox_giou(pred_xywh, label_xywh), axis=-1)
        input_size = tf.cast(input_size, tf.float32)

        bbox_loss_scale = 2.0 - 1.0 * label_xywh[:, :, :, :, 2:3] * label_xywh[:, :, :, :, 3:4] / (input_size ** 2)
        giou_loss = respond_bbox * bbox_loss_scale * (1- giou)

        iou = self.bbox_iou(pred_xywh[:, :, :, :, np.newaxis, :], bboxes[:, np.newaxis, np.newaxis, np.newaxis, :, :])
        max_iou = tf.expand_dims(tf.reduce_max(iou, axis=-1), axis=-1)

        respond_bgd = (1.0 - respond_bbox) * tf.cast( max_iou < self.iou_loss_thresh, tf.float32 )

        conf_focal = self.focal(respond_bbox, pred_conf)

        conf_loss = conf_focal * (
                respond_bbox * tf.nn.sigmoid_cross_entropy_with_logits(labels=respond_bbox, logits=conv_raw_conf)
                +
                respond_bgd * tf.nn.sigmoid_cross_entropy_with_logits(labels=respond_bbox, logits=conv_raw_conf)
        )

        prob_loss = respond_bbox * tf.nn.sigmoid_cross_entropy_with_logits(labels=label_prob, logits=conv_raw_prob)

        giou_loss = tf.reduce_mean(tf.reduce_sum(giou_loss, axis=[1,2,3,4]))
        conf_loss = tf.reduce_mean(tf.reduce_sum(conf_loss, axis=[1,2,3,4]))
        prob_loss = tf.reduce_mean(tf.reduce_sum(prob_loss, axis=[1,2,3,4]))

        return giou_loss, conf_loss, prob_loss



    def compute_loss(self, label_sbbox, label_mbbox, label_lbbox, true_sbbox, true_mbbox, true_lbbox):

        with tf.name_scope('smaller_box_loss'):
            loss_sbbox = self.loss_layer(self.conv_sbbox, self.pred_sbbox, label_sbbox, true_sbbox,
                                         anchors = self.anchors[0], stride = self.strides[0])

        with tf.name_scope('medium_box_loss'):
            loss_mbbox = self.loss_layer(self.conv_mbbox, self.pred_mbbox, label_mbbox, true_mbbox,
                                         anchors = self.anchors[1], stride = self.strides[1])

        with tf.name_scope('bigger_box_loss'):
            loss_lbbox = self.loss_layer(self.conv_lbbox, self.pred_lbbox, label_lbbox, true_lbbox,
                                         anchors = self.anchors[2], stride = self.strides[2])

        with tf.name_scope('giou_loss'):
            giou_loss = loss_sbbox[0] + loss_mbbox[0] + loss_lbbox[0]

        with tf.name_scope('conf_loss'):
            conf_loss = loss_sbbox[1] + loss_mbbox[1] + loss_lbbox[1]

        with tf.name_scope('prob_loss'):
            prob_loss = loss_sbbox[2] + loss_mbbox[2] + loss_lbbox[2]

        return giou_loss, conf_loss, prob_loss

    def loss_per_scale(self, conv, pred, label, bboxes, stride):
        
        conv_shape = tf.shape(conv)
        batch_size = conv_shape[0]
        output_size = conv_shape[1]
        input_size = stride * output_size
        conv = tf.reshape(conv, (batch_size, output_size, output_size,
                                self.gt_per_grid, 5 + self.num_class))
        conv_raw_conf = conv[..., 4:5]
        conv_raw_prob = conv[..., 5:]

        pred_coor = pred[..., 0:4]
        pred_conf = pred[..., 4:5]

        label_coor = label[..., 0:4]
        respond_bbox = label[..., 4:5]
        label_prob = label[..., 5:-1]
        label_mixw = label[..., -1:]

        # 计算GIOU损失
        GIOU = self.bbox_giou(pred_coor, label_coor)
        GIOU = GIOU[..., np.newaxis]
        input_size = tf.cast(input_size, tf.float32)
        bbox_wh = label_coor[..., 2:] - label_coor[..., :2]
        bbox_loss_scale = 2.0 - 1.0 * bbox_wh[..., 0:1] * bbox_wh[..., 1:2] / (input_size ** 2)
        GIOU_loss = respond_bbox * bbox_loss_scale * (1.0 - GIOU)

        # (2)计算confidence损失
        iou = self.bbox_iou(pred_coor[:, :, :, :, np.newaxis, :],
                            bboxes[:, np.newaxis, np.newaxis, np.newaxis, :, : ])
        max_iou = tf.reduce_max(iou, axis=-1)
        max_iou = max_iou[..., np.newaxis]
        respond_bgd = (1.0 - respond_bbox) * tf.cast(max_iou < self.iou_loss_thresh, tf.float32)

        conf_focal = self.focal(respond_bbox, pred_conf)

        conf_loss = conf_focal * (
                respond_bbox * tf.nn.sigmoid_cross_entropy_with_logits(labels=respond_bbox, logits=conv_raw_conf)
                +
                respond_bgd * tf.nn.sigmoid_cross_entropy_with_logits(labels=respond_bbox, logits=conv_raw_conf)
        )

        # (3)计算classes损失
        prob_loss = respond_bbox * tf.nn.sigmoid_cross_entropy_with_logits(labels=label_prob, logits=conv_raw_prob)
        loss = tf.concat([GIOU_loss, conf_loss, prob_loss], axis=-1)
        loss = loss * label_mixw
        loss = tf.reduce_mean(tf.reduce_sum(loss, axis=[1, 2, 3, 4]))
        return loss

    def compute_loss_mobile(self, label_sbbox, label_mbbox, label_lbbox, true_sbbox, true_mbbox, true_lbbox):

        with tf.name_scope('smaller_box_loss'):
            loss_sbbox = self.loss_per_scale(self.conv_sbbox, self.pred_sbbox, label_sbbox, true_sbbox,
                                          stride = self.strides[0])

        with tf.name_scope('medium_box_loss'):
            loss_mbbox = self.loss_per_scale(self.conv_mbbox, self.pred_mbbox, label_mbbox, true_mbbox,
                                         stride = self.strides[1])

        with tf.name_scope('bigger_box_loss'):
            loss_lbbox = self.loss_per_scale(self.conv_lbbox, self.pred_lbbox, label_lbbox, true_lbbox,
                                        stride = self.strides[2])

        with tf.name_scope('giou_loss'):
            giou_loss = loss_sbbox[0] + loss_mbbox[0] + loss_lbbox[0]

        with tf.name_scope('conf_loss'):
            conf_loss = loss_sbbox[1] + loss_mbbox[1] + loss_lbbox[1]

        with tf.name_scope('prob_loss'):
            prob_loss = loss_sbbox[2] + loss_mbbox[2] + loss_lbbox[2]

        return giou_loss, conf_loss, prob_loss