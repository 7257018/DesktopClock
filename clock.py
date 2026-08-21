#!/usr/bin/env python3                          # 指定使用 Python3 解释器运行
# -*- coding: utf-8 -*-                        # 声明源码文件编码为 UTF-8
"""
桌面时钟小组件                                  # 模块文档字符串，描述程序用途
- 显示秒针时数字完整，无任何裁剪（边距0.8倍字体，最小40px）   # 说明秒数显示不会被裁剪的边距策略
- 切换渐变主题                                  # 支持多种渐变色彩主题
- 日期/星期字体大小为时间0.45倍                  # 日期与星期字号为主时间的 0.45 倍
- 设置读写类型安全，无残留，单实例强制             # 配置项类型安全，单实例运行
- Python 3.13 + PyQt6 + Windows 11 测试通过    # 已通过的环境组合
- 作者：李旭敏                                  # 作者信息
"""

import sys                                     # 导入系统模块，用于命令行参数与退出
import os                                      # 导入操作系统模块，用于路径判断
import atexit                                  # 导入退出处理模块，注册程序退出回调
import traceback                               # 导入堆栈跟踪模块，用于异常日志
from datetime import date                      # 从 datetime 导入 date，用于公历日期计算
from PyQt6.QtWidgets import (                  # 导入 PyQt6 控件组件
    QApplication, QWidget, QSystemTrayIcon, QMenu, QDialog,  # 应用、窗口、托盘、菜单、对话框
    QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QSlider,   # 各类布局与基础控件
    QPushButton, QColorDialog, QFontDialog, QCheckBox, QComboBox,  # 按钮、颜色/字体对话框、复选框、下拉框
    QSpinBox, QGroupBox, QMessageBox           # 数值调节框、分组框、消息框
)
from PyQt6.QtGui import (                      # 导入 PyQt6 GUI 绘制相关类
    QFont, QPainter, QColor, QLinearGradient, QFontMetrics,  # 字体、画笔、颜色、线性渐变、字体度量
    QAction, QIcon, QPixmap, QBrush, QPen, QFontDatabase, QGradient  # 动作、图标、位图、画刷、画笔、字体库、渐变基类
)
from PyQt6.QtCore import (                     # 导入 PyQt6 核心类
    Qt, QTimer, QTime, QDate, QRect, QPoint,   # 枚举、定时器、时间、日期、矩形、点
    QSharedMemory, pyqtSignal, QObject, QCoreApplication, QSettings  # 共享内存、信号、对象、核心应用、设置
)

# ---------------------------- 常量定义 ----------------------------
APP_NAME = "DesktopClock"                    # 应用名称，用于注册表与共享内存标识
APP_KEY = "DesktopClockApp"                  # 单实例共享内存键名
ORG_NAME = "MyOrg"                             # 组织名称，QSettings 使用
DEFAULT_FONT_FAMILY = "Arial"                  # 默认字体族
DEFAULT_BASE_SIZE = 50                         # 默认主时间字号
DEFAULT_FONT_OPACITY = 255                     # 默认字体不透明度（0-255）
DEFAULT_COLOR = QColor(255, 255, 255)  # 白色  # 默认字体颜色为白色
DEFAULT_THEME = "单色"                         # 默认主题为单色
DEFAULT_SHOW_DATE = True                       # 默认显示公历日期
DEFAULT_SHOW_WEEK = True                       # 默认显示星期
DEFAULT_SHOW_SECONDS = True                    # 默认显示秒钟
DEFAULT_SHOW_LUNAR = True                      # 默认显示农历
DEFAULT_SHOW_LUNAR_YEAR = False                 # 默认不显示农历年（二〇二六年）
DEFAULT_SHOW_GANZHI = False                     # 默认不显示天干地支（丙午）
DEFAULT_SHOW_ZODIAC = False                     # 默认不显示属相（马）
DEFAULT_DATE_WEEK_SAME_LINE = False              # 默认日期与星期并排同一行
DEFAULT_COUNTDOWN_MINUTES = 25                 # 默认倒计时分钟数
DEFAULT_STARTUP_WITH_OS = True                 # 默认开机自启动
DEFAULT_FIXED_POS = False                      # 默认不固定时钟位置（可拖动）
DEFAULT_STAY_ON_TOP = False                    # 默认不置顶显示


# ---------------------------- 主题管理器 ----------------------------
class ThemeManager:                             # 主题管理器类，统一管理渐变主题
    """管理渐变主题，返回颜色停止点列表"""          # 类文档：负责返回颜色停止点列表
    
    THEMES = {                                  # 所有可用主题字典，键为主题名，值为停止点列表
        "单色": [(0.0, QColor(255, 255, 255))],  # 单色主题：起始即白色
        "彩虹": [                               # 彩虹主题：红橙黄绿青蓝紫渐变
            (0.0, QColor(255, 0, 0)),      # 红        # 渐变位置 0.0，红色
            (0.16, QColor(255, 165, 0)),   # 橙        # 渐变位置 0.16，橙色
            (0.33, QColor(255, 255, 0)),   # 黄        # 渐变位置 0.33，黄色
            (0.5, QColor(0, 255, 0)),      # 绿        # 渐变位置 0.5，绿色
            (0.66, QColor(0, 255, 255)),   # 青        # 渐变位置 0.66，青色
            (0.83, QColor(0, 0, 255)),     # 蓝        # 渐变位置 0.83，蓝色
            (1.0, QColor(128, 0, 128)),    # 紫        # 渐变位置 1.0，紫色
        ],
        "落日": [                               # 落日主题：橙红到黄
            (0.0, QColor(255, 69, 0)),     # 橙红       # 起始橙红
            (0.33, QColor(255, 140, 0)),   # 橙        # 中段橙色
            (0.66, QColor(255, 215, 0)),   # 金黄       # 后段金黄
            (1.0, QColor(255, 255, 0)),    # 黄        # 末段黄色
        ],
        "黑白": [                               # 黑白主题：白到黑灰阶
            (0.0, QColor(255, 255, 255)),         # 起始纯白
            (0.33, QColor(200, 200, 200)),        # 浅灰
            (0.66, QColor(100, 100, 100)),        # 中灰
            (1.0, QColor(0, 0, 0)),               # 末段纯黑
        ],
        "紫色心情": [                            # 紫色心情主题：多层次紫
            (0.0, QColor(230, 230, 250)),  # 薰衣草     # 起始薰衣草色
            (0.33, QColor(147, 112, 219)), # 紫罗兰     # 中段紫罗兰
            (0.66, QColor(138, 43, 226)),  # 蓝紫       # 后段蓝紫
            (1.0, QColor(186, 85, 211)),   # 中紫       # 末段中紫
        ],
        "红色风暴": [                            # 红色风暴主题：红色渐深
            (0.0, QColor(255, 0, 0)),              # 起始亮红
            (0.33, QColor(200, 0, 0)),             # 中红
            (0.66, QColor(150, 0, 0)),             # 深红
            (1.0, QColor(100, 0, 0)),              # 暗红
        ],
        "海洋蓝": [                              # 海洋蓝主题：浅蓝到深蓝
            (0.0, QColor(0, 191, 255)),            # 起始亮蓝
            (0.33, QColor(30, 144, 255)),          # 道奇蓝
            (0.66, QColor(70, 130, 180)),          # 钢蓝
            (1.0, QColor(25, 25, 112)),            # 末段午夜蓝
        ],
        "森林绿": [                              # 森林绿主题：浅绿到深绿
            (0.0, QColor(173, 255, 47)),           # 起始绿黄
            (0.33, QColor(124, 252, 0)),           # 草绿
            (0.66, QColor(50, 205, 50)),           # 石灰绿
            (1.0, QColor(34, 139, 34)),            # 末段森林绿
        ],
        "极光": [                                # 极光主题：绿青蓝紫
            (0.0, QColor(0, 255, 127)),            # 起始春绿
            (0.33, QColor(0, 255, 255)),           # 青色
            (0.66, QColor(0, 191, 255)),           # 深天蓝
            (1.0, QColor(138, 43, 226)),           # 末段蓝紫
        ],
        "糖果": [                                # 糖果主题：粉色调
            (0.0, QColor(255, 182, 193)),          # 起始浅粉
            (0.33, QColor(255, 192, 203)),         # 粉色
            (0.66, QColor(255, 218, 185)),         # 桃色
            (1.0, QColor(255, 228, 225)),          # 末段雪色
        ],
        "烈焰": [                                # 烈焰主题：橙红到金黄
            (0.0, QColor(255, 99, 71)),            # 起始番茄红
            (0.33, QColor(255, 69, 0)),            # 橙红
            (0.66, QColor(255, 140, 0)),           # 深橙
            (1.0, QColor(255, 215, 0)),            # 末段金黄
        ],
    }
    
    @classmethod                                # 类方法装饰器
    def get_gradient_stops(cls, theme_name):    # 根据主题名获取渐变停止点
        return cls.THEMES.get(theme_name, cls.THEMES["单色"])  # 找不到则回退到单色


