import win32api, win32con, win32gui
import win32process
import pandas as pd
import numpy as np
import datetime
import time
import os
from PIL import ImageGrab, Image
from jqdatasdk import get_trade_days

# reference https://zhuanlan.zhihu.com/p/97574557

BASE_DIR = "data/"

def get_handles():
    '''
    description: 获取系统当前所有句柄
    '''
    handle_title = dict()

    def get_all_handle(handle, mouse):
        if win32gui.IsWindow(handle) and win32gui.IsWindowEnabled(handle) and win32gui.IsWindowVisible(handle):
            handle_title.update({handle: win32gui.GetWindowText(handle)})

    win32gui.EnumWindows(get_all_handle, 0)
    # for h, t in handle_title.items():
    #     if t is not '':
    #         print(h, t)

    return handle_title


def get_child_handles(parent):
    '''
    description: 获得parent的所有子窗口句柄列表(预留函数)
     '''
    if not parent:
        return

    hwndChildList = []
    win32gui.EnumChildWindows(parent, lambda hwnd, param: param.append(hwnd), hwndChildList)

    return hwndChildList


def get_tick_handle():
    '''
    description: 根据最小值判定获取右下角(历史分时)子窗口的坐标，通用方法
    '''
    handle = win32gui.FindWindow(0, "东方财富终端")
    base_pid = win32process.GetWindowThreadProcessId(handle)
    handle_list = []

    for h, t in get_handles().items(): # handle id, handle text
        pid = win32process.GetWindowThreadProcessId(h)
        print(pid,h,t)
        if pid == base_pid and h != handle :
            handle_list.append(h)

    if len(handle_list)==0 :
        print("handle not found.") # 必须在高亮情况下才能被发现
        return

    # Treat the handle with the smallest handle number within the same process as the child window
    child_handle = min(handle_list)
    print(child_handle)

    x1, y1, x2, y2 = win32gui.GetWindowRect(child_handle) # constant value: 1319, 692, 1915, 1170

    return (x1, y1, x2, y2)


def get_tick_handle2(stock_code):
    '''
    description: 根据股票代码获取右下角(历史分时)子窗口的日期以及坐标
                 仅限子窗口标题满足以下形式: (000001) 2020年5月13日 星期三
    stock_code: like '000001'
    '''
    for h, t in get_handles().items(): # handle id, handle text
        pid = win32process.GetWindowThreadProcessId(h)
        print(pid,h,t)

        if t.startswith('('+stock_code+')'):
            print(h, t)
            x1, y1, x2, y2 = win32gui.GetWindowRect(h) # constant value: 1319, 692, 1915, 1170

            # make date
            str_p = str.split(t, " ")[1]
            dt = datetime.datetime.strptime(str_p, '%Y年%m月%d日')

            return dt, (x1, y1, x2, y2)

    print('handle not found.')


def make_title(stock_code, dt):
    '''
    description: 根据股票代码和日期生成小窗标题(预留函数)
    stock_code: 123456
    dt: datetime object
    title: (000001) 2020年5月13日 星期三
    '''
    year = dt.year
    month = dt.month
    day = dt.day
    weekday = dt.weekday()
    week_day = {
        0: '星期一',
        1: '星期二',
        2: '星期三',
        3: '星期四',
        4: '星期五',
        5: '星期六',
        6: '星期日',
    }
    title = '(' + stock_code + ') ' + str(year) + '年' + str(month) + '月' + str(day) + '日 ' + week_day[weekday]
    return title


def make_screenshots(stock_code, amt, start_date=None):
    '''
    description: 在主软件日线窗口和分时小窗同时开启的状态下连续截图，注意停牌会导致日期不准确
    stock_code: string like '000001'
    amt: screenshot amount
    start_date: must be a trading day as string format 'yyyy-mm-dd'
    '''
    handle = win32gui.FindWindow(0, "东方财富终端")
    if handle == 0 :
        print('base handle not found.')
        return

    win32gui.ShowWindow(handle, win32con.SW_MAXIMIZE) # 最大化

    (x1, y1, x2, y2) = get_tick_handle()
    if (x1, y1, x2, y2) != (1319, 692, 1915, 1170): # constant value
        print((x1, y1, x2, y2), "is different with constant value (1319, 692, 1915, 1170).")
        return

    if start_date is None:
        # get recent trade date
        start_date = get_trade_days(end_date=datetime.date.today(), count=1)[0]
        # todo: self-define get_trade_days

    dt = start_date

    dir_path = 'screenshot/'+stock_code
    if not os.path.exists(dir_path): os.makedirs(dir_path)

    for i in range(amt):
        win32gui.SetForegroundWindow(handle) # 高亮
        time.sleep(1)
        win32api.keybd_event(37, 0, 0, 0) # 左方向键键位码是37
        win32api.keybd_event(37, 0, win32con.KEYEVENTF_KEYUP, 0) # 释放按键
        time.sleep(1)

        pic = ImageGrab.grab((x1, y1, x2, y2))
        # pic.show()
        file_name = stock_code + '_' + str(dt) + '.png'
        pic.save(dir_path + file_name)
        print(file_name, 'saved.')

        # change dt to its last trading date
        dt = get_trade_days(end_date=dt, count=2)[0]
        # todo: self-define get_trade_days

    win32gui.ShowWindow(handle, win32con.SW_MINIMIZE) # 最小化


