# coding: utf-8
import os
import sys
import subprocess
import shutil
import time
import math
from PIL import Image, ImageDraw
import random
import json
import re
import numpy as np


abspath = os.path.dirname(sys.argv[0])   
if not os.path.isdir(abspath):
    abspath = sys.path[0]
if not os.path.isdir(abspath):
    abspath = os.path.dirname(__file__)
os.chdir(abspath)
# print(abspath)
default_encoding = 'utf-8'
if sys.getdefaultencoding() != default_encoding:
    reload(sys)
    sys.setdefaultencoding(default_encoding)

def open_accordant_config():
    screen_size = _get_screen_size()
    config_file = "{path}/config/{screen_size}/config.json".format(
        path = abspath,
        screen_size=screen_size
    )
    print("------path of config file--------------")
    # print(screen_size)
    print(config_file)
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            # print("Load config file from {}".format(config_file))
            return json.load(f)
    else:
        with open('{}/config/default.json'.format(abspath), 'r') as f:
            # print("Load default config")
            return json.load(f)


def _get_screen_size():
    size_str = os.popen('adb shell wm size').read()
    m = re.search('(\d+)x(\d+)', size_str)
    if m:
        width = m.group(1)
        height = m.group(2)
        return "{height}x{width}".format(height=height, width=width)

def pull_screenshot():
    process = subprocess.Popen('adb shell screencap -p', shell=True, stdout=subprocess.PIPE)
    screenshot = process.stdout.read()
    if sys.platform == 'win32':
        screenshot = screenshot.replace(b'\r\n', b'\n')
        # print("win32----")
    f = open('autojump.png', 'wb')
    f.write(screenshot)
    f.close()

def pull_screenshot2():
    os.system('del autojump.png')
    os.system('adb shell screencap -p /sdcard/autojump.png')
    os.system('adb pull /sdcard/autojump.png .')

def set_button_position(im):
    # 将swipe设置为 `再来一局` 按钮的位置
    global swipe_x1, swipe_y1, swipe_x2, swipe_y2
    w, h = im.size
    left = w / 2
    top = 1003 * (h / 1280.0) + 10
    swipe_x1, swipe_y1, swipe_x2, swipe_y2 = left, top, left, top


def jump(distance):
    press_time = distance * press_coefficient
    press_time = max(press_time, 200)   # 设置 200 ms 是最小的按压时间
    press_time = int(press_time)
    cmd = 'adb shell input swipe {x1} {y1} {x2} {y2} {duration}'.format(
        x1=swipe['x1'],
        y1=swipe['y1'],
        x2=swipe['x2'],
        y2=swipe['y2'],
        duration=press_time
    )
    # print(cmd)
    os.system(cmd)

# 转换色彩模式hsv2rgb
def hsv2rgb(h, s, v):
    h = float(h)
    s = float(s)
    v = float(v)
    h60 = h / 60.0
    h60f = math.floor(h60)
    hi = int(h60f) % 6
    f = h60 - h60f
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    r, g, b = 0, 0, 0
    if hi == 0: r, g, b = v, t, p
    elif hi == 1: r, g, b = q, v, p
    elif hi == 2: r, g, b = p, v, t
    elif hi == 3: r, g, b = p, q, v
    elif hi == 4: r, g, b = t, p, v
    elif hi == 5: r, g, b = v, p, q
    r, g, b = int(r * 255), int(g * 255), int(b * 255)
    return r, g, b

# 转换色彩模式rgb2hsv
def rgb2hsv(r, g, b):
    r, g, b = r/255.0, g/255.0, b/255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    df = mx-mn
    if mx == mn:
        h = 0
    elif mx == r:
        h = (60 * ((g-b)/df) + 360) % 360
    elif mx == g:
        h = (60 * ((b-r)/df) + 120) % 360
    elif mx == b:
        h = (60 * ((r-g)/df) + 240) % 360
    if mx == 0:
        s = 0
    else:
        s = df/mx
    v = mx
    return h, s, v