# ---------------------------- 农历计算（自包含，1900-2100） ----------------------------
class LunarCalendar:                            # 农历计算类，自包含无外部依赖
    """公历转农历，无外部依赖。数据表覆盖 1900-2100 年。
    每年 16 位编码：bits 0-3 闰月月份(0=无)，bits 4-15 十二个月大小(1=30天,0=29天)，
    bit 16 为闰月天数(1=30天,0=29天)。"""                         # 编码说明文档

    LUNAR_INFO = [                              # 1900-2100 年的农历数据表
        0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,  # 1900
        0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,  # 1910
        0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,  # 1920
        0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,  # 1930
        0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,  # 1940
        0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,  # 1950
        0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,  # 1960
        0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,  # 1970
        0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,  # 1980
        0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x055c0, 0x0ab60, 0x096d5, 0x092e0,  # 1990
        0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,  # 2000
        0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,  # 2010
        0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,  # 2020
        0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,  # 2030
        0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,  # 2040
        0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0,  # 2050
        0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,  # 2060
        0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,  # 2070
        0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,  # 2080
        0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,  # 2090
        0x0d520,  # 2100                          # 2100 年数据
    ]

    GAN = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']  # 十天干
    ZHI = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']  # 十二地支
    ZODIAC = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']  # 十二生肖
    MONTH_NAME = ['正', '二', '三', '四', '五', '六', '七', '八', '九', '十', '冬', '腊']  # 农历月名

    @staticmethod                                # 静态方法装饰器
    def _leap_month(year):                       # 获取指定年份的闰月月份
        idx = year - 1900                        # 计算在数据表中的索引
        if 0 <= idx < len(LunarCalendar.LUNAR_INFO):  # 索引合法
            return LunarCalendar.LUNAR_INFO[idx] & 0x0f  # 低 4 位为闰月月份，0 表示无闰月
        return 0                                 # 越界返回 0

    @staticmethod                                # 静态方法装饰器
    def _leap_days(year):                        # 获取指定年份闰月的天数
        if LunarCalendar._leap_month(year):      # 存在闰月
            idx = year - 1900                    # 计算索引
            return 30 if (LunarCalendar.LUNAR_INFO[idx] & 0x10000) else 29  # bit16 为 1 则 30 天，否则 29 天
        return 0                                 # 无闰月返回 0 天

    @staticmethod                                # 静态方法装饰器
    def _month_days(year, month):                # 获取指定年份某月的天数
        idx = year - 1900                        # 计算索引
        if 0 <= idx < len(LunarCalendar.LUNAR_INFO):  # 索引合法
            # bit 15 = 正月, bit 4 = 十二月
            return 29 + ((LunarCalendar.LUNAR_INFO[idx] >> (16 - month)) & 0x01)  # 对应位为 1 则 30 天，否则 29 天
        return 29                                # 越界默认返回 29 天

    @staticmethod                                # 静态方法装饰器
    def _year_days(year):                        # 获取指定农历年的总天数
        idx = year - 1900                        # 计算索引
        if 0 <= idx < len(LunarCalendar.LUNAR_INFO):  # 索引合法
            total = 348                          # 12 个月基础 29 天合计 = 348
            bit = 0x8000                         # 从 bit 15 开始
            while bit > 0x8:                     # 遍历到 bit 4 为止
                if LunarCalendar.LUNAR_INFO[idx] & bit:  # 该位为 1 表示对应月为 30 天
                    total += 1                   # 累加 1 天
                bit >>= 1                        # 右移处理下一位
            return total + LunarCalendar._leap_days(year)  # 加上闰月天数
        return 348                               # 越界默认返回 348

    @staticmethod                                # 静态方法装饰器
    def solar_to_lunar(year, month, day):        # 公历转农历主函数
        """公历转农历，返回 (lunar_year, lunar_month, lunar_day, is_leap)。越界返回原值。"""
        try:                                     # 异常保护
            base = date(1900, 1, 31)  # 1900年正月初一  # 农历基准日期
            solar = date(year, month, day)       # 构造公历日期对象
            offset = (solar - base).days         # 计算与基准日的天数差
            if offset < 0:                       # 早于基准日
                return (year, month, day, False) # 越界返回原值

            # 确定农历年：逐年扣除该年总天数
            lunar_year = 1900                    # 农历年起始
            while lunar_year < 2100:             # 遍历至 2100 年
                yd = LunarCalendar._year_days(lunar_year)  # 当年总天数
                if offset < yd:                  # 剩余天数少于当年总天数
                    break                        # 已确定农历年
                offset -= yd                     # 扣除当年天数
                lunar_year += 1                  # 进入下一年

            # 确定农历月和日：逐月扣除，闰月紧跟同名普通月之后
            leap = LunarCalendar._leap_month(lunar_year)  # 当年闰月月份
            lunar_month = 1                      # 农历月初始为 1
            is_leap = False                      # 是否闰月标记
            for m in range(1, 13):               # 遍历 12 个月
                days = LunarCalendar._month_days(lunar_year, m)  # 当月天数
                if offset < days:                # 剩余天数少于当月天数
                    lunar_month = m              # 确定为该月
                    break                        # 退出循环
                offset -= days                   # 扣除当月天数
                # 闰月出现在普通月之后
                if leap == m:                    # 当月后跟闰月
                    ldays = LunarCalendar._leap_days(lunar_year)  # 闰月天数
                    if offset < ldays:           # 落入闰月
                        lunar_month = m          # 月份号相同
                        is_leap = True           # 标记为闰月
                        break                    # 退出循环
                    offset -= ldays              # 扣除闰月天数
                lunar_month = m + 1              # 进入下一个月

            return (lunar_year, lunar_month, offset + 1, is_leap)  # 返回农历年月日及闰月标记（日从 1 开始）
        except Exception:                        # 异常处理
            return (year, month, day, False)     # 异常时返回原值

    @staticmethod                                # 静态方法装饰器
    def _day_name(day):                          # 将农历日数转为中文名
        if day == 10:                            # 初十
            return '初十'
        if day == 20:                            # 二十
            return '二十'
        if day == 30:                            # 三十
            return '三十'
        prefix = ['初', '十', '廿']              # 十位前缀：1-9 用初，10-19 用十，20-29 用廿
        nums = ['一', '二', '三', '四', '五', '六', '七', '八', '九']  # 个位数字
        return prefix[(day - 1) // 10] + nums[(day % 10) - 1]  # 组合返回如 '初一'、'十五'

    @staticmethod                                # 静态方法装饰器
    def format_lunar(year, month, day, show_year=False, show_ganzhi=False, show_zodiac=False):  # 格式化农历字符串
        """格式化农历，按需组合 '二〇二六年(丙午 马)七月初五'。异常返回空串。
        - show_year: 是否显示农历年（二〇二六年）
        - show_ganzhi: 是否显示天干地支（丙午）
        - show_zodiac: 是否显示属相（马）
        - 括号规则：show_ganzhi 与 show_zodiac 至少一个为真时显示括号，否则不显示
        """
        try:                                     # 异常保护
            ly, lm, ld, is_leap = LunarCalendar.solar_to_lunar(year, month, day)  # 转换为农历

            # 组装农历年部分（如 "二〇二六年"）
            year_part = ""                       # 农历年字符串
            if show_year:                        # 需要显示农历年
                cn_digits = ['〇', '一', '二', '三', '四', '五', '六', '七', '八', '九']  # 中文数字
                year_str = "".join(cn_digits[int(ch)] for ch in str(ly))  # 逐位转中文数字
                year_part = f"{year_str}年"      # 拼接为 二〇二六年

            # 组装干支/属相部分，括号规则：至少一个为真才显示括号
            gz_part = ""                         # 干支属相字符串
            inner_items = []                     # 括号内条目列表
            if show_ganzhi or show_zodiac:       # 至少一项为真，需要括号
                offset = (ly - 4) % 60           # 计算 60 甲子序号（公元 4 年为甲子年）
                if show_ganzhi:                  # 显示干支
                    inner_items.append(f"{LunarCalendar.GAN[offset % 10]}{LunarCalendar.ZHI[offset % 12]}")  # 丙午
                if show_zodiac:                  # 显示属相
                    inner_items.append(LunarCalendar.ZODIAC[offset % 12])  # 马
                gz_part = "(" + " ".join(inner_items) + ")"  # 拼接为 (丙午 马) 或 (丙午) 或 (马)

            # 组装月日部分
            month_str = ("闰" if is_leap else "") + LunarCalendar.MONTH_NAME[lm - 1] + "月"  # 拼接月名（闰月加前缀）
            return f"{year_part}{gz_part}{month_str}{LunarCalendar._day_name(ld)}"  # 拼接完整农历字符串
        except Exception:                        # 异常处理
            return ""                            # 返回空串


# ---------------------------- 计时管理器 ----------------------------
class TimerManager(QObject):                    # 计时管理器类，继承 QObject 以支持信号
    """管理倒计时和秒表，发射更新信号供主窗口显示"""  # 类文档：管理倒计时与秒表
    
    countdown_updated = pyqtSignal(int)         # 倒计时数值更新信号
    stopwatch_updated = pyqtSignal(int)         # 秒表数值更新信号
    countdown_finished = pyqtSignal()           # 倒计时结束信号
    countdown_state_changed = pyqtSignal(bool)  # 倒计时运行状态变化信号
    stopwatch_state_changed = pyqtSignal(bool)  # 秒表运行状态变化信号
    
    def __init__(self):                         # 构造函数
        super().__init__()                       # 调用父类构造
        self.countdown_seconds = DEFAULT_COUNTDOWN_MINUTES * 60  # 倒计时剩余秒数
        self.stopwatch_seconds = 0               # 秒表累计秒数
        self.countdown_running = False           # 倒计时是否运行中
        self.stopwatch_running = False           # 秒表是否运行中
        
        self.countdown_timer = QTimer()          # 倒计时定时器
        self.countdown_timer.timeout.connect(self._on_countdown_tick)  # 连接超时信号
        self.countdown_timer.setInterval(1000)   # 每 1000 毫秒触发一次
        
        self.stopwatch_timer = QTimer()          # 秒表定时器
        self.stopwatch_timer.timeout.connect(self._on_stopwatch_tick)  # 连接超时信号
        self.stopwatch_timer.setInterval(1000)   # 每 1000 毫秒触发一次
    
    def start_countdown(self, minutes=None):     # 启动倒计时
        if minutes is not None:                  # 指定了分钟数
            self.countdown_seconds = minutes * 60  # 重置剩余秒数
        if not self.countdown_running and self.countdown_seconds > 0:  # 未运行且有剩余时间
            self.countdown_running = True         # 标记为运行中
            self.countdown_timer.start()          # 启动定时器
            self.countdown_state_changed.emit(True)  # 发射状态变化信号
    
    def pause_countdown(self):                   # 暂停倒计时
        self.countdown_running = False            # 标记为停止
        self.countdown_timer.stop()               # 停止定时器
        self.countdown_state_changed.emit(False)  # 发射状态变化信号
    
    def reset_countdown(self, minutes=None):     # 重置倒计时
        self.pause_countdown()                    # 先暂停
        self.countdown_seconds = (minutes or DEFAULT_COUNTDOWN_MINUTES) * 60  # 重置秒数
        self.countdown_updated.emit(self.countdown_seconds)  # 发射更新信号
    
    def set_countdown_minutes(self, minutes):    # 设置倒计时分钟数
        self.countdown_seconds = minutes * 60    # 转为秒数
        if not self.countdown_running:            # 未运行时立即更新显示
            self.countdown_updated.emit(self.countdown_seconds)  # 发射更新信号
    
    def start_stopwatch(self):                   # 启动秒表
        if not self.stopwatch_running:            # 未运行时
            self.stopwatch_running = True         # 标记为运行中
            self.stopwatch_timer.start()          # 启动定时器
            self.stopwatch_state_changed.emit(True)  # 发射状态变化信号
    
    def pause_stopwatch(self):                   # 暂停秒表
        self.stopwatch_running = False            # 标记为停止
        self.stopwatch_timer.stop()               # 停止定时器
        self.stopwatch_state_changed.emit(False)  # 发射状态变化信号
    
    def reset_stopwatch(self):                   # 重置秒表
        self.pause_stopwatch()                    # 先暂停
        self.stopwatch_seconds = 0                # 清零
        self.stopwatch_updated.emit(0)            # 发射更新信号
    
    def _on_countdown_tick(self):                # 倒计时定时器回调
        if self.countdown_seconds > 0:            # 还有剩余时间
            self.countdown_seconds -= 1           # 秒数减 1
            self.countdown_updated.emit(self.countdown_seconds)  # 发射更新信号
            if self.countdown_seconds == 0:       # 倒计时归零
                self.countdown_finished.emit()    # 发射结束信号
                self.pause_countdown()            # 暂停
        else:                                    # 已无剩余
            self.pause_countdown()                # 暂停
    
    def _on_stopwatch_tick(self):                # 秒表定时器回调
        self.stopwatch_seconds += 1              # 秒数加 1
        self.stopwatch_updated.emit(self.stopwatch_seconds)  # 发射更新信号
    
    def get_countdown_time_str(self):            # 获取倒计时显示字符串
        if self.countdown_seconds < 0:           # 防御性处理负值
            self.countdown_seconds = 0            # 归零
        m = self.countdown_seconds // 60         # 计算分钟
        s = self.countdown_seconds % 60          # 计算秒
        return f"{m:02d}:{s:02d}"                # 返回 mm:ss 格式
    
    def get_stopwatch_time_str(self):            # 获取秒表显示字符串
        h = self.stopwatch_seconds // 3600       # 计算小时
        m = (self.stopwatch_seconds % 3600) // 60  # 计算分钟
        s = self.stopwatch_seconds % 60          # 计算秒
        return f"{h:02d}:{m:02d}:{s:02d}"        # 返回 hh:mm:ss 格式


# ---------------------------- 时钟主窗口（计时器独占模式） ----------------------------
class ClockWidget(QWidget):                     # 时钟主窗口类，继承 QWidget
    """透明背景时钟窗口，支持渐变流动、拖拽、计时独占显示"""  # 类文档
    
    appearance_changed = pyqtSignal()           # 外观变化信号
    
    def __init__(self, settings, timer_mgr):    # 构造函数，传入设置与计时管理器
        super().__init__()                       # 调用父类构造
        self.settings = settings                 # 保存设置管理器引用
        self.timer_mgr = timer_mgr               # 保存计时管理器引用
        
        # 窗口属性
        self.setWindowFlags(                     # 设置窗口标志
            Qt.WindowType.FramelessWindowHint |  # 无边框
            Qt.WindowType.Tool |                 # 工具窗口（不在任务栏显示）
            (Qt.WindowType.WindowStaysOnTopHint if self.settings.get("stay_on_top", DEFAULT_STAY_ON_TOP) else Qt.WindowType.Widget)  # 根据设置决定是否置顶
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 启用透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # 显示时不抢占焦点
        
        # 字体/颜色/透明度/主题
        self.font_family = self.settings.get("font_family", DEFAULT_FONT_FAMILY)  # 字体族
        self.base_font_size = self.settings.get("base_size", DEFAULT_BASE_SIZE)  # 主字号
        self.font_opacity = self.settings.get("font_opacity", DEFAULT_FONT_OPACITY)  # 不透明度
        self.custom_color = self.settings.get("custom_color", DEFAULT_COLOR)  # 自定义颜色
        self.theme_name = self.settings.get("theme", DEFAULT_THEME)  # 主题名
        
        # 显示选项
        self.show_date = self.settings.get("show_date", DEFAULT_SHOW_DATE)  # 是否显示日期
        self.show_week = self.settings.get("show_week", DEFAULT_SHOW_WEEK)  # 是否显示星期
        self.show_seconds = self.settings.get("show_seconds", DEFAULT_SHOW_SECONDS)  # 是否显示秒
        self.show_lunar = self.settings.get("show_lunar", DEFAULT_SHOW_LUNAR)  # 是否显示农历
        self.show_lunar_year = self.settings.get("show_lunar_year", DEFAULT_SHOW_LUNAR_YEAR)  # 是否显示农历年
        self.show_ganzhi = self.settings.get("show_ganzhi", DEFAULT_SHOW_GANZHI)  # 是否显示天干地支
        self.show_zodiac = self.settings.get("show_zodiac", DEFAULT_SHOW_ZODIAC)  # 是否显示属相
        self.date_week_same_line = self.settings.get("date_week_same_line", DEFAULT_DATE_WEEK_SAME_LINE)  # 日期与星期是否并排同行
        
        # 位置固定
        self.is_fixed = self.settings.get("fixed_pos", DEFAULT_FIXED_POS)  # 是否固定位置
        self.drag_position = None                # 拖拽偏移量
        
        # 渐变流动
        self.gradient_offset = 0                 # 渐变流动偏移量
        self.animation_timer = QTimer()          # 渐变动画定时器
        self.animation_timer.timeout.connect(self._update_gradient)  # 连接超时信号
        self.animation_timer.setInterval(50)     # 每 50 毫秒更新一次
        if self.theme_name != "单色":             # 非单色主题时启动动画
            self.animation_timer.start()
        
        # 时钟更新定时器
        self.clock_timer = QTimer()              # 时钟刷新定时器
        self.clock_timer.timeout.connect(self.update)  # 触发重绘
        self.clock_timer.setInterval(1000 if not self.show_seconds else 100)  # 显示秒时 100ms 刷新，否则 1s
        self.clock_timer.start()                 # 启动定时器
        
        # 缓存
        self._cached_fonts = {}                  # 字体缓存字典
        self._cached_metrics = {}                # 字体度量缓存字典
        self._cached_gradient = None             # 渐变缓存
        self._cached_size = None                 # 缓存对应的窗口尺寸
        
        # 初始化位置
        self._load_position()                    # 加载上次保存的位置
        
        # 连接计时器信号
        self.timer_mgr.countdown_updated.connect(self._on_timer_changed)  # 倒计时更新
        self.timer_mgr.stopwatch_updated.connect(self._on_timer_changed)  # 秒表更新
        self.timer_mgr.countdown_finished.connect(self._on_timer_changed)  # 倒计时结束
        self.timer_mgr.countdown_state_changed.connect(self._on_timer_changed)  # 倒计时状态变化
        self.timer_mgr.stopwatch_state_changed.connect(self._on_timer_changed)  # 秒表状态变化
        
        self.update_geometry()                   # 计算并设置窗口尺寸
    
    # -------------------- 计时器独占模式判断 --------------------
    def _is_timer_active(self):                  # 判断是否处于计时独占模式
        countdown_active = (                     # 倒计时激活条件
            self.timer_mgr.countdown_running or  # 正在运行
            self.timer_mgr.countdown_seconds != DEFAULT_COUNTDOWN_MINUTES * 60  # 已被改动
        )
        stopwatch_active = (                     # 秒表激活条件
            self.timer_mgr.stopwatch_running or  # 正在运行
            self.timer_mgr.stopwatch_seconds > 0  # 有累计时间
        )
        return countdown_active or stopwatch_active  # 任一激活即独占显示
    
    def _on_timer_changed(self, *args):          # 计时器变化回调
        self.update_geometry()                   # 重新计算尺寸
        self.update()                            # 触发重绘
    
    # -------------------- 几何尺寸自适应 --------------------
    def _get_display_lines(self):                # 构建要绘制的行列表（统一供几何与绘制使用）
        """返回 [(text, is_large), ...]。
        普通时钟模式行顺序：
          1) 时间（大字体）
          2) 日期/星期：若 date_week_same_line 则合并一行，否则日期、星期各占一行
          3) 农历（小字体）
        计时器独占模式返回单行计时文本。
        """
        if self._is_timer_active():              # 计时器独占模式
            return [(self._get_timer_text(), True)]  # 单行大字体
        lines = []                               # 行列表
        lines.append((self._get_time_text(), True))  # 第一行：时间（大字体）
        if self.date_week_same_line:             # 日期与星期并排同行
            if self.show_date or self.show_week:  # 任一启用
                lines.append((self._get_date_week_text(), False))  # 合并为一行
        else:                                   # 分行模式
            if self.show_date:                   # 日期单独一行
                lines.append((self._get_date_text(), False))
            if self.show_week:                   # 星期单独一行
                lines.append((self._get_week_text(), False))
        if self.show_lunar:                      # 农历一行
            lunar_text = self._get_lunar_text()
            if lunar_text:                       # 非空才加入
                lines.append((lunar_text, False))
        return lines                             # 返回行列表

    def update_geometry(self):                   # 根据内容自适应窗口尺寸
        lines = self._get_display_lines()        # 获取行列表
        if not lines:                            # 无内容
            self.setFixedSize(0, 0)
            return
        fm_time = self._get_font_metrics(self.base_font_size)  # 大字体度量
        fm_small = self._get_font_metrics(int(self.base_font_size * 0.45))  # 小字体度量

        # ★★★ 强迫症治愈级边距：0.8倍字体大小 + 最小40像素，任何字符永不裁剪 ★★★
        time_margin = max(int(self.base_font_size * 0.8), 40)  # 时间文本边距
        small_margin = int(self.base_font_size * 0.4)  # 小字体行边距余量

        # 计算每行宽度，取最大值
        max_width = 0                           # 最大宽度
        total_height = 4                        # 顶部起始 y=4
        for text, is_large in lines:            # 遍历每行
            fm = fm_time if is_large else fm_small  # 选择字体度量
            adv = fm.horizontalAdvance(text)    # 文本前进宽度
            margin = time_margin if is_large else small_margin  # 选择边距
            w = adv + margin                    # 行宽度
            if w > max_width:                    # 更新最大宽度
                max_width = w
            total_height += fm.height() + 2    # 累加行高（含行间距 2）
        total_height += 4                       # 底部留白
        self.setFixedSize(int(max_width) + 20, int(total_height))  # 设置固定尺寸（加左右边距）
    
    # -------------------- 字体缓存 --------------------
    def _get_font(self, size):                   # 获取字体（带缓存）
        key = (self.font_family, size)           # 缓存键
        if key not in self._cached_fonts:        # 未缓存
            font = QFont(self.font_family, size)  # 创建字体
            self._cached_fonts[key] = font       # 存入缓存
        return self._cached_fonts[key]           # 返回缓存字体
    
    def _get_font_metrics(self, size):           # 获取字体度量（带缓存）
        key = (self.font_family, size)           # 缓存键
        if key not in self._cached_metrics:      # 未缓存
            font = self._get_font(size)          # 获取字体
            metrics = QFontMetrics(font)         # 创建字体度量
            self._cached_metrics[key] = metrics  # 存入缓存
        return self._cached_metrics[key]         # 返回缓存的度量
    
    # -------------------- 文本生成 --------------------
    def _get_time_text(self):                    # 生成时间显示文本
        t = QTime.currentTime()                  # 获取当前时间
        if self.show_seconds:                    # 显示秒
            return t.toString("hh:mm:ss")        # 时:分:秒
        else:                                    # 不显示秒
            return t.toString("hh:mm")           # 时:分
    
    def _get_date_text(self):                    # 生成公历日期文本
        return QDate.currentDate().toString("yyyy-MM-dd")  # 返回 yyyy-MM-dd 格式

    def _get_week_text(self):                    # 生成星期文本
        cn_week = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]  # 中文星期
        return cn_week[QDate.currentDate().dayOfWeek() - 1]  # dayOfWeek 1=周一，需减 1

    def _get_date_week_text(self):               # 生成"日期 + 星期"合并文本（同一行）
        # 仅当日期或星期任一启用时返回合并文本，中间用 4 个空格间隔对齐美观
        parts = []                               # 文本片段列表
        if self.show_date:                       # 显示日期
            parts.append(self._get_date_text())  # 添加日期
        if self.show_week:                       # 显示星期
            parts.append(self._get_week_text())  # 添加星期
        return "    ".join(parts)                # 用 4 个空格连接，返回合并字符串

    def _get_lunar_text(self):                   # 生成农历文本（按显示选项组合）
        d = QDate.currentDate()                  # 当前日期
        # 传入是否显示农历年/干支/属相，format_lunar 内部处理括号规则
        return LunarCalendar.format_lunar(
            d.year(), d.month(), d.day(),
            show_year=self.show_lunar_year,
            show_ganzhi=self.show_ganzhi,
            show_zodiac=self.show_zodiac
        )  # 调用农历格式化
    
    def _get_timer_text(self):                   # 生成计时器文本
        if self._is_timer_active():              # 计时器激活
            if self.timer_mgr.countdown_seconds != DEFAULT_COUNTDOWN_MINUTES * 60 or self.timer_mgr.countdown_running:  # 倒计时优先
                return f"⏳ {self.timer_mgr.get_countdown_time_str()}"  # 倒计时文本
            else:                                # 否则显示秒表
                return f"⏱️ {self.timer_mgr.get_stopwatch_time_str()}"  # 秒表文本
        return ""                                # 未激活返回空串
    
    # -------------------- 绘制事件 --------------------
    def paintEvent(self, event):                 # 重绘事件回调
        painter = QPainter(self)                 # 创建画笔
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 启用抗锯齿
        painter.setOpacity(self.font_opacity / 255.0)  # 设置整体不透明度
        
        # 设置画笔 - 防崩溃保护
        try:                                     # 异常保护
            if self.theme_name == "单色":         # 单色主题
                painter.setPen(self.custom_color)  # 直接用自定义颜色
            else:                                # 渐变主题
                if self._cached_gradient is None or self._cached_size != self.size():  # 需重建渐变
                    self._cached_gradient = QLinearGradient(0, 0, self.width(), 0)  # 横向线性渐变
                    stops = ThemeManager.get_gradient_stops(self.theme_name)  # 获取停止点
                    for pos, color in stops:      # 遍历停止点
                        self._cached_gradient.setColorAt(pos, color)  # 设置颜色
                    if stops and len(stops) > 1:  # 多停止点
                        self._cached_gradient.setColorAt(1.0, stops[0][1])  # 末尾颜色与起始相同，循环无接缝
                    self._cached_gradient.setSpread(QGradient.Spread.RepeatSpread)  # 重复平铺
                    self._cached_size = self.size()  # 记录缓存尺寸
                
                if self.animation_timer.isActive():  # 动画运行中
                    self._cached_gradient.setStart(self.gradient_offset, 0)  # 更新起点
                    self._cached_gradient.setFinalStop(self.gradient_offset + self.width(), 0)  # 更新终点
                painter.setPen(QPen(QBrush(self._cached_gradient), 0))  # 用渐变画刷设置画笔
        except Exception:                        # 异常处理
            # 任何渐变异常，回退到单色（避免崩溃）
            painter.setPen(self.custom_color)    # 回退单色
        
        y = 4                                    # 起始 y 坐标
        lines = self._get_display_lines()         # 获取统一行列表

        for text, is_large in lines:             # 遍历每行绘制
            size = self.base_font_size if is_large else int(self.base_font_size * 0.45)  # 选择字号
            painter.setFont(self._get_font(size))  # 设置字体
            fm = self._get_font_metrics(size)    # 字体度量
            # 在整窗口宽度矩形内居中绘制，确保不超出边界
            painter.drawText(QRect(0, y, self.width(), fm.height()),
                             Qt.AlignmentFlag.AlignCenter, text)
            y += fm.height() + 2                  # y 下移一行
    
    def _update_gradient(self):                  # 渐变动画定时器回调
        if self.width() > 0:                     # 窗口宽度有效
            self.gradient_offset += 2            # 偏移量加 2
            self.gradient_offset %= self.width()  # 取模循环
            self.update()                        # 触发重绘
    
    # -------------------- 鼠标拖拽 --------------------
    def mousePressEvent(self, event):            # 鼠标按下事件
        if event.button() == Qt.MouseButton.LeftButton and not self.is_fixed:  # 左键且未固定
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()  # 记录拖拽偏移
            event.accept()                       # 接受事件
    
    def mouseMoveEvent(self, event):             # 鼠标移动事件
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_fixed and self.drag_position is not None:  # 左键拖拽中
            self.move(event.globalPosition().toPoint() - self.drag_position)  # 移动窗口
            event.accept()                       # 接受事件
    
    def mouseReleaseEvent(self, event):          # 鼠标释放事件
        self.drag_position = None                # 清除拖拽偏移
        self._save_position()                    # 保存位置
    
    # -------------------- 位置持久化 --------------------
    def _save_position(self):                    # 保存当前位置到设置
        pos = self.pos()                         # 获取当前位置
        self.settings.set("pos_x", pos.x())      # 保存 x
        self.settings.set("pos_y", pos.y())      # 保存 y
    
    def _load_position(self):                    # 从设置加载位置
        x = self.settings.get("pos_x", 100)      # 读取 x，默认 100
        y = self.settings.get("pos_y", 100)      # 读取 y，默认 100
        self.move(x, y)                          # 移动窗口
    
    # -------------------- 公共设置接口 --------------------
    def set_font_family(self, family):           # 设置字体族
        self.font_family = family                # 更新字体族
        self._cached_fonts.clear()               # 清除字体缓存
        self._cached_metrics.clear()             # 清除度量缓存
        self.update_geometry()                   # 重新计算尺寸
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def set_base_font_size(self, size):          # 设置主字号
        size = max(20, min(250, size))           # 限制在 20-250
        self.base_font_size = size               # 更新字号
        self._cached_fonts.clear()               # 清除字体缓存
        self._cached_metrics.clear()             # 清除度量缓存
        self.update_geometry()                   # 重新计算尺寸
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def set_font_opacity(self, opacity):         # 设置不透明度
        self.font_opacity = max(0, min(255, opacity))  # 限制 0-255
        self.update()                            # 触发重绘
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def set_custom_color(self, color):           # 设置自定义颜色
        self.custom_color = color                # 更新颜色
        if self.theme_name == "单色":             # 单色主题立即重绘
            self.update()
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def set_theme(self, theme_name):             # 设置主题
        """切换主题，带崩溃保护"""                  # 方法文档
        try:                                    # 异常保护
            self.theme_name = theme_name         # 更新主题名
            
            self.animation_timer.stop()          # 停止动画
            self.gradient_offset = 0             # 重置偏移
            
            self._cached_gradient = None         # 清除渐变缓存
            self._cached_size = None             # 清除尺寸缓存
            
            if theme_name != "单色":              # 非单色主题
                QTimer.singleShot(50, self._safe_start_animation)  # 延迟 50ms 安全启动动画
            
            self.update()                        # 触发重绘
            self.appearance_changed.emit()       # 发射外观变化信号
        except Exception as e:                   # 异常处理
            print(f"切换主题异常: {e}")            # 打印异常
            traceback.print_exc()                # 打印堆栈
            self.theme_name = "单色"              # 回退到单色
            self._cached_gradient = None         # 清除缓存
            self.animation_timer.stop()          # 停止动画
            self.update()                        # 触发重绘
    
    def _safe_start_animation(self):             # 安全启动渐变动画
        try:                                    # 异常保护
            if not self.animation_timer.isActive():  # 未运行
                self.animation_timer.start()     # 启动
        except:                                 # 异常忽略
            pass
    
    def set_show_date(self, show):               # 设置是否显示日期
        self.show_date = show                    # 更新标志
        self.update_geometry()                   # 重新计算尺寸
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def set_show_week(self, show):               # 设置是否显示星期
        self.show_week = show                    # 更新标志
        self.update_geometry()                   # 重新计算尺寸
        self.appearance_changed.emit()           # 发射外观变化信号

    def set_show_lunar(self, show):              # 设置是否显示农历
        self.show_lunar = show                   # 更新标志
        self.update_geometry()                   # 重新计算尺寸
        self.appearance_changed.emit()           # 发射外观变化信号

    def set_show_lunar_year(self, show):          # 设置是否显示农历年
        self.show_lunar_year = show               # 更新标志
        self.update_geometry()                   # 重新计算尺寸（农历行宽度可能变化）
        self.appearance_changed.emit()           # 发射外观变化信号

    def set_show_ganzhi(self, show):              # 设置是否显示天干地支
        self.show_ganzhi = show                   # 更新标志
        self.update_geometry()                   # 重新计算尺寸（农历行宽度可能变化）
        self.appearance_changed.emit()           # 发射外观变化信号

    def set_show_zodiac(self, show):              # 设置是否显示属相
        self.show_zodiac = show                   # 更新标志
        self.update_geometry()                   # 重新计算尺寸（农历行宽度可能变化）
        self.appearance_changed.emit()           # 发射外观变化信号

    def set_date_week_same_line(self, same_line):  # 设置日期与星期是否并排同行
        self.date_week_same_line = same_line      # 更新标志
        self.update_geometry()                   # 重新计算尺寸（行数变化）
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def set_show_seconds(self, show):            # 设置是否显示秒
        self.show_seconds = show                 # 更新标志
        self.clock_timer.setInterval(1000 if not show else 100)  # 调整刷新间隔
        self.update()                            # 触发重绘
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def set_fixed_pos(self, fixed):              # 设置是否固定位置
        self.is_fixed = fixed                    # 更新标志
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def set_stay_on_top(self, on_top):           # 设置是否置顶
        flags = self.windowFlags()               # 获取当前窗口标志
        if on_top:                               # 置顶
            flags |= Qt.WindowType.WindowStaysOnTopHint  # 添加置顶标志
        else:                                    # 不置顶
            flags &= ~Qt.WindowType.WindowStaysOnTopHint  # 移除置顶标志
        self.setWindowFlags(flags)               # 设置新标志
        self.show()                              # 重新显示（setWindowFlags 后需重新 show）
        self.appearance_changed.emit()           # 发射外观变化信号
    
    def closeEvent(self, event):                 # 关闭事件回调
        self._save_position()                    # 保存位置
        event.ignore()                           # 忽略关闭事件
        self.hide()                              # 仅隐藏，不真正关闭


# ---------------------------- 设置对话框 ----------------------------
class SettingsDialog(QDialog):                  # 设置对话框类，继承 QDialog
    """外观、倒计时、启动设置对话框，实时预览"""    # 类文档
    
    font_family_changed = pyqtSignal(str)       # 字体族变化信号
    base_size_changed = pyqtSignal(int)         # 字号变化信号
    font_opacity_changed = pyqtSignal(int)      # 不透明度变化信号
    custom_color_changed = pyqtSignal(QColor)   # 颜色变化信号
    theme_changed = pyqtSignal(str)             # 主题变化信号
    show_date_changed = pyqtSignal(bool)        # 显示日期变化信号
    show_week_changed = pyqtSignal(bool)        # 显示星期变化信号
    show_seconds_changed = pyqtSignal(bool)     # 显示秒变化信号
    show_lunar_changed = pyqtSignal(bool)       # 显示农历变化信号
    show_lunar_year_changed = pyqtSignal(bool)   # 显示农历年变化信号
    show_ganzhi_changed = pyqtSignal(bool)       # 显示天干地支变化信号
    show_zodiac_changed = pyqtSignal(bool)       # 显示属相变化信号
    date_week_same_line_changed = pyqtSignal(bool)  # 日期星期并排变化信号
    fixed_pos_changed = pyqtSignal(bool)        # 固定位置变化信号
    stay_on_top_changed = pyqtSignal(bool)      # 置顶变化信号
    countdown_minutes_changed = pyqtSignal(int) # 倒计时分钟数变化信号
    
    def __init__(self, settings, clock, timer_mgr, parent=None):  # 构造函数
        super().__init__(parent)                 # 调用父类构造
        self.settings = settings                 # 保存设置管理器
        self.clock = clock                       # 保存时钟窗口引用
        self.timer_mgr = timer_mgr               # 保存计时管理器
        
        self.setWindowTitle("时钟设置")           # 对话框标题
        self.setMinimumSize(500, 400)            # 最小尺寸
        
        self._size_timer = QTimer()              # 字号滑块防抖定时器
        self._size_timer.setSingleShot(True)     # 单次触发
        self._size_timer.timeout.connect(self._on_size_slider_released)  # 连接回调
        self._opacity_timer = QTimer()           # 透明度滑块防抖定时器
        self._opacity_timer.setSingleShot(True)  # 单次触发
        self._opacity_timer.timeout.connect(self._on_opacity_slider_released)  # 连接回调
        
        self._init_ui()                          # 初始化界面
        self._load_settings()                    # 加载当前设置到控件
        self._connect_signals()                  # 连接控件信号
    
    def _init_ui(self):                          # 初始化界面
        layout = QVBoxLayout()                   # 主垂直布局
        self.tab_widget = QTabWidget()           # 选项卡控件
        
        # ---------- 外观选项卡 ----------
        appearance_tab = QWidget()               # 外观选项卡页
        tab_layout = QVBoxLayout()               # 选项卡内布局
        
        font_layout = QHBoxLayout()              # 字体行水平布局
        font_layout.addWidget(QLabel("字体:"))   # 字体标签
        self.font_combo = QComboBox()            # 字体下拉框
        self.font_combo.setEditable(True)        # 可编辑
        self.font_combo.addItems(QFontDatabase.families())  # 填充系统字体
        font_layout.addWidget(self.font_combo)   # 添加下拉框
        font_layout.addStretch()                 # 添加伸展
        tab_layout.addLayout(font_layout)        # 添加字体行
        
        size_layout = QHBoxLayout()              # 字号行
        size_layout.addWidget(QLabel("字体大小:"))  # 字号标签
        self.size_slider = QSlider(Qt.Orientation.Horizontal)  # 字号滑块
        self.size_slider.setRange(20, 250)       # 字号范围
        self.size_slider.setTickInterval(10)     # 刻度间隔
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)  # 刻度在下方
        self.size_label = QLabel("80")           # 字号显示标签
        size_layout.addWidget(self.size_slider)  # 添加滑块
        size_layout.addWidget(self.size_label)   # 添加标签
        tab_layout.addLayout(size_layout)        # 添加字号行
        
        opacity_layout = QHBoxLayout()           # 透明度行
        opacity_layout.addWidget(QLabel("透明度:"))  # 透明度标签
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)  # 透明度滑块
        self.opacity_slider.setRange(0, 255)     # 范围 0-255
        self.opacity_slider.setTickInterval(51)  # 刻度间隔
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)  # 刻度在下方
        self.opacity_label = QLabel("255")       # 透明度显示标签
        opacity_layout.addWidget(self.opacity_slider)  # 添加滑块
        opacity_layout.addWidget(self.opacity_label)  # 添加标签
        tab_layout.addLayout(opacity_layout)     # 添加透明度行
        
        color_layout = QHBoxLayout()             # 颜色行
        color_layout.addWidget(QLabel("字体颜色:"))  # 颜色标签
        self.color_btn = QPushButton("选择颜色")  # 颜色按钮
        self.color_btn.clicked.connect(self._choose_color)  # 连接点击信号
        self.color_preview = QLabel("   ")       # 颜色预览标签
        self.color_preview.setStyleSheet("background-color: white; border:1px solid black;")  # 预览样式
        self.color_preview.setFixedSize(30, 20)  # 预览固定尺寸
        color_layout.addWidget(self.color_btn)   # 添加按钮
        color_layout.addWidget(self.color_preview)  # 添加预览
        color_layout.addStretch()                # 伸展
        tab_layout.addLayout(color_layout)       # 添加颜色行
        
        theme_layout = QHBoxLayout()             # 主题行
        theme_layout.addWidget(QLabel("渐变主题:"))  # 主题标签
        self.theme_combo = QComboBox()           # 主题下拉框
        self.theme_combo.addItems(ThemeManager.THEMES.keys())  # 填充主题名
        theme_layout.addWidget(self.theme_combo)  # 添加下拉框
        theme_layout.addStretch()                # 伸展
        tab_layout.addLayout(theme_layout)       # 添加主题行
        
        display_group = QGroupBox("显示内容")    # 显示内容分组
        display_layout = QVBoxLayout()           # 分组内布局
        self.show_date_cb = QCheckBox("显示日期")  # 日期复选框
        self.show_week_cb = QCheckBox("显示星期")  # 星期复选框
        self.show_seconds_cb = QCheckBox("显示秒钟")  # 秒钟复选框
        self.show_lunar_cb = QCheckBox("显示农历")  # 农历复选框
        self.show_lunar_year_cb = QCheckBox("显示农历年（二〇二六年）")  # 农历年复选框
        self.show_ganzhi_cb = QCheckBox("显示天干地支（丙午）")  # 天干地支复选框
        self.show_zodiac_cb = QCheckBox("显示属相（马）")  # 属相复选框
        self.date_week_same_line_cb = QCheckBox("日期与星期并排同一行")  # 日期星期并排复选框
        display_layout.addWidget(self.show_date_cb)  # 添加日期
        display_layout.addWidget(self.show_week_cb)  # 添加星期
        display_layout.addWidget(self.show_seconds_cb)  # 添加秒钟
        display_layout.addWidget(self.show_lunar_cb)  # 添加农历
        display_layout.addWidget(self.show_lunar_year_cb)  # 添加农历年
        display_layout.addWidget(self.show_ganzhi_cb)  # 添加天干地支
        display_layout.addWidget(self.show_zodiac_cb)  # 添加属相
        display_layout.addWidget(self.date_week_same_line_cb)  # 添加日期星期并排
        display_group.setLayout(display_layout)  # 设置分组布局
        tab_layout.addWidget(display_group)      # 添加分组
        
        tab_layout.addStretch()                  # 伸展
        appearance_tab.setLayout(tab_layout)     # 设置选项卡布局
        self.tab_widget.addTab(appearance_tab, "外观")  # 添加外观选项卡
        
        # ---------- 倒计时设置选项卡 ----------
        countdown_tab = QWidget()                # 倒计时选项卡页
        cd_layout = QVBoxLayout()                # 倒计时布局
        cd_layout.addWidget(QLabel("默认倒计时时间:"))  # 标签
        self.countdown_spin = QSpinBox()         # 倒计时数值框
        self.countdown_spin.setRange(1, 999)     # 范围 1-999
        self.countdown_spin.setSuffix(" 分钟")   # 后缀
        cd_layout.addWidget(self.countdown_spin)  # 添加数值框
        cd_layout.addStretch()                   # 伸展
        countdown_tab.setLayout(cd_layout)       # 设置布局
        self.tab_widget.addTab(countdown_tab, "倒计时")  # 添加倒计时选项卡
        
        # ---------- 启动设置选项卡 ----------
        startup_tab = QWidget()                  # 启动选项卡页
        st_layout = QVBoxLayout()                # 启动布局
        self.startup_cb = QCheckBox("开机自启动")  # 开机自启动复选框
        self.fixed_pos_cb = QCheckBox("固定时钟")  # 固定时钟复选框
        self.stay_on_top_cb = QCheckBox("时钟置顶")  # 时钟置顶复选框
        st_layout.addWidget(self.startup_cb)     # 添加开机自启动
        st_layout.addWidget(self.fixed_pos_cb)   # 添加固定时钟
        st_layout.addWidget(self.stay_on_top_cb)  # 添加时钟置顶
        st_layout.addStretch()                   # 伸展
        startup_tab.setLayout(st_layout)         # 设置布局
        self.tab_widget.addTab(startup_tab, "启动")  # 添加启动选项卡
        
        layout.addWidget(self.tab_widget)        # 添加选项卡控件
        
        btn_layout = QHBoxLayout()               # 按钮行
        self.ok_btn = QPushButton("确定")         # 确定按钮
        self.ok_btn.clicked.connect(self.accept)  # 连接接受
        self.cancel_btn = QPushButton("取消")     # 取消按钮
        self.cancel_btn.clicked.connect(self.reject)  # 连接拒绝
        btn_layout.addStretch()                  # 伸展
        btn_layout.addWidget(self.ok_btn)        # 添加确定
        btn_layout.addWidget(self.cancel_btn)    # 添加取消
        layout.addLayout(btn_layout)             # 添加按钮行
        
        self.setLayout(layout)                   # 设置主布局
    
    def _load_settings(self):                    # 加载设置到控件
        self.font_combo.setCurrentText(self.clock.font_family)  # 字体
        self.size_slider.setValue(self.clock.base_font_size)  # 字号
        self.size_label.setText(str(self.clock.base_font_size))  # 字号标签
        self.opacity_slider.setValue(self.clock.font_opacity)  # 透明度
        self.opacity_label.setText(str(self.clock.font_opacity))  # 透明度标签
        self.color_preview.setStyleSheet(f"background-color: {self.clock.custom_color.name()}; border:1px solid black;")  # 颜色预览
        self.theme_combo.setCurrentText(self.clock.theme_name)  # 主题
        self.show_date_cb.setChecked(self.clock.show_date)  # 日期
        self.show_week_cb.setChecked(self.clock.show_week)  # 星期
        self.show_seconds_cb.setChecked(self.clock.show_seconds)  # 秒钟
        self.show_lunar_cb.setChecked(self.clock.show_lunar)  # 农历
        self.show_lunar_year_cb.setChecked(self.clock.show_lunar_year)  # 农历年
        self.show_ganzhi_cb.setChecked(self.clock.show_ganzhi)  # 天干地支
        self.show_zodiac_cb.setChecked(self.clock.show_zodiac)  # 属相
        self.date_week_same_line_cb.setChecked(self.clock.date_week_same_line)  # 日期星期并排
        self.countdown_spin.setValue(self.settings.get("countdown_minutes", DEFAULT_COUNTDOWN_MINUTES))  # 倒计时分钟
        self.startup_cb.setChecked(self.settings.get("startup_with_os", DEFAULT_STARTUP_WITH_OS))  # 开机自启动
        self.fixed_pos_cb.setChecked(self.clock.is_fixed)  # 固定位置
        self.stay_on_top_cb.setChecked(self.settings.get("stay_on_top", DEFAULT_STAY_ON_TOP))  # 置顶
    
    def _connect_signals(self):                  # 连接控件信号
        self.font_combo.currentTextChanged.connect(self.font_family_changed)  # 字体变化
        self.font_combo.currentTextChanged.connect(lambda f: self.settings.set("font_family", f))  # 同时保存
        
        self.size_slider.valueChanged.connect(lambda v: self.size_label.setText(str(v)))  # 字号标签同步
        self.size_slider.valueChanged.connect(lambda: self._size_timer.start(50))  # 防抖触发
        
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(str(v)))  # 透明度标签同步
        self.opacity_slider.valueChanged.connect(lambda: self._opacity_timer.start(50))  # 防抖触发
        
        self.theme_combo.currentTextChanged.connect(self.theme_changed)  # 主题变化
        self.theme_combo.currentTextChanged.connect(lambda t: self.settings.set("theme", t))  # 同时保存
        
        self.show_date_cb.toggled.connect(self.show_date_changed)  # 日期变化
        self.show_date_cb.toggled.connect(lambda b: self.settings.set("show_date", b))  # 同时保存
        self.show_week_cb.toggled.connect(self.show_week_changed)  # 星期变化
        self.show_week_cb.toggled.connect(lambda b: self.settings.set("show_week", b))  # 同时保存
        self.show_seconds_cb.toggled.connect(self.show_seconds_changed)  # 秒钟变化
        self.show_seconds_cb.toggled.connect(lambda b: self.settings.set("show_seconds", b))  # 同时保存
        self.show_lunar_cb.toggled.connect(self.show_lunar_changed)  # 农历变化
        self.show_lunar_cb.toggled.connect(lambda b: self.settings.set("show_lunar", b))  # 同时保存
        self.show_lunar_year_cb.toggled.connect(self.show_lunar_year_changed)  # 农历年变化
        self.show_lunar_year_cb.toggled.connect(lambda b: self.settings.set("show_lunar_year", b))  # 同时保存
        self.show_ganzhi_cb.toggled.connect(self.show_ganzhi_changed)  # 天干地支变化
        self.show_ganzhi_cb.toggled.connect(lambda b: self.settings.set("show_ganzhi", b))  # 同时保存
        self.show_zodiac_cb.toggled.connect(self.show_zodiac_changed)  # 属相变化
        self.show_zodiac_cb.toggled.connect(lambda b: self.settings.set("show_zodiac", b))  # 同时保存
        self.date_week_same_line_cb.toggled.connect(self.date_week_same_line_changed)  # 日期星期并排变化
        self.date_week_same_line_cb.toggled.connect(lambda b: self.settings.set("date_week_same_line", b))  # 同时保存
        
        self.countdown_spin.valueChanged.connect(lambda v: self.settings.set("countdown_minutes", v))  # 倒计时保存
        self.countdown_spin.valueChanged.connect(self.countdown_minutes_changed)  # 倒计时变化
        
        self.startup_cb.toggled.connect(lambda b: self.settings.set("startup_with_os", b))  # 开机自启动保存
        self.fixed_pos_cb.toggled.connect(self.fixed_pos_changed)  # 固定位置变化
        self.fixed_pos_cb.toggled.connect(lambda b: self.settings.set("fixed_pos", b))  # 同时保存
        self.stay_on_top_cb.toggled.connect(self.stay_on_top_changed)  # 置顶变化
        self.stay_on_top_cb.toggled.connect(lambda b: self.settings.set("stay_on_top", b))  # 同时保存
    
    def _on_size_slider_released(self):          # 字号滑块释放（防抖）回调
        val = self.size_slider.value()           # 获取滑块值
        self.base_size_changed.emit(val)         # 发射信号
        self.settings.set("base_size", val)      # 保存设置
    
    def _on_opacity_slider_released(self):       # 透明度滑块释放回调
        val = self.opacity_slider.value()        # 获取滑块值
        self.font_opacity_changed.emit(val)      # 发射信号
        self.settings.set("font_opacity", val)   # 保存设置
    
    def _choose_color(self):                     # 选择颜色按钮回调
        color = QColorDialog.getColor(self.clock.custom_color, self)  # 弹出颜色对话框
        if color.isValid():                      # 颜色有效
            self.color_preview.setStyleSheet(f"background-color: {color.name()}; border:1px solid black;")  # 更新预览
            self.custom_color_changed.emit(color)  # 发射信号
            self.settings.set("custom_color", color)  # 保存设置
    
    def accept(self):                            # 确定按钮回调
        self._on_size_slider_released()          # 提交字号
        self._on_opacity_slider_released()       # 提交透明度
        self.timer_mgr.set_countdown_minutes(self.countdown_spin.value())  # 设置倒计时分钟
        super().accept()                         # 调用父类 accept
    
    def reject(self):                            # 取消按钮回调
        super().reject()                         # 调用父类 reject


