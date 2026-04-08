#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据过滤软件

功能一：数据标签过滤
- txt文件夹读取
- 保存文件夹位置
- 数据标签操作（修改、删除）

功能二：标签格式转换
- txt 与 xml（Pascal VOC）之间互转
- 保护原始标签信息
- 结果统一保存到指定输出文件夹
"""

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import re
from xml.etree import ElementTree as ET
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from PIL import Image
except Exception:  # 如果未安装Pillow，相关功能会在运行时报错提示
    Image = None

try:
    # COCO 标注解析库
    from pycocotools.coco import COCO
except ImportError as e:
    COCO = None
    print(f"警告: pycocotools 导入失败: {e}")
    print("提示: 如果已安装但仍报错，可能需要安装 Visual C++ 编译工具或使用预编译版本")
except Exception as e:
    COCO = None
    print(f"警告: pycocotools 导入时出现异常: {e}")

try:
    # 数据可视化库
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('TkAgg')  # 设置matplotlib后端
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import seaborn as sns
    import numpy as np
except ImportError as e:
    plt = None
    sns = None
    np = None
    print(f"警告: 数据可视化库导入失败: {e}")
    print("提示: 如果要使用数据集展示功能，请安装: pip install matplotlib numpy seaborn")
except Exception as e:
    plt = None
    sns = None
    np = None
    print(f"警告: 数据可视化库导入异常: {e}")

# UI美化配置
class UIStyle:
    """UI样式配置"""
    # 颜色方案
    PRIMARY_COLOR = "#4A90E2"      # 主色调 - 蓝色
    SECONDARY_COLOR = "#5CB85C"    # 辅助色 - 绿色
    ACCENT_COLOR = "#F39C12"       # 强调色 - 橙色
    WARNING_COLOR = "#E74C3C"      # 警告色 - 红色

    # 背景色
    BG_LIGHT = "#F8F9FA"           # 浅背景
    BG_DARK = "#343A40"            # 深背景
    BG_CARD = "#FFFFFF"            # 卡片背景

    # 文字颜色
    TEXT_PRIMARY = "#2C3E50"       # 主文字
    TEXT_SECONDARY = "#6C757D"     # 副文字
    TEXT_LIGHT = "#FFFFFF"         # 浅色文字

    # 边框和阴影
    BORDER_COLOR = "#DEE2E6"
    SHADOW_COLOR = "#ADB5BD"

    # 字体配置
    FONT_TITLE = ("Microsoft YaHei UI", 18, "bold")
    FONT_SUBTITLE = ("Microsoft YaHei UI", 12, "bold")
    FONT_BODY = ("Microsoft YaHei UI", 10)
    FONT_SMALL = ("Microsoft YaHei UI", 9)

    @staticmethod
    def apply_theme(root):
        """应用主题样式"""
        style = ttk.Style()

        # 配置整体主题
        style.configure("TFrame", background=UIStyle.BG_LIGHT)
        style.configure("TLabel", background=UIStyle.BG_LIGHT, foreground=UIStyle.TEXT_PRIMARY, font=UIStyle.FONT_BODY)
        style.configure("TButton", font=UIStyle.FONT_BODY, padding=8)
        style.configure("TEntry", font=UIStyle.FONT_BODY, padding=5)
        style.configure("TCombobox", font=UIStyle.FONT_BODY, padding=5)

        # 主页面按钮样式
        style.configure("MainPage.TButton",
                       font=("Microsoft YaHei UI", 14, "bold"),
                       padding=15,
                       background=UIStyle.PRIMARY_COLOR,
                       foreground=UIStyle.TEXT_LIGHT)
        style.map("MainPage.TButton",
                 background=[("active", UIStyle.SECONDARY_COLOR),
                           ("pressed", UIStyle.ACCENT_COLOR)])

        # 功能按钮样式
        style.configure("Function.TButton",
                       font=UIStyle.FONT_SUBTITLE,
                       padding=10,
                       background=UIStyle.SECONDARY_COLOR,
                       foreground=UIStyle.TEXT_LIGHT)
        style.map("Function.TButton",
                 background=[("active", UIStyle.PRIMARY_COLOR),
                           ("pressed", UIStyle.ACCENT_COLOR)])

        # 导航按钮样式
        style.configure("Nav.TButton",
                       font=UIStyle.FONT_BODY,
                       padding=5,
                       background=UIStyle.BG_LIGHT,
                       foreground=UIStyle.TEXT_SECONDARY)
        style.map("Nav.TButton",
                 background=[("active", UIStyle.BORDER_COLOR)])

        # 标签页样式
        style.configure("Card.TFrame", background=UIStyle.BG_CARD, relief="raised", borderwidth=1)
        # 配置 TLabelFrame 的样式（直接修改默认样式）
        style.configure("TLabelFrame", background=UIStyle.BG_CARD, foreground=UIStyle.TEXT_PRIMARY,
                       font=UIStyle.FONT_SUBTITLE, padding=10, relief="solid", borderwidth=1)

        # 状态栏样式
        style.configure("Status.TLabel", background=UIStyle.BG_DARK, foreground=UIStyle.TEXT_LIGHT,
                       font=UIStyle.FONT_SMALL, padding=5)

        # 设置窗口背景
        root.configure(bg=UIStyle.BG_LIGHT)


class MainApp:
    """主应用类，管理页面切换"""
    def __init__(self, root):
        self.root = root
        self.root.title("🎯 数据过滤软件")
        self.root.geometry("950x950")

        # 应用UI主题
        UIStyle.apply_theme(root)

        # 当前页面
        self.current_page = None

        # 创建主容器
        self.container = ttk.Frame(root, style="Card.TFrame")
        self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建主页面
        self.show_main_page()
    
    def show_main_page(self):
        """显示主页面"""
        if self.current_page:
            self.current_page.destroy()
        
        self.current_page = MainPage(self.container, self)
        self.current_page.pack(fill=tk.BOTH, expand=True)
    
    def show_data_filter_page(self):
        """显示数据过滤页面"""
        if self.current_page:
            self.current_page.destroy()
        
        self.current_page = DataFilterPage(self.container, self)
        self.current_page.pack(fill=tk.BOTH, expand=True)

    def show_label_convert_page(self):
        """显示标签转换页面"""
        if self.current_page:
            self.current_page.destroy()

        self.current_page = LabelConvertPage(self.container, self)
        self.current_page.pack(fill=tk.BOTH, expand=True)

    def show_dataset_split_page(self):
        """显示数据集分类页面"""
        if self.current_page:
            self.current_page.destroy()

        self.current_page = DatasetSplitPage(self.container, self)
        self.current_page.pack(fill=tk.BOTH, expand=True)

    def show_dataset_visualize_page(self):
        """显示数据集展示页面"""
        if self.current_page:
            self.current_page.destroy()

        self.current_page = DatasetVisualizePage(self.container, self)
        self.current_page.pack(fill=tk.BOTH, expand=True)


class MainPage(ttk.Frame):
    """主页面"""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.create_widgets()
    
    def create_widgets(self):
        """创建主页面组件"""
        # 标题区域
        title_frame = ttk.Frame(self, style="Card.TFrame")
        title_frame.pack(pady=30, padx=30, fill=tk.X)

        title_label = ttk.Label(
            title_frame,
            text="🎯 数据过滤软件",
            font=UIStyle.FONT_TITLE,
            foreground=UIStyle.TEXT_PRIMARY
        )
        title_label.pack(pady=(20, 10))

        subtitle_label = ttk.Label(
            title_frame,
            text="专业的目标检测数据处理工具",
            font=UIStyle.FONT_SUBTITLE,
            foreground=UIStyle.TEXT_SECONDARY
        )
        subtitle_label.pack(pady=(0, 20))

        # 功能按钮区域
        button_frame = ttk.Frame(self, style="Card.TFrame")
        button_frame.pack(pady=20, padx=50, fill=tk.BOTH, expand=True)

        # 创建按钮网格布局
        button_container = ttk.Frame(button_frame)
        button_container.pack(pady=30, padx=30)

        # 第一行按钮
        row1_frame = ttk.Frame(button_container)
        row1_frame.pack(pady=10)

        # 数据过滤功能按钮
        filter_btn = ttk.Button(
            row1_frame,
            text="🏷️ 数据标签过滤",
            command=self.app.show_data_filter_page,
            style="MainPage.TButton",
            width=25
        )
        filter_btn.pack(side=tk.LEFT, padx=15)

        # 标签转换功能按钮
        convert_btn = ttk.Button(
            row1_frame,
            text="🔄 标签格式转换",
            command=self.app.show_label_convert_page,
            style="MainPage.TButton",
            width=25
        )
        convert_btn.pack(side=tk.LEFT, padx=15)

        # 第二行按钮
        row2_frame = ttk.Frame(button_container)
        row2_frame.pack(pady=10)

        # 数据集分类功能按钮
        split_btn = ttk.Button(
            row2_frame,
            text="📊 数据集分类",
            command=self.app.show_dataset_split_page,
            style="MainPage.TButton",
            width=25
        )
        split_btn.pack(side=tk.LEFT, padx=15)

        # 第三行按钮
        row3_frame = ttk.Frame(button_container)
        row3_frame.pack(pady=10)

        # 数据集展示功能按钮
        visualize_btn = ttk.Button(
            row3_frame,
            text="📈 数据集展示",
            command=self.app.show_dataset_visualize_page,
            style="MainPage.TButton",
            width=25
        )
        visualize_btn.pack(side=tk.LEFT, padx=15)

        # 占位按钮（为保持对称）
        placeholder_btn = ttk.Button(
            row2_frame,
            text="🚀 更多功能",
            state="disabled",
            style="MainPage.TButton",
            width=25
        )
        placeholder_btn.pack(side=tk.LEFT, padx=15)
        
        # 功能说明区域
        info_frame = ttk.LabelFrame(self, text="📖 功能介绍")
        info_frame.pack(pady=20, padx=50, fill=tk.BOTH, expand=True)

        # 创建滚动文本区域
        info_text_widget = scrolledtext.ScrolledText(
            info_frame,
            wrap=tk.WORD,
            font=UIStyle.FONT_BODY,
            bg=UIStyle.BG_CARD,
            fg=UIStyle.TEXT_PRIMARY,
            height=12,
            padx=15,
            pady=15
        )
        info_text_widget.pack(fill=tk.BOTH, expand=True)

        info_text = """🎯 数据标签过滤功能：
   • 支持txt文件夹批量处理，自动扫描标注文件
   • 强大的标签修改功能：简单映射、范围映射、批量映射
   • 支持标签删除操作，清理不需要的标注
   • 灵活的保存选项：保存到新文件夹或直接修改源文件

🔄 标签格式转换功能：
   • 支持TXT (YOLO) ↔ XML (Pascal VOC) 双向转换
   • 支持COCO JSON ↔ XML (Pascal VOC) 格式转换
   • 支持YOLO TXT ↔ COCO JSON 互转
   • 智能类别映射，保护原始标注信息

📊 数据集分类功能：
   • 自动识别数据集结构和类别信息
   • 智能划分训练集、验证集、测试集（自定义比例）
   • 自动生成YOLO标准的data.yaml配置文件
   • 创建训练所需的txt文件列表，一键完成数据集准备

📈 数据集展示功能：
   • 类别分布柱状图（含具体数量标注）
   • 小中大目标统计饼图（按bbox面积分类）
   • bbox尺寸散点图（宽度-高度分布）
   • bbox面积分布直方图
   • bbox中心点热力图
   • 每图目标数统计直方图
   • 图片尺寸分布图

