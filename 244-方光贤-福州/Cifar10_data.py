import os
import tensorflow as tf

# 数据分为10类
num_classes = 10

# 设定样本数 训练五万张 测试一万张
num_examples_pre_epoch_for_train = 50000
num_examples_pre_epoch_for_eval = 10000

# 定义一个空类返回读取的数据
class CIFAR10Record(object):
    pass

# 定义一个读取函数来读取文件内容
def read_cifar10(file_queue):
    result = CIFAR10Record()
    # 标签数为10 图像shape 为32*32*3
    label_bytes = 1
    result.height = 32
    result.width = 32
    result.depth = 3

    image_bytes = result.height * result.width * result.depth  # 图片像素数量
    record_bytes = label_bytes + image_bytes  # 每个元素的总个数要加上标签数

    reader = tf.FixedLengthRecordReader(record_bytes=record_bytes)  # 使用tf.FixedLengthRecordReader()创建一个文件读取类读取文件
    result.key, value = reader.read(file_queue)  # 使用read()函数读取文件
    record_bytes = tf.decode_raw(value, tf.uint8)  # 从字符串形式解析为图像对应的像素数组
    
    # 第一个元素是标签 使用strided_slice()函数将标签提取出来 并且使用tf.cast()函数将这一个标签转换成int32的数值形式
    result.label=tf.cast(tf.strided_slice(record_bytes,[0],[label_bytes]),tf.int32)

    # 剩下的元素再分割得到图片数据把格式转换成[depth,height,width]
    depth_major = tf.reshape(tf.strided_slice(record_bytes, [label_bytes], [label_bytes + image_bytes]),
                           [result.depth, result.height, result.width])
    result.uint8image = tf.transpose(depth_major,[1,2,0])

    return result

def inputs(data_dir,batch_size,distorted):
    filenames = [os.path.join(data_dir, "data_batch_%d.bin" % i)for i in range(1, 6)]  # 拼接文件名地址

    file_queue = tf.train.string_input_producer(filenames)  # 创建文件队列
    read_input = read_cifar10(file_queue)  # 读取队列文件

    reshaped_image = tf.cast(read_input.uint8image,tf.float32)   # 转回float32

    num_examples_per_epoch = num_examples_pre_epoch_for_train  # 训练轮次

    # 要进行图片增强处理
    if distorted != None:
        cropped_image = tf.random_crop(reshaped_image, [24, 24, 3])  # 先使用tf.random_crop()函数进行剪切

        flipped_image = tf.image.random_flip_left_right(cropped_image)  # 使用tf.image.random_flip_left_right()函数左右翻转

        adjusted_brightness = tf.image.random_brightness(flipped_image, max_delta=0.8)  # 使用tf.image.random_brightness()函数调整亮度

        adjusted_contrast = tf.image.random_contrast(adjusted_brightness, lower=0.2, upper=1.8)    # 使用tf.image.random_contrast()函数调整对比度

        float_image = tf.image.per_image_standardization(adjusted_contrast)  # 使用tf.image.per_image_standardization()批标准化

        float_image.set_shape([24,24,3])
        read_input.label.set_shape([1])

        min_queue_examples = int(num_examples_pre_epoch_for_eval * 0.4)
        print("Filling queue with %d CIFAR images before starting to train.    This will take a few minutes."
              % min_queue_examples)

        images_train, labels_train = tf.train.shuffle_batch([float_image,read_input.label], batch_size=batch_size,
                                                         num_threads = 16,
                                                         capacity = min_queue_examples + 3 * batch_size,
                                                         min_after_dequeue = min_queue_examples,
                                                         )  # 使用tf.train.shuffle_batch()函数随机产生一个batch的image和label

        return images_train, tf.reshape(labels_train, [batch_size])

    else:  # 不对图像数据进行数据增强处理
        resized_image = tf.image.resize_image_with_crop_or_pad(reshaped_image, 24, 24)  # 使用函数tf.image.resize_image_with_crop_or_pad()对图片数据进行剪切

        float_image = tf.image.per_image_standardization(resized_image)  # 剪切完成以后直接进行图片标准化操作

        float_image.set_shape([24, 24, 3])
        read_input.label.set_shape([1])

        min_queue_examples=int(num_examples_per_epoch * 0.4)

        images_test,labels_test=tf.train.batch([float_image,read_input.label],
                                              batch_size=batch_size,num_threads=16,
                                              capacity=min_queue_examples + 3 * batch_size)  # 这里使用batch()函数
        return images_test,tf.reshape(labels_test, [batch_size])