# ---------------------------- 托盘图标 ----------------------------
class TrayIcon(QSystemTrayIcon):                # 系统托盘图标类
    """系统托盘，提供右键菜单和双击响应"""          # 类文档
    
    show_hide_clock = pyqtSignal()              # 显示/隐藏时钟信号
    quit_app = pyqtSignal()                     # 退出应用信号
    
    def __init__(self, parent=None):            # 构造函数
        super().__init__(parent)                 # 调用父类构造
        self.setIcon(self._create_icon())        # 设置图标
        self.setToolTip("桌面时钟")              # 设置提示文本
        
        self.menu = QMenu()                     # 右键菜单
        
        self.show_action = QAction("显示时钟", self)  # 显示时钟动作
        self.show_action.setCheckable(True)      # 可勾选
        self.show_action.setChecked(True)        # 默认勾选
        self.show_action.triggered.connect(self._on_show_clock)  # 连接触发信号
        
        self.countdown_action = QAction("开始倒计时", self)  # 倒计时动作
        self.stopwatch_action = QAction("开始计时", self)  # 秒表动作
        self.reset_countdown_action = QAction("重置倒计时", self)  # 重置倒计时
        self.reset_stopwatch_action = QAction("重置计时", self)  # 重置秒表
        
        self.settings_action = QAction("时钟设置", self)  # 设置动作
        self.quit_action = QAction("退出", self)  # 退出动作
        self.quit_action.triggered.connect(self.quit_app.emit)  # 连接退出信号
        
        self.menu.addAction(self.show_action)    # 添加显示时钟
        self.menu.addSeparator()                 # 分隔线
        self.menu.addAction(self.countdown_action)  # 添加倒计时
        self.menu.addAction(self.reset_countdown_action)  # 添加重置倒计时
        self.menu.addSeparator()                 # 分隔线
        self.menu.addAction(self.stopwatch_action)  # 添加秒表
        self.menu.addAction(self.reset_stopwatch_action)  # 添加重置秒表
        self.menu.addSeparator()                 # 分隔线
        self.menu.addAction(self.settings_action)  # 添加设置
        self.menu.addSeparator()                 # 分隔线
        self.menu.addAction(self.quit_action)    # 添加退出
        
        self.setContextMenu(self.menu)           # 设置右键菜单
        self.activated.connect(self._on_activated)  # 连接激活信号
    
    def _create_icon(self):                      # 创建托盘图标
        pixmap = QPixmap(64, 64)                 # 64x64 位图
        pixmap.fill(Qt.GlobalColor.transparent)  # 透明填充
        painter = QPainter(pixmap)               # 画笔
        painter.setPen(QPen(Qt.GlobalColor.white, 3))  # 白色画笔
        painter.setBrush(QBrush(Qt.GlobalColor.gray))  # 灰色画刷
        painter.drawEllipse(4, 4, 56, 56)        # 画圆形表盘
        painter.setPen(QPen(Qt.GlobalColor.white, 2))  # 细白色画笔
        painter.drawLine(32, 32, 32, 16)         # 画时针（向上）
        painter.drawLine(32, 32, 48, 32)         # 画分针（向右）
        painter.end()                            # 结束绘制
        return QIcon(pixmap)                     # 返回图标
    
    def _on_activated(self, reason):             # 托盘激活回调
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:  # 双击
            self.show_hide_clock.emit()          # 发射显示/隐藏信号
    
    def _on_show_clock(self, checked):           # 显示时钟菜单项回调
        self.show_hide_clock.emit()              # 发射信号
    
    def set_countdown_running(self, running):    # 设置倒计时菜单文本
        self.countdown_action.setText("暂停倒计时" if running else "开始倒计时")  # 根据状态切换文本
    
    def set_stopwatch_running(self, running):    # 设置秒表菜单文本
        self.stopwatch_action.setText("暂停计时" if running else "开始计时")  # 根据状态切换文本