def find_piece_and_board(im):
    w, h = im.size
    piece_x_sum = 0
    piece_x_c = 0
    piece_y_max = 0
    board_x = 0
    board_y = 0

    left_value = 0
    left_count = 0
    right_value = 0
    right_count = 0
    from_left_find_board_y = 0
    from_right_find_board_y = 0


    scan_x_border = int(w / 8)  # 扫描棋子时的左右边界
    scan_start_y = 0  # 扫描的起始y坐标
    im_pixel=im.load()
    # 以50px步长，尝试探测scan_start_y
    for i in range(int(h / 3), int( h*2 /3 ), 50):
        last_pixel = im_pixel[0,i]
        for j in range(1, w):
            pixel=im_pixel[j,i]
            # 不是纯色的线，则记录scan_start_y的值，准备跳出循环
            if pixel[0] != last_pixel[0] or pixel[1] != last_pixel[1] or pixel[2] != last_pixel[2]:
                scan_start_y = i - 50
                break
        if scan_start_y:
            break
    # print('scan_start_y: ', scan_start_y)

    # 从scan_start_y开始往下扫描，棋子应位于屏幕上半部分，这里暂定不超过2/3
    for i in range(scan_start_y, int(h * 2 / 3)):
        for j in range(scan_x_border, w - scan_x_border):  # 横坐标方面也减少了一部分扫描开销
            pixel = im_pixel[j,i]
            # 根据棋子的最低行的颜色判断，找最后一行那些点的平均值，这个颜色这样应该 OK，暂时不提出来
            if (50 < pixel[0] < 60) and (53 < pixel[1] < 63) and (95 < pixel[2] < 110):
                piece_x_sum += j
                piece_x_c += 1
                piece_y_max = max(i, piece_y_max)

    if not all((piece_x_sum, piece_x_c)):
        return 0, 0, 0, 0
    piece_x = piece_x_sum / piece_x_c
    piece_y = piece_y_max - piece_base_height_1_2  # 上移棋子底盘高度的一半

    for i in range(int(h / 3), int(h * 2 / 3)):

        last_pixel = im_pixel[0, i]
        # 计算阴影的RGB值,通过photoshop观察,阴影部分其实就是背景色的明度V 乘以0.7的样子
        h, s, v = rgb2hsv(last_pixel[0], last_pixel[1], last_pixel[2])
        r, g, b = hsv2rgb(h, s, v * 0.7)

        if from_left_find_board_y and from_right_find_board_y:
            break

        if not board_x:
            board_x_sum = 0
            board_x_c = 0

            for j in range(w):
                pixel = im_pixel[j,i]
                # 修掉脑袋比下一个小格子还高的情况的 bug
                if abs(j - piece_x) < piece_body_width:
                    continue

                # 修掉圆顶的时候一条线导致的小 bug，这个颜色判断应该 OK，暂时不提出来
                if abs(pixel[0] - last_pixel[0]) + abs(pixel[1] - last_pixel[1]) + abs(pixel[2] - last_pixel[2]) > 10:
                    board_x_sum += j
                    board_x_c += 1
            if board_x_sum:
                board_x = board_x_sum / board_x_c
        else:
            # 继续往下查找,从左到右扫描,找到第一个与背景颜色不同的像素点,记录位置
            # 当有连续3个相同的记录时,表示发现了一条直线
            # 这条直线即为目标board的左边缘
            # 然后当前的 y 值减 3 获得左边缘的第一个像素
            # 就是顶部的左边顶点
            for j in range(w):
                pixel = im_pixel[j, i]
                # 修掉脑袋比下一个小格子还高的情况的 bug
                if abs(j - piece_x) < piece_body_width:
                    continue
                if (abs(pixel[0] - last_pixel[0]) + abs(pixel[1] - last_pixel[1]) + abs(pixel[2] - last_pixel[2])
                        > 10) and (abs(pixel[0] - r) + abs(pixel[1] - g) + abs(pixel[2] - b) > 10):
                    if left_value == j:
                        left_count = left_count+1
                    else:
                        left_value = j
                        left_count = 1

                    if left_count > 3:
                        from_left_find_board_y = i - 3
                    break
            # 逻辑跟上面类似,但是方向从右向左
            # 当有遮挡时,只会有一边有遮挡
            # 算出来两个必然有一个是对的
            for j in range(w)[::-1]:
                pixel = im_pixel[j, i]
                # 修掉脑袋比下一个小格子还高的情况的 bug
                if abs(j - piece_x) < piece_body_width:
                    continue
                if (abs(pixel[0] - last_pixel[0]) + abs(pixel[1] - last_pixel[1]) + abs(pixel[2] - last_pixel[2])
                    > 10) and (abs(pixel[0] - r) + abs(pixel[1] - g) + abs(pixel[2] - b) > 10):
                    if right_value == j:
                        right_count = left_count + 1
                    else:
                        right_value = j
                        right_count = 1

                    if right_count > 3:
                        from_right_find_board_y = i - 3
                    break

    # 如果顶部像素比较多,说明图案近圆形,相应的求出来的值需要增大,这里暂定增大顶部宽的三分之一
    if board_x_c > 5:
        from_left_find_board_y = from_left_find_board_y + board_x_c / 3
        from_right_find_board_y = from_right_find_board_y + board_x_c / 3

    # 按实际的角度来算，找到接近下一个 board 中心的坐标 这里的角度应该是30°,值应该是tan 30°,math.sqrt(3) / 3
    board_y = piece_y - abs(board_x - piece_x) * math.sqrt(3) / 3

    # 从左从右取出两个数据进行对比,选出来更接近原来老算法的那个值
    if abs(board_y - from_left_find_board_y) > abs(from_right_find_board_y):
        new_board_y = from_right_find_board_y
    else:
        new_board_y = from_left_find_board_y

    if not all((board_x, board_y)):
        return 0, 0, 0, 0

    return piece_x, piece_y, board_x, new_board_y