💡 使用提示：
   • 所有操作都支持批量处理，提高工作效率
   • 提供详细的操作日志和状态反馈
   • 支持多种文件编码，确保兼容性
   • 界面简洁直观，操作简单易用"""

        info_text_widget.insert(tk.END, info_text)
        info_text_widget.config(state=tk.DISABLED)  # 设置为只读


class DataFilterPage(ttk.Frame):
    """数据过滤页面"""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        
        # 配置文件路径
        self.config_file = "config.json"
        
        # 当前文件夹路径（源文件夹）
        self.current_folder = ""
        
        # 保存文件夹路径（目标文件夹）
        self.save_folder = ""
        
        # 文件列表（内部使用，不显示）
        self.file_list = []
        
        # 加载配置
        self.load_config()
        
        # 创建界面
        self.create_widgets()
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.current_folder = config.get('folder_path', '')
                    self.save_folder = config.get('save_folder_path', '')
            except Exception as e:
                print(f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置文件"""
        try:
            config = {
                'folder_path': self.current_folder,
                'save_folder_path': self.save_folder
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
    def create_widgets(self):
        """创建界面组件"""
        # 顶部导航栏
        nav_frame = ttk.Frame(self, style="Card.TFrame")
        nav_frame.pack(fill=tk.X, padx=10, pady=10)

        back_btn = ttk.Button(nav_frame, text="🏠 返回主页", command=self.app.show_main_page, style="Nav.TButton")
        back_btn.pack(side=tk.LEFT, padx=(0, 20))

        title_label = ttk.Label(nav_frame, text="🏷️ 数据标签过滤", font=UIStyle.FONT_SUBTITLE,
                               foreground=UIStyle.PRIMARY_COLOR)
        title_label.pack(side=tk.LEFT)
        
        # 主框架
        main_frame = ttk.Frame(self, style="Card.TFrame", padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=0)
        main_frame.rowconfigure(2, weight=0)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # 标签文件夹选择区域
        label_folder_frame = ttk.LabelFrame(main_frame, text="📁 标签文件夹选择")
        label_folder_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        label_folder_frame.columnconfigure(1, weight=1)
        
        ttk.Label(label_folder_frame, text="标签文件夹路径:").grid(row=0, column=0, padx=5, pady=5)
        
        self.label_folder_path_var = tk.StringVar(value=self.current_folder)
        label_folder_entry = ttk.Entry(label_folder_frame, textvariable=self.label_folder_path_var, width=50)
        label_folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(label_folder_frame, text="浏览", command=self.browse_label_folder).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(label_folder_frame, text="加载文件", command=self.load_files).grid(row=0, column=3, padx=5, pady=5)
        
        # 图片文件夹选择区域
        image_folder_frame = ttk.LabelFrame(main_frame, text="🖼️ 图片文件夹选择", padding="10")
        image_folder_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        image_folder_frame.columnconfigure(1, weight=1)
        
        ttk.Label(image_folder_frame, text="图片文件夹路径:").grid(row=0, column=0, padx=5, pady=5)
        
        self.image_folder_path_var = tk.StringVar(value="")
        image_folder_entry = ttk.Entry(image_folder_frame, textvariable=self.image_folder_path_var, width=50)
        image_folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(image_folder_frame, text="浏览", command=self.browse_image_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # 保存文件夹选择区域
        save_folder_frame = ttk.LabelFrame(main_frame, text="💾 保存文件夹选择", padding="10")
        save_folder_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        save_folder_frame.columnconfigure(1, weight=1)
        
        # 标签保存文件夹
        ttk.Label(save_folder_frame, text="标签保存文件夹:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.label_save_folder_path_var = tk.StringVar(value=self.save_folder)
        label_save_folder_entry = ttk.Entry(save_folder_frame, textvariable=self.label_save_folder_path_var, width=40)
        label_save_folder_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(save_folder_frame, text="浏览", command=self.browse_label_save_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # 图片保存文件夹
        ttk.Label(save_folder_frame, text="图片保存文件夹:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        
        self.image_save_folder_path_var = tk.StringVar(value=self.save_folder)
        image_save_folder_entry = ttk.Entry(save_folder_frame, textvariable=self.image_save_folder_path_var, width=40)
        image_save_folder_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        
        ttk.Button(save_folder_frame, text="浏览", command=self.browse_image_save_folder).grid(row=1, column=2, padx=5, pady=5)
        
        # 标签操作区域
        label_frame = ttk.LabelFrame(main_frame, text="🔧 标签操作")
        label_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        label_frame.columnconfigure(0, weight=1)
        label_frame.columnconfigure(1, weight=1)
        
        # 标签修改区域
        modify_frame = ttk.LabelFrame(label_frame, text="修改标签", padding="10")
        modify_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        modify_frame.columnconfigure(1, weight=1)
        
        ttk.Label(modify_frame, text="标签映射:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.modify_entry = ttk.Entry(modify_frame, width=30)
        self.modify_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(modify_frame, text="格式: 1->3,2->6 或 1-5->10 或 1,2,3->5 (多个用逗号分隔)").grid(row=1, column=1, padx=5, sticky=tk.W)
        
        ttk.Button(modify_frame, text="执行修改", command=self.modify_labels).grid(row=0, column=2, padx=5, pady=5)
        
        # 标签删除区域
        delete_frame = ttk.LabelFrame(label_frame, text="删除标签", padding="10")
        delete_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        delete_frame.columnconfigure(1, weight=1)
        
        ttk.Label(delete_frame, text="要删除的标签:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.delete_entry = ttk.Entry(delete_frame, width=30)
        self.delete_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(delete_frame, text="格式: 1,2,3 (多个用逗号分隔)").grid(row=1, column=1, padx=5, sticky=tk.W)
        
        ttk.Button(delete_frame, text="执行删除", command=self.delete_labels).grid(row=0, column=2, padx=5, pady=5)
        
        # 操作日志区域
        log_frame = ttk.LabelFrame(main_frame, text="📋 操作日志")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD,
                                                 font=UIStyle.FONT_SMALL,
                                                 bg=UIStyle.BG_LIGHT,
                                                 fg=UIStyle.TEXT_PRIMARY,
                                                 padx=10, pady=10)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 状态栏
        self.status_var = tk.StringVar(value="✅ 就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel")
        status_bar.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
    
    def browse_label_folder(self):
        """浏览标签文件夹"""
        folder = filedialog.askdirectory(initialdir=self.current_folder)
        if folder:
            self.current_folder = folder
            self.label_folder_path_var.set(folder)
            self.save_config()
            self.log(f"选择标签文件夹: {folder}")
    
    def browse_image_folder(self):
        """浏览图片文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.image_folder_path_var.set(folder)
            self.log(f"选择图片文件夹: {folder}")
    
    def browse_label_save_folder(self):
        """浏览标签保存文件夹"""
        folder = filedialog.askdirectory(initialdir=self.save_folder)
        if folder:
            self.save_folder = folder
            self.label_save_folder_path_var.set(folder)
            self.save_config()
            self.log(f"选择标签保存文件夹: {folder}")
    
    def browse_image_save_folder(self):
        """浏览图片保存文件夹"""
        folder = filedialog.askdirectory(initialdir=self.save_folder)
        if folder:
            self.image_save_folder_path_var.set(folder)
            self.log(f"选择图片保存文件夹: {folder}")
    
    def load_files(self):
        """加载txt文件列表"""
        folder = self.label_folder_path_var.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("错误", "请先选择有效的标签文件夹路径！")
            return
        
        self.current_folder = folder
        self.save_config()
        
        # 查找所有txt文件
        self.file_list = []
        try:
            for file in os.listdir(folder):
                if file.lower().endswith('.txt'):
                    self.file_list.append(file)
            
            self.log(f"加载了 {len(self.file_list)} 个txt文件")
            self.status_var.set(f"已加载 {len(self.file_list)} 个文件")
            
            if len(self.file_list) == 0:
                messagebox.showwarning("警告", "未找到任何txt文件！")
        except Exception as e:
            messagebox.showerror("错误", f"加载文件失败: {e}")
            self.log(f"错误: {e}")
    
    def parse_label_mapping(self, mapping_str):
        """解析标签映射字符串
        支持多种格式:
        1. 简单映射: 1->3,2->6
        2. 范围映射: 1-5->10 (将1到5都映射为10)
        3. 批量映射: 1,2,3->5 (将1,2,3都映射为5)
        返回: {old_label: new_label}
        """
        mapping = {}
        try:
            parts = mapping_str.split(',')
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                
                # 处理范围映射: 1-5->10
                if '->' in part and '-' in part.split('->')[0]:
                    range_part, new_label = part.split('->')
                    range_part = range_part.strip()
                    new_label = new_label.strip()
                    
                    if '-' in range_part:
                        start_str, end_str = range_part.split('-')
                        start = int(start_str.strip())
                        end = int(end_str.strip())
                        new = int(new_label)
                        
                        for label in range(start, end + 1):
                            mapping[label] = new
                    continue
                
                # 处理批量映射: 1,2,3->5
                if '->' in part:
                    old_part, new_label = part.split('->')
                    old_part = old_part.strip()
                    new_label = new_label.strip()
                    
                    # 检查是否有多个旧标签
                    if ',' in old_part:
                        old_labels = [int(x.strip()) for x in old_part.split(',')]
                        new = int(new_label)
                        for old in old_labels:
                            mapping[old] = new
                    else:
                        # 单个映射
                        old = int(old_part)
                        new = int(new_label)
                        mapping[old] = new
        except Exception as e:
            raise ValueError(f"标签映射格式错误: {e}")
        return mapping
    
    def parse_delete_labels(self, delete_str):
        """解析要删除的标签字符串
        格式: 1,2,3
        返回: [1, 2, 3]
        """
        labels = []
        try:
            parts = delete_str.split(',')
            for part in parts:
                part = part.strip()
                if part:
                    labels.append(int(part))
        except Exception as e:
            raise ValueError(f"删除标签格式错误: {e}")
        return labels
    
    def process_file_labels(self, file_path, output_path=None, label_mapping=None, delete_labels=None):
        """处理文件中的标签
        file_path: 源文件路径
        output_path: 输出文件路径（如果为None，则覆盖原文件）
        label_mapping: {old_label: new_label}
        delete_labels: [label1, label2, ...]
        
        支持多种标签格式：
        1. 每行一个标签数字
        2. 行中包含标签数字（空格或其他分隔符），只修改第一个数字（标签列）
        
        返回: (modified, is_empty)
        modified: 是否修改了文件
        is_empty: 处理后文件是否为空
        """
        try:
            # 标准化路径分隔符
            file_path = os.path.normpath(file_path)
            if output_path:
                output_path = os.path.normpath(output_path)
            
            # 尝试读取文件
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except PermissionError:
                # 尝试以只读模式打开
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
            
            modified_lines = []
            modified = False
            
            for line in lines:
                original_line = line
                line_stripped = line.rstrip('\n\r')
                
                if not line_stripped.strip():
                    modified_lines.append(original_line)
                    continue
                
                # 分割行内容，获取第一个元素作为标签
                parts = line_stripped.split()
                if not parts:
                    modified_lines.append(original_line)
                    continue
                
                try:
                    # 尝试将第一个元素解析为标签
                    label = int(parts[0])
                    
                    # 检查是否要删除
                    if delete_labels and label in delete_labels:
                        # 删除这一行（不添加到结果中）
                        modified = True
                        continue
                    
                    # 检查是否需要修改
                    if label_mapping and label in label_mapping:
                        # 修改标签列
                        new_label = label_mapping[label]
                        parts[0] = str(new_label)
                        new_line = ' '.join(parts)
                        modified = True
                    else:
                        # 没有变化，保持原样
                        new_line = line_stripped
                    
                    # 保持原有的换行符格式
                    if original_line.endswith('\r\n'):
                        modified_lines.append(new_line + '\r\n')
                    elif original_line.endswith('\n'):
                        modified_lines.append(new_line + '\n')
                    else:
                        modified_lines.append(new_line + '\n')
                except ValueError:
                    # 第一个元素不是数字，保持原样
                    modified_lines.append(original_line)
            
            # 检查处理后文件是否为空（只包含空行）
            is_empty = True
            for line in modified_lines:
                if line.strip():
                    is_empty = False
                    break
            
            # 如果文件为空且有输出路径，不保存文件
            if is_empty and output_path:
                return (modified, True)
            
            # 确定输出路径
            if output_path is None:
                output_path = file_path
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir, exist_ok=True)
                except Exception as e:
                    raise Exception(f"创建输出目录失败: {e}")
            
            # 尝试写入文件
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.writelines(modified_lines)
            except PermissionError:
                # 尝试以不同的方式写入
                try:
                    # 先写入临时文件
                    temp_path = output_path + '.tmp'
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        f.writelines(modified_lines)
                    # 然后替换原文件
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    os.rename(temp_path, output_path)
                except Exception as e:
                    raise Exception(f"写入文件失败（权限错误）: {e}")
            
            return (modified, is_empty)
            
        except Exception as e:
            raise Exception(f"处理文件失败 {os.path.basename(file_path)}: {e}")
    
    def modify_labels(self):
        """执行标签修改"""
        mapping_str = self.modify_entry.get().strip()
        if not mapping_str:
            messagebox.showwarning("警告", "请输入标签映射！")
            return
        
        if not self.file_list:
            messagebox.showwarning("警告", "请先加载文件！")
            return
        
        # 获取标签保存文件夹和图片保存文件夹
        label_save_folder = self.label_save_folder_path_var.get().strip()
        image_save_folder = self.image_save_folder_path_var.get().strip()
        
        if not label_save_folder:
            if messagebox.askyesno("确认", "未设置标签保存文件夹，将直接修改源文件。是否继续？"):
                label_save_folder = None
            else:
                return
        
        # 获取图片文件夹路径
        image_folder = self.image_folder_path_var.get().strip()
        
        try:
            label_mapping = self.parse_label_mapping(mapping_str)
            if not label_mapping:
                messagebox.showwarning("警告", "标签映射格式错误！")
                return
            
            self.log(f"开始修改标签: {label_mapping}")
            if label_save_folder:
                self.log(f"标签保存到: {label_save_folder}")
            if image_save_folder and image_folder:
                self.log(f"图片保存到: {image_save_folder}")
            
            success_count = 0
            error_count = 0
            
            for file_name in self.file_list:
                file_path = os.path.join(self.current_folder, file_name)
                try:
                    if label_save_folder:
                        output_path = os.path.join(label_save_folder, file_name)
                    else:
                        output_path = None
                    
                    modified, is_empty = self.process_file_labels(file_path, output_path=output_path, label_mapping=label_mapping)
                    
                    # 如果保存到新文件夹且文件不为空，复制对应的图片
                    if label_save_folder and not is_empty and image_folder and image_save_folder:
                        # 生成图片文件名（将.txt改为常见图片格式）
                        base_name = os.path.splitext(file_name)[0]
                        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
                        image_found = False
                        
                        for ext in image_extensions:
                            image_file = os.path.join(image_folder, base_name + ext)
                            if os.path.exists(image_file):
                                # 复制图片到图片保存文件夹
                                import shutil
                                dest_image_file = os.path.join(image_save_folder, base_name + ext)
                                # 确保图片保存文件夹存在
                                os.makedirs(os.path.dirname(dest_image_file), exist_ok=True)
                                shutil.copy2(image_file, dest_image_file)
                                self.log(f"  ✓ 复制图片: {base_name + ext} -> {os.path.basename(image_save_folder)}/{base_name + ext}")
                                image_found = True
                                break
                        
                        if not image_found:
                            self.log(f"  ? 未找到对应图片: {base_name}")
                    
                    if modified:
                        success_count += 1
                        if label_save_folder:
                            self.log(f"  ✓ {file_name} -> {os.path.basename(label_save_folder)}/{file_name}")
                        else:
                            self.log(f"  ✓ {file_name}")
                    else:
                        self.log(f"  - {file_name} (无变化)")
                except Exception as e:
                    error_count += 1
                    self.log(f"  ✗ {file_name}: {e}")
            
            self.status_var.set(f"修改完成: 成功 {success_count}, 失败 {error_count}")
            messagebox.showinfo("完成", f"标签修改完成！\n成功: {success_count}\n失败: {error_count}")
            
        except Exception as e:
            messagebox.showerror("错误", f"修改标签失败: {e}")
            self.log(f"错误: {e}")
    
    def delete_labels(self):
        """执行标签删除"""
        delete_str = self.delete_entry.get().strip()
        if not delete_str:
            messagebox.showwarning("警告", "请输入要删除的标签！")
            return
        
        if not self.file_list:
            messagebox.showwarning("警告", "请先加载文件！")
            return
        
        # 获取标签保存文件夹和图片保存文件夹
        label_save_folder = self.label_save_folder_path_var.get().strip()
        image_save_folder = self.image_save_folder_path_var.get().strip()
        
        if not label_save_folder:
            if messagebox.askyesno("确认", "未设置标签保存文件夹，将直接修改源文件。是否继续？"):
                label_save_folder = None
            else:
                return
        
        # 获取图片文件夹路径
        image_folder = self.image_folder_path_var.get().strip()
        
        try:
            delete_labels = self.parse_delete_labels(delete_str)
            if not delete_labels:
                messagebox.showwarning("警告", "删除标签格式错误！")
                return
            
            self.log(f"开始删除标签: {delete_labels}")
            if label_save_folder:
                self.log(f"标签保存到: {label_save_folder}")
            if image_save_folder and image_folder:
                self.log(f"图片保存到: {image_save_folder}")
            
            success_count = 0
            error_count = 0
            
            for file_name in self.file_list:
                file_path = os.path.join(self.current_folder, file_name)
                try:
                    if label_save_folder:
                        output_path = os.path.join(label_save_folder, file_name)
                    else:
                        output_path = None
                    
                    modified, is_empty = self.process_file_labels(file_path, output_path=output_path, delete_labels=delete_labels)
                    
                    # 如果保存到新文件夹且文件不为空，复制对应的图片
                    if label_save_folder and not is_empty and image_folder and image_save_folder:
                        # 生成图片文件名（将.txt改为常见图片格式）
                        base_name = os.path.splitext(file_name)[0]
                        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
                        image_found = False
                        
                        for ext in image_extensions:
                            image_file = os.path.join(image_folder, base_name + ext)
                            if os.path.exists(image_file):
                                # 复制图片到图片保存文件夹
                                import shutil
                                dest_image_file = os.path.join(image_save_folder, base_name + ext)
                                # 确保图片保存文件夹存在
                                os.makedirs(os.path.dirname(dest_image_file), exist_ok=True)
                                shutil.copy2(image_file, dest_image_file)
                                self.log(f"  ✓ 复制图片: {base_name + ext} -> {os.path.basename(image_save_folder)}/{base_name + ext}")
                                image_found = True
                                break
                        
                        if not image_found:
                            self.log(f"  ? 未找到对应图片: {base_name}")
                    
                    if modified:
                        success_count += 1
                        if label_save_folder:
                            self.log(f"  ✓ {file_name} -> {os.path.basename(label_save_folder)}/{file_name}")
                        else:
                            self.log(f"  ✓ {file_name}")
                    else:
                        self.log(f"  - {file_name} (无变化)")
                except Exception as e:
                    error_count += 1
                    self.log(f"  ✗ {file_name}: {e}")
            
            self.status_var.set(f"删除完成: 成功 {success_count}, 失败 {error_count}")
            messagebox.showinfo("完成", f"标签删除完成！\n成功: {success_count}\n失败: {error_count}")
            
        except Exception as e:
            messagebox.showerror("错误", f"删除标签失败: {e}")
            self.log(f"错误: {e}")
    
    def log(self, message):
        """添加日志"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)


class LabelConvertPage(ttk.Frame):
    """标签格式转换页面（txt <-> xml）"""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # 源标注文件夹、图片文件夹、输出文件夹
        self.anno_folder = ""
        self.image_folder = ""
        self.save_folder = ""

        # 创建界面
        self.create_widgets()

    # ---------- 界面 ----------
    def create_widgets(self):
        """创建界面组件"""
        # 顶部导航栏
        nav_frame = ttk.Frame(self, style="Card.TFrame")
        nav_frame.pack(fill=tk.X, padx=10, pady=10)

        back_btn = ttk.Button(nav_frame, text="🏠 返回主页", command=self.app.show_main_page, style="Nav.TButton")
        back_btn.pack(side=tk.LEFT, padx=(0, 20))

        title_label = ttk.Label(nav_frame, text="🔄 标签格式转换", font=UIStyle.FONT_SUBTITLE,
                               foreground=UIStyle.PRIMARY_COLOR)
        title_label.pack(side=tk.LEFT)

        # 主框架
        main_frame = ttk.Frame(self, style="Card.TFrame", padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # 源标注文件夹/文件
        anno_frame = ttk.LabelFrame(main_frame, text="📂 源标注路径（根据转换方向选择文件或文件夹）")
        anno_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        anno_frame.columnconfigure(1, weight=1)

        self.anno_label_var = tk.StringVar(value="标注文件夹路径:")
        ttk.Label(anno_frame, textvariable=self.anno_label_var).grid(row=0, column=0, padx=5, pady=5)
        self.anno_folder_var = tk.StringVar(value=self.anno_folder)
        anno_entry = ttk.Entry(anno_frame, textvariable=self.anno_folder_var, width=50)
        anno_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(anno_frame, text="浏览", command=self.browse_anno_folder).grid(row=0, column=2, padx=5, pady=5)

        # 提示标签
        self.anno_hint_var = tk.StringVar(value="选择包含 txt/xml 文件的文件夹")
        ttk.Label(anno_frame, textvariable=self.anno_hint_var, font=("Arial", 8)).grid(row=1, column=1, padx=5, sticky=tk.W)

        # 图片文件夹（txt->xml 时需要）
        image_frame = ttk.LabelFrame(main_frame, text="🖼️ 图片文件夹（txt->xml 时必选）")
        image_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        image_frame.columnconfigure(1, weight=1)

        ttk.Label(image_frame, text="图片文件夹路径:").grid(row=0, column=0, padx=5, pady=5)
        self.image_folder_var = tk.StringVar(value=self.image_folder)
        image_entry = ttk.Entry(image_frame, textvariable=self.image_folder_var, width=50)
        image_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(image_frame, text="浏览", command=self.browse_image_folder).grid(row=0, column=2, padx=5, pady=5)

        # 输出文件夹
        save_frame = ttk.LabelFrame(main_frame, text="💾 输出文件夹（必选，保护原始标注）")
        save_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        save_frame.columnconfigure(1, weight=1)

        ttk.Label(save_frame, text="输出文件夹路径:").grid(row=0, column=0, padx=5, pady=5)
        self.save_folder_var = tk.StringVar(value=self.save_folder)
        save_entry = ttk.Entry(save_frame, textvariable=self.save_folder_var, width=50)
        save_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(save_frame, text="浏览", command=self.browse_save_folder).grid(row=0, column=2, padx=5, pady=5)

        # 转换方向
        option_frame = ttk.LabelFrame(main_frame, text="⚙️ 转换选项")
        option_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        self.direction_var = tk.StringVar(value="txt2xml")
        # 行 0：YOLO/TXT <-> VOC
        ttk.Radiobutton(option_frame, text="TXT (YOLO) -> XML (Pascal VOC)", variable=self.direction_var,
                        value="txt2xml", command=self.update_direction_labels).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(option_frame, text="XML (Pascal VOC) -> TXT (YOLO)", variable=self.direction_var,
                        value="xml2txt", command=self.update_direction_labels).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        # 行 2：COCO / YOLO <-> COCO
        ttk.Radiobutton(option_frame, text="COCO JSON -> XML (Pascal VOC)", variable=self.direction_var,
                        value="coco2voc", command=self.update_direction_labels).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Radiobutton(option_frame, text="YOLO TXT -> COCO JSON", variable=self.direction_var,
                        value="yolo2coco", command=self.update_direction_labels).grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)

        # 初始化标签显示
        self.update_direction_labels()

        # 类别映射输入
        ttk.Label(option_frame, text="类别映射 (示例: 0:cat,1:door)").grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.class_map_var = tk.StringVar(value="")
        class_entry = ttk.Entry(option_frame, textvariable=self.class_map_var, width=40)
        class_entry.grid(row=1, column=1, rowspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))

        ttk.Button(option_frame, text="开始转换", command=self.start_convert).grid(row=0, column=2, rowspan=4, padx=20, pady=5)

        # 日志
        log_frame = ttk.LabelFrame(main_frame, text="📋 转换日志")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, wrap=tk.WORD,
                                                 font=UIStyle.FONT_SMALL,
                                                 bg=UIStyle.BG_LIGHT,
                                                 fg=UIStyle.TEXT_PRIMARY,
                                                 padx=10, pady=10)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 状态栏
        self.status_var = tk.StringVar(value="✅ 就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel")
        status_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

    # ---------- 浏览路径 ----------
    def browse_anno_folder(self):
        direction = getattr(self, "direction_var", None).get() if hasattr(self, "direction_var") else "txt2xml"
        if direction == "coco2voc":
            # COCO JSON 选择文件
            path = filedialog.askopenfilename(
                initialdir=self.anno_folder or ".",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
        else:
            # 其他模式选择文件夹
            path = filedialog.askdirectory(initialdir=self.anno_folder or ".")
        if path:
            self.anno_folder = path
            self.anno_folder_var.set(path)

    def browse_image_folder(self):
        folder = filedialog.askdirectory(initialdir=self.image_folder or ".")
        if folder:
            self.image_folder = folder
            self.image_folder_var.set(folder)

    def browse_save_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_folder or ".")
        if folder:
            self.save_folder = folder
            self.save_folder_var.set(folder)

    # ---------- 工具 ----------
    def log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def update_direction_labels(self):
        """根据选择的转换方向更新界面标签"""
        direction = self.direction_var.get()
        if direction == "coco2voc":
            self.anno_label_var.set("标注文件路径:")
            self.anno_hint_var.set("选择 COCO JSON 文件 (如 instances_train2017.json)")
        elif direction == "yolo2coco":
            self.anno_label_var.set("标注文件夹路径:")
            self.anno_hint_var.set("选择包含 YOLO TXT 文件的文件夹")
        else:  # txt2xml 或 xml2txt
            self.anno_label_var.set("标注文件夹路径:")
            self.anno_hint_var.set("选择包含 txt/xml 文件的文件夹")

    def parse_class_map(self, text: str):
        """
        解析类别映射字符串，支持格式：
        0:cat,1:door
        0：cat，1：door   （中文冒号/逗号也可）
        返回 (id_to_name, name_to_id)
        """
        if not text.strip():
            return {}, {}
        id_to_name = {}
        name_to_id = {}
        text = text.replace("，", ",").replace("：", ":")
        parts = text.split(",")
        for part in parts:
            if ":" not in part:
                continue
            left, right = part.split(":", 1)
            left = left.strip()
            right = right.strip()
            if not left or not right:
                continue
            try:
                idx = int(left)
            except ValueError:
                continue
            id_to_name[idx] = right
            name_to_id[right] = idx
        return id_to_name, name_to_id

    def get_image_size(self, image_path):
        """获取图片尺寸 (w, h)。需要 Pillow 支持。"""
        if Image is None:
            raise RuntimeError("未安装 Pillow 库，无法读取图片尺寸，请先执行: pip install pillow")
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")
        with Image.open(image_path) as img:
            return img.size  # (w, h)

    # ---------- VOC XML 写入工具（给 COCO->VOC / YOLO->VOC 复用） ----------
    def save_voc_xml(self, filename, size, objs, save_path, image_path=None):
        """
        保存 VOC XML 文件
        size: dict(width, height, depth)
        objs: [[name, xmin, ymin, xmax, ymax], ...]
        image_path: 图片完整路径（可选），用于设置 <path> 标签
        """
        annotation = ET.Element("annotation")

        folder_el = ET.SubElement(annotation, "folder")
        folder_el.text = "DATA"

        filename_el = ET.SubElement(annotation, "filename")
        filename_el.text = filename
        
        # 如果提供了图片路径，添加 path 标签（规范化路径格式）
        if image_path:
            path_el = ET.SubElement(annotation, "path")
            normalized_path = os.path.normpath(image_path)
            path_el.text = normalized_path.replace("\\", "/")

        source_el = ET.SubElement(annotation, "source")
        db_el = ET.SubElement(source_el, "database")
        db_el.text = "The VOC Database"
        ann_el = ET.SubElement(source_el, "annotation")
        ann_el.text = "PASCAL VOC"
        img_el = ET.SubElement(source_el, "image")
        img_el.text = "flickr"

        size_el = ET.SubElement(annotation, "size")
        w_el = ET.SubElement(size_el, "width")
        h_el = ET.SubElement(size_el, "height")
        d_el = ET.SubElement(size_el, "depth")
        w_el.text = str(size["width"])
        h_el.text = str(size["height"])
        d_el.text = str(size.get("depth", 3))

        segmented_el = ET.SubElement(annotation, "segmented")
        segmented_el.text = "0"

        for obj in objs:
            name, xmin, ymin, xmax, ymax = obj
            obj_el = ET.SubElement(annotation, "object")
            name_el = ET.SubElement(obj_el, "name")
            name_el.text = str(name)

            pose_el = ET.SubElement(obj_el, "pose")
            pose_el.text = "Unspecified"
            truncated_el = ET.SubElement(obj_el, "truncated")
            truncated_el.text = "0"
            difficult_el = ET.SubElement(obj_el, "difficult")
            difficult_el.text = "0"

            bnd_el = ET.SubElement(obj_el, "bndbox")
            xmin_el = ET.SubElement(bnd_el, "xmin")
            ymin_el = ET.SubElement(bnd_el, "ymin")
            xmax_el = ET.SubElement(bnd_el, "xmax")
            ymax_el = ET.SubElement(bnd_el, "ymax")
            xmin_el.text = str(int(xmin))
            ymin_el.text = str(int(ymin))
            xmax_el.text = str(int(xmax))
            ymax_el.text = str(int(ymax))

        os.makedirs(save_path, exist_ok=True)
        xml_path = os.path.join(save_path, os.path.splitext(filename)[0] + ".xml")
        tree = ET.ElementTree(annotation)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)

    # ---------- 转换核心 ----------
    def txt_to_xml_one(self, txt_path, xml_path, image_folder, id_to_name=None):
        """将单个 YOLO 风格 txt 转为 VOC xml（可选类别映射，保护原始标签）"""
        base = os.path.splitext(os.path.basename(txt_path))[0]

        # 寻找对应图片
        img_path = None
        for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            candidate = os.path.join(image_folder, base + ext)
            if os.path.exists(candidate):
                img_path = candidate
                break
        if img_path is None:
            raise FileNotFoundError(f"未找到对应图片: {base}.jpg/.png 等")

        img_w, img_h = self.get_image_size(img_path)

        # 读取 txt 标注
        if not os.path.exists(txt_path):
            raise FileNotFoundError(f"标注文件不存在: {txt_path}")

        with open(txt_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]

        # 构造 VOC XML
        annotation = ET.Element("annotation")

        folder_el = ET.SubElement(annotation, "folder")
        folder_el.text = os.path.basename(os.path.dirname(img_path))

        filename_el = ET.SubElement(annotation, "filename")
        filename_el.text = os.path.basename(img_path)

        path_el = ET.SubElement(annotation, "path")
        # 规范化路径并统一使用正斜杠（XML标准）
        normalized_path = os.path.normpath(img_path)
        path_el.text = normalized_path.replace("\\", "/")

        source_el = ET.SubElement(annotation, "source")
        db_el = ET.SubElement(source_el, "database")
        db_el.text = "Unknown"

        size_el = ET.SubElement(annotation, "size")
        w_el = ET.SubElement(size_el, "width")
        h_el = ET.SubElement(size_el, "height")
        d_el = ET.SubElement(size_el, "depth")
        w_el.text = str(img_w)
        h_el.text = str(img_h)
        d_el.text = "3"

        segmented_el = ET.SubElement(annotation, "segmented")
        segmented_el.text = "0"

        for line in lines:
            parts = line.split()
            if len(parts) != 5:
                # 支持 name cx cy w h 或 id cx cy w h
                if len(parts) < 5:
                    continue
            cls_raw = parts[0]
            # 如果是数字且提供了映射，则用映射到的名称；否则保留原始内容
            cls = cls_raw
            if id_to_name:
                try:
                    cls_idx = int(cls_raw)
                    cls = id_to_name.get(cls_idx, cls_raw)
                except ValueError:
                    # 非数字则直接使用
                    cls = cls_raw
            cx, cy, bw, bh = map(float, parts[1:5])

            # 反归一化
            box_w = bw * img_w
            box_h = bh * img_h
            center_x = cx * img_w
            center_y = cy * img_h

            xmin = max(0, int(center_x - box_w / 2))
            ymin = max(0, int(center_y - box_h / 2))
            xmax = min(img_w - 1, int(center_x + box_w / 2))
            ymax = min(img_h - 1, int(center_y + box_h / 2))

            obj_el = ET.SubElement(annotation, "object")
            name_el = ET.SubElement(obj_el, "name")
            name_el.text = str(cls)  # 使用映射后的标签或原始标签

            pose_el = ET.SubElement(obj_el, "pose")
            pose_el.text = "Unspecified"
            truncated_el = ET.SubElement(obj_el, "truncated")
            truncated_el.text = "0"
            difficult_el = ET.SubElement(obj_el, "difficult")
            difficult_el.text = "0"

            bndbox_el = ET.SubElement(obj_el, "bndbox")
            xmin_el = ET.SubElement(bndbox_el, "xmin")
            ymin_el = ET.SubElement(bndbox_el, "ymin")
            xmax_el = ET.SubElement(bndbox_el, "xmax")
            ymax_el = ET.SubElement(bndbox_el, "ymax")
            xmin_el.text = str(xmin)
            ymin_el.text = str(ymin)
            xmax_el.text = str(xmax)
            ymax_el.text = str(ymax)

        tree = ET.ElementTree(annotation)
        os.makedirs(os.path.dirname(xml_path), exist_ok=True)
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)

    def xml_to_txt_one(self, xml_path, txt_path, name_to_id=None):
        """将单个 VOC xml 转为 YOLO 风格 txt（可选类别映射，保护原始标签）"""
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"XML 不存在: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()

        size_el = root.find("size")
        if size_el is None:
            raise ValueError(f"XML 中缺少 <size> 信息: {xml_path}")
        img_w = float(size_el.findtext("width"))
        img_h = float(size_el.findtext("height"))

        lines = []
        for obj in root.findall("object"):
            name = obj.findtext("name")
            bnd = obj.find("bndbox")
            if bnd is None:
                continue
            xmin = float(bnd.findtext("xmin"))
            ymin = float(bnd.findtext("ymin"))
            xmax = float(bnd.findtext("xmax"))
            ymax = float(bnd.findtext("ymax"))

            # 归一化为 YOLO 格式
            box_w = xmax - xmin
            box_h = ymax - ymin
            center_x = xmin + box_w / 2
            center_y = ymin + box_h / 2

            cx = center_x / img_w
            cy = center_y / img_h
            bw = box_w / img_w
            bh = box_h / img_h

            # 第一列使用映射后的 id；若无映射则保留原始 name
            if name_to_id and name in name_to_id:
                first_col = str(name_to_id[name])
            else:
                first_col = name
            line = f"{first_col} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"
            lines.append(line)

        os.makedirs(os.path.dirname(txt_path), exist_ok=True)
        with open(txt_path, "w", encoding="utf-8") as f:
            for ln in lines:
                f.write(ln + "\n")

    def coco_to_voc(self, json_path, save_folder, id_to_name=None):
        """COCO JSON -> VOC XML（可选类别映射）"""
        if COCO is None:
            error_msg = (
                "未安装 pycocotools 或导入失败，无法进行 COCO 转换。\n\n"
                "请尝试以下方法：\n"
                "1. 安装: pip install pycocotools\n"
                "2. 如果安装失败，可能需要先安装: pip install Cython\n"
                "3. Windows 用户可能需要安装 Visual C++ 编译工具\n"
                "4. 或使用预编译版本: pip install pycocotools-windows"
            )
            raise RuntimeError(error_msg)

        if not os.path.exists(json_path):
            raise FileNotFoundError(f"COCO 标注文件不存在: {json_path}")

        # 检查文件是否为有效的 COCO JSON
        if not json_path.lower().endswith('.json'):
            raise ValueError(f"文件不是 JSON 格式: {json_path}。请确保选择 COCO 格式的标注文件（如 instances_train2017.json）")

        # 检查是否选择了错误的配置文件
        if os.path.basename(json_path) == 'config.json':
            raise ValueError("您选择了程序配置文件，请选择 COCO 格式的标注文件（如 instances_train2017.json）")

        try:
            # 尝试以 UTF-8 编码读取并验证 JSON 格式
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = f.read()
                # 验证是否为有效的 JSON
                import json
                parsed_data = json.loads(json_data)

                # 检查是否包含 COCO 必需的字段
                if 'images' not in parsed_data or 'annotations' not in parsed_data or 'categories' not in parsed_data:
                    raise ValueError(f"文件不是有效的 COCO JSON 格式: {json_path}")

            coco = COCO(json_path)
        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(f"COCO JSON 文件编码错误，请确保文件为 UTF-8 编码: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 文件格式错误: {e}")
        except Exception as e:
            raise Exception(f"加载 COCO 文件失败: {e}")
        cat_ids = coco.getCatIds()
        cats = coco.loadCats(cat_ids)
        cat_id_to_name = {c["id"]: c["name"] for c in cats}

        # 如果提供了 id_to_name，则优先使用映射名称
        def map_cat_name(cat_id):
            name = cat_id_to_name.get(cat_id, str(cat_id))
            if id_to_name and cat_id in id_to_name:
                return id_to_name[cat_id]
            return name

        img_ids = coco.getImgIds()
        for img_id in img_ids:
            img = coco.loadImgs(img_id)[0]
            filename = img["file_name"]
            width = img.get("width", 0)
            height = img.get("height", 0)
            size = {"width": width, "height": height, "depth": 3}

            ann_ids = coco.getAnnIds(imgIds=img_id, iscrowd=None)
            anns = coco.loadAnns(ann_ids)
            objs = []
            for ann in anns:
                cat_name = map_cat_name(ann["category_id"])
                # COCO bbox: [x, y, w, h]
                x, y, w, h = ann["bbox"]
                xmin = x
                ymin = y
                xmax = x + w
                ymax = y + h
                objs.append([cat_name, xmin, ymin, xmax, ymax])

            if objs:
                self.save_voc_xml(filename, size, objs, save_folder)

    def yolo_to_coco(self, image_folder, anno_folder, save_folder, id_to_name=None):
        """YOLO TXT -> COCO JSON（支持类别映射或 classes.txt）"""
        if not os.path.exists(image_folder):
            raise FileNotFoundError(f"图片文件夹不存在: {image_folder}")
        if not os.path.exists(anno_folder):
            raise FileNotFoundError(f"标注文件夹不存在: {anno_folder}")

        # 读取类别映射：优先使用界面输入，否则尝试 classes.txt
        if not id_to_name:
            classes_path = os.path.join(anno_folder, "classes.txt")
            if os.path.exists(classes_path):
                id_to_name = {}
                with open(classes_path, "r", encoding="utf-8") as f:
                    for idx, line in enumerate(f.readlines()):
                        name = line.strip()
                        if name:
                            id_to_name[idx] = name
        if not id_to_name:
            raise RuntimeError("未提供类别映射，且未在标注文件夹中找到 classes.txt，无法进行 YOLO->COCO 转换")

        # 构建 COCO 结构
        coco = {"images": [], "type": "instances", "annotations": [], "categories": []}
        # categories
        for k, v in id_to_name.items():
            coco["categories"].append({"supercategory": "none", "id": int(k), "name": v})

        def xywhn2xywh(bbox, size):
            # bbox: [cx, cy, w, h] (normalized), size: (h, w, c)
            bbox = list(map(float, bbox))
            h, w = float(size[0]), float(size[1])
            xmin = (bbox[0] - bbox[2] / 2.0) * w
            ymin = (bbox[1] - bbox[3] / 2.0) * h
            bw = bbox[2] * w
            bh = bbox[3] * h
            return [int(xmin), int(ymin), int(bw), int(bh)]

        image_id = 0
        annotation_id = 0

        # 建立图片索引
        images = {}
        for fname in os.listdir(image_folder):
            if fname.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                stem = os.path.splitext(fname)[0]
                images[stem] = fname

        for fname in os.listdir(anno_folder):
            if not fname.lower().endswith(".txt") or fname.startswith("classes"):
                continue
            stem = os.path.splitext(fname)[0]
            if stem not in images:
                # 没有对应图片，跳过
                continue
            img_path = os.path.join(image_folder, images[stem])
            try:
                w, h = self.get_image_size(img_path)
                size = (h, w, 3)
            except Exception as e:
                self.log(f"  ✗ 读取图片尺寸失败 {images[stem]}: {e}")
                continue

            image_id += 1
            coco["images"].append(
                {
                    "id": image_id,
                    "file_name": images[stem],
                    "width": w,
                    "height": h,
                    "license": None,
                    "flickr_url": None,
                    "coco_url": None,
                    "date_captured": "",
                }
            )

            txt_path = os.path.join(anno_folder, fname)
            with open(txt_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    cat_id = int(parts[0])
                    if cat_id not in id_to_name:
                        continue
                    bbox_xywh = xywhn2xywh(parts[1:5], size)
                    annotation_id += 1
                    seg = [
                        bbox_xywh[0],
                        bbox_xywh[1],
                        bbox_xywh[0],
                        bbox_xywh[1] + bbox_xywh[3],
                        bbox_xywh[0] + bbox_xywh[2],
                        bbox_xywh[1] + bbox_xywh[3],
                        bbox_xywh[0] + bbox_xywh[2],
                        bbox_xywh[1],
                    ]
                    coco["annotations"].append(
                        {
                            "segmentation": [seg],
                            "area": bbox_xywh[2] * bbox_xywh[3],
                            "iscrowd": 0,
                            "ignore": 0,
                            "image_id": image_id,
                            "bbox": bbox_xywh,
                            "category_id": cat_id,
                            "id": annotation_id,
                        }
                    )

        os.makedirs(save_folder, exist_ok=True)
        json_path = os.path.join(save_folder, "instances_converted.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(coco, f, ensure_ascii=False)

    # ---------- 批量转换 ----------
    def start_convert(self):
        anno_folder = self.anno_folder_var.get().strip()
        image_folder = self.image_folder_var.get().strip()
        save_folder = self.save_folder_var.get().strip()
        direction = self.direction_var.get()
        class_map_text = self.class_map_var.get().strip()
        id_to_name, name_to_id = self.parse_class_map(class_map_text)

        if not anno_folder or not os.path.exists(anno_folder):
            messagebox.showerror("错误", "请先选择有效的标注路径！（标注文件夹或 COCO JSON 文件）")
            return
        if not save_folder:
            messagebox.showerror("错误", "必须选择输出文件夹，以保护原始标注！")
            return

        os.makedirs(save_folder, exist_ok=True)

        self.log(f"开始转换，方向: {direction}，源标注: {anno_folder}，输出: {save_folder}")
        if direction in ("txt2xml", "yolo2coco"):
            self.log(f"图片文件夹: {image_folder}")
        if class_map_text:
            self.log(f"类别映射: {id_to_name}")

        # 特殊方向：COCO JSON -> VOC XML
        if direction == "coco2voc":
            # 运行时再次尝试导入 pycocotools（如果启动时导入失败）
            global COCO
            if COCO is None:
                try:
                    # 重新导入
                    import importlib
                    coco_module = importlib.import_module('pycocotools.coco')
                    COCO = coco_module.COCO
                    self.log("成功导入 pycocotools")
                except ImportError as e:
                    error_detail = str(e)
                    self.log(f"pycocotools 导入失败: {error_detail}")
                    messagebox.showerror(
                        "导入错误",
                        f"无法导入 pycocotools\n\n错误详情: {error_detail}\n\n"
                        "请检查：\n"
                        "1. 是否已安装: pip install pycocotools\n"
                        "2. Python 版本是否兼容\n"
                        "3. 是否需要安装依赖: pip install Cython numpy\n"
                        "4. Windows 用户可能需要 Visual C++ 编译工具\n"
                        "5. 或尝试: pip install pycocotools-windows"
                    )
                    return
                except Exception as e:
                    error_detail = str(e)
                    self.log(f"pycocotools 导入异常: {error_detail}")
                    messagebox.showerror("导入错误", f"导入 pycocotools 时出现异常:\n{error_detail}")
                    return
            
            try:
                self.coco_to_voc(anno_folder, save_folder, id_to_name=id_to_name)
                self.status_var.set("COCO -> VOC 转换完成")
                messagebox.showinfo("完成", "COCO -> VOC 转换完成！\n详情请查看日志。")
            except Exception as e:
                messagebox.showerror("错误", f"COCO -> VOC 转换失败: {e}")
                self.log(f"错误: {e}")
            return

        # 特殊方向：YOLO TXT -> COCO JSON
        if direction == "yolo2coco":
            if not image_folder or not os.path.exists(image_folder):
                messagebox.showerror("错误", "YOLO -> COCO 转换需要提供图片文件夹！")
                return
            try:
                self.yolo_to_coco(image_folder, anno_folder, save_folder, id_to_name=id_to_name)
                self.status_var.set("YOLO -> COCO 转换完成")
                messagebox.showinfo("完成", "YOLO -> COCO 转换完成！\n详情请查看日志。")
            except Exception as e:
                messagebox.showerror("错误", f"YOLO -> COCO 转换失败: {e}")
                self.log(f"错误: {e}")
            return

        # 其余方向：TXT <-> XML
        if direction == "txt2xml":
            if not image_folder or not os.path.exists(image_folder):
                messagebox.showerror("错误", "TXT -> XML 转换需要提供图片文件夹！")
                return

        success = 0
        failed = 0

        try:
            # 收集所有需要处理的文件
            files_to_process = []
            for fname in os.listdir(anno_folder):
                src_path = os.path.join(anno_folder, fname)
                if not os.path.isfile(src_path):
                    continue

                name, ext = os.path.splitext(fname)
                ext_lower = ext.lower()

                if direction == "txt2xml":
                    if ext_lower != ".txt":
                        continue
                    dst_path = os.path.join(save_folder, name + ".xml")
                    files_to_process.append((src_path, dst_path, direction, image_folder, id_to_name, name_to_id))
                elif direction == "xml2txt":
                    if ext_lower != ".xml":
                        continue
                    dst_path = os.path.join(save_folder, name + ".txt")
                    files_to_process.append((src_path, dst_path, direction, image_folder, id_to_name, name_to_id))

            # 使用多线程处理文件
            if files_to_process:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                # 确定线程池大小（根据CPU核心数和文件数量动态调整）
                import multiprocessing
                max_workers = min(multiprocessing.cpu_count(), len(files_to_process), 8)  # 最多8线程
                
                self.log(f"开始多线程处理，使用 {max_workers} 个线程")
                
                def process_file(args):
                    """处理单个文件的函数"""
                    src_path, dst_path, direction, image_folder, id_to_name, name_to_id = args
                    fname = os.path.basename(src_path)
                    try:
                        if direction == "txt2xml":
                            self.txt_to_xml_one(src_path, dst_path, image_folder, id_to_name=id_to_name)
                        elif direction == "xml2txt":
                            self.xml_to_txt_one(src_path, dst_path, name_to_id=name_to_id)
                        return (True, fname, os.path.basename(dst_path), None)
                    except Exception as e:
                        return (False, fname, None, str(e))
                
                # 创建线程池并执行
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 提交所有任务
                    futures = [executor.submit(process_file, args) for args in files_to_process]
                    
                    # 处理结果
                    for future in as_completed(futures):
                        success_flag, fname, dst_name, error = future.result()
                        if success_flag:
                            success += 1
                            self.log(f"  ✓ {fname} -> {dst_name}")
                        else:
                            failed += 1
                            self.log(f"  ✗ {fname}: {error}")
            else:
                self.log("没有找到需要处理的文件")

            self.status_var.set(f"转换完成: 成功 {success}, 失败 {failed}")
            messagebox.showinfo("完成", f"转换完成！\n成功: {success}\n失败: {failed}")
        except Exception as e:
            messagebox.showerror("错误", f"转换过程出错: {e}")
            self.log(f"错误: {e}")


def main():
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()


class DatasetSplitPage(ttk.Frame):
    """数据集分类页面（生成YAML配置文件和划分数据集）"""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # 数据集路径
        self.dataset_path = ""
        self.output_path = ""

        # 创建界面
        self.create_widgets()

    # ---------- 界面 ----------
    def create_widgets(self):
        """创建界面组件"""
        # 顶部导航栏
        nav_frame = ttk.Frame(self, style="Card.TFrame")
        nav_frame.pack(fill=tk.X, padx=10, pady=10)

        back_btn = ttk.Button(nav_frame, text="🏠 返回主页", command=self.app.show_main_page, style="Nav.TButton")
        back_btn.pack(side=tk.LEFT, padx=(0, 20))

        title_label = ttk.Label(nav_frame, text="📊 数据集分类", font=UIStyle.FONT_SUBTITLE,
                               foreground=UIStyle.PRIMARY_COLOR)
        title_label.pack(side=tk.LEFT)

        # 主框架
        main_frame = ttk.Frame(self, style="Card.TFrame", padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # 数据集路径选择
        dataset_frame = ttk.LabelFrame(main_frame, text="📂 数据集路径")
        dataset_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        dataset_frame.columnconfigure(1, weight=1)

        ttk.Label(dataset_frame, text="数据集根目录:").grid(row=0, column=0, padx=5, pady=5)
        self.dataset_path_var = tk.StringVar(value=self.dataset_path)
        dataset_entry = ttk.Entry(dataset_frame, textvariable=self.dataset_path_var, width=50)
        dataset_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(dataset_frame, text="浏览", command=self.browse_dataset).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(dataset_frame, text="建议结构: dataset/images/ 和 dataset/labels/").grid(row=1, column=1, padx=5, sticky=tk.W)

        # 输出路径选择
        output_frame = ttk.LabelFrame(main_frame, text="💾 输出路径")
        output_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="输出目录:").grid(row=0, column=0, padx=5, pady=5)
        self.output_path_var = tk.StringVar(value=self.output_path)
        output_entry = ttk.Entry(output_frame, textvariable=self.output_path_var, width=50)
        output_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(output_frame, text="浏览", command=self.browse_output).grid(row=0, column=2, padx=5, pady=5)

        # 数据集划分设置
        split_frame = ttk.LabelFrame(main_frame, text="✂️ 数据集划分")
        split_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # 划分比例输入
        ratio_frame = ttk.Frame(split_frame)
        ratio_frame.pack(fill=tk.X, pady=5)

        ttk.Label(ratio_frame, text="训练集比例:").grid(row=0, column=0, padx=5, pady=5)
        self.train_ratio_var = tk.StringVar(value="0.7")
        ttk.Entry(ratio_frame, textvariable=self.train_ratio_var, width=10).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(ratio_frame, text="验证集比例:").grid(row=0, column=2, padx=5, pady=5)
        self.val_ratio_var = tk.StringVar(value="0.2")
        ttk.Entry(ratio_frame, textvariable=self.val_ratio_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(ratio_frame, text="测试集比例:").grid(row=0, column=4, padx=5, pady=5)
        self.test_ratio_var = tk.StringVar(value="0.1")
        ttk.Entry(ratio_frame, textvariable=self.test_ratio_var, width=10).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(ratio_frame, text="(总和应为1.0)").grid(row=0, column=6, padx=5, pady=5)

        # 随机种子
        seed_frame = ttk.Frame(split_frame)
        seed_frame.pack(fill=tk.X, pady=5)

        ttk.Label(seed_frame, text="随机种子:").grid(row=0, column=0, padx=5, pady=5)
        self.seed_var = tk.StringVar(value="42")
        ttk.Entry(seed_frame, textvariable=self.seed_var, width=10).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(seed_frame, text="(用于重现相同划分结果)").grid(row=0, column=2, padx=5, pady=5)

        # 操作按钮
        button_frame = ttk.Frame(split_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="扫描数据集", command=self.scan_dataset).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(button_frame, text="生成配置文件", command=self.generate_config).grid(row=0, column=1, padx=10, pady=5)

        # 日志显示
        log_frame = ttk.LabelFrame(main_frame, text="📋 操作日志")
        log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD,
                                                 font=UIStyle.FONT_SMALL,
                                                 bg=UIStyle.BG_LIGHT,
                                                 fg=UIStyle.TEXT_PRIMARY,
                                                 padx=10, pady=10)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 状态栏
        self.status_var = tk.StringVar(value="✅ 就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel")
        status_bar.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

    # ---------- 路径选择 ----------
    def browse_dataset(self):
        folder = filedialog.askdirectory(initialdir=self.dataset_path or ".", title="选择数据集根目录")
        if folder:
            self.dataset_path = folder
            self.dataset_path_var.set(folder)
            self.log(f"选择数据集目录: {folder}")

    def browse_output(self):
        folder = filedialog.askdirectory(initialdir=self.output_path or ".", title="选择输出目录")
        if folder:
            self.output_path = folder
            self.output_path_var.set(folder)
            self.log(f"选择输出目录: {folder}")

    # ---------- 工具函数 ----------
    def log(self, msg: str):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def validate_ratios(self, train_ratio, val_ratio, test_ratio):
        """验证比例总和为1.0"""
        try:
            train = float(train_ratio)
            val = float(val_ratio)
            test = float(test_ratio)
            total = train + val + test
            if abs(total - 1.0) > 0.001:
                return False, f"比例总和应为1.0，当前为{total:.3f}"
            if train <= 0 or val <= 0 or test <= 0:
                return False, "所有比例都必须大于0"
            return True, (train, val, test)
        except ValueError as e:
            return False, f"比例格式错误: {e}"

    def scan_dataset(self):
        """扫描数据集结构"""
        dataset_path = self.dataset_path_var.get().strip()
        if not dataset_path or not os.path.exists(dataset_path):
            messagebox.showerror("错误", "请先选择有效的数据集目录！")
            return

        self.log("开始扫描数据集结构...")
        self.log(f"数据集路径: {dataset_path}")

        try:
            # 查找images和labels目录
            images_dir = None
            labels_dir = None

            for item in os.listdir(dataset_path):
                item_path = os.path.join(dataset_path, item)
                if os.path.isdir(item_path):
                    if item.lower() in ['images', 'image', 'img', 'imgs', 'pictures', 'photos']:
                        images_dir = item_path
                        self.log(f"找到图片目录: {item}")
                    elif item.lower() in ['labels', 'label', 'ann', 'annotations', 'txt']:
                        labels_dir = item_path
                        self.log(f"找到标注目录: {item}")

            # 如果没找到标准目录，尝试直接在根目录下找
            if not images_dir:
                for item in os.listdir(dataset_path):
                    item_path = os.path.join(dataset_path, item)
                    if os.path.isdir(item_path):
                        # 检查是否包含图片文件
                        for file in os.listdir(item_path)[:10]:  # 只检查前10个文件
                            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                                images_dir = item_path
                                self.log(f"检测到图片目录: {item}")
                                break

            if not labels_dir:
                for item in os.listdir(dataset_path):
                    item_path = os.path.join(dataset_path, item)
                    if os.path.isdir(item_path):
                        # 检查是否包含txt文件
                        for file in os.listdir(item_path)[:10]:
                            if file.lower().endswith('.txt'):
                                labels_dir = item_path
                                self.log(f"检测到标注目录: {item}")
                                break

            # 统计文件数量
            image_count = 0
            label_count = 0

            if images_dir:
                for file in os.listdir(images_dir):
                    if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        image_count += 1

            if labels_dir:
                for file in os.listdir(labels_dir):
                    if file.lower().endswith('.txt'):
                        label_count += 1

            self.log(f"图片文件数量: {image_count}")
            self.log(f"标注文件数量: {label_count}")

            # 检查是否有类别信息
            classes_file = os.path.join(labels_dir or dataset_path, 'classes.txt')
            if os.path.exists(classes_file):
                with open(classes_file, 'r', encoding='utf-8') as f:
                    classes = [line.strip() for line in f.readlines() if line.strip()]
                self.log(f"类别信息: {len(classes)}个类别")
                for i, cls in enumerate(classes):
                    self.log(f"  {i}: {cls}")
            else:
                self.log("未找到classes.txt文件，将从标注文件中提取类别信息")

            self.status_var.set(f"扫描完成 - 图片:{image_count}, 标注:{label_count}")

        except Exception as e:
            messagebox.showerror("错误", f"扫描数据集失败: {e}")
            self.log(f"错误: {e}")

    def generate_config(self):
        """生成YAML配置文件和划分数据集"""
        dataset_path = self.dataset_path_var.get().strip()
        output_path = self.output_path_var.get().strip()

        if not dataset_path or not os.path.exists(dataset_path):
            messagebox.showerror("错误", "请先选择有效的数据集目录！")
            return
        if not output_path:
            messagebox.showerror("错误", "请先选择输出目录！")
            return

        # 验证比例
        valid, result = self.validate_ratios(
            self.train_ratio_var.get(),
            self.val_ratio_var.get(),
            self.test_ratio_var.get()
        )
        if not valid:
            messagebox.showerror("错误", result)
            return

        train_ratio, val_ratio, test_ratio = result

        try:
            seed = int(self.seed_var.get())
        except ValueError:
            messagebox.showerror("错误", "随机种子必须是整数！")
            return

        self.log("开始生成配置文件和划分数据集...")
        self.log(f"训练集比例: {train_ratio}, 验证集比例: {val_ratio}, 测试集比例: {test_ratio}")
        self.log(f"随机种子: {seed}")

        try:
            import random
            import shutil

            # 查找images和labels目录
            images_dir = None
            labels_dir = None

            for item in os.listdir(dataset_path):
                item_path = os.path.join(dataset_path, item)
                if os.path.isdir(item_path):
                    if item.lower() in ['images', 'image', 'img', 'imgs']:
                        images_dir = item_path
                    elif item.lower() in ['labels', 'label', 'ann', 'annotations', 'txt']:
                        labels_dir = item_path

            # 如果没找到，使用根目录
            if not images_dir:
                images_dir = dataset_path
            if not labels_dir:
                labels_dir = dataset_path

            # 收集所有图片文件
            image_files = []
            for file in os.listdir(images_dir):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    image_files.append(file)

            if not image_files:
                raise ValueError(f"在 {images_dir} 中未找到图片文件")

            # 设置随机种子保证可重现
            random.seed(seed)
            random.shuffle(image_files)

            # 计算划分数量
            total = len(image_files)
            train_count = int(total * train_ratio)
            val_count = int(total * val_ratio)
            test_count = total - train_count - val_count

            # 划分数据集
            train_files = image_files[:train_count]
            val_files = image_files[train_count:train_count + val_count]
            test_files = image_files[train_count + val_count:]

            self.log(f"数据集划分: 总计{total}个文件")
            self.log(f"  训练集: {len(train_files)}个文件")
            self.log(f"  验证集: {len(val_files)}个文件")
            self.log(f"  测试集: {len(test_files)}个文件")

            # 提取类别信息
            classes = set()
            for file in image_files:
                stem = os.path.splitext(file)[0]
                txt_file = os.path.join(labels_dir, stem + '.txt')
                if os.path.exists(txt_file):
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                parts = line.split()
                                if len(parts) >= 1:
                                    classes.add(parts[0])  # 第一列可能是数字或字符串

            # 如果有classes.txt文件，使用它
            classes_file = os.path.join(labels_dir, 'classes.txt')
            if os.path.exists(classes_file):
                with open(classes_file, 'r', encoding='utf-8') as f:
                    classes = [line.strip() for line in f.readlines() if line.strip()]
                self.log(f"使用classes.txt文件: {len(classes)}个类别")
            else:
                # 尝试将类别转换为数字索引
                try:
                    classes = sorted(list(set(int(cls) for cls in classes if cls.isdigit())))
                    classes = [str(i) for i in range(len(classes))]  # 生成默认类别名
                    self.log(f"自动提取: {len(classes)}个类别")
                except:
                    classes = sorted(list(classes))
                    self.log(f"使用字符串类别: {len(classes)}个类别")

            # 创建输出目录结构
            self.log("创建输出目录结构...")
            train_images_dir = os.path.join(output_path, 'train', 'images')
            train_labels_dir = os.path.join(output_path, 'train', 'labels')
            val_images_dir = os.path.join(output_path, 'val', 'images')
            val_labels_dir = os.path.join(output_path, 'val', 'labels')
            test_images_dir = os.path.join(output_path, 'test', 'images')
            test_labels_dir = os.path.join(output_path, 'test', 'labels')

            os.makedirs(train_images_dir, exist_ok=True)
            os.makedirs(train_labels_dir, exist_ok=True)
            os.makedirs(val_images_dir, exist_ok=True)
            os.makedirs(val_labels_dir, exist_ok=True)
            os.makedirs(test_images_dir, exist_ok=True)
            os.makedirs(test_labels_dir, exist_ok=True)

            self.log("  ✓ 创建 train/images, train/labels")
            self.log("  ✓ 创建 val/images, val/labels")
            self.log("  ✓ 创建 test/images, test/labels")

            # 复制文件到对应的文件夹
            def copy_files(file_list, target_images_dir, target_labels_dir, split_name):
                copied_images = 0
                copied_labels = 0
                for file in file_list:
                    # 复制图片文件
                    src_image = os.path.join(images_dir, file)
                    dst_image = os.path.join(target_images_dir, file)
                    if os.path.exists(src_image):
                        shutil.copy2(src_image, dst_image)
                        copied_images += 1

                    # 复制对应的标签文件
                    stem = os.path.splitext(file)[0]
                    src_label = os.path.join(labels_dir, stem + '.txt')
                    dst_label = os.path.join(target_labels_dir, stem + '.txt')
                    if os.path.exists(src_label):
                        shutil.copy2(src_label, dst_label)
                        copied_labels += 1

                self.log(f"  ✓ {split_name}: 复制 {copied_images} 个图片, {copied_labels} 个标签")
                return copied_images, copied_labels

            self.log("复制文件到对应的文件夹...")
            train_img_count, train_lbl_count = copy_files(train_files, train_images_dir, train_labels_dir, "训练集")
            val_img_count, val_lbl_count = copy_files(val_files, val_images_dir, val_labels_dir, "验证集")
            test_img_count, test_lbl_count = copy_files(test_files, test_images_dir, test_labels_dir, "测试集")

            # 生成txt文件（包含完整图片路径）
            def write_file_list(file_list, filename, images_dir_path):
                with open(os.path.join(output_path, filename), 'w', encoding='utf-8') as f:
                    for file in file_list:
                        # 写入完整图片路径
                        img_path = os.path.join(images_dir_path, file).replace('\\', '/')
                        f.write(f"{img_path}\n")

            write_file_list(train_files, 'train.txt', train_images_dir)
            write_file_list(val_files, 'val.txt', val_images_dir)
            write_file_list(test_files, 'test.txt', test_images_dir)

            # 生成YAML配置文件
            output_path_norm = output_path.replace('\\', '/')

            # 构建YAML格式的类别名称列表
            names_yaml = '\n'.join([f"  {i}: {name}" for i, name in enumerate(classes)])

            yaml_content = f"""# YOLO 数据集配置文件
# 由数据过滤软件自动生成

# 数据集根目录
path: {output_path_norm}

# 训练/验证/测试路径
train: train/images
val: val/images
test: test/images

# 类别数量
nc: {len(classes)}

# 类别名称
names:
{names_yaml}
"""

            yaml_file = os.path.join(output_path, 'data.yaml')
            with open(yaml_file, 'w', encoding='utf-8') as f:
                f.write(yaml_content)

            self.log("生成文件:")
            self.log(f"  ✓ {os.path.join(output_path, 'train.txt')} ({len(train_files)} 个文件)")
            self.log(f"  ✓ {os.path.join(output_path, 'val.txt')} ({len(val_files)} 个文件)")
            self.log(f"  ✓ {os.path.join(output_path, 'test.txt')} ({len(test_files)} 个文件)")
            self.log(f"  ✓ {yaml_file}")

            self.status_var.set(f"配置生成完成 - {len(classes)}个类别")
            messagebox.showinfo("完成", f"配置文件生成完成！\n\n输出目录: {output_path}\n类别数量: {len(classes)}\n\n训练集: {train_img_count} 个图片, {train_lbl_count} 个标签\n验证集: {val_img_count} 个图片, {val_lbl_count} 个标签\n测试集: {test_img_count} 个图片, {test_lbl_count} 个标签")

        except Exception as e:
            messagebox.showerror("错误", f"生成配置文件失败: {e}")
            self.log(f"错误: {e}")


def main():
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()


class DatasetVisualizePage(ttk.Frame):
    """数据集展示页面（生成统计图表）"""
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # 路径变量
        self.image_path = ""
        self.label_path = ""

        # 统计数据
        self.stats_data = None

        # 多线程相关
        self.analysis_thread = None
        self.stop_analysis = False
        self.progress_queue = queue.Queue()

        # 创建界面
        self.create_widgets()

    # ---------- 界面 ----------
    def create_widgets(self):
        """创建界面组件"""
        # 顶部导航栏
        nav_frame = ttk.Frame(self, style="Card.TFrame")
        nav_frame.pack(fill=tk.X, padx=10, pady=10)

        back_btn = ttk.Button(nav_frame, text="🏠 返回主页", command=self.app.show_main_page, style="Nav.TButton")
        back_btn.pack(side=tk.LEFT, padx=(0, 20))

        title_label = ttk.Label(nav_frame, text="📈 数据集展示", font=UIStyle.FONT_SUBTITLE,
                               foreground=UIStyle.PRIMARY_COLOR)
        title_label.pack(side=tk.LEFT)

        # 主框架
        main_frame = ttk.Frame(self, style="Card.TFrame", padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # 数据集路径选择
        dataset_frame = ttk.LabelFrame(main_frame, text="📂 数据集路径")
        dataset_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        dataset_frame.columnconfigure(1, weight=1)

        # 图片路径
        ttk.Label(dataset_frame, text="🖼️ 图片文件夹:").grid(row=0, column=0, padx=5, pady=5)
        self.image_path_var = tk.StringVar(value=self.image_path)
        image_entry = ttk.Entry(dataset_frame, textvariable=self.image_path_var, width=50)
        image_entry.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(dataset_frame, text="浏览", command=lambda: self.browse_path("image")).grid(row=0, column=2, padx=5, pady=5)

        # 标签路径
        ttk.Label(dataset_frame, text="🏷️ 标签文件夹:").grid(row=1, column=0, padx=5, pady=5)
        self.label_path_var = tk.StringVar(value=self.label_path)
        label_entry = ttk.Entry(dataset_frame, textvariable=self.label_path_var, width=50)
        label_entry.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Button(dataset_frame, text="浏览", command=lambda: self.browse_path("label")).grid(row=1, column=2, padx=5, pady=5)

        # 分析按钮
        ttk.Button(dataset_frame, text="🚀 多线程分析", command=self.start_analysis_thread).grid(row=2, column=0, columnspan=3, pady=10)

        # 图表显示区域
        chart_frame = ttk.LabelFrame(main_frame, text="📈 统计图表")
        chart_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        chart_frame.columnconfigure(0, weight=1)
        chart_frame.rowconfigure(1, weight=1)

        # 绘图按钮区域
        button_frame = ttk.Frame(chart_frame)
        button_frame.grid(row=0, column=0, pady=5)

        ttk.Button(button_frame, text="🎨 开始绘图", command=self.start_plotting).grid(row=0, column=0, padx=10, pady=5)
        ttk.Button(button_frame, text="💾 下载图表", command=self.download_chart).grid(row=0, column=1, padx=10, pady=5)
        self.plot_status_label = ttk.Label(button_frame, text="请先选择数据集并分析", foreground=UIStyle.TEXT_SECONDARY)
        self.plot_status_label.grid(row=0, column=2, padx=10, pady=5)

        # 创建图表容器
        self.chart_container = ttk.Frame(chart_frame)
        self.chart_container.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)

        # 图表类型选择
        chart_type_frame = ttk.Frame(chart_frame)
        chart_type_frame.grid(row=2, column=0, pady=5)

        ttk.Label(chart_type_frame, text="图表类型:").pack(side=tk.LEFT, padx=5)
        self.chart_type_var = tk.StringVar(value="category_bar")
        chart_types = [
            ("🏷️ 类别分布柱状图", "category_bar"),
            ("🥧 目标尺寸统计饼图", "size_pie"),
            ("📈 bbox尺寸散点图", "bbox_scatter"),
            ("📊 bbox面积分布", "bbox_area"),
            ("🔥 bbox中心点热力图", "bbox_heatmap"),
            ("📊 每图目标数统计", "targets_per_image"),
            ("🖼️ 图片尺寸分布", "image_sizes")
        ]

        for text, value in chart_types:
            ttk.Radiobutton(chart_type_frame, text=text, variable=self.chart_type_var,
                          value=value, command=self.show_selected_chart).pack(side=tk.LEFT, padx=10)

        # 状态栏
        self.status_var = tk.StringVar(value="✅ 就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel")
        status_bar.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

    # ---------- 路径选择 ----------
    def browse_path(self, path_type):
        """选择路径"""
        folder = filedialog.askdirectory(title=f"选择{'图片' if path_type == 'image' else '标签'}文件夹")
        if folder:
            if path_type == "image":
                self.image_path = folder
                self.image_path_var.set(folder)
            else:
                self.label_path = folder
                self.label_path_var.set(folder)

            self.update_status()

    def update_status(self):
        """更新状态显示"""
        image_path = self.image_path_var.get().strip()
        label_path = self.label_path_var.get().strip()

        if image_path and label_path:
            self.status_var.set("✅ 路径已设置，点击'多线程分析'开始分析")
        elif image_path:
            self.status_var.set("📁 图片路径已设置，请设置标签路径")
        elif label_path:
            self.status_var.set("🏷️ 标签路径已设置，请设置图片路径")
        else:
            self.status_var.set("请设置图片和标签文件夹路径")

    def start_analysis_thread(self):
        """启动多线程分析"""
        image_path = self.image_path_var.get().strip()
        label_path = self.label_path_var.get().strip()

        if not image_path or not label_path:
            messagebox.showerror("错误", "请先设置图片和标签文件夹路径！")
            return

        if not os.path.exists(image_path):
            messagebox.showerror("错误", f"图片文件夹不存在: {image_path}")
            return

        if not os.path.exists(label_path):
            messagebox.showerror("错误", f"标签文件夹不存在: {label_path}")
            return

        # 检查可视化库
        if plt is None or sns is None or np is None:
            messagebox.showerror("错误", "未安装数据可视化库！\n请安装: pip install matplotlib numpy seaborn")
            return

        # 如果已有分析线程在运行，先停止
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.stop_analysis = True
            self.analysis_thread.join()
            self.stop_analysis = False

        # 启动新的分析线程
        self.stop_analysis = False
        self.analysis_thread = threading.Thread(target=self.analyze_dataset_thread, args=(image_path, label_path))
        self.analysis_thread.daemon = True
        self.analysis_thread.start()

        # 启动进度更新
        self.after(100, self.update_progress)

    def analyze_dataset_thread(self, image_path, label_path):
        """多线程分析数据集"""
        try:
            self.stats_data = self.analyze_dataset_multithreaded(image_path, label_path)
            self.progress_queue.put(("complete", self.stats_data))

        except Exception as e:
            self.progress_queue.put(("error", str(e)))

    def update_progress(self):
        """更新分析进度"""
        try:
            while True:
                msg_type, data = self.progress_queue.get_nowait()

                if msg_type == "progress":
                    self.status_var.set(f"🔍 正在分析... {data}")
                elif msg_type == "complete":
                    total_images = data['total_images']
                    total_targets = data['total_targets']
                    self.status_var.set(f"✅ 分析完成 - {total_images}张图片，{total_targets}个目标")
                    self.show_analysis_complete_message()
                elif msg_type == "error":
                    self.status_var.set("❌ 分析失败")
                    messagebox.showerror("错误", f"数据集分析失败: {data}")

        except queue.Empty:
            pass

        # 如果分析仍在进行，继续更新
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.after(100, self.update_progress)

    def analyze_dataset_multithreaded(self, image_path, label_path):
        """多线程分析数据集"""
        self.log("开始多线程分析数据集...")

        # 初始化统计数据
        stats = {
            'categories': {},
            'bbox_sizes': [],
            'bbox_areas': [],
            'bbox_centers': [],
            'targets_per_image': {},
            'image_sizes': [],
            'total_images': 0,
            'total_targets': 0
        }

        # 获取所有图片文件
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        image_files = []

        for filename in os.listdir(image_path):
            if os.path.splitext(filename)[1].lower() in image_extensions:
                image_files.append(filename)

        total_files = len(image_files)
        self.log(f"发现 {total_files} 张图片文件")

        # 多线程处理
        max_workers = min(8, max(1, total_files // 10))  # 根据文件数量调整线程数

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_file = {
                executor.submit(self.process_single_file, filename, image_path, label_path, stats): filename
                for filename in image_files
            }

            # 处理结果
            processed = 0
            for future in as_completed(future_to_file):
                if self.stop_analysis:
                    break

                try:
                    result = future.result()
                    if result:
                        stats['total_images'] += 1
                        processed += 1

                        # 更新进度
                        if processed % 10 == 0 or processed == total_files:
                            progress_msg = f"已处理 {processed}/{total_files} 张图片"
                            self.progress_queue.put(("progress", progress_msg))

                except Exception as e:
                    self.log(f"处理文件时出错: {e}")

        if not self.stop_analysis:
            self.log(f"多线程分析完成，共处理 {stats['total_images']} 张图片")
            stats['total_targets'] = sum(stats['categories'].values())

        return stats

    def process_single_file(self, filename, image_path, label_path, stats):
        """处理单个文件（线程安全）"""
        try:
            stem = os.path.splitext(filename)[0]
            img_path = os.path.join(image_path, filename)

            # 获取图片尺寸
            try:
                if Image:
                    with Image.open(img_path) as img:
                        img_w, img_h = img.size
                        stats['image_sizes'].append((img_w, img_h))
                else:
                    stats['image_sizes'].append((640, 480))
            except Exception as e:
                stats['image_sizes'].append((640, 480))

            # 读取对应的标注文件
            txt_file = os.path.join(label_path, stem + '.txt')
            target_count = 0

            if os.path.exists(txt_file):
                try:
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            parts = line.split()
                            if len(parts) >= 5:
                                category = parts[0]
                                cx, cy, bw, bh = map(float, parts[1:5])

                                # 统计类别
                                if category not in stats['categories']:
                                    stats['categories'][category] = 0
                                stats['categories'][category] += 1

                                # 计算实际bbox尺寸
                                bbox_w = bw * img_w
                                bbox_h = bh * img_h
                                bbox_area = bbox_w * bbox_h

                                stats['bbox_sizes'].append((bbox_w, bbox_h))
                                stats['bbox_areas'].append(bbox_area)
                                stats['bbox_centers'].append((cx, cy))

                                target_count += 1

                except Exception as e:
                    pass  # 忽略单个文件错误

            stats['targets_per_image'][stem] = target_count
            return True

        except Exception as e:
            return False

    # ---------- 工具函数 ----------
    def log(self, msg: str):
        """简化版日志输出（仅打印到控制台）"""
        print(f"[数据集展示] {msg}")

    def clear_charts(self):
        """清除图表容器"""
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        # 清理figure引用
        if hasattr(self, 'current_figure') and self.current_figure is not None:
            plt.close(self.current_figure)
            self.current_figure = None

    def show_selected_chart(self):
        """显示选中的图表"""
        if self.stats_data:
            self.generate_single_chart(self.chart_type_var.get())

    def start_plotting(self):
        """开始绘图"""
        if not self.stats_data:
            messagebox.showwarning("提示", "请先选择数据集并完成分析！")
            return

        self.plot_status_label.config(text="🎨 正在生成图表...", foreground=UIStyle.TEXT_SECONDARY)
        self.update()

        try:
            self.show_selected_chart()
            self.plot_status_label.config(text="✅ 图表生成完成", foreground=UIStyle.SECONDARY_COLOR)
        except Exception as e:
            messagebox.showerror("错误", f"图表生成失败: {e}")
            self.plot_status_label.config(text="❌ 图表生成失败", foreground=UIStyle.WARNING_COLOR)

    def download_chart(self):
        """下载当前图表"""
        if not hasattr(self, 'current_figure') or self.current_figure is None:
            messagebox.showwarning("提示", "请先生成图表后再下载！")
            return

        # 文件类型选项
        file_types = [
            ("PNG图片", "*.png"),
            ("JPEG图片", "*.jpg"),
            ("PDF文档", "*.pdf"),
            ("SVG矢量图", "*.svg"),
            ("所有文件", "*.*")
        ]

        # 获取当前图表类型作为默认文件名
        chart_type = self.chart_type_var.get()
        chart_names = {
            "category_bar": "类别分布柱状图",
            "size_pie": "目标尺寸统计饼图",
            "bbox_scatter": "bbox尺寸散点图",
            "bbox_area": "bbox面积分布",
            "bbox_heatmap": "bbox中心点热力图",
            "targets_per_image": "每图目标数统计",
            "image_sizes": "图片尺寸分布"
        }

        default_filename = chart_names.get(chart_type, "统计图表")

        # 打开保存对话框
        filename = filedialog.asksaveasfilename(
            title="保存图表",
            defaultextension=".png",
            filetypes=file_types,
            initialfile=f"{default_filename}.png"
        )

        if not filename:
            return  # 用户取消

        try:
            self.plot_status_label.config(text="💾 正在保存图表...", foreground=UIStyle.TEXT_SECONDARY)
            self.update()

            # 根据文件扩展名确定保存参数
            file_ext = os.path.splitext(filename)[1].lower()

            if file_ext == '.png':
                # PNG格式：高质量，支持透明
                self.current_figure.savefig(filename, dpi=300, bbox_inches='tight',
                                          facecolor='white', edgecolor='none')
            elif file_ext == '.jpg' or file_ext == '.jpeg':
                # JPEG格式：压缩但兼容性好
                self.current_figure.savefig(filename, dpi=300, bbox_inches='tight',
                                          facecolor='white', edgecolor='none',
                                          pil_kwargs={'quality': 95})
            elif file_ext == '.pdf':
                # PDF格式：矢量图，适合打印
                self.current_figure.savefig(filename, dpi=300, bbox_inches='tight',
                                          facecolor='white', edgecolor='none')
            elif file_ext == '.svg':
                # SVG格式：矢量图，可缩放
                self.current_figure.savefig(filename, dpi=300, bbox_inches='tight',
                                          facecolor='white', edgecolor='none')
            else:
                # 其他格式使用默认设置
                self.current_figure.savefig(filename, dpi=300, bbox_inches='tight',
                                          facecolor='white', edgecolor='none')

            self.plot_status_label.config(text=f"✅ 图表已保存: {os.path.basename(filename)}",
                                        foreground=UIStyle.SECONDARY_COLOR)

            # 显示成功消息
            messagebox.showinfo("保存成功",
                              f"图表已成功保存到:\n{filename}\n\n"
                              f"分辨率: 300 DPI\n"
                              f"格式: {file_ext.upper()[1:]}")

        except Exception as e:
            error_msg = f"保存图表失败: {e}"
            self.plot_status_label.config(text="❌ 保存失败", foreground=UIStyle.WARNING_COLOR)
            messagebox.showerror("错误", error_msg)

    def show_analysis_complete_message(self):
        """显示分析完成提示"""
        self.clear_charts()

        # 创建提示消息
        message_frame = ttk.Frame(self.chart_container)
        message_frame.pack(expand=True, fill=tk.BOTH)

        # 分析结果摘要
        summary_text = f"""📊 数据集分析完成！

统计信息：
• 图片数量：{self.stats_data['total_images']} 张
• 目标总数：{self.stats_data['total_targets']} 个
• 类别数量：{len(self.stats_data['categories'])} 个

🎯 类别分布：
"""
        for category, count in self.stats_data['categories'].items():
            summary_text += f"• 类别 {category}: {count} 个目标\n"

        summary_text += "\n请点击上方'开始绘图'按钮查看详细图表分析。"

        # 显示消息
        message_label = ttk.Label(message_frame, text=summary_text, justify=tk.LEFT,
                                 font=UIStyle.FONT_BODY, foreground=UIStyle.TEXT_PRIMARY)
        message_label.pack(pady=20, padx=20)

        self.plot_status_label.config(text="分析完成，点击'开始绘图'查看图表", foreground=UIStyle.PRIMARY_COLOR)

    # ---------- 数据分析 ----------
    def analyze_dataset_internal(self, dataset_path):
        """分析数据集并提取统计信息"""
        if not dataset_path or not os.path.exists(dataset_path):
            raise ValueError("数据集目录不存在")

        self.log("开始分析数据集...")
        self.log(f"数据集路径: {dataset_path}")

        try:
            # 查找images和labels目录
            images_dir = None
            labels_dir = None

            for item in os.listdir(dataset_path):
                item_path = os.path.join(dataset_path, item)
                if os.path.isdir(item_path):
                    if item.lower() in ['images', 'image', 'img', 'imgs']:
                        images_dir = item_path
                    elif item.lower() in ['labels', 'label', 'ann', 'annotations', 'txt']:
                        labels_dir = item_path

            if not images_dir:
                images_dir = dataset_path
            if not labels_dir:
                labels_dir = dataset_path

            self.log(f"图片目录: {images_dir}")
            self.log(f"标注目录: {labels_dir}")

            # 初始化统计数据
            stats = {
                'categories': {},  # 类别统计
                'bbox_sizes': [],  # bbox尺寸列表
                'bbox_areas': [],  # bbox面积列表
                'bbox_centers': [],  # bbox中心点列表
                'targets_per_image': {},  # 每图目标数
                'image_sizes': [],  # 图片尺寸列表
                'total_images': 0,
                'total_targets': 0
            }

            # 扫描图片和标注文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

            for filename in os.listdir(images_dir):
                if os.path.splitext(filename)[1].lower() in image_extensions:
                    img_path = os.path.join(images_dir, filename)
                    stem = os.path.splitext(filename)[0]

                    # 获取图片尺寸
                    try:
                        if Image:
                            with Image.open(img_path) as img:
                                img_w, img_h = img.size
                                stats['image_sizes'].append((img_w, img_h))
                        else:
                            # 如果没有PIL，使用默认尺寸
                            stats['image_sizes'].append((640, 480))
                    except Exception as e:
                        self.log(f"警告: 无法读取图片尺寸 {filename}: {e}")
                        stats['image_sizes'].append((640, 480))

                    # 读取对应的标注文件
                    txt_file = os.path.join(labels_dir, stem + '.txt')
                    target_count = 0

                    if os.path.exists(txt_file):
                        try:
                            with open(txt_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if not line:
                                        continue

                                    parts = line.split()
                                    if len(parts) >= 5:
                                        category = parts[0]
                                        cx, cy, bw, bh = map(float, parts[1:5])

                                        # 统计类别
                                        if category not in stats['categories']:
                                            stats['categories'][category] = 0
                                        stats['categories'][category] += 1

                                        # 计算实际bbox尺寸
                                        bbox_w = bw * img_w
                                        bbox_h = bh * img_h
                                        bbox_area = bbox_w * bbox_h

                                        stats['bbox_sizes'].append((bbox_w, bbox_h))
                                        stats['bbox_areas'].append(bbox_area)
                                        stats['bbox_centers'].append((cx, cy))

                                        target_count += 1
                                        stats['total_targets'] += 1

                        except Exception as e:
                            self.log(f"警告: 读取标注文件失败 {txt_file}: {e}")

                    stats['targets_per_image'][stem] = target_count
                    stats['total_images'] += 1

            self.stats_data = stats

            self.log("\n📊 数据集分析完成:")
            self.log(f"   图片数量: {stats['total_images']}")
            self.log(f"   目标总数: {stats['total_targets']}")
            self.log(f"   类别数量: {len(stats['categories'])}")
            self.log(f"   类别详情: {stats['categories']}")

            self.status_var.set(f"分析完成 - {stats['total_images']}张图片，{stats['total_targets']}个目标")

        except Exception as e:
            messagebox.showerror("错误", f"数据集分析失败: {e}")
            self.log(f"错误: {e}")

    # ---------- 图表生成 ----------
    def generate_single_chart(self, chart_type):
        """生成单个图表"""
        if not self.stats_data:
            return

        # 清除现有图表
        self.clear_charts()

        # 设置matplotlib样式和中文字体
        plt.style.use('default')
        sns.set_palette("husl")

        # 设置中文字体支持
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False

        # 创建figure
        fig, ax = plt.subplots(figsize=(10, 6), dpi=100)

        if chart_type == "category_bar":
            # 类别分布柱状图
            categories = list(self.stats_data['categories'].keys())
            counts = list(self.stats_data['categories'].values())

            bars = ax.bar(categories, counts, color=UIStyle.PRIMARY_COLOR, alpha=0.7)

            # 添加数值标签
            for bar, count in zip(bars, counts):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                       f'{count}', ha='center', va='bottom', fontweight='bold')

            ax.set_title('类别分布统计', fontsize=14, fontweight='bold', pad=20)
            ax.set_xlabel('类别', fontsize=12)
            ax.set_ylabel('数量', fontsize=12)
            ax.grid(True, alpha=0.3)

        elif chart_type == "size_pie":
            # 目标尺寸统计饼图
            areas = np.array(self.stats_data['bbox_areas'])

            # 定义尺寸类别
            small_threshold = 1000  # 小目标：面积 < 1000
            medium_threshold = 10000  # 中目标：1000 <= 面积 < 10000

            small_count = np.sum(areas < small_threshold)
            medium_count = np.sum((areas >= small_threshold) & (areas < medium_threshold))
            large_count = np.sum(areas >= medium_threshold)

            sizes = [small_count, medium_count, large_count]
            labels = ['小目标', '中目标', '大目标']
            colors = [UIStyle.SECONDARY_COLOR, UIStyle.PRIMARY_COLOR, UIStyle.ACCENT_COLOR]

            # 只显示非零的类别
            filtered_sizes = []
            filtered_labels = []
            filtered_colors = []
            for size, label, color in zip(sizes, labels, colors):
                if size > 0:
                    filtered_sizes.append(size)
                    filtered_labels.append(f'{label} ({size})')  # 移除换行符，避免重叠
                    filtered_colors.append(color)

            wedges, texts, autotexts = ax.pie(filtered_sizes, labels=None,  # 先不显示标签
                                             colors=filtered_colors, autopct='%1.1f%%',
                                             startangle=90, shadow=True,
                                             textprops={'fontsize': 10, 'fontweight': 'bold', 'color': 'white'})

            # 设置百分比文本的样式
            for autotext in autotexts:
                autotext.set_fontsize(10)
                autotext.set_fontweight('bold')
                autotext.set_color('white')

            # 添加图例来显示标签，避免重叠
            if filtered_labels:
                ax.legend(filtered_labels, title="目标尺寸", loc="center left", bbox_to_anchor=(1, 0.5),
                         fontsize=9, title_fontsize=10)

            ax.set_title('目标尺寸分布', fontsize=14, fontweight='bold', pad=20)
            ax.axis('equal')

        elif chart_type == "bbox_scatter":
            # bbox尺寸散点图
            sizes = np.array(self.stats_data['bbox_sizes'])
            if len(sizes) > 0:
                widths, heights = sizes[:, 0], sizes[:, 1]

                scatter = ax.scatter(widths, heights, alpha=0.6, color=UIStyle.PRIMARY_COLOR, s=50)

                ax.set_title('bbox尺寸分布散点图', fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel('宽度 (像素)', fontsize=12)
                ax.set_ylabel('高度 (像素)', fontsize=12)
                ax.grid(True, alpha=0.3)

                # 添加对角线
                max_val = max(ax.get_xlim()[1], ax.get_ylim()[1])
                ax.plot([0, max_val], [0, max_val], 'r--', alpha=0.5, label='正方形')
                ax.legend()

        elif chart_type == "bbox_area":
            # bbox面积分布直方图
            areas = np.array(self.stats_data['bbox_areas'])
            if len(areas) > 0:
                ax.hist(areas, bins=30, alpha=0.7, color=UIStyle.PRIMARY_COLOR, edgecolor='black')

                ax.set_title('bbox面积分布直方图', fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel('面积 (像素²)', fontsize=12)
                ax.set_ylabel('频次', fontsize=12)
                ax.grid(True, alpha=0.3)

        elif chart_type == "bbox_heatmap":
            # bbox中心点热力图
            centers = np.array(self.stats_data['bbox_centers'])
            if len(centers) > 0:
                cx, cy = centers[:, 0], centers[:, 1]

                # 创建2D直方图
                hist, xedges, yedges = np.histogram2d(cx, cy, bins=20, range=[[0, 1], [0, 1]])

                # 显示热力图
                im = ax.imshow(hist.T, origin='lower', extent=[0, 1, 0, 1],
                              cmap='YlOrRd', aspect='auto')

                ax.set_title('bbox中心点热力图', fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel('归一化X坐标', fontsize=12)
                ax.set_ylabel('归一化Y坐标', fontsize=12)

                # 添加colorbar
                plt.colorbar(im, ax=ax, label='密度')

        elif chart_type == "targets_per_image":
            # 每图目标数统计直方图
            target_counts = list(self.stats_data['targets_per_image'].values())
            if target_counts:
                ax.hist(target_counts, bins=range(max(target_counts)+2), alpha=0.7,
                       color=UIStyle.PRIMARY_COLOR, edgecolor='black', align='left')

                ax.set_title('每图目标数统计直方图', fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel('目标数量', fontsize=12)
                ax.set_ylabel('图片数量', fontsize=12)
                ax.grid(True, alpha=0.3)

        elif chart_type == "image_sizes":
            # 图片尺寸分布
            img_sizes = np.array(self.stats_data['image_sizes'])
            if len(img_sizes) > 0:
                widths, heights = img_sizes[:, 0], img_sizes[:, 1]

                scatter = ax.scatter(widths, heights, alpha=0.6, color=UIStyle.PRIMARY_COLOR, s=50)

                ax.set_title('图片尺寸分布', fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel('宽度 (像素)', fontsize=12)
                ax.set_ylabel('高度 (像素)', fontsize=12)
                ax.grid(True, alpha=0.3)

                # 添加尺寸信息
                avg_w, avg_h = np.mean(widths), np.mean(heights)
                ax.text(0.02, 0.98, f'平均尺寸: {avg_w:.0f}×{avg_h:.0f}',
                       transform=ax.transAxes, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # 调整布局
        plt.tight_layout()

        # 保存当前figure引用用于下载
        self.current_figure = fig

        # 将matplotlib图表嵌入到tkinter中
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 注意：不关闭figure，保持引用用于下载功能


def main():
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