# ---------------------------- 设置持久化（类型安全版） ----------------------------
class SettingsManager:                          # 设置管理器类
    """使用QSettings保存/加载配置，自动处理类型转换"""  # 类文档
    
    def __init__(self):                         # 构造函数
        self.qsettings = QSettings(ORG_NAME, APP_NAME)  # 创建 QSettings，按组织名+应用名存储
    
    def get(self, key, default=None):           # 读取设置，带类型转换
        value = self.qsettings.value(key, default)  # 读取原始值
        if default is not None:                 # 有默认值才进行类型转换
            if isinstance(default, bool):       # 布尔类型
                if isinstance(value, str):       # 字符串形式
                    return value.lower() == "true"  # 转布尔
                return bool(value) if value is not None else default  # 其他形式
            elif isinstance(default, int):       # 整型
                try:                            # 尝试转换
                    return int(value) if value is not None else default  # 转 int
                except:                         # 转换失败
                    return default              # 返回默认值
            elif isinstance(default, float):     # 浮点型
                try:                            # 尝试转换
                    return float(value) if value is not None else default  # 转 float
                except:                         # 转换失败
                    return default              # 返回默认值
            elif isinstance(default, str):       # 字符串型
                return str(value) if value is not None else default  # 转 str
            elif isinstance(default, QColor):    # 颜色型
                if isinstance(value, str):       # 字符串形式
                    return QColor(value)         # 构造 QColor
                elif isinstance(value, QColor):  # 已是 QColor
                    return value                # 直接返回
                return default                  # 其他返回默认
        return value                            # 无默认值直接返回
    
    def set(self, key, value):                  # 保存设置
        self.qsettings.setValue(key, value)     # 写入 QSettings
    
    def sync(self):                             # 同步到磁盘
        self.qsettings.sync()                   # 调用 sync


