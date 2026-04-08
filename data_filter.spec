# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(SPEC))

# PyInstaller分析配置
a = Analysis(
    ['data_filter.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        # 包含README和requirements文件
        ('README.md', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        # tkinter相关
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.scrolledtext',

        # matplotlib相关
        'matplotlib',
        'matplotlib.pyplot',
        'matplotlib.backends.backend_tkagg',
        'matplotlib.figure',
        'matplotlib.backends._backend_tk',
        'matplotlib.backends.backend_agg',

        # PIL相关
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',

        # pycocotools相关
        'pycocotools',
        'pycocotools.coco',

        # numpy相关
        'numpy',
        'numpy.core.multiarray',
        'numpy.core.umath',

        # seaborn相关
        'seaborn',

        # 其他可能的隐藏导入
        'scipy.sparse.csgraph._validation',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不必要的模块以减小体积
        'tkinter.test',
        'test',
        'unittest',
        'pdb',
        'pydoc',
        # 排除大型库
        'tensorflow',
        'torch',
        'torchvision',
        'transformers',
        'keras',
        'sklearn',
        'nltk',
        'cv2',
        'dask',
        'distributed',
        'h5py',
        'botocore',
        'fsspec',
        'pyarrow',
        'llvmlite',
        'numba',
        'lxml',
        'QtCore',
        'QtGui',
        'QtWidgets',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# 过滤掉不需要的二进制文件
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='数据过滤软件',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以后续添加图标
)
