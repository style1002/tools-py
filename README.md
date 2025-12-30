# Tools Project

这是一个用于存放各种 Python 脚本的杂项项目。

## 项目结构

```
.
├── src/                # 源代码目录
│   ├── scripts/        # 所有脚本的主目录
│   │   ├── stock/      # 股票相关脚本
│   │   │   ├── get_stock_holder.py
│   │   │   ├── get_stock_price.py
│   │   │   └── get_stock_real-time_price.py
│   │   ├── examples/   # 示例脚本
│   │   │   └── script_Hi_PyCharm.py
│   │   └── [其他分类]/ # 将来可以添加更多分类，如 web/, database/, api/ 等
│   │
│   └── utils/          # 工具函数库
│       ├── get_phone_location.py
│       └── print_schema_fields.py
│
├── out/                # 输出目录（脚本生成的文件）
│   └── [按脚本分类的输出文件]
│
├── requirements.txt    # Python 依赖
└── README.md          # 项目说明
```

## 目录说明

- **src/scripts/**: 存放所有可执行的脚本文件
  - **stock/**: 股票数据处理相关脚本
  - **examples/**: 示例和测试脚本
  - 将来可以根据需要添加新的分类目录（如 `web/`, `database/`, `api/` 等）

- **src/utils/**: 存放可复用的工具函数和辅助模块

- **out/**: 输出目录，存放所有脚本生成的文件
  - 位于项目根目录（与 `src/` 同级）
  - 各脚本的输出文件按功能分类存放（如 `out/stock_01341/`）
  - 此目录已在 `.gitignore` 中忽略，不会提交到版本控制

## 使用说明

1. 添加新的脚本时，请根据脚本的功能分类，放入 `scripts/` 下对应的子目录
2. 如果是通用工具函数，请放入 `utils/` 目录
3. 如果现有分类都不合适，可以创建新的分类目录

## 依赖安装

```bash
pip install -r requirements.txt
```