# ---------------------------- 单实例保护（PyQt6 纯标志位版） ----------------------------
class SingleInstance:                           # 单实例保护类
    """共享内存锁，确保只有一个实例运行（无 setData，纯 create/attach 判断）"""  # 类文档
    
    def __init__(self, key):                    # 构造函数
        self.key = key                          # 共享内存键名
        self.shared_mem = QSharedMemory(key)    # 创建共享内存对象
        self.is_running = False                 # 是否已有实例运行

    def try_lock(self):                         # 尝试获取锁
        if self.shared_mem.isAttached():        # 已附加
            self.shared_mem.detach()            # 先分离

        if self.shared_mem.create(1):           # 尝试创建 1 字节共享内存
            return True                         # 创建成功，获得锁

        if self.shared_mem.error() == QSharedMemory.SharedMemoryError.AlreadyExists:  # 已存在
            if self.shared_mem.attach():        # 尝试附加
                self.shared_mem.detach()        # 附加后立即分离
                self.is_running = True          # 标记已有实例
                return False                    # 获取锁失败
            else:                               # 附加失败
                self._force_clean()             # 强制清理
                return self.try_lock()          # 重试
        else:                                   # 其他错误
            return True                         # 视为获得锁

    def _force_clean(self):                     # 强制清理共享内存
        try:                                   # 异常保护
            if self.shared_mem.attach():        # 尝试附加
                self.shared_mem.detach()        # 分离
        except:                                # 异常忽略
            pass

    def release(self):                          # 释放锁
        if self.shared_mem.isAttached():        # 已附加
            self.shared_mem.detach()            # 分离