def make_cropped(stock_code):
    '''
    description: 将小窗截图进行裁剪并做黑色替换处理，只保留白色走势曲线
    '''
    # data from get_tick_handle()
    window = {"x1": 1319, "y1": 692, "x2": 1915, "y2": 1170}

    # data from FastStone Capture
    scope = {"X1": 1382, "Y1": 740, "X2": 1851, "Y2": 1082}

    left = scope["X1"]-window["x1"]+1
    upper =scope["Y1"]-window["y1"]+1
    right =scope["X2"]-window["x1"]+1
    lower =scope["Y2"]-window["y1"]+1

    file_list = os.listdir('screenshot/'+stock_code)

    dir_path = 'cropped/'+stock_code
    if not os.path.exists(dir_path): os.makedirs(dir_path)

    for item in file_list:
        img = Image.open('screenshot/'+stock_code+'/'+ item)
        cropped = img.crop((left, upper, right, lower))

        # # 获取当前图片中存在的颜色种类
        # array = np.asarray(cropped).reshape((scope["X2"]-scope["X1"]-1)*(scope["Y2"]-scope["Y1"]-1), 3)
        # l = []
        # for i in range(array.shape[0]):
        #     l.append(tuple(array[i]))
        #     print(set(l))
        #     # 黑色(近似)：(7, 7, 7)
        #     # 绿色(近似)：(57, 227, 101)
        #     # 灰色(近似):(60, 60, 60)
        #     # 白色(近似):(192, 192, 192)
        #     # 红色(近似)：(255, 92, 92)

        width, height = cropped.size # constant value: (468, 341)
        for x in range(width):
            for y in range(height):
                # r, g, b = cropped.getpixel((x, y))
                # rgba = (r, g, b)
                rgb = cropped.getpixel((x, y))
                if rgb != (192, 192, 192):
                    cropped.putpixel((x, y), (7, 7, 7))
        cropped = cropped.convert('RGB')
        # cropped.show()
        # cropped = cropped.resize((850, 1100))
        cropped.save(dir_path + item)
        print('item of %s is saved ' % (item))


def make_datafile(stock_code):
    '''
    description: 根据黑白图像生成数据文件
    stock_code: 123456
    '''
    # size data is from make_cropped()
    cropped_size = {"width": 468, "height": 341}

    df = pd.DataFrame(columns=list(range(cropped_size["width"])))
    file_list = os.listdir('cropped/'+stock_code)
    for item in file_list:
        img = Image.open('cropped/'+stock_code+'/'+item)
        index = item[7:-4] # YYYY-MM-DD
        curve = []
        for x in range(cropped_size["width"]):
            # 设置游标记录每列是否发现银白色像素
            c_len = len(curve)
            for y in range(cropped_size["height"]):
                rgb = img.getpixel((x, y))
                if rgb == (192, 192, 192): #银白色
                    curve.append(y)
                    break
            # 如果某列经过一次行遍历后未发现银白色像素，那么该列的值以相邻元素值代替，避免出现列表长度不足的问题
            if c_len == len(curve):
                curve.append(curve[-1])
        df.loc[index] = curve
        print("%s row add." % (index))
    # rewrite
    df.to_csv("datafile/"+stock_code+".txt", sep=" ", index=True, header=None) # \t
    print("make datafile for %s" % (stock_code))


def load_datafile(stock_code):
    '''
    description: load datafile data as df
    '''
    data_file = "datafile/"+stock_code+".txt"
    if not os.path.exists(data_file):
        print("file does not exist:", data_file)
        return
    else:
        df = pd.read_csv(data_file, sep=' ', header=False, index_col=0)
        print("file loaded with df.shape:", df.shape) #000001.txt: (3419, 469)
        return df


def sorted_sam(df, example):
    '''
    description: find the top 5 most similar trade days with example using SUM-ABS-MINUS
    df: get from load_datafile() or load_curve()
    example: string 2019-08-22, example date
    '''
    sam_list = []
    for row in df.iterrows():
        if str(row[0].date()) != example:
            sam_list.append((str(row[0].date()), sum(abs(row[1] - df.loc[example]))))
    sam_list.sort(key=lambda x: x[1], reverse=False)

    # touple list
    return sam_list[:5]