def dump_device_info():
    size_str = os.popen('adb shell wm size').read()
    device_str = os.popen('adb shell getprop ro.product.model').read()
    density_str = os.popen('adb shell wm density').read()
    # print("如果你的脚本无法工作，上报issue时请copy如下信息:\n**********\
    #     \nScreen: {size}\nDensity: {dpi}\nDeviceType: {type}\nOS: {os}\nPython: {python}\n**********".format(
    #         size=size_str.strip(),
    #         type=device_str.strip(),
    #         dpi=density_str.strip(),
    #         os=sys.platform,
    #         python=sys.version
    # ))

def check_adb():
    flag = os.system('adb devices')
    if flag == 1:
        print('Please install ADB and configure environment variables')
        x = input('Press any key to exit')
        sys.exit()

def main():

    h, s, v = rgb2hsv(201, 204, 214)
    # print(h, s, v)
    r, g, b = hsv2rgb(h, s, v*0.7)
    # print(r, g, b)

    dump_device_info()
    check_adb()
    while True:
        pull_screenshot2()
        im = Image.open('autojump.png')
        # w, h = im.size
        # if w > h:
        #     im = im.transpose(Image.ROTATE_90)
        # im = np.array(Image.open('autojump.png'))
        # 获取棋子和 board 的位置
        # print('-------------------------')
        piece_x, piece_y, board_x, board_y = find_piece_and_board(im)
        ts = int(time.time())
        # print(ts, piece_x, piece_y, board_x, board_y)
        set_button_position(im)
        jump(math.sqrt((board_x - piece_x) ** 2 + (board_y - piece_y) ** 2))
        # save_debug_creenshot(ts, im, piece_x, piece_y, board_x, board_y)
        # backup_screenshot(ts)
        time.sleep(random.uniform(1.2, 1.4))   # 为了保证截图的时候应落稳了，多延迟一会儿
        # x = input('input::::::')


if __name__ == '__main__':
    # x = input('input:')
    try:

        config = open_accordant_config()
        # Magic Number，不设置可能无法正常执行，请根据具体截图从上到下按需设置
        under_game_score_y = config['under_game_score_y']
        press_coefficient = config['press_coefficient']       # 长按的时间系数，请自己根据实际情况调节
        piece_base_height_1_2 = config['piece_base_height_1_2']   # 二分之一的棋子底座高度，可能要调节
        piece_body_width = config['piece_body_width']             # 棋子的宽度，比截图中量到的稍微大一点比较安全，可能要调节

        # 模拟按压的起始点坐标，需要自动重复游戏请设置成“再来一局”的坐标
        if config.get('swipe'):
            swipe = config['swipe']
        else:
            swipe = {}
            swipe['x1'], swipe['y1'], swipe['x2'], swipe['y2'] = 320, 410, 320, 410

        main()
    except Exception as e:
        print(e.message)
        x = input('there are some error. please try again...')
    # x = input('input:')