# ---------------------------- 开机自启动僵尸项清理 ----------------------------
def clean_dead_startup_entries():               # 清理失效的开机启动项
    """清理注册表中指向不存在 exe 的开机启动项（同名项）"""  # 函数文档
    if sys.platform != "win32":                 # 非 Windows 平台
        return                                  # 直接返回
    
    import os                                   # 导入 os 模块
    current_name = QCoreApplication.applicationName()  # 当前应用名
    
    reg_paths = [                               # 待检查的注册表路径列表
        "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run",  # 当前用户启动项
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",  # 所有用户启动项
        "HKEY_LOCAL_MACHINE\\SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Run"  # 32 位启动项
    ]
    
    for path in reg_paths:                      # 遍历每个注册表路径
        try:                                   # 异常保护
            settings = QSettings(path, QSettings.Format.NativeFormat)  # 打开注册表
            keys = settings.childKeys()         # 获取所有键
            for key in keys:                    # 遍历键
                if current_name.lower() in key.lower():  # 同名项
                    exe_path = settings.value(key)  # 读取路径
                    if exe_path and not os.path.exists(exe_path.replace('"', '')):  # 路径不存在
                        settings.remove(key)    # 删除该项
        except:                                # 异常忽略
            continue                            # 继续下一个


# ---------------------------- 全局异常捕获 ----------------------------
def _global_excepthook(exc_type, exc_value, exc_tb):  # 全局异常钩子
    """捕获未处理异常，写入日志而非静默崩溃"""      # 函数文档
    try:                                       # 异常保护
        log_dir = os.path.join(os.path.expanduser("~"), ".DesktopClock")  # 日志目录
        os.makedirs(log_dir, exist_ok=True)    # 创建目录
        log_path = os.path.join(log_dir, "error.log")  # 日志文件路径
        with open(log_path, "a", encoding="utf-8") as f:  # 追加打开
            f.write("=" * 60 + "\n")           # 写入分隔线
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)  # 写入堆栈
    except Exception:                          # 异常忽略
        pass
    traceback.print_exception(exc_type, exc_value, exc_tb)  # 同时打印到控制台


# ---------------------------- 主程序入口 ----------------------------
def main():                                      # 主程序入口函数
    sys.excepthook = _global_excepthook          # 安装全局异常钩子

    # 高 DPI 支持（PyQt6 默认启用，显式设置以防环境差异）
    try:                                         # 异常保护
        QApplication.setHighDpiScaleFactorRoundingPolicy(  # 设置高 DPI 缩放舍入策略
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough  # 透传策略，不进行舍入
        )
    except Exception:                            # 异常忽略
        pass

    app = QApplication(sys.argv)                 # 创建 QApplication
    app.setApplicationName(APP_NAME)             # 设置应用名
    app.setOrganizationName(ORG_NAME)            # 设置组织名
    app.setQuitOnLastWindowClosed(False)         # 关闭最后一个窗口不退出（托盘常驻）

    # 清理已失效的自身开机启动项
    clean_dead_startup_entries()                 # 调用清理函数
    
    # 单实例检查
    instance = SingleInstance(APP_KEY)           # 创建单实例对象
    if not instance.try_lock():                  # 获取锁失败
        for widget in app.topLevelWidgets():     # 遍历顶级窗口
            if isinstance(widget, ClockWidget):  # 找到已存在的时钟窗口
                widget.showNormal()              # 正常显示
                widget.raise_()                  # 提到最前
                widget.activateWindow()          # 激活窗口
                break                            # 退出循环
        sys.exit(0)                              # 退出当前实例
    
    def cleanup():                               # 清理函数
        instance.release()                       # 释放单实例锁
        QCoreApplication.processEvents()         # 处理待处理事件
    
    atexit.register(cleanup)                     # 注册退出回调
    app.aboutToQuit.connect(cleanup)             # 连接 aboutToQuit 信号
    
    settings = SettingsManager()                 # 创建设置管理器
    timer_mgr = TimerManager()                   # 创建计时管理器
    clock = ClockWidget(settings, timer_mgr)     # 创建时钟窗口

    # 托盘创建容错：部分环境（远程会话/无Shell）可能无系统托盘
    tray = None                                  # 托盘默认为 None
    try:                                         # 异常保护
        if QSystemTrayIcon.isSystemTrayAvailable():  # 系统托盘可用
            tray = TrayIcon()                    # 创建托盘图标
    except Exception:                            # 异常忽略
        tray = None                              # 置为 None

    settings_dlg = SettingsDialog(settings, clock, timer_mgr)  # 创建设置对话框

    if tray is not None:                         # 托盘创建成功
        tray.show_hide_clock.connect(lambda: clock.setVisible(not clock.isVisible()))  # 显示/隐藏
        tray.quit_app.connect(lambda: QCoreApplication.quit())  # 退出
        tray.settings_action.triggered.connect(settings_dlg.exec)  # 打开设置

        timer_mgr.countdown_state_changed.connect(tray.set_countdown_running)  # 倒计时状态同步
        timer_mgr.stopwatch_state_changed.connect(tray.set_stopwatch_running)  # 秒表状态同步

        def on_countdown_triggered():            # 倒计时菜单触发回调
            if timer_mgr.countdown_running:      # 运行中
                timer_mgr.pause_countdown()      # 暂停
            else:                                # 未运行
                timer_mgr.start_countdown()      # 启动
        tray.countdown_action.triggered.connect(on_countdown_triggered)  # 连接
        tray.reset_countdown_action.triggered.connect(lambda: timer_mgr.reset_countdown())  # 重置

        def on_stopwatch_triggered():            # 秒表菜单触发回调
            if timer_mgr.stopwatch_running:      # 运行中
                timer_mgr.pause_stopwatch()      # 暂停
            else:                                # 未运行
                timer_mgr.start_stopwatch()      # 启动
        tray.stopwatch_action.triggered.connect(on_stopwatch_triggered)  # 连接
        tray.reset_stopwatch_action.triggered.connect(timer_mgr.reset_stopwatch)  # 重置
    
    settings_dlg.font_family_changed.connect(clock.set_font_family)  # 字体族
    settings_dlg.base_size_changed.connect(clock.set_base_font_size)  # 字号
    settings_dlg.font_opacity_changed.connect(clock.set_font_opacity)  # 透明度
    settings_dlg.custom_color_changed.connect(clock.set_custom_color)  # 颜色
    settings_dlg.theme_changed.connect(clock.set_theme)  # 主题
    settings_dlg.show_date_changed.connect(clock.set_show_date)  # 日期
    settings_dlg.show_week_changed.connect(clock.set_show_week)  # 星期
    settings_dlg.show_seconds_changed.connect(clock.set_show_seconds)  # 秒钟
    settings_dlg.show_lunar_changed.connect(clock.set_show_lunar)  # 农历
    settings_dlg.show_lunar_year_changed.connect(clock.set_show_lunar_year)  # 农历年
    settings_dlg.show_ganzhi_changed.connect(clock.set_show_ganzhi)  # 天干地支
    settings_dlg.show_zodiac_changed.connect(clock.set_show_zodiac)  # 属相
    settings_dlg.date_week_same_line_changed.connect(clock.set_date_week_same_line)  # 日期星期并排
    settings_dlg.fixed_pos_changed.connect(clock.set_fixed_pos)  # 固定位置
    settings_dlg.stay_on_top_changed.connect(clock.set_stay_on_top)  # 置顶
    settings_dlg.countdown_minutes_changed.connect(timer_mgr.set_countdown_minutes)  # 倒计时分钟
    
    # 开机自启动设置
    def set_startup_with_os(enable):             # 开机自启动设置函数
        if sys.platform != "win32":              # 非 Windows
            return                               # 不处理
        import winreg                            # 导入注册表模块
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"  # 注册表启动项路径
        try:                                    # 异常保护
            if enable:                           # 启用
                if getattr(sys, 'frozen', False):  # 打包后的 exe
                    # 打包后的 exe：直接注册可执行文件路径
                    exe_path = sys.executable    # 获取 exe 路径
                    cmd = f'"{exe_path}"'        # 命令字符串
                else:                            # 开发模式
                    # 开发模式：pythonw + 脚本路径
                    python_exe = sys.executable.replace("python.exe", "pythonw.exe")  # 用 pythonw 避免黑窗口
                    script_path = os.path.abspath(__file__)  # 脚本绝对路径
                    cmd = f'"{python_exe}" "{script_path}"'  # 命令字符串
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)  # 打开键
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)  # 写入值
                winreg.CloseKey(key)             # 关闭键
            else:                                # 禁用
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)  # 打开键
                try:                            # 异常保护
                    winreg.DeleteValue(key, APP_NAME)  # 删除值
                except FileNotFoundError:        # 值不存在
                    pass                         # 忽略
                winreg.CloseKey(key)             # 关闭键
        except Exception as e:                   # 异常处理
            QMessageBox.warning(None, "错误", f"设置开机自启动失败: {e}")  # 弹窗提示
    
    settings_dlg.startup_cb.toggled.connect(set_startup_with_os)  # 连接开机自启动切换
    if settings.get("startup_with_os", DEFAULT_STARTUP_WITH_OS):  # 默认启用开机自启动
        set_startup_with_os(True)                # 调用启用
    
    clock.show()                                 # 显示时钟
    clock.raise_()                               # 提到最前
    clock.activateWindow()                       # 激活窗口

    if tray is not None:                         # 托盘存在
        tray.show()                              # 显示托盘
    
    exit_code = app.exec()                       # 进入事件循环
    
    settings.sync()                              # 同步设置到磁盘
    
    sys.exit(exit_code)                          # 退出


if __name__ == "__main__":                       # 脚本直接运行入口
    main()                                       # 调用主函数